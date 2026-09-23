"""Rebuild the four ChatGPT tracking curves from 9 September 2026.

This is not a historical test: it starts from Bernard's tracking date, uses
the immutable v0.1 decisions already calculated from information available on
each decision date, then applies them to the actual subsequently published
fund prices.
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

START = pd.Timestamp("2026-09-09")
PRICES = Path("data/prices/daily.csv")
BASELINE = Path("data/benchmarks/bernard_origin.csv")
DECISIONS = Path("history/chatgpt/backtests")
OUT = Path("data/chatgpt")


def read_decisions(strategy_id):
    path = DECISIONS / strategy_id / "v0.1" / "decisions.jsonl"
    records = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]
    return sorted(records, key=lambda row: row["effective_date"] or "9999-12-31")


def curve_for_strategy(px, dates, strategy_id):
    decisions = read_decisions(strategy_id)
    weights, latest = {}, {}
    value, rows = 100.0, []
    previous = None
    for dt in dates:
        effective = str(dt.date())
        eligible = [row for row in decisions if row["effective_date"] and row["effective_date"] <= effective]
        if eligible:
            weights = {asset: float(weight) / 100.0 for asset, weight in eligible[-1]["target_allocation_percent"].items()}
            latest = dict(weights)
        if previous is not None:
            change = 0.0
            for asset, weight in weights.items():
                current, prior = px.at[dt, asset] if asset in px.columns else None, px.at[previous, asset] if asset in px.columns else None
                if pd.notna(current) and pd.notna(prior) and prior > 0:
                    change += weight * (float(current) / float(prior) - 1.0)
            value *= 1.0 + change
        rows.append((dt, value))
        previous = dt
    return pd.Series(dict(rows)), latest


def main():
    raw = pd.read_csv(PRICES, parse_dates=["date"])
    px = raw.pivot_table(index="date", columns="asset_id", values="close_eur", aggfunc="last").sort_index()
    benchmark = pd.read_csv(BASELINE, parse_dates=["date"])
    dates = [dt for dt in benchmark["date"] if dt >= START and dt in px.index]
    if not dates or dates[0] != START:
        raise ValueError("No common actual valuation on the requested tracking start date")
    strategies = sorted(path.parent.parent.name for path in DECISIONS.glob("*/v0.1/decisions.jsonl"))
    curves, allocations = {}, []
    for strategy_id in strategies:
        curve, latest = curve_for_strategy(px, dates, strategy_id)
        curves[strategy_id] = curve
        allocations.extend({"strategy_id": strategy_id, "asset_id": asset, "weight_pct": round(100.0 * weight, 6)} for asset, weight in latest.items())
    OUT.mkdir(parents=True, exist_ok=True)
    result = pd.DataFrame(curves)
    result.index.name = "date"
    result.to_csv(OUT / "performance.csv")
    pd.DataFrame(allocations).to_csv(OUT / "latest_allocations.csv", index=False)
    print(f"Rebuilt {len(strategies)} actual-price tracking curve(s) from {START.date()} through {dates[-1].date()}.")


if __name__ == "__main__":
    main()
