from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

BASELINE = Path("data/benchmarks/bernard_origin.csv")
ACADEMIC = Path("data/academic/performance.csv")
STRATEGIES = Path("strategies")
OUT = Path("docs/data")
START_EUR = os.getenv("PORTFOLIO_START_EUR")


def read_series(path: Path):
    if not path.exists():
        return None
    df = pd.read_csv(path)
    if df.empty or "date" not in df.columns:
        return None
    return df


def load_existing_metadata(name: str):
    path = OUT / f"{name}.json"
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return {"strategies": data.get("strategies", {})}
    except Exception:
        return {}


def load_actor_results(name: str):
    """Read an actor-owned result file without allowing it to edit generated JSON."""
    path = STRATEGIES / name / "strategies.json"
    if not path.exists():
        return None, []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None, []

    strategies = data.get("strategies", {})
    curves = []
    if not isinstance(strategies, dict):
        return strategies, curves

    for strategy_id, spec in sorted(strategies.items()):
        points = spec.get("courbe", [])
        values = {}
        for point in points:
            try:
                date = str(point["date"])
                value = float(point["valeur"])
            except (KeyError, TypeError, ValueError):
                continue
            values[date] = value
        if values:
            curves.append({
                "label": str(spec.get("label") or strategy_id),
                "by_date": values,
            })
    return strategies, curves


def payload(series_map, dates, start_eur=None, extra=None):
    data = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "start_eur": float(start_eur) if start_eur else None,
        "dates": [str(x) for x in dates],
        "series": series_map,
    }
    if extra:
        data.update(extra)
    return data


def aligned_series(label, values_by_date, dates):
    return {
        "label": label,
        "values": [values_by_date.get(date) for date in dates],
    }


def main():
    OUT.mkdir(parents=True, exist_ok=True)

    baseline = read_series(BASELINE)
    academic = read_series(ACADEMIC)

    if baseline is not None:
        base_dates = baseline["date"].astype(str).tolist()
        base_values = pd.to_numeric(baseline["baseline"], errors="coerce").round(6).tolist()
        baseline_by_date = dict(zip(base_dates, base_values))
    else:
        base_dates = ["2026-09-07"]
        baseline_by_date = {"2026-09-07": 100.0}

    bernard = {"label": "Bernard origine", "values": [baseline_by_date[d] for d in base_dates]}
    series = [bernard]
    dates = base_dates

    if academic is not None:
        labels = {
            "sixty_forty": "60/40 mondial adapté",
            "permanent_portfolio": "Harry Browne adapté",
            "faber_trend": "Faber Trend 10 mois",
            "academic_momentum": "Momentum académique 12 mois",
        }
        merged = pd.DataFrame({"date": dates})
        merged["date"] = merged["date"].astype(str)
        a = academic.copy()
        a["date"] = a["date"].astype(str)
        merged = merged.merge(a, on="date", how="left")
        for col, label in labels.items():
            if col in merged.columns:
                vals = pd.to_numeric(merged[col], errors="coerce").round(6)
                series.append({
                    "label": label,
                    "values": [None if pd.isna(x) else float(x) for x in vals],
                })

    (OUT / "academic.json").write_text(
        json.dumps(payload(series, dates, START_EUR), ensure_ascii=False),
        encoding="utf-8",
    )

    for name in ("chatgpt", "claude"):
        source_strategies, actor_curves = load_actor_results(name)
        metadata = (
            {"strategies": source_strategies}
            if source_strategies is not None
            else load_existing_metadata(name)
        )
        actor_dates = sorted(set(base_dates).union(
            date for curve in actor_curves for date in curve["by_date"]
        ))
        actor_series = [aligned_series("Bernard origine", baseline_by_date, actor_dates)]
        actor_series.extend(
            aligned_series(curve["label"], curve["by_date"], actor_dates)
            for curve in actor_curves
        )
        (OUT / f"{name}.json").write_text(
            json.dumps(payload(actor_series, actor_dates, START_EUR, metadata), ensure_ascii=False),
            encoding="utf-8",
        )

    print("Dashboard JSON generated.")


if __name__ == "__main__":
    main()
