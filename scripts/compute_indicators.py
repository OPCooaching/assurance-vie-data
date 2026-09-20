from __future__ import annotations

from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

PRICES = Path("data/prices/daily.csv")
LATEST = Path("data/indicators/latest.csv")
SNAP_DIR = Path("data/snapshots")


def period_return(close: pd.Series, n: int):
    return close.iloc[-1] / close.iloc[-1 - n] - 1 if len(close) > n else np.nan


def max_drawdown(close: pd.Series):
    if len(close) < 2:
        return np.nan
    peak = close.cummax()
    return (close / peak - 1).min()


def one_asset(g: pd.DataFrame):
    g = g.sort_values("date")
    if "close_eur" not in g:
        raise ValueError("EUR-normalised prices are required before computing indicators.")
    close = pd.to_numeric(g["close_eur"], errors="coerce").dropna()
    ret = close.pct_change().dropna()

    return {
        "date": g["date"].iloc[-1],
        "asset_id": g["asset_id"].iloc[-1],
        "symbol": g["symbol"].iloc[-1],
        "quote_currency": g["quote_currency"].iloc[-1],
        "close_eur": close.iloc[-1] if len(close) else np.nan,
        "close": close.iloc[-1] if len(close) else np.nan,
        "ret_5d": period_return(close, 5),
        "ret_20d": period_return(close, 20),
        "ret_60d": period_return(close, 60),
        "ret_120d": period_return(close, 120),
        "vol_20d_ann": ret.tail(20).std() * np.sqrt(252) if len(ret) >= 10 else np.nan,
        "vol_60d_ann": ret.tail(60).std() * np.sqrt(252) if len(ret) >= 20 else np.nan,
        "drawdown_60d": max_drawdown(close.tail(61)),
        "drawdown_252d": max_drawdown(close.tail(253)),
        "sma20_ratio": close.iloc[-1] / close.tail(20).mean() - 1 if len(close) >= 20 else np.nan,
        "sma50_ratio": close.iloc[-1] / close.tail(50).mean() - 1 if len(close) >= 50 else np.nan,
        "sma200_ratio": close.iloc[-1] / close.tail(200).mean() - 1 if len(close) >= 200 else np.nan,
        "observations": len(close),
    }


def main():
    if not PRICES.exists():
        print("No price history yet.")
        return

    df = pd.read_csv(PRICES)
    if df.empty:
        print("Price history is empty.")
        return

    rows = [one_asset(g) for _, g in df.groupby("asset_id")]
    result = pd.DataFrame(rows).sort_values("asset_id")

    LATEST.parent.mkdir(parents=True, exist_ok=True)
    SNAP_DIR.mkdir(parents=True, exist_ok=True)

    result.to_csv(LATEST, index=False)
    result.to_csv(SNAP_DIR / f"{date.today().isoformat()}.csv", index=False)
    print(f"Computed indicators for {len(result)} assets.")


if __name__ == "__main__":
    main()
