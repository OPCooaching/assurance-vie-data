from __future__ import annotations

import csv
from pathlib import Path

import pandas as pd
import yfinance as yf

MAP = Path("config/symbol_map.csv")
OUT = Path("data/prices/daily.csv")
BATCH = 40


def load_map():
    with MAP.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    return [r for r in rows if r.get("status") == "resolved" and r.get("symbol")]


def download_batch(symbols, period):
    return yf.download(
        tickers=symbols,
        period=period,
        interval="1d",
        auto_adjust=False,
        progress=False,
        group_by="ticker",
        threads=True,
    )


def extract(data, symbol):
    if data.empty:
        return pd.DataFrame()
    if isinstance(data.columns, pd.MultiIndex):
        if symbol not in data.columns.get_level_values(0):
            return pd.DataFrame()
        x = data[symbol].copy()
    else:
        x = data.copy()
    if "Close" not in x:
        return pd.DataFrame()
    out = pd.DataFrame({
        "date": pd.to_datetime(x.index).date.astype(str),
        "close": pd.to_numeric(x["Close"], errors="coerce"),
        "volume": pd.to_numeric(x.get("Volume"), errors="coerce"),
    })
    return out.dropna(subset=["close"])


def main():
    rows = load_map()
    OUT.parent.mkdir(parents=True, exist_ok=True)

    existing = pd.read_csv(OUT) if OUT.exists() else pd.DataFrame()
    period = "1y" if existing.empty else "7d"

    new_parts = []
    for i in range(0, len(rows), BATCH):
        batch = rows[i:i+BATCH]
        symbols = list(dict.fromkeys(r["symbol"] for r in batch))
        try:
            data = download_batch(symbols, period)
        except Exception:
            continue
        for r in batch:
            x = extract(data, r["symbol"])
            if x.empty:
                continue
            x["asset_id"] = r["asset_id"]
            x["symbol"] = r["symbol"]
            x["provider"] = r.get("provider") or "yahoo"
            new_parts.append(x)

    if not new_parts:
        print("No market data downloaded.")
        return

    new = pd.concat(new_parts, ignore_index=True)
    cols = ["date", "asset_id", "symbol", "close", "volume", "provider"]
    new = new[cols]
    all_data = pd.concat([existing, new], ignore_index=True) if not existing.empty else new
    all_data = all_data.drop_duplicates(["date", "asset_id"], keep="last")
    all_data = all_data.sort_values(["date", "asset_id"])
    all_data.to_csv(OUT, index=False)
    print(f"Saved {len(all_data)} price rows for {all_data.asset_id.nunique()} assets.")


if __name__ == "__main__":
    main()
