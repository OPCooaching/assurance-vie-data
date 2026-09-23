#!/usr/bin/env python3
"""Walk-forward test for ChatGPT G v0.2.

Each Friday is treated as a real decision date. The model may use only prices
and external observations available before that date, relearns its signal
weights from earlier weeks, and applies the resulting allocation from the next
published valuation. It never selects a pre-defined number of holdings.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[3]
PRICES = ROOT / "data/prices/daily.csv"
CONTEXT = ROOT / "data/context/daily.csv"
CONTEXT_CONFIG = ROOT / "config/context_series.yml"
OUTPUT = ROOT / "docs/data/chatgpt-backtests.json"
CURVE_OUTPUT = Path(__file__).with_name("backtest_v0.2.csv")
DECISIONS_OUTPUT = Path(__file__).with_name("backtest_v0.2-decisions.jsonl")

STRATEGY_ID = "chatgpt-ai-allocation-review"
VERSION = "v0.2"
WARMUP_DAYS = 252
TRAINING_WEEKS = 52
HOLDING_DAYS = 5
RIDGE_PENALTY = 25.0
SIGNAL_NAMES = (
    "ret_5d", "ret_20d", "ret_60d", "ret_120d", "sma20", "sma50",
    "sma200", "minus_vol60", "drawdown60",
)


def load_prices() -> pd.DataFrame:
    raw = pd.read_csv(PRICES, parse_dates=["date"])
    if "close_eur" not in raw.columns:
        raise ValueError("Backtest requires the shared EUR-normalised closing prices.")
    prices = raw.pivot_table(index="date", columns="asset_id", values="close_eur", aggfunc="last")
    return prices.sort_index().ffill()


def load_context() -> tuple[pd.DataFrame, list[dict]]:
    config = yaml.safe_load(CONTEXT_CONFIG.read_text(encoding="utf-8")) or {}
    series = config.get("series") or []
    context = pd.read_csv(CONTEXT, parse_dates=["date"]).sort_values("date")
    return context, series


def decision_dates(index: pd.DatetimeIndex) -> list[pd.Timestamp]:
    grouped = pd.Series(index, index=index).groupby(index.to_period("W-FRI")).last()
    return [pd.Timestamp(value) for value in grouped.tolist()]


def zscore_cross_section(values: pd.Series) -> pd.Series:
    values = values.astype(float)
    center, spread = values.mean(), values.std(ddof=0)
    if not np.isfinite(spread) or spread <= 1e-12:
        return pd.Series(np.nan, index=values.index)
    return ((values - center) / spread).clip(-4.0, 4.0)


def context_vector(context: pd.DataFrame, configured: list[dict], decision: pd.Timestamp) -> np.ndarray:
    """Return only values that a Friday decision could actually have known."""
    result: list[float] = []
    for item in configured:
        identifier = item.get("id", "")
        column = item.get("column", identifier)
        if column not in context.columns:
            result.append(0.0)
            continue
        frequency = item.get("frequency", "daily")
        if frequency == "weekly" and identifier == "NFCI":
            cutoff = decision - pd.Timedelta(days=5)
        elif frequency == "weekly" and identifier == "WEI":
            cutoff = decision - pd.Timedelta(days=6)
        elif frequency == "weekly":
            cutoff = decision - pd.Timedelta(days=7)
        else:
            cutoff = decision - pd.offsets.BDay(1)
        values = pd.to_numeric(context.loc[context["date"] <= cutoff, column], errors="coerce").dropna().tail(260)
        if len(values) < 20 or float(values.std(ddof=0)) <= 1e-12:
            result.append(0.0)
        else:
            result.append(float(np.clip((values.iloc[-1] - values.mean()) / values.std(ddof=0), -4.0, 4.0)))
    return np.asarray(result, dtype=float)


def feature_frame(prices: pd.DataFrame, position: int, context: np.ndarray) -> tuple[pd.DataFrame, pd.Series]:
    history = prices.iloc[:position + 1]
    current = history.iloc[-1]
    signals = pd.DataFrame(index=prices.columns)
    signals["ret_5d"] = current / history.iloc[-6] - 1.0
    signals["ret_20d"] = current / history.iloc[-21] - 1.0
    signals["ret_60d"] = current / history.iloc[-61] - 1.0
    signals["ret_120d"] = current / history.iloc[-121] - 1.0
    signals["sma20"] = current / history.iloc[-20:].mean() - 1.0
    signals["sma50"] = current / history.iloc[-50:].mean() - 1.0
    signals["sma200"] = current / history.iloc[-200:].mean() - 1.0
    daily_returns = history.iloc[-61:].pct_change(fill_method=None).iloc[1:]
    signals["minus_vol60"] = -daily_returns.std(ddof=0) * np.sqrt(252.0)
    signals["drawdown60"] = current / history.iloc[-60:].max() - 1.0
    signals = signals.loc[:, SIGNAL_NAMES].apply(zscore_cross_section).dropna(how="any")
    expanded = [signals]
    for value in context:
        expanded.append(signals * float(value))
    features = pd.concat(expanded, axis=1, ignore_index=True).dropna(how="any")
    return features, (-signals["minus_vol60"]).reindex(features.index)


def sample_for_date(prices: pd.DataFrame, position: int, context: np.ndarray) -> dict | None:
    if position < WARMUP_DAYS or position + HOLDING_DAYS >= len(prices.index):
        return None
    features, volatility = feature_frame(prices, position, context)
    current, future = prices.iloc[position], prices.iloc[position + HOLDING_DAYS]
    target = (future / current - 1.0).reindex(features.index)
    valid = target.notna() & np.isfinite(features).all(axis=1) & volatility.notna() & (volatility > 0)
    if int(valid.sum()) < 20:
        return None
    return {
        "date": prices.index[position],
        "position": position,
        "assets": features.index[valid].tolist(),
        "features": features.loc[valid].to_numpy(dtype=float),
        "target": target.loc[valid].to_numpy(dtype=float),
        "volatility": volatility.loc[valid],
    }


def fit_predict(training: list[dict], current: dict) -> np.ndarray:
    x_train = np.vstack([sample["features"] for sample in training])
    y_train = np.concatenate([sample["target"] for sample in training])
    mean, scale = x_train.mean(axis=0), x_train.std(axis=0)
    scale[scale < 1e-9] = 1.0
    x = (x_train - mean) / scale
    y_mean = float(y_train.mean())
    coefficients = np.linalg.solve(
        x.T @ x + RIDGE_PENALTY * np.eye(x.shape[1]), x.T @ (y_train - y_mean)
    )
    return y_mean + ((current["features"] - mean) / scale) @ coefficients


def weights_from_prediction(prices: pd.DataFrame, sample: dict, prediction: np.ndarray) -> tuple[dict[str, float], dict]:
    assets = pd.Index(sample["assets"])
    relative_prediction = prediction - np.nanmedian(prediction)
    selected = relative_prediction > 0.0
    if not selected.any():
        selected[np.nanargmin(sample["volatility"].to_numpy(dtype=float))] = True
    assets = assets[selected]
    # Ranking keeps one extreme forecast from absorbing the portfolio. Every
    # support with a positive relative prediction remains eligible: no top-N.
    strength = pd.Series(relative_prediction[selected], index=assets).rank(pct=True).to_numpy(dtype=float)
    risk = sample["volatility"].reindex(assets).to_numpy(dtype=float)
    strength = np.sqrt(strength / np.maximum(risk / np.nanmedian(risk), 1e-6))
    returns = prices.loc[:sample["date"], assets].pct_change(fill_method=None).tail(60)
    corr = returns.corr().clip(lower=0.0).fillna(0.0)
    similarity = (
        (corr.sum(axis=1) - 1.0) / (len(assets) - 1)
        if len(assets) > 1 else pd.Series(0.0, index=assets)
    )
    raw = np.maximum(strength, 0.0) / (1.0 + similarity.reindex(assets).to_numpy(dtype=float))
    if not np.isfinite(raw).all() or raw.sum() <= 0:
        raw = np.ones(len(assets), dtype=float)
    weights = raw / raw.sum()
    allocation = {asset: float(weight) for asset, weight in zip(assets, weights)}
    hhi = float(np.square(weights).sum())
    off_diagonal = corr.to_numpy()[~np.eye(len(assets), dtype=bool)] if len(assets) > 1 else np.array([])
    return allocation, {
        "holdings": int(len(assets)),
        "effective_holdings": float(1.0 / hhi),
        "mean_positive_correlation": float(off_diagonal.mean()) if off_diagonal.size else 0.0,
    }


def build_curve(prices: pd.DataFrame, allocations: dict[pd.Timestamp, dict[str, float]]) -> pd.DataFrame:
    value, active, rows = 100.0, {}, []
    for position in range(1, len(prices.index)):
        today, previous = prices.index[position], prices.index[position - 1]
        if today in allocations:
            active = allocations[today]
        if not active:
            continue
        current, prior = prices.loc[today, list(active)], prices.loc[previous, list(active)]
        returns = (current / prior - 1.0).replace([np.inf, -np.inf], np.nan).fillna(0.0)
        value *= 1.0 + sum(active[asset] * float(returns[asset]) for asset in active)
        rows.append({"date": today.date().isoformat(), "value_base_100": value})
    return pd.DataFrame(rows)


def metrics(curve: pd.DataFrame, decisions: list[dict]) -> dict:
    values = curve["value_base_100"]
    returns = values.pct_change().dropna()
    elapsed_years = max((pd.Timestamp(curve["date"].iloc[-1]) - pd.Timestamp(curve["date"].iloc[0])).days / 365.25, 1 / 365.25)
    return {
        "start": str(curve["date"].iloc[0]),
        "end": str(curve["date"].iloc[-1]),
        "final_value": round(float(values.iloc[-1]), 4),
        "annualized_return": round(float((values.iloc[-1] / values.iloc[0]) ** (1.0 / elapsed_years) - 1.0), 6),
        "annualized_volatility": round(float(returns.std(ddof=0) * np.sqrt(252.0)), 6),
        "max_drawdown": round(float((values / values.cummax() - 1.0).min()), 6),
        "decisions": len(decisions),
        "average_holdings": round(float(np.mean([row["holdings"] for row in decisions])), 2),
        "average_effective_holdings": round(float(np.mean([row["effective_holdings"] for row in decisions])), 2),
        "average_positive_correlation": round(float(np.mean([row["mean_positive_correlation"] for row in decisions])), 4),
    }


def main() -> None:
    prices = load_prices()
    context, configured = load_context()
    samples, allocations, decisions = [], {}, []
    for decision in decision_dates(prices.index):
        position = int(prices.index.get_loc(decision))
        sample = sample_for_date(prices, position, context_vector(context, configured, decision))
        if sample is None:
            continue
        if len(samples) >= TRAINING_WEEKS:
            allocation, diagnostic = weights_from_prediction(prices, sample, fit_predict(samples[-TRAINING_WEEKS:], sample))
            effective = prices.index[position + 1]
            allocations[effective] = allocation
            decisions.append({
                "decision_date": decision.date().isoformat(),
                "effective_date": effective.date().isoformat(),
                "strategy_id": STRATEGY_ID,
                "strategy_version": VERSION,
                "target_allocation_percent": {asset: round(weight * 100.0, 6) for asset, weight in allocation.items()},
                **diagnostic,
            })
        samples.append(sample)

    curve = build_curve(prices, allocations)
    if curve.empty or not decisions:
        raise RuntimeError("No walk-forward result was produced; more valid history is required.")
    CURVE_OUTPUT.write_text(curve.to_csv(index=False), encoding="utf-8")
    DECISIONS_OUTPUT.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in decisions), encoding="utf-8")
    previous = json.loads(OUTPUT.read_text(encoding="utf-8")) if OUTPUT.exists() else {"results": []}
    result = {
        "strategy_id": STRATEGY_ID,
        "label": "ChatGPT G — Stratégie qui réapprend chaque semaine",
        "status": "backtest",
        "metrics": metrics(curve, decisions),
        "data_quality": "provisional_revised_macro_data",
        "limitations": [
            "current_universe_only",
            "macro_data_uses_conservative_publication_lags",
            "historical_macro_revisions_not_fully_reconstructible",
        ],
    }
    previous["version"] = VERSION
    previous["results"] = [row for row in previous.get("results", []) if row.get("strategy_id") != STRATEGY_ID] + [result]
    OUTPUT.write_text(json.dumps(previous, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Backtested {STRATEGY_ID}: {len(decisions)} weekly decisions, {len(curve)} valuation days.")


if __name__ == "__main__":
    main()
