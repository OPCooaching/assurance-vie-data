from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

UNIVERSE = Path("config/universe.csv")
SYMBOL_MAP = Path("config/symbol_map.csv")
INDICATORS = Path("data/indicators/latest.csv")
PRICES = Path("data/prices/daily.csv")
OUTPUT = Path("docs/data/screener.json")

# These supports do not have a comparable daily market price. They remain visible
# in the inventory, but the screener must not manufacture a market signal for them.
NON_MARKET_CATEGORIES = {
    "Fonds en euros",
    "Croissance",
    "SCPI - SCI",
    "OPCI",
    "FCPR",
    "Fonds structurés /Autres",
}
MIN_OBSERVATIONS = 120
PRICE_FIELDS = ["ret_20d", "ret_60d", "ret_120d", "vol_60d_ann", "drawdown_252d"]


def clean_number(value):
    if value is None or pd.isna(value) or not np.isfinite(float(value)):
        return None
    return round(float(value), 6)


def percentile(series: pd.Series, ascending: bool = True) -> pd.Series:
    values = pd.to_numeric(series, errors="coerce")
    return values.rank(pct=True, ascending=ascending) * 100


def latest_volume_features(prices: pd.DataFrame) -> pd.DataFrame:
    if prices.empty or "volume" not in prices.columns:
        return pd.DataFrame(columns=["asset_id", "volume_available", "volume_ratio_20d"])

    work = prices[["asset_id", "date", "volume"]].copy()
    work["date"] = pd.to_datetime(work["date"], errors="coerce")
    work["volume"] = pd.to_numeric(work["volume"], errors="coerce")
    rows = []
    for asset_id, group in work.dropna(subset=["date"]).groupby("asset_id"):
        volume = group.sort_values("date")["volume"].tail(21).dropna()
        # A volume signal is useful only when it has a real, repeated reading.
        non_zero = volume[volume > 0]
        available = len(volume) >= 21 and len(non_zero) >= 15
        ratio = None
        if available and len(volume) >= 21:
            average = volume.iloc[:-1].mean()
            if average > 0:
                ratio = clean_number(volume.iloc[-1] / average)
        rows.append({
            "asset_id": asset_id,
            "volume_available": bool(available),
            "volume_ratio_20d": ratio,
        })
    return pd.DataFrame(rows)


def explain_row(row: pd.Series) -> tuple[str, str]:
    category = row.get("category", "")
    observations = pd.to_numeric(row.get("observations"), errors="coerce")
    if category in NON_MARKET_CATEGORIES:
        return (
            "hors screener de marché",
            "Ce support n’a pas de prix de marché quotidien comparable ; aucun signal n’est calculé.",
        )
    if row.get("status") != "resolved":
        return (
            "données à résoudre",
            "Aucun symbole de marché validé : le screener ne peut pas le classer.",
        )
    if row.get("currency_status") not in {"verified_eur", "verified_fx_to_eur"}:
        return (
            "devise à vérifier",
            "La devise de cotation n’est pas validée ; le screener exclut ce support.",
        )
    if pd.isna(observations) or observations < MIN_OBSERVATIONS:
        return (
            "historique insuffisant",
            f"Moins de {MIN_OBSERVATIONS} observations utilisables : pas de classement.",
        )
    return (
        "analysable par les prix",
        "Tendance, stabilité et recul maximal sont calculés sur les prix normalisés en euros.",
    )


def main():
    required = [UNIVERSE, SYMBOL_MAP, INDICATORS, PRICES]
    missing = [str(path) for path in required if not path.exists()]
    if missing:
        raise SystemExit("Missing screener inputs: " + ", ".join(missing))

    universe = pd.read_csv(UNIVERSE).fillna("")
    symbols = pd.read_csv(SYMBOL_MAP).fillna("")
    indicators = pd.read_csv(INDICATORS)
    prices = pd.read_csv(PRICES)

    volume = latest_volume_features(prices)
    df = universe.merge(
        symbols[[
            "asset_id", "symbol", "status", "quote_currency", "exchange",
            "currency_status", "history_status",
        ]],
        on="asset_id",
        how="left",
    ).merge(indicators, on="asset_id", how="left", suffixes=("", "_indicator")).merge(
        volume, on="asset_id", how="left"
    )
    df["volume_available"] = df["volume_available"].fillna(False).astype(bool)

    states = df.apply(explain_row, axis=1)
    df["screening_status"] = [state[0] for state in states]
    df["screening_note"] = [state[1] for state in states]
    eligible = df["screening_status"].eq("analysable par les prix")

    # A cross-asset score uses only signals available on the same EUR-normalised
    # price history. It is an observation aid, not a buy recommendation.
    df["trend_score"] = np.nan
    df["stability_score"] = np.nan
    df["market_observation_score"] = np.nan
    if eligible.any():
        candidate = df.loc[eligible].copy()
        trend_components = pd.concat(
            [
                percentile(candidate["ret_20d"]),
                percentile(candidate["ret_60d"]),
                percentile(candidate["ret_120d"]),
            ],
            axis=1,
        )
        candidate["trend_score"] = trend_components.mean(axis=1)
        stability_components = pd.concat(
            [
                percentile(candidate["vol_60d_ann"], ascending=False),
                percentile(candidate["drawdown_252d"], ascending=True),
            ],
            axis=1,
        )
        candidate["stability_score"] = stability_components.mean(axis=1)
        candidate["market_observation_score"] = (
            0.65 * candidate["trend_score"] + 0.35 * candidate["stability_score"]
        )
        df.loc[candidate.index, ["trend_score", "stability_score", "market_observation_score"]] = candidate[
            ["trend_score", "stability_score", "market_observation_score"]
        ]

    rows = []
    for _, row in df.sort_values(
        ["screening_status", "market_observation_score", "support_name"],
        ascending=[True, False, True],
        na_position="last",
    ).iterrows():
        values = {field: clean_number(row.get(field)) for field in PRICE_FIELDS}
        rows.append({
            "asset_id": row["asset_id"],
            "name": row["support_name"],
            "category": row["category"],
            "symbol": row.get("symbol") or None,
            "exchange": row.get("exchange") or None,
            "quote_currency": row.get("quote_currency") or None,
            "currency_status": row.get("currency_status") or None,
            "history_status": row.get("history_status") or None,
            "status": row["screening_status"],
            "note": row["screening_note"],
            "observations": int(row["observations"]) if pd.notna(row.get("observations")) else 0,
            "volume_available": bool(row["volume_available"]),
            "volume_ratio_20d": clean_number(row.get("volume_ratio_20d")),
            "trend_score": clean_number(row.get("trend_score")),
            "stability_score": clean_number(row.get("stability_score")),
            "market_observation_score": clean_number(row.get("market_observation_score")),
            **values,
        })

    counts = {
        "total_supports": len(rows),
        "price_analysable": int((df["screening_status"] == "analysable par les prix").sum()),
        "volume_analysable": int((eligible & df["volume_available"]).sum()),
        "fundamentals_available": 0,
    }
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "as_of_date": str(pd.to_datetime(indicators["date"]).max().date()),
        "scope": {
            "title": "Observatoire commun des données",
            "summary": (
                "Le classement combine tendance sur 20, 60 et 120 séances, "
                "stabilité sur 60 séances et recul maximal sur 252 séances. "
                "Il sert à explorer des candidats ; il ne constitue ni un ordre ni une stratégie."
            ),
            "free_updates": (
                "Ces données proviennent de la collecte Yahoo Finance déjà exécutée "
                "chaque jour ouvré, sans clé ni abonnement."
            ),
        },
        "data_contract": [
            {
                "family": "Prix, tendance et risque",
                "availability": "Disponible maintenant pour les supports avec historique suffisant",
                "use": "Peut comparer des supports aux prix normalisés en euros.",
            },
            {
                "family": "Volume relatif sur 20 séances",
                "availability": "Disponible seulement lorsque la cotation publie un volume fiable",
                "use": "Signal complémentaire pour actions et ETF cotés ; absent des fonds non cotés.",
            },
            {
                "family": "Valorisation fondamentale (P/E, qualité, bénéfices)",
                "availability": "Non intégrée : aucune source gratuite, homogène et datée ne couvre équitablement tout l’univers",
                "use": "À tester séparément pour les actions directes, jamais appliquée aux obligations, fonds euros ou immobilier.",
            },
        ],
        "counts": counts,
        "rows": rows,
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        f"Built screener for {counts['total_supports']} supports: "
        f"{counts['price_analysable']} price-analysable, "
        f"{counts['volume_analysable']} with usable volume."
    )


if __name__ == "__main__":
    main()
