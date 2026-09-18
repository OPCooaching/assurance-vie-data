from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd
import yaml

CFG = Path("config/academic_strategies.yml")
UNIVERSE = Path("config/universe.csv")
PRICES = Path("data/prices/daily.csv")
OUT = Path("data/academic/performance.csv")
ALLOC_OUT = Path("data/academic/latest_allocations.csv")


def load_prices():
    df = pd.read_csv(PRICES)
    df["date"] = pd.to_datetime(df["date"])
    px = df.pivot_table(index="date", columns="asset_id", values="close", aggfunc="last")
    return px.sort_index().ffill()


def portfolio_curve(px, target_weights, start_date, rebalance):
    assets = [a for a in target_weights if a in px.columns]
    if len(assets) != len(target_weights):
        return None

    sub = px[assets].loc[px.index >= start_date].dropna()
    if sub.empty:
        return None

    rets = sub.pct_change().fillna(0.0)
    weights = pd.Series({a: target_weights[a] for a in assets}, dtype=float)
    weights = weights / weights.sum()
    value = 1.0
    rows = []

    last_key = None
    for dt, r in rets.iterrows():
        key = (dt.year, dt.month) if rebalance == "monthly" else dt.year
        if last_key is None or key != last_key:
            weights = pd.Series({a: target_weights[a] for a in assets}, dtype=float)
            weights = weights / weights.sum()
            last_key = key

        port_ret = float((weights * r).sum())
        value *= (1.0 + port_ret)

        grown = weights * (1.0 + r)
        denom = grown.sum()
        if denom > 0:
            weights = grown / denom

        rows.append((dt, value))

    return pd.Series(dict(rows)).sort_index()


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

    rr = daily[risk_asset].pct_change().fillna(0.0)
    dr = daily[defensive_asset].pct_change().fillna(0.0)
    port_ret = daily["risk_on"] * rr + (1.0 - daily["risk_on"]) * dr
    curve = (1.0 + port_ret).cumprod()

    last_alloc = {
        risk_asset: float(daily["risk_on"].iloc[-1]),
        defensive_asset: float(1.0 - daily["risk_on"].iloc[-1]),
    }
    return curve, last_alloc


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
    mom = month_ends[assets].pct_change(12)
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
    daily_rets = daily.pct_change().fillna(0.0)
    value = 1.0
    rows = []
    current = {defensive_asset: 1.0}

    for dt, row in daily_rets.iterrows():
        period = dt.to_period("M")
        if period in signals:
            current = signals[period]

        port_ret = 0.0
        for asset, w in current.items():
            if asset in row.index and pd.notna(row[asset]):
                port_ret += w * float(row[asset])
        value *= 1.0 + port_ret
        rows.append((dt, value))

    return pd.Series(dict(rows)).sort_index(), current


def main():
    if not (CFG.exists() and UNIVERSE.exists() and PRICES.exists()):
        print("Academic strategies skipped: required data not available yet.")
        return

    cfg = yaml.safe_load(CFG.read_text(encoding="utf-8"))
    start = pd.Timestamp(cfg["start_date"])
    norm = float(cfg.get("normalization", 100))
    universe = pd.read_csv(UNIVERSE)
    px = load_prices()

    curves = {}
    allocations = []

    for sid, spec in cfg["strategies"].items():
        typ = spec["type"]

        if typ == "static":
            curve = portfolio_curve(px, spec["allocations"], start, spec.get("rebalance", "monthly"))
            alloc = spec["allocations"]
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
    out.index.name = "date"
    OUT.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(OUT)

    pd.DataFrame(allocations).to_csv(ALLOC_OUT, index=False)
    print(f"Computed {len(curves)} academic strategy curve(s).")


if __name__ == "__main__":
    main()
