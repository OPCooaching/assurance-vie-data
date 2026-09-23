"""Reproducible walk-forward backtests for the four ChatGPT v0.1 families.

Each decision sees prices and context observations dated on or before its
decision date. Target weights only start earning returns on the next available
valuation. Macro results remain explicitly provisional until FRED/ALFRED
vintages are added to the shared data pipeline.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

CFG = Path("config/chatgpt_backtests_v0_1.yml")
PRICES = Path("data/prices/daily.csv")
CONTEXT = Path("data/context/daily.csv")
UNIVERSE = Path("config/universe.csv")
OUT = Path("history/chatgpt/backtests")
WEB_OUT = Path("docs/data/chatgpt-backtests.json")


def load_inputs():
    cfg = yaml.safe_load(CFG.read_text(encoding="utf-8"))
    raw = pd.read_csv(PRICES, parse_dates=["date"])
    px = raw.pivot_table(index="date", columns="asset_id", values="close_eur", aggfunc="last").sort_index()
    context = pd.read_csv(CONTEXT, parse_dates=["date"]).set_index("date").sort_index()
    universe = pd.read_csv(UNIVERSE)
    return cfg, px, context, universe


def monthly_dates(index):
    return set(pd.Series(index, index=index).groupby(index.to_period("M")).last())


def weekly_dates(index):
    iso = index.isocalendar()
    return set(pd.Series(index, index=index).groupby([iso.year, iso.week]).last())


def normalise(weights):
    result = {asset: float(weight) for asset, weight in weights.items() if float(weight) > 0}
    total = sum(result.values())
    if not result or total <= 0:
        raise ValueError("Empty allocation")
    return {asset: weight / total for asset, weight in result.items()}


def momentum_weights(px, dt, assets, spec, defensive):
    history = px.loc[:dt, assets]
    lookbacks = [int(x) for x in spec["lookbacks_sessions"]]
    if len(history) <= max(max(lookbacks), int(spec["trend_days"])):
        return {defensive: 1.0}, {"selected": [], "reason": "insufficient_history"}
    last = history.iloc[-1]
    score = pd.Series(0.0, index=assets)
    valid = pd.Series(True, index=assets)
    for window in lookbacks:
        component = last.div(history.iloc[-1 - window]).sub(1.0)
        score = score.add(component.fillna(0.0), fill_value=0.0)
        valid &= component.notna()
    score /= len(lookbacks)
    trend = last.gt(history.tail(int(spec["trend_days"])).mean())
    winners = score[valid & trend & score.gt(0)].sort_values(ascending=False).head(int(spec["top_n"])).index.tolist()
    return (normalise({asset: 1.0 for asset in winners}) if winners else {defensive: 1.0},
            {"selected": winners, "reason": "positive_momentum" if winners else "no_positive_trend"})


def context_as_of(context, dt, columns):
    subset = context.loc[:dt, columns]
    values, dates = {}, {}
    for column in columns:
        known = subset[column].dropna()
        if known.empty:
            return None, None
        values[column] = float(known.iloc[-1])
        dates[column] = str(known.index[-1].date())
    return values, dates


def risk_weights(px, dt, spec, defensive):
    assets = [asset for asset in spec["risk_assets"] if asset in px.columns]
    window = int(spec["volatility_window_sessions"])
    history = px.loc[:dt, assets].dropna()
    if len(history) <= window:
        return {defensive: 1.0}, {"reason": "insufficient_history"}
    returns = history.iloc[-window - 1:].pct_change().dropna()
    basket = returns.mean(axis=1)
    realised = float(basket.std() * np.sqrt(252))
    if realised <= 0:
        exposure = float(spec["minimum_risk_exposure"])
    else:
        exposure = float(spec["target_volatility_annual"]) / realised
        exposure = min(float(spec["maximum_risk_exposure"]), max(float(spec["minimum_risk_exposure"]), exposure))
    weights = {asset: exposure / len(assets) for asset in assets}
    weights[defensive] = weights.get(defensive, 0.0) + 1.0 - exposure
    return normalise(weights), {"realised_volatility": realised, "risk_exposure": exposure}


def macro_weights(context, dt, spec):
    cols = ["financial_conditions_us", "policy_uncertainty_us", "vix_us_equity_volatility"]
    values, dates = context_as_of(context, dt, cols)
    if values is None:
        return normalise(spec["cautious_allocation"]), {"reason": "missing_context", "publication_dates": {}}
    uncertainty = context.loc[:dt, "policy_uncertainty_us"].dropna().tail(int(spec["conditions"]["uncertainty_window_observations"]))
    threshold = float(uncertainty.quantile(float(spec["conditions"]["uncertainty_quantile"])))
    flags = {
        "nfci": values["financial_conditions_us"] > float(spec["conditions"]["nfci_above"]),
        "uncertainty": values["policy_uncertainty_us"] > threshold,
        "vix": values["vix_us_equity_volatility"] > float(spec["conditions"]["vix_above"]),
    }
    cautious = sum(flags.values()) >= 2
    return normalise(spec["cautious_allocation"] if cautious else spec["normal_allocation"]), {
        "state": "cautious" if cautious else "normal", "flags": flags,
        "publication_dates": dates, "uncertainty_threshold": threshold,
        "data_quality": spec["data_quality_label"],
    }


def run(name, px, decision_dates, signal):
    returns = px.pct_change().fillna(0.0)
    value = 100.0
    weights = None
    rows, decisions = [], []
    for position, dt in enumerate(px.index):
        if position and weights:
            value *= 1.0 + sum(weights.get(asset, 0.0) * float(returns.at[dt, asset]) for asset in weights if asset in returns.columns)
        if dt in decision_dates:
            target, details = signal(dt)
            target = normalise(target)
            decisions.append({"decision_date": str(dt.date()), "effective_date": str(px.index[position + 1].date()) if position + 1 < len(px.index) else None, "target_allocation_percent": {a: round(w * 100, 6) for a, w in target.items()}, "details": details})
            weights = target
        rows.append({"date": str(dt.date()), "value": value})
    return pd.DataFrame(rows), decisions


def metrics(curve, decisions):
    values = curve["value"]
    elapsed = max(len(values) - 1, 1)
    annual = (float(values.iloc[-1]) / float(values.iloc[0])) ** (252 / elapsed) - 1.0
    daily = values.pct_change().dropna()
    drawdown = values.div(values.cummax()).sub(1.0).min()
    return {"start": curve.iloc[0].date, "end": curve.iloc[-1].date, "final_value": round(float(values.iloc[-1]), 4), "annualized_return": round(float(annual), 6), "annualized_volatility": round(float(daily.std() * np.sqrt(252)), 6), "max_drawdown": round(float(drawdown), 6), "decisions": len(decisions)}


def main():
    cfg, px, context, universe = load_inputs()
    base = cfg["backtest"]
    defensive = base["defensive_asset"]
    if defensive not in px.columns:
        raise ValueError("Defensive asset missing from prices")
    px = px.ffill().dropna(how="all")
    etfs = universe.loc[universe["category"].str.upper().eq("ETF"), "asset_id"].tolist()
    eligible = [asset for asset in etfs if asset in px.columns and asset != defensive and px[asset].notna().sum() >= int(base["start_after_sessions"])]
    start = px.index[int(base["start_after_sessions"])]
    test_px = px.loc[start:].copy()
    monthly, weekly = monthly_dates(test_px.index), weekly_dates(test_px.index)
    specs = cfg["strategies"]
    jobs = {
        "chatgpt-momentum-mensuel": (monthly, lambda dt: momentum_weights(px, dt, eligible, specs["chatgpt-momentum-mensuel"], defensive)),
        "chatgpt-volatilite-pilotee": (weekly, lambda dt: risk_weights(px, dt, specs["chatgpt-volatilite-pilotee"], defensive)),
        "chatgpt-regime-macro-financier": (weekly, lambda dt: macro_weights(context, dt, specs["chatgpt-regime-macro-financier"])),
        "chatgpt-hybride-selection-protection": (weekly, None),
    }
    hybrid = specs["chatgpt-hybride-selection-protection"]
    selected, last_month = {defensive: 1.0}, None
    def hybrid_signal(dt):
        nonlocal selected, last_month
        if dt in monthly:
            selected, details = momentum_weights(px, dt, eligible, hybrid, defensive)
            last_month = details
        values, dates = context_as_of(context, dt, ["financial_conditions_us", "vix_us_equity_volatility"])
        protect = values is None or values["financial_conditions_us"] > float(hybrid["protective_nfci_above"]) or values["vix_us_equity_volatility"] > float(hybrid["protective_vix_above"])
        exposure = float(hybrid["protective_risk_exposure"]) if protect else 1.0
        weights = {asset: weight * exposure for asset, weight in selected.items()}
        weights[defensive] = weights.get(defensive, 0.0) + 1.0 - exposure
        return normalise(weights), {"monthly_selection": last_month, "protection_active": protect, "publication_dates": dates or {}, "data_quality": "provisional_revised_macro_data"}
    jobs["chatgpt-hybride-selection-protection"] = (weekly, hybrid_signal)
    web = {"version": base["version"], "start": str(start.date()), "end": str(test_px.index[-1].date()), "results": []}
    for strategy_id, (dates, signal) in jobs.items():
        curve, decisions = run(strategy_id, test_px, dates, signal)
        folder = OUT / strategy_id / base["version"]
        folder.mkdir(parents=True, exist_ok=True)
        (folder / "specification.yml").write_text(
            yaml.safe_dump({"backtest": base, "strategy": specs[strategy_id]}, allow_unicode=True, sort_keys=False),
            encoding="utf-8",
        )
        curve.to_csv(folder / "performance.csv", index=False)
        with (folder / "decisions.jsonl").open("w", encoding="utf-8") as handle:
            for decision in decisions:
                handle.write(json.dumps(decision, ensure_ascii=False) + "\n")
        data_quality = specs[strategy_id].get("data_quality_label", "price_data_walk_forward")
        if strategy_id == "chatgpt-hybride-selection-protection":
            data_quality = "provisional_revised_macro_data"
        limitations = ["current_universe_only"]
        if data_quality == "provisional_revised_macro_data":
            limitations.append("macro_data_not_yet_point_in_time")
        result = {"strategy_id": strategy_id, "status": "backtest", "metrics": metrics(curve, decisions), "data_quality": data_quality, "limitations": limitations}
        (folder / "metrics.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        web["results"].append(result)
    WEB_OUT.write_text(json.dumps(web, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(web, ensure_ascii=False))


if __name__ == "__main__":
    main()
