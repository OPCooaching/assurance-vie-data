from __future__ import annotations

"""Fail the refresh when an external context input is absent or stale."""

from pathlib import Path

import pandas as pd
import yaml


CONFIG = Path("config/context_series.yml")
CONTEXT = Path("data/context/daily.csv")
# Some daily FRED series arrive with a multi-day publisher delay. Ten calendar
# days detects a prolonged outage without treating a documented publication lag
# as a fabricated missing value.
MAX_AGE_DAYS = {"daily": 10, "daily_business": 10, "daily_7d": 10, "weekly": 14}


def main() -> None:
    if not CONFIG.exists() or not CONTEXT.exists():
        raise SystemExit("Context-data quality gate: configuration or data file is missing.")

    config = yaml.safe_load(CONFIG.read_text(encoding="utf-8")) or {}
    series = config.get("series") or []
    if not series:
        raise SystemExit("Context-data quality gate: no configured series.")

    frame = pd.read_csv(CONTEXT)
    if "date" not in frame.columns or frame.empty:
        raise SystemExit("Context-data quality gate: missing or empty date column.")
    frame["date"] = pd.to_datetime(frame["date"], errors="coerce")
    if frame["date"].isna().any() or frame["date"].duplicated().any():
        raise SystemExit("Context-data quality gate: invalid or duplicate dates.")

    today = pd.Timestamp.now(tz="UTC").normalize().tz_localize(None)
    messages: list[str] = []
    for item in series:
        identifier = item.get("id", "unknown")
        column = item.get("column", identifier)
        frequency = item.get("frequency")
        if column not in frame.columns:
            raise SystemExit(f"Context-data quality gate: {identifier} column is missing.")
        if frequency not in MAX_AGE_DAYS:
            raise SystemExit(f"Context-data quality gate: {identifier} has invalid frequency.")

        values = pd.to_numeric(frame[column], errors="coerce")
        valid_dates = frame.loc[values.notna(), "date"]
        if valid_dates.empty:
            raise SystemExit(f"Context-data quality gate: {identifier} has no usable observation.")

        latest = valid_dates.max().normalize()
        age_days = int((today - latest).days)
        allowed = MAX_AGE_DAYS[frequency]
        if age_days > allowed:
            raise SystemExit(
                f"Context-data quality gate: {identifier} is {age_days} days old "
                f"(maximum {allowed})."
            )
        messages.append(f"{identifier}={latest.date().isoformat()} ({age_days}d)")

    print("Context-data quality gate passed: " + "; ".join(messages))


if __name__ == "__main__":
    main()
