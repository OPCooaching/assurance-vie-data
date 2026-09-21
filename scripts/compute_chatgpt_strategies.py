from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import yaml

CFG = Path("config/chatgpt_strategies.yml")
UNIVERSE = Path("config/universe.csv")
PRICES = Path("data/prices/daily.csv")
BASELINE = Path("data/benchmarks/bernard_origin.csv")
OUT = Path("data/chatgpt/performance.csv")
ALLOC_OUT = Path("data/chatgpt/latest_allocations.csv")


def load_inputs():
    prices = pd.read_csv(PRICES)
    if "close_eur" not in prices.columns:
        raise ValueError("ChatGPT strategies require EUR-normalised shared prices.")
    prices["date"] = pd.to_datetime(prices["date"])
    px = prices.pivot_table(index="date", columns="asset_id", values="close_eur", aggfunc="last")
    return px.sort_index().ffill(), pd.read_csv(UNIVERSE), yaml.safe_load(CFG.read_text(encoding="utf-8"))


def score_and_trend(px, assets, dt, lookbacks, trend_days):
    history = px.loc[:dt, assets]
    if len(history) < max(max(lookbacks), trend_days) + 1:
        return pd.Series(dtype=float), pd.Series(dtype=bool)
    last = history.iloc[-1]
    scores = pd.Series(0.0, index=assets)
    valid = pd.Series(True, index=assets)
    for days in lookbacks:
        prior = history.iloc[-(days + 1)]
        component = last.div(prior).sub(1.0)
        scores = scores.add(component.fillna(0.0), fill_value=0.0)
        valid &= component.notna()
    scores /= len(lookbacks)
    trend = last.gt(history.tail(trend_days).mean())
    return scores[valid], trend[valid]


def select_momentum(px, assets, dt, top_n, lookbacks, trend_days):
    score, trend = score_and_trend(px, assets, dt, lookbacks, trend_days)
    candidates = score[trend & score.gt(0)].sort_values(ascending=False).head(top_n)
    return candidates.index.tolist()


def signal_impulsion(px, assets, dt, cfg):
    winners = select_momentum(
        px, assets, dt, int(cfg["top_n"]), cfg["lookbacks"], int(cfg["trend_days"])
    )
    if not winners:
        return {cfg["defensive_asset"]: 1.0}
    return {asset: 1.0 / len(winners) for asset in winners}


def signal_adaptative(px, assets, dt, cfg):
    score, trend = score_and_trend(px, assets, dt, cfg["lookbacks"], int(cfg["trend_days"]))
    breadth = float(trend.mean()) if len(trend) else 0.0
    if breadth >= float(cfg["full_exposure_breadth"]):
        exposure = 1.0
    elif breadth >= float(cfg["half_exposure_breadth"]):
        exposure = 0.5
    else:
        exposure = 0.0
    winners = score[trend & score.gt(0)].sort_values(ascending=False).head(int(cfg["top_n"])).index.tolist()
    weights = {cfg["defensive_asset"]: 1.0 - exposure}
    if winners and exposure:
        for asset in winners:
            weights[asset] = exposure / len(winners)
    return {asset: weight for asset, weight in weights.items() if weight > 0}


def signal_rotation(px, assets, dt, cfg):
    score, trend = score_and_trend(px, assets, dt, cfg["lookbacks"], int(cfg["trend_days"]))
    ranked = score[trend & score.gt(0)].sort_values(ascending=False).head(int(cfg["candidate_count"])).index.tolist()
    history = px.loc[:dt, ranked].pct_change().tail(int(cfg["correlation_days"]))
    chosen = []
    for asset in ranked:
        if not chosen:
            chosen.append(asset)
        else:
            correlations = history[[asset] + chosen].corr().loc[asset, chosen].abs()
            if correlations.dropna().le(float(cfg["max_abs_correlation"])).all():
                chosen.append(asset)
        if len(chosen) >= int(cfg["top_n"]):
            break
    if not chosen:
        return {cfg["defensive_asset"]: 1.0}
    return {asset: 1.0 / len(chosen) for asset in chosen}


def is_rebalance_date(dt, first_date):
    return dt == first_date or dt.weekday() == 0


def daily_curve(px, dates, signal_fn, assets):
    value = 1.0
    values = []
    weights = None
    last_prices = None
    latest_weights = {}
    for dt in dates:
        prices = px.loc[dt]
        if last_prices is not None and weights:
            ret = 0.0
            for asset, weight in weights.items():
                current, previous = prices.get(asset), last_prices.get(asset)
                if pd.notna(current) and pd.notna(previous) and previous > 0:
                    ret += float(weight) * (float(current) / float(previous) - 1.0)
            value *= 1.0 + ret
        if is_rebalance_date(dt, dates[0]):
            weights = signal_fn(dt)
            latest_weights = dict(weights)
        values.append((dt, value))
        last_prices = prices
    return pd.Series(dict(values)), latest_weights


def main():
    if not all(path.exists() for path in (CFG, UNIVERSE, PRICES, BASELINE)):
        print("ChatGPT live strategies skipped: required data not available yet.")
        return

    px, universe, cfg = load_inputs()
    # The defensive support is common to the three distinct rule sets.
    for name in ("impulsion", "adaptative", "rotation_diversifiee"):
        cfg[name]["defensive_asset"] = cfg["defensive_asset"]
    baseline_dates = pd.to_datetime(pd.read_csv(BASELINE)["date"])
    dates = [dt for dt in baseline_dates if dt in px.index]
    if not dates:
        print("ChatGPT live strategies skipped: no common actual valuation dates.")
        return

    eligible = universe.loc[universe["category"].str.upper().eq("ETF"), "asset_id"].tolist()
    defensive = cfg["defensive_asset"]
    assets = [asset for asset in eligible if asset in px.columns and asset != defensive]
    if defensive not in px.columns:
        raise ValueError("Configured defensive asset is missing from EUR price data.")

    curves, allocations = {}, []
    builders = {
        "chatgpt_impulsion": lambda dt: signal_impulsion(px, assets, dt, cfg["impulsion"]),
        "chatgpt_adaptative": lambda dt: signal_adaptative(px, assets, dt, cfg["adaptative"]),
        "chatgpt_rotation_diversifiee": lambda dt: signal_rotation(px, assets, dt, cfg["rotation_diversifiee"]),
    }
    for strategy_id, signal_fn in builders.items():
        curve, latest = daily_curve(px, dates, signal_fn, assets)
        curves[strategy_id] = 100.0 * curve / float(curve.iloc[0])
        allocations.extend(
            {"strategy_id": strategy_id, "asset_id": asset, "weight_pct": round(100.0 * weight, 6)}
            for asset, weight in latest.items()
        )

    OUT.parent.mkdir(parents=True, exist_ok=True)
    frame = pd.DataFrame(curves)
    frame.index.name = "date"
    frame.to_csv(OUT)
    pd.DataFrame(allocations).to_csv(ALLOC_OUT, index=False)
    print(f"Computed {len(curves)} ChatGPT live strategy curve(s) across {len(frame)} actual valuation dates.")


if __name__ == "__main__":
    main()
