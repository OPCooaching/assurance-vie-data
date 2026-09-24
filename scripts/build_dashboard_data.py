from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import yaml

BASELINE = Path("data/benchmarks/bernard_origin.csv")
ACADEMIC = Path("data/academic/performance.csv")
ACADEMIC_CFG = Path("config/academic_strategies.yml")
UNIVERSE = Path("config/universe.csv")
STRATEGIES = Path("strategies")
OUT = Path("docs/data")
BASELINE_CFG = Path("config/baseline_bernard.yml")


def initial_portfolio_value_eur():
    if not BASELINE_CFG.exists():
        return None
    config = yaml.safe_load(BASELINE_CFG.read_text(encoding="utf-8")) or {}
    value = config.get("initial_portfolio_value_eur")
    return float(value) if value is not None else None


def read_series(path: Path):
    if not path.exists():
        return None
    df = pd.read_csv(path)
    if df.empty or "date" not in df.columns:
        return None
    return df


def asset_names():
    if not UNIVERSE.exists():
        return {}
    frame = pd.read_csv(UNIVERSE)
    return dict(zip(frame["asset_id"], frame["support_name"]))


def attach_allocations(strategies, actor, names):
    """Attach the current workflow allocation to its public strategy description."""
    path = Path("data") / actor / "latest_allocations.csv"
    if not path.exists() or not isinstance(strategies, dict):
        return strategies
    frame = pd.read_csv(path)
    if frame.empty or not {"strategy_id", "asset_id", "weight_pct"}.issubset(frame.columns):
        return strategies
    for strategy_id, group in frame.groupby("strategy_id"):
        candidates = (strategy_id, strategy_id.replace("_", "-"), strategy_id.replace("-", "_"))
        target = next((key for key in candidates if key in strategies), None)
        if target is None:
            continue
        strategies[target]["holdings"] = [
            {
                "asset_id": str(row.asset_id),
                "name": str(names.get(row.asset_id, row.asset_id)),
                "weight_pct": round(float(row.weight_pct), 2),
            }
            for row in group.sort_values("weight_pct", ascending=False).itertuples()
            if float(row.weight_pct) > 0
        ]
    return strategies


def academic_metadata():
    if not ACADEMIC_CFG.exists():
        return {}
    cfg = yaml.safe_load(ACADEMIC_CFG.read_text(encoding="utf-8")) or {}
    rules = {
        "static": "Allocation fixe ; rééquilibrage à la fréquence indiquée.",
        "faber_sma10": "Chaque fin de mois, l’indice monde est détenu seulement au-dessus de sa moyenne 10 mois ; sinon la poche va au monétaire.",
        "momentum_12m": "Chaque fin de mois, les cinq ETF au momentum 12 mois positif le plus élevé sont détenus ; sinon la poche va au monétaire.",
    }
    result = {}
    for strategy_id, spec in (cfg.get("strategies") or {}).items():
        frequency = spec.get("rebalance") or spec.get("signal_frequency") or "selon la règle"
        frequency = {"monthly": "mensuelle", "annual": "annuelle"}.get(str(frequency), frequency)
        result[strategy_id] = {
            "label": spec.get("label") or strategy_id,
            "version": "règle de référence",
            "resume": "Référence académique suivie avec les prix réellement observés depuis le 09/09/2026.",
            "regle": rules.get(spec.get("type"), "Règle documentée dans la configuration académique."),
            "frequence": f"Revue ou rééquilibrage : {frequency}.",
            "status": "live_paper_tracking",
            "statut_public": "Suivi quotidien depuis le 09/09/2026. La composition ci-dessous est celle de la dernière revue disponible.",
        }
    return result


def load_existing_metadata(name: str):
    path = OUT / f"{name}.json"
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return {"strategies": data.get("strategies", {})}
    except Exception:
        return {}


def load_decision_history(name: str):
    """Read immutable decisions for display; malformed records stay private."""
    root = Path("history") / name / "decisions"
    if not root.exists():
        return []
    records = []
    for path in sorted(root.rglob("*.json")):
        try:
            record = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(record, dict) or record.get("status") == "template_not_a_decision":
            continue
        if not record.get("strategy_id") or not record.get("decision_type"):
            continue
        records.append({
            "decision_id": record.get("decision_id"),
            "date": record.get("effective_valuation_date") or record.get("decided_at_utc"),
            "strategy_id": record["strategy_id"],
            "strategy_version": record.get("strategy_version"),
            "decision_type": record["decision_type"],
            "rationale": record.get("rationale"),
            "target_allocation_percent": record.get("target_allocation_percent", {}),
            "warnings": record.get("warnings", []),
        })
    return sorted(records, key=lambda item: str(item.get("date") or ""), reverse=True)


def load_actor_performance(name: str, strategies):
    """Read daily live paper-tracking values produced by the common workflow."""
    path = Path("data") / name / "performance.csv"
    frame = read_series(path)
    if frame is None:
        return []

    labels = {
        "chatgpt-momentum-mensuel": "ChatGPT A — Momentum mensuel multi-horizons",
        "chatgpt-volatilite-pilotee": "ChatGPT B — Exposition pilotée par le risque",
        "chatgpt-regime-macro-financier": "ChatGPT C — Régime macro-financier",
        "chatgpt-hybride-selection-protection": "ChatGPT D — Sélection mensuelle et protection hebdomadaire",
        "chatgpt-weekly-open-analysis": "ChatGPT E — Analyse hebdomadaire complète",
        "chatgpt_impulsion": "ChatGPT A — Momentum hebdomadaire",
        "chatgpt_adaptative": "ChatGPT B — Momentum adaptatif",
        "chatgpt_rotation_diversifiee": "ChatGPT C — Momentum diversifié",
        "claude_socle_satellites": "Claude A — Socle mondial et satellites",
        "claude_risque_cible": "Claude B — Risque cible constant",
        "claude_double_filtre": "Claude C — Tendance confirmée par l’ampleur",
        "claude_momentum_multi": "Claude D — Momentum multi-horizon",
        "claude_momentum_prudent": "Claude E — Momentum sous garde-fou",
    }
    result = []
    for column in frame.columns:
        if column == "date":
            continue
        points = {}
        for _, row in frame[["date", column]].dropna().iterrows():
            points[str(row["date"])] = float(row[column])
        if points:
            result.append({"label": labels.get(column, column), "by_date": points})
    return result


def load_actor_results(name: str):
    """Read an actor-owned result file without allowing it to edit generated JSON."""
    path = STRATEGIES / name / "strategies.json"
    if not path.exists():
        return None, []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None, []

    # Strategy files are documentation and research artefacts. They may
    # never supply a public performance curve: only workflow-generated
    # data/<actor>/performance.csv files are accepted below.  Publish a
    # compact description only; historical backtests, simulated decisions and
    # allocations remain in the actor's private research area.
    raw = data.get("strategies", {})
    public = {}
    allowed = (
        "label", "version", "resume", "objectif", "regle", "frequence", "faiblesse",
        "tracking_start", "status", "statut_public",
    )
    if isinstance(raw, dict):
        for strategy_id, spec in raw.items():
            if not isinstance(spec, dict):
                continue
            item = {field: spec[field] for field in allowed if field in spec}
            item["frequence"] = item.get("frequence") or (
                "Revue hebdomadaire, chaque lundi ; l’allocation décidée s’applique à la valorisation suivante."
            )
            item.setdefault("status", "live_paper_tracking")
            if item["status"] == "live_paper_tracking":
                item.setdefault("statut_public", (
                    "Suivi quotidien depuis le 09/09/2026 sur prix réellement observés. "
                    "Aucune courbe antérieure ni résultat de backtest n’est publié ici."
                ))
            else:
                item.setdefault("statut_public", "Hypothèse documentée ; pas encore de suivi de portefeuille.")
            public[strategy_id] = item
    return public, []


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
    start_eur = initial_portfolio_value_eur()

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

    academic_info = attach_allocations(academic_metadata(), "academic", asset_names())
    (OUT / "academic.json").write_text(
        json.dumps(payload(series, dates, start_eur, {"strategies": academic_info}), ensure_ascii=False),
        encoding="utf-8",
    )

    for name in ("chatgpt", "claude"):
        source_strategies, actor_curves = load_actor_results(name)
        metadata = (
            {"strategies": source_strategies}
            if source_strategies is not None
            else load_existing_metadata(name)
        )
        metadata["strategies"] = attach_allocations(
            metadata.get("strategies", {}), name, asset_names()
        )
        metadata["decision_history"] = load_decision_history(name)
        # Only workflow-produced tracking files may add public actor curves.
        # Their dates begin at the declared live-tracking start, never in a
        # reconstructed historical period.
        actor_curves.extend(load_actor_performance(name, metadata.get("strategies", {})))
        actor_dates = sorted(set(base_dates).union(
            date for curve in actor_curves for date in curve["by_date"]
        ))
        actor_series = [aligned_series("Bernard origine", baseline_by_date, actor_dates)]
        actor_series.extend(
            aligned_series(curve["label"], curve["by_date"], actor_dates)
            for curve in actor_curves
        )
        (OUT / f"{name}.json").write_text(
            json.dumps(payload(actor_series, actor_dates, start_eur, metadata), ensure_ascii=False),
            encoding="utf-8",
        )

    # The public page loads this JavaScript companion directly. It avoids a
    # browser-specific block on JSON fetches while preserving chatgpt.json as
    # the machine-readable source.
    chatgpt_payload = (OUT / "chatgpt.json").read_text(encoding="utf-8")
    (OUT / "chatgpt-data.js").write_text(
        "window.CHATGPT_DATA = " + chatgpt_payload + ";\n",
        encoding="utf-8",
    )
    print("Dashboard JSON generated.")


if __name__ == "__main__":
    main()
