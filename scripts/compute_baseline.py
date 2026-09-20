from __future__ import annotations

from pathlib import Path
import math
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
    euro_rate = float(cfg["fund_euro"]["provisional_annual_rate"])

    market = portfolio[portfolio["asset_id"] != euro_id].copy()
    euro_weight = float(
        portfolio.loc[portfolio["asset_id"] == euro_id, "weight"].sum()
    )

    dates = pd.date_range(start, pd.Timestamp.today().normalize(), freq="D")
    result = pd.DataFrame({"date": dates})
    result["baseline"] = euro_weight * (
        (1.0 + euro_rate) ** ((result["date"] - start).dt.days / 365.0)
    )

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
        px["relative"] = px["close_eur"] / first
        rel = (
            px.set_index("date")["relative"]
            .reindex(dates)
            .ffill()
            .bfill()
            .values
        )
        result["baseline"] += weight * rel

    represented = 1.0 - sum(
        float(portfolio.loc[portfolio["asset_id"] == aid, "weight"].sum())
        for aid in missing
    )

    if represented <= 0:
        print("Baseline skipped: no represented assets.")
        return

    result["baseline"] = base * result["baseline"] / represented
    result["coverage_pct"] = represented * 100.0
    result["provisional_fund_euro_rate"] = euro_rate

    OUT.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(OUT, index=False)

    print(
        f"Baseline written: {len(result)} rows; "
        f"coverage={represented:.2%}; missing_assets={len(missing)}"
    )


if __name__ == "__main__":
    main()
