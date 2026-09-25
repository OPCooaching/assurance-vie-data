from __future__ import annotations

import csv
import os
from datetime import date, timedelta
from pathlib import Path

import pandas as pd
import yfinance as yf

MAP = Path("config/symbol_map.csv")
OUT = Path("data/prices/daily.csv")
BATCH = 40
BOOTSTRAP_PERIOD = "5y"
UPDATE_PERIOD = "7d"
MIN_BOOTSTRAP_SPAN_DAYS = 5 * 365 - 14
METADATA_MAX_AGE_DAYS = 30
PRICE_COLUMNS = [
    "date", "asset_id", "symbol", "close_raw", "close_native", "close_eur",
    "close", "volume", "provider", "quote_currency", "exchange",
    "quality_status",
]


def load_map():
    with MAP.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def save_map(rows):
    fields = [
        "asset_id", "isin", "symbol", "provider", "status", "last_checked",
        "quote_currency", "exchange", "currency_status", "metadata_checked",
        "history_status", "history_start", "history_end", "history_checked",
        "notes",
    ]
    with MAP.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows([{field: row.get(field, "") for field in fields} for row in rows])


def metadata_is_stale(row):
    if os.getenv("REFRESH_MARKET_METADATA") == "1":
        return True
    if not row.get("quote_currency") or not row.get("currency_status"):
        return True
    try:
        return date.today() - date.fromisoformat(row["metadata_checked"]) > timedelta(days=METADATA_MAX_AGE_DAYS)
    except (TypeError, ValueError):
        return True


def refresh_quote_metadata(rows):
    """Verify the actual Yahoo trading currency before accepting prices.

    A fund share class and the exchange listing are different things: an ETF
    may be available in EUR, GBP or CHF.  Yahoo history metadata describes the
    latter, which is the currency that must be converted for performance work.
    """
    today = date.today().isoformat()
    for row in rows:
        if row.get("status") != "resolved" or not row.get("symbol") or not metadata_is_stale(row):
            continue
        try:
            ticker = yf.Ticker(row["symbol"])
            metadata = ticker.get_history_metadata() or {}
            currency = str(metadata.get("currency") or "").upper()
            exchange = metadata.get("exchangeName") or metadata.get("exchange") or row.get("exchange") or ""
            row["metadata_checked"] = today
            if len(currency) == 3 and currency.isalpha():
                row["quote_currency"] = currency
                row["exchange"] = str(exchange)
                row["currency_status"] = "verified_eur" if currency == "EUR" else "verified_fx_to_eur"
            else:
                row["currency_status"] = "unverified"
                row["notes"] = "Yahoo quote currency unavailable"
        except Exception as exc:
            row["metadata_checked"] = today
            row["currency_status"] = "unverified"
            row["notes"] = f"Yahoo metadata error: {type(exc).__name__}"


def resolved_rows(rows):
    return [
        row for row in rows
        if row.get("status") == "resolved" and row.get("symbol")
        and row.get("currency_status") in {"verified_eur", "verified_fx_to_eur"}
    ]


def download_batch(symbols, period):
    return yf.download(
        tickers=symbols,
        period=period,
        interval="1d",
        auto_adjust=False,
        progress=False,
        group_by="ticker",
        threads=True,
    )


def extract(data, symbol):
    if data.empty:
        return pd.DataFrame()
    if isinstance(data.columns, pd.MultiIndex):
        if symbol not in data.columns.get_level_values(0):
            return pd.DataFrame()
        x = data[symbol].copy()
    else:
        x = data.copy()
    if "Close" not in x:
        return pd.DataFrame()
    # Yahoo's unadjusted close is retained for audit.  Indicators and
    # backtests use the adjusted close: split/dividend corrections otherwise
    # create reversible one-day jumps such as XDEB.DE on 2025-10-24.
    adjusted = x["Adj Close"] if "Adj Close" in x else x["Close"]
    out = pd.DataFrame({
        "date": pd.to_datetime(x.index).date.astype(str),
        "close_raw": pd.to_numeric(x["Close"], errors="coerce"),
        "close_native": pd.to_numeric(adjusted, errors="coerce"),
        "volume": pd.to_numeric(x.get("Volume"), errors="coerce"),
    })
    return out.dropna(subset=["close_native"])


def needs_bootstrap(existing: pd.DataFrame, row: dict[str, str]) -> bool:
    asset_id = row["asset_id"]
    if existing.empty or not set(PRICE_COLUMNS).issubset(existing.columns):
        return True
    g = existing.loc[existing["asset_id"] == asset_id]
    if g.empty:
        return True
    dates = pd.to_datetime(g["date"], errors="coerce").dropna()
    if dates.empty:
        return True
    span = (dates.max() - dates.min()).days
    # A product that genuinely launched recently gets ordinary daily updates,
    # not an expensive five-year retry at every workflow run.
    return span < MIN_BOOTSTRAP_SPAN_DAYS and not row.get("history_status")


def refresh_history_status(rows, prices):
    """Record whether Yahoo delivered five years, a shorter valid history, or none."""
    today = date.today().isoformat()
    by_asset = {asset_id: group for asset_id, group in prices.groupby("asset_id")}
    for row in rows:
        if row.get("status") != "resolved" or not row.get("symbol"):
            continue
        group = by_asset.get(row["asset_id"])
        row["history_checked"] = today
        if group is None or group.empty:
            row["history_status"] = "unavailable"
            row["history_start"] = ""
            row["history_end"] = ""
            continue
        dates = pd.to_datetime(group["date"], errors="coerce").dropna()
        row["history_start"] = dates.min().date().isoformat()
        row["history_end"] = dates.max().date().isoformat()
        row["history_status"] = (
            "five_years" if (dates.max() - dates.min()).days >= MIN_BOOTSTRAP_SPAN_DAYS
            else "shorter_history"
        )


def extract_fx(data, symbol):
    if data.empty:
        return pd.Series(dtype=float)
    if isinstance(data.columns, pd.MultiIndex):
        if symbol not in data.columns.get_level_values(0):
            return pd.Series(dtype=float)
        data = data[symbol]
    if "Close" not in data:
        return pd.Series(dtype=float)
    result = pd.to_numeric(data["Close"], errors="coerce")
    result.index = pd.to_datetime(result.index).date.astype(str)
    return result.dropna()


def fx_rates_to_eur(currencies, period):
    foreign = sorted({currency for currency in currencies if currency != "EUR"})
    if not foreign:
        return {}
    symbols = [f"EUR{currency}=X" for currency in foreign]
    data = download_batch(symbols, period)
    rates = {}
    for currency, symbol in zip(foreign, symbols):
        series = extract_fx(data, symbol)
        if series.empty:
            raise RuntimeError(f"Missing EUR conversion history for {currency} ({symbol}).")
        rates[currency] = series
    return rates


def normalise_to_eur(parts, period):
    if not parts:
        return []
    currencies = [part["quote_currency"].iloc[0] for part in parts]
    fx = fx_rates_to_eur(currencies, period)
    result = []
    for part in parts:
        currency = part["quote_currency"].iloc[0]
        if currency == "EUR":
            part["close_eur"] = part["close_native"]
        else:
            rates = fx[currency].reindex(part["date"]).ffill().bfill()
            if rates.isna().any() or (rates <= 0).any():
                raise RuntimeError(f"Invalid EUR conversion history for {currency}.")
            # EURUSD=X means USD for one EUR, hence a USD quote is divided by it.
            part["close_eur"] = part["close_native"].to_numpy() / rates.to_numpy()
        # `close` remains as a compatibility alias, but it is now explicitly
        # EUR-normalised.  Consumers below require close_eur by name.
        part["close"] = part["close_eur"]
        result.append(part)
    return result


def clean_reversible_ticks(part):
    """Neutralise provider ticks, not ordinary volatile market sessions.

    A candidate must reverse almost entirely on the following quote and carry
    either zero reported volume or a move of at least 50%. This deliberately
    leaves high-volume, smaller reversals (for example biotech shares) intact.
    The unadjusted provider close remains in ``close_raw`` for audit.
    """
    part = part.sort_values("date").copy()
    close = part["close_native"]
    previous = close.shift(1)
    following = close.shift(-1)
    up = close / previous - 1.0
    down = following / close - 1.0
    round_trip = following / previous - 1.0
    volume = pd.to_numeric(part["volume"], errors="coerce").fillna(0.0)
    candidate = (
        (up.abs() >= 0.12)
        & (down.abs() >= 0.10)
        & (round_trip.abs() <= 0.02)
        & ((volume == 0) | (up.abs() >= 0.50) | (down.abs() >= 0.50))
    )
    part["quality_status"] = "standard"
    for index in part.index[candidate]:
        # The geometric midpoint preserves the surrounding two-day return and
        # avoids inventing a directional gain or loss at the faulty quote.
        part.loc[index, "close_native"] = (previous.loc[index] * following.loc[index]) ** 0.5
        part.loc[index, "quality_status"] = "reversible_tick_neutralised"
    return part


def neutralise_merged_eur_ticks(frame):
    """Neutralise a provider outlier detected only after all EUR rows are merged.

    Download batches can cut a three-day reversal at their edge. Rechecking
    the final EUR-normalised table closes that gap while preserving close_raw
    as the audit record. Only near-complete, high-magnitude reversals with
    zero volume (or a 50%+ move) are changed.
    """
    frame = frame.sort_values(["asset_id", "date"]).copy()
    neutralised = 0
    for _, group in frame.groupby("asset_id", sort=False):
        close = pd.to_numeric(group["close_eur"], errors="coerce")
        previous = close.shift(1)
        following = close.shift(-1)
        up = close / previous - 1.0
        down = following / close - 1.0
        round_trip = following / previous - 1.0
        volume = pd.to_numeric(group["volume"], errors="coerce").fillna(0.0)
        candidate = (
            (up.abs() >= 0.12)
            & (down.abs() >= 0.10)
            & (round_trip.abs() <= 0.02)
            & ((volume == 0) | (up.abs() >= 0.50) | (down.abs() >= 0.50))
        )
        for index in group.index[candidate]:
            old_eur = float(frame.loc[index, "close_eur"])
            new_eur = float((previous.loc[index] * following.loc[index]) ** 0.5)
            if not old_eur > 0:
                continue
            ratio = new_eur / old_eur
            frame.loc[index, "close_eur"] = new_eur
            frame.loc[index, "close"] = new_eur
            frame.loc[index, "close_native"] = float(frame.loc[index, "close_native"]) * ratio
            frame.loc[index, "quality_status"] = "reversible_tick_neutralised"
            neutralised += 1
    return frame, neutralised


def fetch_rows(rows, period):
    parts = []
    for i in range(0, len(rows), BATCH):
        batch = rows[i:i+BATCH]
        symbols = list(dict.fromkeys(r["symbol"] for r in batch))
        try:
            data = download_batch(symbols, period)
        except Exception:
            continue
        for r in batch:
            x = extract(data, r["symbol"])
            if x.empty:
                continue
            x["asset_id"] = r["asset_id"]
            x["symbol"] = r["symbol"]
            x["provider"] = r.get("provider") or "yahoo"
            x["quote_currency"] = r["quote_currency"]
            x["exchange"] = r.get("exchange") or ""
            parts.append(clean_reversible_ticks(x))
    return normalise_to_eur(parts, period)


def main():
    map_rows = load_map()
    refresh_quote_metadata(map_rows)
    save_map(map_rows)
    rows = resolved_rows(map_rows)
    unresolved_currency = [
        row for row in map_rows
        if row.get("status") == "resolved" and row.get("symbol") and row not in rows
    ]
    if unresolved_currency:
        raise SystemExit(
            f"Refusing mixed-currency update: {len(unresolved_currency)} resolved symbol(s) have unverified quote currency."
        )
    OUT.parent.mkdir(parents=True, exist_ok=True)

    existing = pd.read_csv(OUT) if OUT.exists() else pd.DataFrame()

    bootstrap_rows = [r for r in rows if needs_bootstrap(existing, r)]
    update_rows = [r for r in rows if r not in bootstrap_rows]

    new_parts = []
    if bootstrap_rows:
        print(f"Bootstrapping {len(bootstrap_rows)} asset(s) with {BOOTSTRAP_PERIOD} history.")
        new_parts.extend(fetch_rows(bootstrap_rows, BOOTSTRAP_PERIOD))
    if update_rows:
        print(f"Updating {len(update_rows)} asset(s) with {UPDATE_PERIOD}.")
        new_parts.extend(fetch_rows(update_rows, UPDATE_PERIOD))

    if not new_parts:
        print("No market data downloaded.")
        return

    new = pd.concat(new_parts, ignore_index=True)[PRICE_COLUMNS]

    # A migration re-downloads every resolved asset.  Do not retain a legacy
    # native-currency row if a normalised replacement was not obtained.
    bootstrap_ids = {row["asset_id"] for row in bootstrap_rows}
    kept = existing.loc[~existing["asset_id"].isin(bootstrap_ids)].copy() if not existing.empty else existing
    all_data = pd.concat([kept, new], ignore_index=True) if not kept.empty else new
    all_data = all_data.drop_duplicates(["date", "asset_id"], keep="last")
    all_data, neutralised = neutralise_merged_eur_ticks(all_data)
    all_data = all_data.sort_values(["date", "asset_id"])
    all_data.to_csv(OUT, index=False)
    refresh_history_status(map_rows, all_data)
    save_map(map_rows)

    print(
        f"Saved {len(all_data)} price rows for "
        f"{all_data.asset_id.nunique()} assets; {neutralised} merged EUR tick(s) neutralised."
    )


if __name__ == "__main__":
    main()
