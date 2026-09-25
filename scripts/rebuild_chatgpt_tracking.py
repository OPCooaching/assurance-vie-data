"""Rebuild ChatGPT paper-tracking curves from published market prices.

A-D reuse their preserved rule decisions. New weekly decisions, including E,
are read from one append-only decision archive. When a support's close is
delayed, the curve temporarily keeps its last published close, exactly as the
Bernard dashboard does. No order is sent to Bernard's contract.
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

START = pd.Timestamp("2026-09-09")
PRICES = Path("data/prices/daily.csv")
BASELINE = Path("data/benchmarks/bernard_origin.csv")
LEGACY_DECISIONS = Path("history/chatgpt/backtests")
WEEKLY_DECISIONS = Path("history/chatgpt/decisions")
OUT = Path("data/chatgpt")


def legacy_decisions(strategy_id: str):
    path = LEGACY_DECISIONS / strategy_id / "v0.1" / "decisions.jsonl"
    if not path.exists():
        return []
    records = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]
    return [
        {
            "effective_date": row.get("effective_date"),
            "target_allocation_percent": row.get("target_allocation_percent", {}),
        }
        for row in records
    ]


def weekly_decisions(strategy_id: str):
    if not WEEKLY_DECISIONS.exists():
        return []
    records = []
    for path in sorted(WEEKLY_DECISIONS.rglob("*.json")):
        try:
            row = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if row.get("status") == "template_not_a_decision" or row.get("strategy_id") != strategy_id:
            continue
        records.append(
            {
                "effective_date": row.get("effective_valuation_date"),
                "target_allocation_percent": row.get("target_allocation_percent", {}),
            }
        )
    return records


def read_decisions(strategy_id: str):
    records = weekly_decisions(strategy_id)
    if not records:
        records = legacy_decisions(strategy_id)
    return sorted(
        (row for row in records if row.get("effective_date") and row.get("target_allocation_percent")),
        key=lambda row: row["effective_date"],
    )


def strategy_ids():
    legacy = {path.parent.parent.name for path in LEGACY_DECISIONS.glob("*/v0.1/decisions.jsonl")}
    weekly = set()
    if WEEKLY_DECISIONS.exists():
        for path in WEEKLY_DECISIONS.rglob("*.json"):
            try:
                row = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            if row.get("status") != "template_not_a_decision" and row.get("strategy_id"):
                weekly.add(row["strategy_id"])
    return sorted(legacy | weekly)


def curve_for_strategy(px, dates, strategy_id):
    # The dashboard may include a provisional valuation date. Forward filling
    # only uses a support's prior published close; it never pulls a later price
    # back into an earlier day.
    px = px.reindex(dates).ffill()
    decisions = read_decisions(strategy_id)
    weights, latest = {}, {}
    value, rows, previous = None, [], None
    for dt in dates:
        effective = str(dt.date())
        eligible = [row for row in decisions if row["effective_date"] <= effective]
        if not eligible:
            rows.append((dt, None))
            previous = dt
            continue
        newest = eligible[-1]
        weights = {
            asset: float(weight) / 100.0
            for asset, weight in newest["target_allocation_percent"].items()
        }
        latest = dict(weights)
        if value is None:
            value = 100.0
        elif previous is not None:
            change = 0.0
            for asset, weight in weights.items():
                current = px.at[dt, asset] if asset in px.columns else None
                prior = px.at[previous, asset] if asset in px.columns else None
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

    curves, allocations = {}, []
    for strategy_id in strategy_ids():
        curve, latest = curve_for_strategy(px, dates, strategy_id)
        curves[strategy_id] = curve
        allocations.extend(
            {"strategy_id": strategy_id, "asset_id": asset, "weight_pct": round(100.0 * weight, 6)}
            for asset, weight in latest.items()
        )

    OUT.mkdir(parents=True, exist_ok=True)
    result = pd.DataFrame(curves)
    result.index.name = "date"
    result.to_csv(OUT / "performance.csv")
    pd.DataFrame(allocations).to_csv(OUT / "latest_allocations.csv", index=False)
    print(f"Rebuilt {len(curves)} ChatGPT comparison curve(s) through {dates[-1].date()} using published closes and explicit temporary carry-forward when a close is delayed.")


if __name__ == "__main__":
    main()
