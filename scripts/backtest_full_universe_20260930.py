#!/usr/bin/env python3
"""Mechanical full-universe strategy research for the Altaprofits contract.

Research only. No live allocation is changed by this script.

Universe = every support with usable EUR-normalised daily prices and enough
history, regardless of whether the support is an Action, OPCVM/FI or ETF.
Illiquid/non-market supports without a valid daily market series simply cannot
enter these price-driven tests.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

PRICES = Path("data/prices/daily.csv")
UNIVERSE = Path("config/universe.csv")
OUT_DIR = Path("history/chatgpt/full-universe-research/2026-09-30")

DEFENSIVE = "LU0290358497"
WORLD = "FR0010315770"
MIN_HISTORY = 260
LOOKBACK_12M = 252
LOOKBACKS = (63, 126, 252)
TREND_DAYS = 200
CORR_DAYS = 60


def load():
    raw = pd.read_csv(PRICES, parse_dates=["date"])
    if "close_eur" not in raw.columns:
        raise RuntimeError("close_eur is required")
    px = raw.pivot_table(index="date", columns="asset_id", values="close_eur", aggfunc="last").sort_index().ffill()
    universe = pd.read_csv(UNIVERSE)
    return px, universe


def monthly_decision_dates(index: pd.DatetimeIndex) -> list[pd.Timestamp]:
    series = pd.Series(index, index=index)
    return [pd.Timestamp(x) for x in series.groupby(index.to_period("M")).last().tolist()]


def valid_assets(px, dt, candidates):
    history = px.loc[:dt, candidates]
    if len(history) <= MIN_HISTORY:
        return []
    last = history.iloc[-1]
    prior = history.iloc[-1 - LOOKBACK_12M]
    valid = last.notna() & prior.notna() & (last > 0) & (prior > 0)
    return valid[valid].index.tolist()


def score_12m(px, dt, assets):
    h = px.loc[:dt, assets]
    last, prior = h.iloc[-1], h.iloc[-1 - LOOKBACK_12M]
    return (last / prior - 1.0).replace([np.inf, -np.inf], np.nan).dropna()


def score_multi(px, dt, assets):
    h = px.loc[:dt, assets]
    last = h.iloc[-1]
    score = pd.Series(0.0, index=assets)
    valid = pd.Series(True, index=assets)
    for lookback in LOOKBACKS:
        component = last / h.iloc[-1 - lookback] - 1.0
        score += component.fillna(0.0)
        valid &= component.notna()
    score /= len(LOOKBACKS)
    trend = last > h.tail(TREND_DAYS).mean()
    return score[valid & trend & (score > 0)].dropna()


def inverse_vol_weights(px, dt, selected):
    if not selected:
        return {DEFENSIVE: 1.0}
    rets = px.loc[:dt, selected].pct_change(fill_method=None).tail(60)
    vol = rets.std(ddof=0).replace(0, np.nan).dropna()
    selected = [a for a in selected if a in vol.index]
    if not selected:
        return {DEFENSIVE: 1.0}
    inv = 1.0 / vol[selected]
    weights = inv / inv.sum()
    return {a: float(weights[a]) for a in selected}


def allocation_mom12(px, dt, assets):
    score = score_12m(px, dt, assets)
    winners = score[score > 0].sort_values(ascending=False).head(5).index.tolist()
    return ({a: 1.0 / len(winners) for a in winners} if winners else {DEFENSIVE: 1.0},
            {"selected": winners})


def allocation_multi(px, dt, assets):
    score = score_multi(px, dt, assets)
    winners = score.sort_values(ascending=False).head(5).index.tolist()
    return ({a: 1.0 / len(winners) for a in winners} if winners else {DEFENSIVE: 1.0},
            {"selected": winners})


def allocation_invvol(px, dt, assets):
    score = score_multi(px, dt, assets)
    winners = score.sort_values(ascending=False).head(8).index.tolist()
    return inverse_vol_weights(px, dt, winners), {"selected": winners}


def allocation_diversified(px, dt, assets):
    score = score_multi(px, dt, assets)
    ranked = score.sort_values(ascending=False).head(25).index.tolist()
    if not ranked:
        return {DEFENSIVE: 1.0}, {"selected": []}
    history = px.loc[:dt, ranked].pct_change(fill_method=None).tail(CORR_DAYS)
    corr = history.corr().abs()
    selected = []
    for asset in ranked:
        if not selected:
            selected.append(asset)
        else:
            vals = corr.loc[asset, selected].dropna()
            if vals.empty or bool((vals <= 0.75).all()):
                selected.append(asset)
        if len(selected) >= 6:
            break
    if not selected:
        return {DEFENSIVE: 1.0}, {"selected": []}
    return {a: 1.0 / len(selected) for a in selected}, {"selected": selected}


def run(px, dates, candidates, allocator):
    decision_set = set(dates)
    scheduled = {}
    decisions = []
    active = {}
    value = 100.0
    rows = []
    prev = None
    turnover = 0.0

    for pos, dt in enumerate(px.index):
        if dt in scheduled:
            target = scheduled[dt]
            universe = set(active) | set(target)
            turnover += 0.5 * sum(abs(target.get(a, 0.0) - active.get(a, 0.0)) for a in universe)
            active = target

        prices = px.loc[dt]
        if prev is not None and active:
            prior = px.loc[prev]
            ret = 0.0
            for asset, weight in active.items():
                current = prices.get(asset)
                previous = prior.get(asset)
                if pd.notna(current) and pd.notna(previous) and previous > 0:
                    ret += float(weight) * (float(current) / float(previous) - 1.0)
            value *= 1.0 + ret

        if dt in decision_set:
            eligible = valid_assets(px, dt, candidates)
            target, detail = allocator(px, dt, eligible)
            total = sum(target.values())
            if total <= 0:
                raise RuntimeError("empty target")
            target = {a: float(w) / total for a, w in target.items() if float(w) > 0}
            if pos + 1 < len(px.index):
                effective = px.index[pos + 1]
                scheduled[effective] = target
                decisions.append({
                    "decision_date": dt.date().isoformat(),
                    "effective_date": effective.date().isoformat(),
                    "target_allocation_percent": {a: round(w * 100, 6) for a, w in target.items()},
                    **detail,
                })
        if active:
            rows.append((dt, value))
        prev = dt

    curve = pd.Series(dict(rows)).sort_index()
    return curve, decisions, turnover


def metrics(curve, decisions, turnover):
    if curve.empty:
        raise RuntimeError("empty curve")
    values = curve
    rets = values.pct_change().dropna()
    days = max((curve.index[-1] - curve.index[0]).days, 1)
    years = days / 365.25
    rolling = values / values.shift(252) - 1.0
    return {
        "start": curve.index[0].date().isoformat(),
        "end": curve.index[-1].date().isoformat(),
        "final_value": round(float(values.iloc[-1]), 4),
        "annualized_return": round(float((values.iloc[-1] / values.iloc[0]) ** (1 / max(years, 1/365.25)) - 1), 6),
        "annualized_volatility": round(float(rets.std(ddof=0) * np.sqrt(252)), 6) if len(rets) else 0.0,
        "max_drawdown": round(float((values / values.cummax() - 1.0).min()), 6),
        "positive_12m_windows_pct": round(float((rolling.dropna() > 0).mean() * 100), 2) if rolling.notna().any() else None,
        "decisions": len(decisions),
        "cumulative_turnover": round(float(turnover), 4),
    }


def main():
    px, universe = load()
    if DEFENSIVE not in px.columns:
        raise RuntimeError("defensive asset missing")
    # All market-priced supports are eligible. This intentionally does not
    # filter to ETFs. The category is kept only for reporting.
    counts = px.notna().sum()
    candidates = [
        asset for asset in px.columns
        if asset != DEFENSIVE and int(counts.get(asset, 0)) >= MIN_HISTORY
    ]
    if len(candidates) < 20:
        raise RuntimeError("too few full-universe candidates")

    decisions = [d for d in monthly_decision_dates(px.index) if px.index.get_loc(d) >= MIN_HISTORY]
    jobs = {
        "momentum_12m_top5_full_universe": allocation_mom12,
        "momentum_multi_top5_full_universe": allocation_multi,
        "momentum_multi_invvol_top8_full_universe": allocation_invvol,
        "momentum_multi_corr_diversified_full_universe": allocation_diversified,
    }

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    curves = {}
    results = []
    latest = {}
    names = universe.set_index("asset_id")["support_name"].to_dict()
    cats = universe.set_index("asset_id")["category"].to_dict()

    for strategy_id, allocator in jobs.items():
        curve, decision_rows, turnover = run(px, decisions, candidates, allocator)
        curves[strategy_id] = curve
        m = metrics(curve, decision_rows, turnover)
        last = decision_rows[-1]["target_allocation_percent"] if decision_rows else {}
        latest[strategy_id] = [
            {
                "asset_id": a,
                "name": names.get(a, a),
                "category": cats.get(a, ""),
                "weight_pct": w,
            }
            for a, w in sorted(last.items(), key=lambda item: -item[1])
        ]
        results.append({"strategy_id": strategy_id, "metrics": m})

        with (OUT_DIR / f"{strategy_id}-decisions.jsonl").open("w", encoding="utf-8") as handle:
            for row in decision_rows:
                handle.write(json.dumps(row, ensure_ascii=False) + "\n")

    frame = pd.concat(curves, axis=1)
    frame.index.name = "date"
    frame.to_csv(OUT_DIR / "performance.csv")

    eligible_meta = universe.loc[universe["asset_id"].isin(candidates), ["asset_id", "category"]]
    category_counts = eligible_meta["category"].value_counts().to_dict()
    report = {
        "status": "research_backtest",
        "as_of": "2026-09-30",
        "universe_rule": "all supports with valid EUR-normalised daily prices and >=260 observations; no ETF-only filter",
        "eligible_assets": len(candidates),
        "eligible_by_category": {str(k): int(v) for k, v in category_counts.items()},
        "strategies": results,
        "latest_allocations": latest,
        "limitations": [
            "current contract universe only",
            "mechanical price-driven research, not a recommendation",
            "free arbitration cost assumption",
            "fund euro is not given an invented daily return",
            "survivorship/current-universe bias remains possible",
        ],
    }
    (OUT_DIR / "results.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    md = [
        "# Recherche stratégies — univers complet — 30/09/2026",
        "",
        "Ces tests utilisent tous les supports disposant d'une série de prix EUR exploitable et d'au moins 260 observations. Aucun filtre ETF n'est appliqué.",
        "",
        f"Supports éligibles au test : **{len(candidates)}**.",
        "",
        "## Résultats",
        "",
        "| Stratégie | Valeur finale | Rendement annualisé | Volatilité | Drawdown max | Fenêtres 12m positives |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for row in results:
        m=row["metrics"]
        md.append(
            f"| {row['strategy_id']} | {m['final_value']:.2f} | {100*m['annualized_return']:.1f}% | "
            f"{100*m['annualized_volatility']:.1f}% | {100*m['max_drawdown']:.1f}% | "
            f"{m['positive_12m_windows_pct'] if m['positive_12m_windows_pct'] is not None else 'n/a'}% |"
        )
    md += [
        "",
        "Ces résultats sont des backtests de recherche. Ils ne remplacent pas le suivi réel de Bernard et ne doivent pas être rétroactivement présentés comme des décisions prises à l'époque.",
        "",
    ]
    (OUT_DIR / "README.md").write_text("\n".join(md), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()
