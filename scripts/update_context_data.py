"""Download ChatGPT's external context series without inventing observations.

This is deliberately separate from data/macro/, which is reserved for Claude's
series.  The output keeps every publisher observation on its release date.
Weekly data stay blank on other dates: strategies must decide explicitly how
and when a released value may be used.
"""
from __future__ import annotations

from datetime import date
from io import StringIO
from pathlib import Path

import pandas as pd
import requests
import yaml

CONFIG = Path("config/context_series.yml")
OUT = Path("data/context/daily.csv")
WINDOW_YEARS = 5
FRED_CSV = "https://fred.stlouisfed.org/graph/fredgraph.csv"


def load_series() -> list[dict]:
    with CONFIG.open(encoding="utf-8") as handle:
        configured = yaml.safe_load(handle) or {}
    series = configured.get("series", [])
    if not series:
        raise ValueError("No external context series configured.")
    required = {"id", "column", "frequency", "source", "url"}
    for item in series:
        missing = required - item.keys()
        if missing:
            raise ValueError(f"Context series is incomplete: missing {sorted(missing)}")
        if item["frequency"] not in {"daily", "weekly"}:
            raise ValueError(f"Unsupported frequency for {item['id']}: {item['frequency']}")
    return series


def download(item: dict, start: pd.Timestamp) -> pd.Series:
    response = requests.get(
        FRED_CSV,
        params={"id": item["id"], "cosd": start.date().isoformat()},
        timeout=30,
    )
    response.raise_for_status()
    raw = pd.read_csv(StringIO(response.text))
    if "observation_date" not in raw.columns or item["id"] not in raw.columns:
        raise ValueError(f"Unexpected FRED response for {item['id']}.")
    result = raw.rename(columns={"observation_date": "date", item["id"]: item["column"]})
    result["date"] = pd.to_datetime(result["date"], errors="coerce")
    result[item["column"]] = pd.to_numeric(result[item["column"]], errors="coerce")
    result = result.dropna(subset=["date", item["column"]])
    result = result.loc[result["date"] >= start, ["date", item["column"]]]
    if result.empty:
        raise ValueError(f"No usable observations returned for {item['id']}.")
    return result.set_index("date")[item["column"]]


def main() -> None:
    series = load_series()
    start = pd.Timestamp(date.today()) - pd.DateOffset(years=WINDOW_YEARS)
    observations = []
    for item in series:
        print(f"Downloading {item['id']} ({item['frequency']}).")
        observations.append(download(item, start))

    # Outer join preserves every date genuinely published by at least one source.
    # No calendar is created and no weekly observation is carried into weekdays.
    output = pd.concat(observations, axis=1, join="outer").sort_index()
    output.index.name = "date"
    output = output.reset_index()
    output["date"] = output["date"].dt.date.astype(str)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    output.to_csv(OUT, index=False, float_format="%.10g")
    print(f"Saved {len(output)} published dates and {len(series)} context series.")


if __name__ == "__main__":
    main()
