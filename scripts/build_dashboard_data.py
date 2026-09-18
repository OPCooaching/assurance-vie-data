from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

BASELINE = Path("data/benchmarks/bernard_origin.csv")
ACADEMIC = Path("data/academic/performance.csv")
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
        return {
            "strategies": data.get("strategies", []),
        }
    except Exception:
        return {}


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


def main():
    OUT.mkdir(parents=True, exist_ok=True)

    baseline = read_series(BASELINE)
    academic = read_series(ACADEMIC)

    if baseline is not None:
        base_dates = baseline["date"].astype(str).tolist()
        base_values = pd.to_numeric(baseline["baseline"], errors="coerce").round(6).tolist()
        bernard = {"label": "Bernard origine", "values": base_values}
    else:
        base_dates = ["2026-09-07"]
        bernard = {"label": "Bernard origine", "values": [100.0]}

    series = [bernard]
    dates = base_dates

    if academic is not None:
        if not dates:
            dates = academic["date"].astype(str).tolist()
        labels = {
            "sixty_forty": "60/40 mondial adapté",
            "permanent_portfolio": "Harry Browne adapté",
            "faber_trend": "Faber Trend 10 mois",
            "academic_momentum": "Momentum académique 12 mois",
        }
        if dates:
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
        metadata = load_existing_metadata(name)
        (OUT / f"{name}.json").write_text(
            json.dumps(payload([bernard], dates, START_EUR, metadata), ensure_ascii=False),
            encoding="utf-8",
        )

    print("Dashboard JSON generated.")


if __name__ == "__main__":
    main()
