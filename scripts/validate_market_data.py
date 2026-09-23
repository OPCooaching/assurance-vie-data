from __future__ import annotations

"""Quality gate for shared market data before any strategy is recomputed."""

from pathlib import Path

import pandas as pd


PRICES = Path("data/prices/daily.csv")
ANOMALIES = Path("data/quality/reversible_raw_ticks.csv")
REQUIRED = {
    "date", "asset_id", "symbol", "close_raw", "close_native", "close_eur",
    "close", "volume", "provider", "quote_currency", "exchange",
    "quality_status",
}


def reversible_ticks(frame: pd.DataFrame, column: str, suspicious_only: bool = False) -> pd.DataFrame:
    rows = []
    for asset_id, group in frame.groupby("asset_id", sort=True):
        group = group.sort_values("date").copy()
        prev = group[column].shift(1)
        current = group[column]
        following = group[column].shift(-1)
        up = current / prev - 1.0
        down = following / current - 1.0
        round_trip = following / prev - 1.0
        mask = (up.abs() >= 0.12) & (down.abs() >= 0.10) & (round_trip.abs() <= 0.02)
        if suspicious_only:
            volume = pd.to_numeric(group["volume"], errors="coerce").fillna(0.0)
            mask &= (volume == 0) | (up.abs() >= 0.50) | (down.abs() >= 0.50)
        for _, row in group.loc[mask].iterrows():
            index = row.name
            rows.append({
                "asset_id": asset_id,
                "symbol": row["symbol"],
                "date": row["date"],
                "price_column": column,
                "one_day_return_pct": round(float(up.loc[index]) * 100, 6),
                "next_day_return_pct": round(float(down.loc[index]) * 100, 6),
                "two_day_return_pct": round(float(round_trip.loc[index]) * 100, 6),
            })
    return pd.DataFrame(rows)


def main():
    if not PRICES.exists():
        raise SystemExit("Market-data quality gate: data/prices/daily.csv is missing.")

    prices = pd.read_csv(PRICES)
    missing = REQUIRED - set(prices.columns)
    if missing:
        raise SystemExit(f"Market-data quality gate: missing normalised fields: {sorted(missing)}")
    essential = REQUIRED - {"volume", "exchange"}
    if prices.empty or prices[list(essential)].isna().any().any():
        raise SystemExit("Market-data quality gate: incomplete normalised price rows.")
    if not prices["quote_currency"].astype(str).str.fullmatch(r"[A-Z]{3}").all():
        raise SystemExit("Market-data quality gate: invalid quote currency.")
    if (prices[["close_native", "close_eur", "close"]] <= 0).any().any():
        raise SystemExit("Market-data quality gate: non-positive price.")
    if not (prices["close"].round(10) == prices["close_eur"].round(10)).all():
        raise SystemExit("Market-data quality gate: compatibility close is not EUR-normalised.")

    latest_date = pd.to_datetime(prices["date"], errors="coerce").max().normalize()
    today = pd.Timestamp.now(tz="UTC").normalize().tz_localize(None)
    if pd.isna(latest_date) or (today - latest_date).days > 7:
        raise SystemExit("Market-data quality gate: prices are more than seven days old.")

    raw = reversible_ticks(prices, "close_raw")
    clean = reversible_ticks(prices, "close_eur", suspicious_only=True)
    ANOMALIES.parent.mkdir(parents=True, exist_ok=True)
    raw.to_csv(ANOMALIES, index=False)

    if not clean.empty:
        raise SystemExit(
            f"Market-data quality gate: {len(clean)} suspect reversible tick(s) remain in EUR-normalised prices."
        )
    print(
        f"Market-data quality gate passed through {latest_date.date().isoformat()}: {len(prices)} rows, "
        f"{prices.asset_id.nunique()} assets; {len(raw)} raw reversals audited, "
        f"{sum(prices.quality_status.eq('reversible_tick_neutralised'))} suspect tick(s) neutralised."
    )


if __name__ == "__main__":
    main()
