from __future__ import annotations

from pathlib import Path
import pandas as pd
import yaml

CFG = Path("config/baseline_bernard.yml")
PORTFOLIO = Path("config/portfolio_current.csv")
PRICES = Path("data/prices/daily.csv")
OUT = Path("data/benchmarks/bernard_origin.csv")


def portfolio_curve(start, portfolio, prices, euro_id, euro_rate, normalization, value_column):
    """Build a buy-and-hold curve from an explicitly dated portfolio composition."""
    portfolio = portfolio.copy()
    portfolio["weight"] = portfolio["allocation_pct"] / 100.0
    market = portfolio[portfolio["asset_id"] != euro_id].copy()
    euro_weight = float(
        portfolio.loc[portfolio["asset_id"] == euro_id, "weight"].sum()
    )

    dates = pd.date_range(start, pd.Timestamp.today().normalize(), freq="D")
    result = pd.DataFrame({"date": dates})
    result[value_column] = euro_weight * (
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
        relative = (
            px.set_index("date")["relative"]
            .reindex(dates)
            .ffill()
            .bfill()
            .values
        )
        result[value_column] += weight * relative

    represented = 1.0 - sum(
        float(portfolio.loc[portfolio["asset_id"] == aid, "weight"].sum())
        for aid in missing
    )
    if represented <= 0:
        return None, 0.0, missing

    result[value_column] = normalization * result[value_column] / represented
    result["coverage_pct"] = represented * 100.0
    result["provisional_fund_euro_rate"] = euro_rate
    return result, represented, missing


def write_curve(path, result, represented, missing, label):
    path.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(path, index=False)
    print(
        f"{label}: {len(result)} rows; coverage={represented:.2%}; "
        f"missing_assets={len(missing)}"
    )


def main():
    if not CFG.exists() or not PORTFOLIO.exists() or not PRICES.exists():
        print("Baseline skipped: required data not available yet.")
        return

    cfg = yaml.safe_load(CFG.read_text(encoding="utf-8"))
    portfolio = pd.read_csv(PORTFOLIO)
    prices = pd.read_csv(PRICES)
    if "close_eur" not in prices.columns:
        raise SystemExit("Baseline requires EUR-normalised shared prices. Run update_market_data.py first.")
    prices["date"] = pd.to_datetime(prices["date"])

    euro_id = cfg["fund_euro"]["asset_id"]
    euro_rate = float(cfg["fund_euro"]["provisional_annual_rate"])
    normalization = float(cfg.get("normalization", 100))

    # Suivi réel : il reste strictement borné à la date d'origine de Bernard.
    origin, represented, missing = portfolio_curve(
        pd.Timestamp(cfg["as_of_date"]),
        portfolio,
        prices,
        euro_id,
        euro_rate,
        normalization,
        "baseline",
    )
    if origin is None:
        print("Baseline skipped: no represented assets.")
        return
    write_curve(OUT, origin, represented, missing, "Bernard origin benchmark")

    # Simulation séparée : elle ne modifie jamais le suivi réel ci-dessus.
    historical = cfg.get("historical_current_composition")
    if not historical:
        return
    simulation, represented, missing = portfolio_curve(
        pd.Timestamp(historical["start_date"]),
        portfolio,
        prices,
        euro_id,
        euro_rate,
        normalization,
        "simulation_current_composition",
    )
    if simulation is None:
        print("Historical Bernard simulation skipped: no represented assets.")
        return
    simulation["simulation_label"] = historical["label"]
    simulation["simulation_note"] = historical["note"]
    output = Path(historical["output_series"])
    write_curve(
        output,
        simulation,
        represented,
        missing,
        "Bernard current-composition simulation",
    )


if __name__ == "__main__":
    main()
