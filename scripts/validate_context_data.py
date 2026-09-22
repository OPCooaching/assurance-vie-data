from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import yaml

CONFIG = Path("config/context_series.yml")
DATA = Path("data/context/daily.csv")
MANIFEST = Path("data/context/manifest.json")


def fail(message: str) -> None:
    raise SystemExit(f"Context-data quality gate failed: {message}")


def main() -> None:
    if not CONFIG.exists() or not DATA.exists() or not MANIFEST.exists():
        fail("configuration, daily data or manifest is missing")
    config = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))
    expected = [entry["id"] for entry in config["series"]]
    frame = pd.read_csv(DATA)
    if frame.empty or list(frame.columns) != ["date", *expected]:
        fail("daily data is empty or columns do not match configuration")
    dates = pd.to_datetime(frame["date"], errors="coerce")
    if dates.isna().any() or not dates.is_monotonic_increasing or dates.duplicated().any():
        fail("dates must be valid, unique and ascending")
    weekly = {entry["id"] for entry in config["series"] if entry["frequency"] == "weekly"}
    counts: dict[str, int] = {}
    for series_id in expected:
        count = int(pd.to_numeric(frame[series_id], errors="coerce").notna().sum())
        if count == 0 or (series_id in weekly and count >= len(frame) * 0.4):
            fail(f"{series_id} has unusable frequency or no observations")
        counts[series_id] = count
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    if manifest.get("schema_version") != config["schema_version"] or not Path(manifest.get("snapshot_path", "")).exists():
        fail("manifest or dated snapshot is invalid")
    print(f"Context-data quality gate passed: {len(frame)} dates; " + ", ".join(f"{key}={value}" for key, value in counts.items()))


if __name__ == "__main__":
    main()
