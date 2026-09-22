"""Build the public catalogue of data and strategy paths.

This is not a screener and contains no cross-support ranking.  It separates:
1. observed/raw data, 2. derived indicators, 3. strategy families they may
support, and 4. data that are unavailable and must not be pretended.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import yaml

INDICATORS = Path("data/indicators/latest.csv")
PRICES = Path("data/prices/daily.csv")
CONTEXT_CONFIG = Path("config/context_series.yml")
CONTEXT_DATA = Path("data/context/daily.csv")
OUTPUT = Path("docs/data/indicators.json")
MIN_HISTORY = 120


def as_number(value):
    if pd.isna(value):
        return None
    return round(float(value), 6)


def usable_volume_assets(prices: pd.DataFrame) -> int:
    if "volume" not in prices:
        return 0
    count = 0
    work = prices[["asset_id", "date", "volume"]].copy()
    work["date"] = pd.to_datetime(work["date"], errors="coerce")
    work["volume"] = pd.to_numeric(work["volume"], errors="coerce")
    for _, group in work.dropna(subset=["date"]).groupby("asset_id"):
        last = group.sort_values("date")["volume"].tail(21).dropna()
        if len(last) >= 21 and (last > 0).sum() >= 15:
            count += 1
    return count


def external_observations() -> list[dict]:
    config = yaml.safe_load(CONTEXT_CONFIG.read_text(encoding="utf-8")) or {}
    context = pd.read_csv(CONTEXT_DATA)
    context["date"] = pd.to_datetime(context["date"], errors="coerce")
    output = []
    for item in config.get("series", []):
        column = item["column"]
        values = pd.to_numeric(context.get(column), errors="coerce")
        valid = context.loc[values.notna(), ["date"]].copy()
        valid["value"] = values.loc[values.notna()]
        if valid.empty:
            raise ValueError(f"No published observation for {item['id']}.")
        last = valid.iloc[-1]
        output.append(
            {
                "id": item["id"],
                "label": item["label"],
                "purpose": item["purpose"],
                "frequency": item["frequency"],
                "source": item["source"],
                "source_url": item["url"],
                "last_observation_date": str(last["date"].date()),
                "value": as_number(last["value"]),
                "kind": "raw_external",
            }
        )
    return output


def main() -> None:
    for path in (INDICATORS, PRICES, CONTEXT_CONFIG, CONTEXT_DATA):
        if not path.exists():
            raise SystemExit(f"Missing indicator catalogue input: {path}")

    latest = pd.read_csv(INDICATORS)
    prices = pd.read_csv(PRICES)
    observations = pd.to_numeric(latest["observations"], errors="coerce")
    price_ready = int((observations >= MIN_HISTORY).sum())
    trend_ready = int((observations >= 200).sum())
    volume_ready = usable_volume_assets(prices)
    price_as_of = str(pd.to_datetime(latest["date"], errors="coerce").max().date())
    external = external_observations()

    groups = [
        {
            "id": "price",
            "title": "1. Ce que les prix permettent déjà de calculer",
            "intro": (
                "Ce ne sont pas de nouvelles données. Ce sont des calculs "
                "effectués à partir des prix réellement publiés. Ils servent "
                "aux stratégies de tendance, de momentum et de contrôle du risque."
            ),
            "cards": [
                {
                    "name": "Tendance de fond",
                    "question": "Le prix reste-t-il au-dessus de sa trajectoire de long terme ?",
                    "indicator": "Prix comparé à sa moyenne des 20, 50 et 200 dernières séances",
                    "strategy_use": "Filtre de tendance : rester investi ou réduire l’exposition.",
                    "availability": "available",
                    "availability_label": f"Disponible pour {trend_ready} supports avec au moins 200 séances.",
                    "is_new_data": False,
                },
                {
                    "name": "Force relative",
                    "question": "Quels supports ont le plus progressé sur une période définie ?",
                    "indicator": "Variation réellement observée sur 1, 3 et 6 mois",
                    "strategy_use": "Momentum et rotation : comparer des supports selon une règle fixée à l’avance.",
                    "availability": "available",
                    "availability_label": f"Disponible pour {price_ready} supports avec au moins {MIN_HISTORY} séances.",
                    "is_new_data": False,
                },
                {
                    "name": "Risque du parcours",
                    "question": "Quelle a été l’ampleur des mouvements et de la pire baisse ?",
                    "indicator": "Volatilité sur 20/60 séances et baisse maximale sur 60/252 séances",
                    "strategy_use": "Risque cible : diminuer ou répartir l’exposition quand le parcours devient trop instable.",
                    "availability": "available",
                    "availability_label": f"Disponible pour {price_ready} supports avec historique suffisant.",
                    "is_new_data": False,
                },
            ],
        },
        {
            "id": "context",
            "title": "2. Nouvelles données externes, indépendantes des prix des supports",
            "intro": (
                "Ces séries ont été ajoutées pour permettre des stratégies qui "
                "ne regardent pas seulement le prix passé des ETF. Elles sont "
                "publiées par leurs sources avec leur propre date ; les séries "
                "hebdomadaires ne sont jamais transformées en valeurs quotidiennes."
            ),
            "cards": [
                {
                    "name": item["label"],
                    "question": item["purpose"],
                    "indicator": "Valeur brute publiée par la source externe",
                    "strategy_use": "Peut servir de condition de régime dans une règle écrite et testée ; ce n’est pas une instruction d’achat.",
                    "availability": "available",
                    "availability_label": f"Dernière publication : {item['last_observation_date']} · {item['frequency']}.",
                    "is_new_data": True,
                    "external_id": item["id"],
                }
                for item in external
            ],
        },
        {
            "id": "volume",
            "title": "3. Activité de cotation",
            "intro": (
                "Le volume mesure combien de titres ont été échangés. Il peut "
                "servir à confirmer un mouvement de marché, mais il n’existe pas "
                "pour la plupart des fonds non cotés."
            ),
            "cards": [
                {
                    "name": "Volume relatif",
                    "question": "Le volume du jour est-il inhabituel par rapport aux 20 dernières séances ?",
                    "indicator": "Volume du jour ÷ volume moyen des 20 séances précédentes",
                    "strategy_use": "Confirmation de mouvement sur les actions et ETF qui publient un volume fiable.",
                    "availability": "partial",
                    "availability_label": f"Disponible pour {volume_ready} supports seulement.",
                    "is_new_data": False,
                }
            ],
        },
    ]

    strategy_paths = [
        {
            "name": "Allocation fixe diversifiée",
            "question": "Répartir durablement entre plusieurs familles d’actifs, sans prédire le prochain gagnant.",
            "needs": "Aucun indicateur de prévision ; seulement des supports représentatifs et une fréquence de rééquilibrage.",
            "status": "ready",
            "status_label": "Déjà testable",
            "current": "Les références académiques 60/40 et Harry Browne relèvent de cette famille.",
        },
        {
            "name": "Tendance et protection",
            "question": "Rester exposé lorsque la tendance est saine, réduire l’exposition lorsqu’elle se dégrade.",
            "needs": "Tendance de fond et règle de révision mensuelle ou hebdomadaire.",
            "status": "ready",
            "status_label": "Données prêtes",
            "current": "Le prix suffit ; une version nouvelle doit toutefois être définie puis testée séparément.",
        },
        {
            "name": "Risque cible et diversification",
            "question": "Donner moins de poids aux supports qui deviennent très instables et éviter les expositions trop semblables.",
            "needs": "Volatilité, baisse maximale et calcul de relations entre les supports retenus.",
            "status": "ready",
            "status_label": "Données prêtes",
            "current": "La volatilité et les baisses sont déjà disponibles ; les relations sont calculées au moment de définir les candidats.",
        },
        {
            "name": "Régime économique et financier",
            "question": "Adapter l’exposition au contexte : incertitude, crédit, dollar, énergie et activité économique.",
            "needs": "Les cinq séries externes ci-dessous et une règle explicite de mise à jour.",
            "status": "ready",
            "status_label": "Nouvelles données prêtes",
            "current": "Aucune courbe ne les utilise encore : il faut d’abord écrire une règle et la tester sans regarder le résultat à l’avance.",
        },
        {
            "name": "Confirmation par l’activité de marché",
            "question": "Ne retenir un mouvement que lorsqu’il s’accompagne d’une activité de cotation inhabituelle.",
            "needs": "Volume relatif fiable.",
            "status": "partial",
            "status_label": "Partiel",
            "current": "Possible seulement sur les actions et ETF disposant d’un volume quotidien fiable.",
        },
        {
            "name": "Sélection par valorisation fondamentale",
            "question": "Comparer bénéfices, prix et qualité financière des entreprises.",
            "needs": "Bénéfices, P/E et données de bilan datées de façon homogène.",
            "status": "unavailable",
            "status_label": "Non utilisable proprement",
            "current": "Ces données ne couvrent pas équitablement tout l’univers et ne sont donc pas intégrées dans une stratégie.",
        },
    ]

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "price_as_of_date": price_as_of,
        "summary": {
            "title": "Indicateurs et stratégies possibles",
            "message": (
                "Cette page ne classe aucun support et ne recommande aucun achat. "
                "Elle répond à trois questions : quelles données existent, quelles "
                "stratégies elles rendent possibles, et quelles données manquent."
            ),
            "price_ready": price_ready,
            "volume_ready": volume_ready,
            "external_ready": len(external),
        },
        "groups": groups,
        "strategy_paths": strategy_paths,
        "external_observations": external,
        "unavailable": [
            {
                "name": "Valorisation fondamentale homogène",
                "reason": (
                    "Pas de source gratuite, quotidienne et comparable pour les "
                    "bénéfices, P/E et bilans de tous les types de supports du contrat."
                ),
                "consequence": "Aucune stratégie value n’est construite à partir de données incomplètes.",
            }
        ],
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Built indicator catalogue: {price_ready} price-ready supports, {len(external)} external series.")


if __name__ == "__main__":
    main()
