from __future__ import annotations

"""Deterministic, walk-forward simulations for the three ChatGPT hypotheses.

These are explicitly labelled research simulations. They never write the real
decision history and use only close_eur prices available on each decision date.
"""

import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

PRICES = Path("data/prices/daily.csv")
UNIVERSE = Path("config/universe.csv")
ROOT = Path("strategies/chatgpt")
DEFENSIVE = "LU0290358497"
START = pd.Timestamp("2022-10-03")
WINDOWS = (21, 63, 126, 252)


def load_prices():
    prices = pd.read_csv(PRICES, parse_dates=["date"])
    if "close_eur" not in prices.columns:
        raise SystemExit("ChatGPT simulations require EUR-normalised prices.")
    universe = pd.read_csv(UNIVERSE)
    eligible = universe.loc[
        (universe["category"].eq("ETF")) & (universe["enabled"].astype(str).str.lower().eq("true")),
        "asset_id",
    ].tolist()
    table = prices.pivot_table(index="date", columns="asset_id", values="close_eur", aggfunc="last")
    table = table.sort_index().ffill()
    candidates = [asset for asset in eligible if asset in table.columns and asset != DEFENSIVE]
    if DEFENSIVE not in table.columns:
        raise SystemExit("The defensive support is missing from shared prices.")
    return table, candidates


def weekly_decisions(index):
    return pd.Series(index, index=index).resample("W-FRI").last().dropna().tolist()


def ranking(table, candidates, date):
    visible = table.loc[:date, candidates]
    if len(visible) < max(WINDOWS) + 1:
        return pd.Series(dtype=float), pd.Series(dtype=bool)
    last = visible.iloc[-1]
    sma200 = visible.rolling(200).mean().iloc[-1]
    components = []
    for window, weight in zip(WINDOWS, (0.10, 0.20, 0.30, 0.40)):
        components.append(weight * (last / visible.iloc[-window - 1] - 1.0))
    score = sum(components)
    trend = last > sma200
    return score[trend].dropna().sort_values(ascending=False), trend


def allocation_impulsion(table, candidates, date):
    score, _ = ranking(table, candidates, date)
    winners = score.head(5).index.tolist()
    return {asset: 1.0 / len(winners) for asset in winners} if winners else {DEFENSIVE: 1.0}


def allocation_adaptative(table, candidates, date):
    score, trend = ranking(table, candidates, date)
    breadth = float(trend.reindex(candidates).fillna(False).mean())
    if breadth >= 0.60:
        winners, risk_weight = score.head(5).index.tolist(), 1.0
    elif breadth >= 0.40:
        winners, risk_weight = score.head(3).index.tolist(), 0.50
    else:
        winners, risk_weight = [], 0.0
    allocation = {asset: risk_weight / len(winners) for asset in winners} if winners else {}
    allocation[DEFENSIVE] = allocation.get(DEFENSIVE, 0.0) + (1.0 - risk_weight)
    return allocation


def allocation_rotation(table, candidates, date):
    score, _ = ranking(table, candidates, date)
    shortlist = score.head(30).index.tolist()
    recent = table.loc[:date, shortlist].pct_change().tail(63)
    winners = []
    for asset in shortlist:
        if not winners:
            winners.append(asset)
        else:
            corr = recent[[asset] + winners].corr().loc[asset, winners].abs().max()
            if pd.isna(corr) or corr < 0.85:
                winners.append(asset)
        if len(winners) == 8:
            break
    return {asset: 1.0 / len(winners) for asset in winners} if winners else {DEFENSIVE: 1.0}


def simulate(table, candidates, allocator):
    index = table.index[table.index >= START]
    decisions = set(weekly_decisions(table.index))
    value = 100.0
    weights = {DEFENSIVE: 1.0}
    rows = []
    for position in range(1, len(index)):
        previous, current = index[position - 1], index[position]
        returns = table.loc[[previous, current], list(weights)].pct_change().iloc[-1]
        portfolio_return = sum(weight * float(returns.get(asset, 0.0) or 0.0) for asset, weight in weights.items())
        value *= 1.0 + portfolio_return
        rows.append({"date": current.date().isoformat(), "valeur": round(value, 6)})
        if previous in decisions:
            weights = allocator(table, candidates, previous)
    return pd.DataFrame(rows)


def strategy_metadata(spec, curve):
    return {
        "id": spec["id"],
        "label": spec["label"],
        "version": "simulation v0.1",
        "short": spec["short"],
        "objective": spec["objective"],
        "main_rule": spec["main_rule"],
        "details": "Simulation walk-forward sur prix EUR, avec décision hebdomadaire appliquée à la séance suivante. Ce résultat est une hypothèse de recherche, pas une décision réelle.",
        "status": "simulation historique v0.1",
        "courbe": curve.to_dict("records"),
    }


def main():
    if not (PRICES.exists() and UNIVERSE.exists()):
        raise SystemExit("Shared prices and universe are required.")
    table, candidates = load_prices()
    definitions = {
        "impulsion": {
            "allocator": allocation_impulsion,
            "short": "Sélection hebdomadaire des cinq ETF les plus forts sur 1, 3, 6 et 12 mois, à condition que leur tendance 200 jours reste positive.",
            "objective": "Tester une rotation momentum concentrée.",
            "main_rule": "Top 5, score pondéré 1/3/6/12 mois, filtre moyenne mobile 200 jours.",
        },
        "adaptative": {
            "allocator": allocation_adaptative,
            "short": "Même sélection momentum, mais l'exposition risquée dépend de la part de l'univers restant au-dessus de sa moyenne 200 jours.",
            "objective": "Réduire l'exposition lorsque le régime de marché se dégrade.",
            "main_rule": "Top 5 au-dessus de 60 % de largeur, 50 % d'exposition entre 40 % et 60 %, sinon défensif.",
        },
        "rotation-diversifiee": {
            "allocator": allocation_rotation,
            "short": "Sélection hebdomadaire de huit leaders momentum en évitant les actifs trop corrélés sur les 63 dernières séances.",
            "objective": "Conserver le momentum avec une contrainte explicite de diversification.",
            "main_rule": "Top 30 momentum, maximum huit lignes, corrélation absolue inférieure à 0,85.",
        },
    }
    results = {}
    for directory, definition in definitions.items():
        strategy_path = ROOT / directory / "strategy.yml"
        spec = yaml.safe_load(strategy_path.read_text(encoding="utf-8"))
        curve = simulate(table, candidates, definition["allocator"])
        curve.to_csv(ROOT / directory / "backtest_v0.1.csv", index=False)
        enriched = {**spec, **{k: v for k, v in definition.items() if k != "allocator"}}
        results[spec["id"]] = strategy_metadata(enriched, curve)

    output = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "comparison_start_date": START.date().isoformat(),
        "strategies": results,
    }
    (ROOT / "strategies.json").write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Computed {len(results)} ChatGPT simulation curves from {START.date()}.")


if __name__ == "__main__":
    main()
