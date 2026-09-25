from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import yaml

CFG = Path("config/baseline_bernard.yml")
PORTFOLIO = Path("config/portfolio_current.csv")
PRICES = Path("data/prices/daily.csv")
OUT = Path("data/benchmarks/bernard_origin.csv")
CONSOLIDATED_OUT = Path("data/benchmarks/bernard_origin_consolidated.csv")
STATUS_OUT = Path("data/benchmarks/bernard_valuation_status.json")


def normalised_result(dates, portfolio, series_by_asset, euro_weight, base, initial_value_eur, represented, use_last_known_prices):
    """Build a valuation on exact closes, or on exact closes plus known prior closes."""
    result = pd.DataFrame({"date": pd.DatetimeIndex(dates)})
    result["baseline"] = euro_weight
    first_date = result["date"].iloc[0]

    for _, row in portfolio.iterrows():
        aid = row["asset_id"]
        if aid not in series_by_asset:
            continue
        values = series_by_asset[aid].reindex(result["date"])
        if use_last_known_prices:
            values = values.ffill()
        if values.isna().any():
            raise ValueError(f"Cannot value {aid}: no price is available before a requested date")
        first = float(series_by_asset[aid].loc[first_date])
        result["baseline"] += float(row["weight"]) * values.div(first).to_numpy()

    result["baseline"] = base * result["baseline"] / represented
    result["value_eur"] = (initial_value_eur * result["baseline"] / base).round(2)
    result["coverage_pct"] = represented * 100.0
    result["fund_euro_return_status"] = "held_at_initial_value_pending_credit"
    return result


def main():
    if not CFG.exists() or not PORTFOLIO.exists() or not PRICES.exists():
        print("Baseline skipped: required data not available yet.")
        return

    cfg = yaml.safe_load(CFG.read_text(encoding="utf-8"))
    start = pd.Timestamp(cfg["as_of_date"])
    base = float(cfg.get("normalization", 100))
    initial_value_eur = float(cfg["initial_portfolio_value_eur"])
    if initial_value_eur <= 0:
        raise SystemExit("initial_portfolio_value_eur must be strictly positive")

    portfolio = pd.read_csv(PORTFOLIO)
    portfolio["weight"] = portfolio["allocation_pct"] / 100.0

    prices = pd.read_csv(PRICES)
    if "close_eur" not in prices.columns:
        raise SystemExit("Baseline requires EUR-normalised shared prices. Run update_market_data.py first.")
    prices["date"] = pd.to_datetime(prices["date"])

    euro_id = cfg["fund_euro"]["asset_id"]
    market = portfolio[portfolio["asset_id"] != euro_id].copy()
    euro_weight = float(portfolio.loc[portfolio["asset_id"] == euro_id, "weight"].sum())

    series_by_asset, common_dates, missing = {}, None, []
    for _, row in market.iterrows():
        aid = row["asset_id"]
        px = prices.loc[prices["asset_id"] == aid, ["date", "close_eur"]].copy()
        px = px[px["date"] >= start].dropna().sort_values("date").drop_duplicates("date", keep="last")
        if px.empty:
            missing.append(aid)
            continue
        values = px.set_index("date")["close_eur"]
        series_by_asset[aid] = values
        dates = set(values.index)
        common_dates = dates if common_dates is None else common_dates & dates

    represented = 1.0 - sum(
        float(portfolio.loc[portfolio["asset_id"] == aid, "weight"].sum())
        for aid in missing
    )
    if represented <= 0 or not common_dates:
        print("Baseline skipped: no common actual valuation dates.")
        return

    # A fully consolidated date has an official close for every represented
    # market support. It remains a separate audit series.
    consolidated_dates = pd.DatetimeIndex(sorted(common_dates))
    first_date = consolidated_dates[0]

    # The public daily series goes up to the latest date for which at least one
    # represented support has published a price. A support that has not yet
    # published that day's close keeps its latest official close temporarily.
    # This is an explicit estimate, never an invented price; the row is
    # automatically replaced by a consolidated row as soon as all closes arrive.
    daily_dates = pd.DatetimeIndex(sorted({
        date
        for values in series_by_asset.values()
        for date in values.index
        if date >= first_date
    }))

    consolidated = normalised_result(
        consolidated_dates, market, series_by_asset, euro_weight, base,
        initial_value_eur, represented, use_last_known_prices=False,
    )
    consolidated["valuation_status"] = "consolidated"

    daily = normalised_result(
        daily_dates, market, series_by_asset, euro_weight, base,
        initial_value_eur, represented, use_last_known_prices=True,
    )
    daily["valuation_status"] = daily["date"].isin(common_dates).map(
        {True: "consolidated", False: "provisional"}
    )

    latest_daily_date = daily_dates[-1]
    latest_consolidated_date = consolidated_dates[-1]
    pending_supports = []
    for _, row in market.iterrows():
        aid = row["asset_id"]
        if aid not in series_by_asset:
            continue
        latest_asset_date = series_by_asset[aid].index[series_by_asset[aid].index <= latest_daily_date].max()
        if latest_asset_date < latest_daily_date:
            pending_supports.append({
                "asset_id": aid,
                "support_name": str(row["support_name"]),
                "latest_official_close_date": str(latest_asset_date.date()),
            })

    status = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "latest_provisional_date": str(latest_daily_date.date()),
        "latest_consolidated_date": str(latest_consolidated_date.date()),
        "latest_status": str(daily.iloc[-1]["valuation_status"]),
        "pending_supports": pending_supports,
        "missing_from_entire_series": missing,
        "method": (
            "Official close on each published support; for a provisional date only, "
            "a delayed support keeps its latest official close until its new close is published."
        ),
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    daily.to_csv(OUT, index=False)
    consolidated.to_csv(CONSOLIDATED_OUT, index=False)
    STATUS_OUT.write_text(json.dumps(status, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        f"Bernard valuation written: {len(daily)} daily rows through {latest_daily_date.date()} "
        f"({status['latest_status']}); {len(consolidated)} consolidated rows through "
        f"{latest_consolidated_date.date()}; pending_supports={len(pending_supports)}"
    )


if __name__ == "__main__":
    main()
