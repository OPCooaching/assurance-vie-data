from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import yaml

BASELINE = Path("data/benchmarks/bernard_origin.csv")
BERNARD_SIMULATION = Path("data/benchmarks/bernard_current_composition_5y.csv")
ACADEMIC = Path("data/academic/performance.csv")
STRATEGIES = Path("strategies")
OUT = Path("docs/data")
START_EUR = os.getenv("PORTFOLIO_START_EUR")


def read_csv(path):
    if not path.exists():
        return None
    data = pd.read_csv(path)
    return data if not data.empty and "date" in data.columns else None


def values_by_date(frame, column):
    if frame is None or column not in frame.columns:
        return {}
    dates = frame["date"].astype(str)
    values = pd.to_numeric(frame[column], errors="coerce")
    return {date: float(value) for date, value in zip(dates, values) if pd.notna(value)}


def load_existing_metadata(name):
    path = OUT / f"{name}.json"
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        strategies = data.get("strategies", [])
        return strategies if isinstance(strategies, list) else list(strategies.values())
    except (OSError, json.JSONDecodeError):
        return []


def load_actor_results(name):
    """Read actor-owned sources; generated public JSON is never an input source."""
    metadata_path = STRATEGIES / name / "strategies.json"
    metadata, curve_ids, curves = [], set(), []
    if metadata_path.exists():
        try:
            source = json.loads(metadata_path.read_text(encoding="utf-8"))
            raw = source.get("strategies", {})
            entries = raw.values() if isinstance(raw, dict) else raw
            for spec in entries:
                if not isinstance(spec, dict):
                    continue
                curve_ids.add(str(spec.get("id", "")))
                metadata.append({key: value for key, value in spec.items() if key != "courbe"})
                points = spec.get("courbe", [])
                by_date = {}
                for point in points:
                    try:
                        by_date[str(point["date"])] = float(point["valeur"])
                    except (KeyError, TypeError, ValueError):
                        continue
                if by_date:
                    curves.append({"label": str(spec.get("label") or spec.get("id")), "by_date": by_date})
        except (OSError, json.JSONDecodeError):
            pass

    # Claude backtests pre-date strategies.json curves. Read their actor-owned CSVs.
    for strategy_file in sorted((STRATEGIES / name).glob("*/strategy.yml")):
        try:
            spec = yaml.safe_load(strategy_file.read_text(encoding="utf-8"))
            strategy_id = str(spec["id"])
            if strategy_id in curve_ids:
                continue
            version = str(spec["active_version"])
            backtest = strategy_file.parent / f"backtest_{version}.csv"
            curve = read_csv(backtest)
            if curve is None or "valeur" not in curve.columns:
                continue
            curves.append({"label": str(spec.get("label") or strategy_id), "by_date": values_by_date(curve, "valeur")})
            metadata.append({
                "id": strategy_id,
                "label": str(spec.get("label") or strategy_id),
                "version": f"simulation {version}",
                "short": str(spec.get("main_rule") or ""),
                "objective": str(spec.get("objective") or ""),
                "main_rule": str(spec.get("main_rule") or ""),
                "details": "Résultat de backtest historique ; il ne constitue pas une décision réelle.",
                "status": str(spec.get("status") or "simulation historique"),
            })
        except (OSError, KeyError, TypeError, yaml.YAMLError):
            continue
    return metadata, curves


def aligned(label, by_date, dates):
    return {"label": label, "values": [by_date.get(date) for date in dates]}


def payload(series, dates, strategies=None):
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "start_eur": float(START_EUR) if START_EUR else None,
        "dates": dates,
        "series": series,
        "strategies": strategies or [],
    }


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    real = values_by_date(read_csv(BASELINE), "baseline")
    simulated = values_by_date(read_csv(BERNARD_SIMULATION), "simulation_current_composition")
    academic = read_csv(ACADEMIC)

    academic_dates = set(academic["date"].astype(str)) if academic is not None else set()
    real_dates = set(real)
    comparison_dates = sorted(academic_dates | real_dates)
    if not comparison_dates:
        comparison_dates = sorted(simulated)

    academic_series = [
        aligned("Bernard — composition actuelle simulée", simulated, comparison_dates),
        aligned("Bernard origine (suivi réel)", real, comparison_dates),
    ]
    if academic is not None:
        labels = {
            "sixty_forty": "60/40 mondial adapté",
            "permanent_portfolio": "Harry Browne adapté",
            "faber_trend": "Faber Trend 10 mois",
            "academic_momentum": "Momentum académique 12 mois",
        }
        for column, label in labels.items():
            if column in academic.columns:
                academic_series.append(aligned(label, values_by_date(academic, column), comparison_dates))
    (OUT / "academic.json").write_text(
        json.dumps(payload(academic_series, comparison_dates), ensure_ascii=False),
        encoding="utf-8",
    )

    for name in ("chatgpt", "claude"):
        metadata, curves = load_actor_results(name)
        if not metadata:
            metadata = load_existing_metadata(name)
        actor_dates = sorted(set(comparison_dates).union(
            date for curve in curves for date in curve["by_date"]
        ))
        actor_series = [
            aligned("Bernard — composition actuelle simulée", simulated, actor_dates),
            aligned("Bernard origine (suivi réel)", real, actor_dates),
        ]
        actor_series.extend(aligned(curve["label"], curve["by_date"], actor_dates) for curve in curves)
        (OUT / f"{name}.json").write_text(
            json.dumps(payload(actor_series, actor_dates, metadata), ensure_ascii=False),
            encoding="utf-8",
        )

    print("Dashboard JSON generated with all available actor curves.")


if __name__ == "__main__":
    main()
