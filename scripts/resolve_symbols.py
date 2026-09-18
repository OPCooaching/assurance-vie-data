from __future__ import annotations

import csv
import os
import time
from datetime import date
from pathlib import Path

import requests

MAP = Path("config/symbol_map.csv")
LIMIT = int(os.getenv("RESOLVE_LIMIT", "30"))
URL = "https://query1.finance.yahoo.com/v1/finance/search"
HEADERS = {"User-Agent": "Mozilla/5.0 assurance-vie-data/1.0"}
ALLOWED_TYPES = {"EQUITY", "ETF", "MUTUALFUND", "INDEX"}


def load_rows():
    with MAP.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def save_rows(rows):
    fields = ["asset_id", "isin", "symbol", "provider", "status", "last_checked", "notes"]
    with MAP.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


def resolve(isin: str):
    r = requests.get(
        URL,
        params={"q": isin, "quotesCount": 8, "newsCount": 0},
        headers=HEADERS,
        timeout=20,
    )
    r.raise_for_status()
    quotes = r.json().get("quotes", [])
    for q in quotes:
        symbol = q.get("symbol")
        qtype = q.get("quoteType")
        if symbol and qtype in ALLOWED_TYPES:
            return symbol, qtype
    return None, None


def main():
    rows = load_rows()
    today = date.today().isoformat()

    candidates = []
    for idx, row in enumerate(rows):
        if row.get("status") == "resolved" and row.get("symbol"):
            continue
        if row.get("status") == "manual":
            continue
        isin = (row.get("isin") or "").strip()
        if len(isin) != 12 or not isin[:2].isalpha():
            continue
        candidates.append((row.get("last_checked") or "0000-00-00", idx))

    candidates.sort()
    selected = candidates[:LIMIT]

    for _, idx in selected:
        row = rows[idx]
        isin = row["isin"].strip()
        try:
            symbol, qtype = resolve(isin)
            row["last_checked"] = today
            if symbol:
                row["symbol"] = symbol
                row["provider"] = "yahoo"
                row["status"] = "resolved"
                row["notes"] = qtype or ""
            else:
                row["status"] = "unresolved"
                row["notes"] = "No Yahoo symbol found"
        except Exception as exc:
            row["last_checked"] = today
            row["status"] = "retry"
            row["notes"] = type(exc).__name__
        time.sleep(0.35)

    save_rows(rows)
    print(f"Checked {len(selected)} unresolved ISIN(s).")


if __name__ == "__main__":
    main()
