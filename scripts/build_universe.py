from __future__ import annotations

import csv
from pathlib import Path

import pandas as pd

CONFIG = Path("config")
PARTS = sorted(CONFIG.glob("universe_part_*.csv"))
UNIVERSE = CONFIG / "universe.csv"
SYMBOL_MAP = CONFIG / "symbol_map.csv"

# Keep market metadata in the mapping, not in a strategy-specific file.  The
# daily update uses these fields to decide whether a Yahoo quote can safely be
# converted to EUR before it enters the shared price history.
MAP_FIELDS = [
    "asset_id", "isin", "symbol", "provider", "status", "last_checked",
    "quote_currency", "exchange", "currency_status", "metadata_checked",
    "history_status", "history_start", "history_end", "history_checked",
    "notes",
]


def main():
    if not PARTS:
        raise SystemExit("No universe_part_*.csv files found.")

    frames = [pd.read_csv(p, dtype=str).fillna("") for p in PARTS]
    universe = pd.concat(frames, ignore_index=True)
    universe = universe.drop_duplicates(subset=["asset_id"], keep="first")
    universe.to_csv(UNIVERSE, index=False)

    existing = {}
    if SYMBOL_MAP.exists():
        with SYMBOL_MAP.open(newline="", encoding="utf-8") as f:
            existing = {r["asset_id"]: r for r in csv.DictReader(f)}

    rows = []
    for _, asset in universe.iterrows():
        aid = asset["asset_id"]
        isin = asset.get("isin", "") or ""
        old = existing.get(aid, {})
        standard_isin = len(isin) == 12 and isin[:2].isalpha()

        if old:
            row = {k: old.get(k, "") for k in MAP_FIELDS}
            row["asset_id"] = aid
            row["isin"] = isin
        else:
            row = {
                "asset_id": aid,
                "isin": isin,
                "symbol": "",
                "provider": "",
                "status": "unresolved" if standard_isin else "manual",
                "last_checked": "",
                "notes": "" if standard_isin else "Non-standard identifier or non-market support",
            }
        rows.append(row)

    with SYMBOL_MAP.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=MAP_FIELDS, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)

    print(f"Universe: {len(universe)} assets; symbol map: {len(rows)} rows.")


if __name__ == "__main__":
    main()
