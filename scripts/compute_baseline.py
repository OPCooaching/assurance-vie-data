from __future__ import annotations

from pathlib import Path

import pandas as pd
import yaml

CFG = Path("config/baseline_bernard.yml")
PORTFOLIO = Path("config/portfolio_current.csv")
PRICES = Path("data/prices/daily.csv")
OUT = Path("data/benchmarks/bernard_origin.csv")


def main():
    if not CFG.exists() or not PORTFOLIO.exists() or not PRICES.exists():
        print("Baseline skipped: required data not available yet.")
        return

    cfg = yaml.safe_load(CFG.read_text(encoding="utf-8"))
    start = pd.Timestamp(cfg["as_of_date"])
    base = float(cfg.get("normalization", 100))
    portfolio = pd.read_csv(PORTFOLIO)
    portfolio["weight"] = portfolio["allocation_pct"] / 100.0

    prices = pd.read_csv(PRICES)
    if "close_eur" not in prices.columns:
        raise SystemExit("Baseline requires EUR-normalised shared prices. Run update_market_data.py first.")
    prices["date"] = pd.to_datetime(prices["date"])

    euro_id = cfg["fund_euro"]["asset_id"]
    market = portfolio[portfolio["asset_id"] != euro_id].copy()
    euro_weight = float(portfolio.loc[portfolio["asset_id"] == euro_id, "weight"].sum())

    # Only actual market valuation dates are displayed. The fund in euros remains
    # at its initial value until an effectively credited rate is recorded.
    dates = pd.DatetimeIndex(sorted(prices.loc[prices["date"] >= start, "date"].unique()))
    result = pd.DataFrame({"date": dates})
    result["baseline"] = euro_weight
    missing = []

    for _, row in market.iterrows():
        aid = row["asset_id"]
        weight = float(row["weight"])
        px = prices.loc[prices["asset_id"] == aid, ["date", "close_eur"]].copy()
        px = px[px["date"] >= start].dropna().sort_values("date")
        if px.empty:
            missing.append(aid)
            continue

        first = float(px.iloc[0]["close_eur"])
        relative = px.set_index("date")["close_eur"].div(first).reindex(dates).ffill()
        result["baseline"] += weight * relative.to_numpy()

    represented = 1.0 - sum(
        float(portfolio.loc[portfolio["asset_id"] == aid, "weight"].sum())
        for aid in missing
    )
    if represented <= 0:
        print("Baseline skipped: no represented assets.")
        return

    result["baseline"] = base * result["baseline"] / represented
    result["coverage_pct"] = represented * 100.0
    result["fund_euro_return_status"] = "held_at_initial_value_pending_credit"
    OUT.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(OUT, index=False)
    print(
        f"Baseline written: {len(result)} actual market dates; "
        f"coverage={represented:.2%}; missing_assets={len(missing)}"
    )


if __name__ == "__main__":
    main()
