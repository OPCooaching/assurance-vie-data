from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd
import yaml
from portfolio_accounting import simulate

CFG = Path("config/academic_strategies.yml")
UNIVERSE = Path("config/universe.csv")
PRICES = Path("data/prices/daily.csv")
BASELINE = Path("data/benchmarks/bernard_origin.csv")
OUT = Path("data/academic/performance.csv")
ALLOC_OUT = Path("data/academic/latest_allocations.csv")


def load_prices():
    df = pd.read_csv(PRICES)
    if "close_eur" not in df.columns:
        raise ValueError("Academic strategies require EUR-normalised shared prices.")
    df["date"] = pd.to_datetime(df["date"])
    px = df.pivot_table(index="date", columns="asset_id", values="close_eur", aggfunc="last")
    return px.sort_index().ffill()


def portfolio_curve(px, target_weights, start_date, rebalance):
    assets = [a for a in target_weights if a in px.columns]
    if len(assets) != len(target_weights):
        return None

    sub = px[assets].loc[px.index >= start_date].dropna()
    if sub.empty:
        return None

    events = []
    last_key = None
    for dt in sub.index:
        key = (dt.year, dt.month) if rebalance == "monthly" else dt.year
        if last_key is None or key != last_key:
            events.append({"date": dt, "weights": target_weights})
            last_key = key
    curve, latest = simulate(px, sub.index, events)
    curve.attrs["latest_allocation"] = latest
    return curve


def faber_curve(px, risk_asset, defensive_asset, start_date):
    if risk_asset not in px.columns or defensive_asset not in px.columns:
        return None, None

    sub = px[[risk_asset, defensive_asset]].loc[px.index >= start_date - pd.Timedelta(days=420)].dropna()
    if sub.empty:
        return None, None

    monthly = sub[risk_asset].resample("ME").last()
    sma10 = monthly.rolling(10).mean()
    signal = (monthly > sma10).astype(float).shift(1).dropna()

    daily = sub.loc[sub.index >= start_date].copy()
    daily["month"] = daily.index.to_period("M")
    monthly_signal = pd.Series(signal.values, index=signal.index.to_period("M"))
    daily["risk_on"] = daily["month"].map(monthly_signal).fillna(0.0)

    events, previous_month = [], None
    for dt, row in daily.iterrows():
        if dt.to_period("M") != previous_month:
            events.append({"date": dt, "weights": {
                risk_asset: float(row["risk_on"]),
                defensive_asset: 1.0 - float(row["risk_on"])}})
            previous_month = dt.to_period("M")
    return simulate(px, daily.index, events)


def momentum_curve(px, universe_df, defensive_asset, start_date, top_n):
    etfs = universe_df.loc[universe_df["category"].str.upper() == "ETF", "asset_id"].tolist()
    assets = [a for a in etfs if a in px.columns]
    if defensive_asset not in px.columns or not assets:
        return None, None

    all_assets = list(dict.fromkeys(assets + [defensive_asset]))
    sub = px[all_assets].loc[px.index >= start_date - pd.Timedelta(days=430)].ffill()
    if sub.empty:
        return None, None

    month_ends = sub.resample("ME").last()
    mom = month_ends[assets].pct_change(12, fill_method=None)
    signals = {}

    for dt in month_ends.index:
        row = mom.loc[dt].dropna()
        winners = row[row > 0].sort_values(ascending=False).head(top_n).index.tolist()
        next_period = (dt + pd.offsets.MonthEnd(1)).to_period("M")
        if winners:
            signals[next_period] = {a: 1.0 / len(winners) for a in winners}
        else:
            signals[next_period] = {defensive_asset: 1.0}

    daily = sub.loc[sub.index >= start_date]
    events, previous_month = [], None
    for dt in daily.index:
        period = dt.to_period("M")
        if period != previous_month:
            events.append({"date": dt, "weights": signals.get(period, {defensive_asset: 1.0})})
            previous_month = period
    return simulate(px, daily.index, events)


def main():
    if not (CFG.exists() and UNIVERSE.exists() and PRICES.exists() and BASELINE.exists()):
        print("Academic strategies skipped: required data not available yet.")
        return

    benchmark_dates = pd.to_datetime(pd.read_csv(BASELINE)["date"], errors="coerce").dropna().sort_values()
    if benchmark_dates.empty:
        print("Academic strategies skipped: no actual common valuation date.")
        return

    cfg = yaml.safe_load(CFG.read_text(encoding="utf-8"))
    # Academic rules may use older prices to form their signals, but public
    # tracking begins on the same first real valuation date as Bernard.
    start = max(pd.Timestamp(cfg["start_date"]), pd.Timestamp(benchmark_dates.iloc[0]))
    norm = float(cfg.get("normalization", 100))
    universe = pd.read_csv(UNIVERSE)
    px = load_prices()
    px = px.loc[px.index <= benchmark_dates.iloc[-1]]

    curves = {}
    allocations = []

    for sid, spec in cfg["strategies"].items():
        typ = spec["type"]

        if typ == "static":
            curve = portfolio_curve(px, spec["allocations"], start, spec.get("rebalance", "monthly"))
            alloc = curve.attrs["latest_allocation"] if curve is not None else None
        elif typ == "faber_sma10":
            curve, alloc = faber_curve(px, spec["risk_asset"], spec["defensive_asset"], start)
        elif typ == "momentum_12m":
            curve, alloc = momentum_curve(
                px,
                universe,
                spec["defensive_asset"],
                start,
                int(spec.get("top_n", 5)),
            )
        else:
            continue

        if curve is None or len(curve) == 0:
            continue

        curve = norm * curve / float(curve.iloc[0])
        curves[sid] = curve

        if alloc:
            for asset, weight in alloc.items():
                allocations.append({
                    "strategy_id": sid,
                    "asset_id": asset,
                    "weight_pct": 100.0 * float(weight),
                })

    if not curves:
        print("No academic curve could be computed yet.")
        return

    out = pd.concat(curves, axis=1).sort_index()
    # Never publish dates that Bernard cannot be valued on a common actual
    # basis.  This also prevents academic-only weekends or later quote dates.
    out = out.loc[out.index.isin(pd.DatetimeIndex(benchmark_dates))]
    out.index.name = "date"
    OUT.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(OUT)

    pd.DataFrame(allocations).to_csv(ALLOC_OUT, index=False)
    print(f"Computed {len(curves)} academic strategy curve(s).")


if __name__ == "__main__":
    main()
