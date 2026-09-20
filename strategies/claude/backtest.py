#!/usr/bin/env python3
"""
Backtest walk-forward des strategies Claude.

Principe : a chaque date de decision, seules les donnees anterieures ou egales
a cette date sont visibles. L'allocation decidee s'applique a partir de la
seance suivante, ce qui reproduit le fait qu'un arbitrage d'assurance vie
s'execute a une valeur liquidative inconnue au moment de l'ordre.

Entrees, toutes en lecture seule :
  config/universe.csv
  config/symbol_map.csv
  data/prices/daily.csv          colonnes date, asset_id, symbol, close, volume, provider
  data/benchmarks/bernard_origin.csv

Sorties, uniquement dans les espaces Claude :
  strategies/claude/<id>/backtest_<version>.csv
  strategies/claude/strategies.json
  history/claude/decisions.jsonl   (append only)

Usage :
  python strategies/claude/backtest.py
  python strategies/claude/backtest.py --strategie claude-socle-satellites
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import yaml

RACINE = Path(__file__).resolve().parents[2]
PRIX = RACINE / "data" / "prices" / "daily.csv"
BENCHMARK = RACINE / "data" / "benchmarks" / "bernard_origin.csv"
ESPACE = RACINE / "strategies" / "claude"
HISTORIQUE = RACINE / "history" / "claude" / "decisions.jsonl"
SORTIE_WEB = RACINE / "docs" / "data" / "claude.json"

# Supports utilises par les strategies Claude
SOCLE = "IE00B4L5Y983"          # iShares Core MSCI World
MONETAIRE = "LU0290358497"       # Xtrackers II EUR Overnight Rate Swap
FONDS_EUROS = "ALTAPROFITS:FONDS-EN-EURO-NETISSIMA"
THEMES = [
    "IE000I8KRLL9",  # semi-conducteurs
    "LU1829219390",  # banques zone euro
    "IE00BM67HK77",  # sante mondiale
    "IE00BMG6Z448",  # emergents hors Chine
]

# Le fonds en euros n'a aucune cotation publique. Rendement modelise, annonce
# comme tel sur la page. A ajuster quand le taux 2026 sera connu.
RENDEMENT_FONDS_EUROS_ANNUEL = 0.03

HISTORIQUE_MINIMAL_JOURS = 260  # une moyenne 200 jours plus une marge


def charger_prix() -> pd.DataFrame:
    if not PRIX.exists():
        raise SystemExit(
            f"Fichier absent : {PRIX}\n"
            "La collecte automatique n'a encore produit aucun cours. "
            "Lancez le workflow 'Daily market data update' avant ce script."
        )
    df = pd.read_csv(PRIX, parse_dates=["date"])
    table = df.pivot_table(index="date", columns="asset_id", values="close", aggfunc="last")
    return table.sort_index()


def ajouter_fonds_euros(table: pd.DataFrame) -> pd.DataFrame:
    """Ajoute une colonne synthetique pour le fonds en euros."""
    jours = (table.index - table.index[0]).days
    table[FONDS_EUROS] = 100.0 * (1 + RENDEMENT_FONDS_EUROS_ANNUEL) ** (jours / 365.25)
    return table


def dates_de_decision(index: pd.DatetimeIndex) -> list[pd.Timestamp]:
    """Un vendredi sur deux, ou la derniere seance de chaque semaine."""
    semaines = pd.Series(index, index=index).groupby(
        [index.isocalendar().year, index.isocalendar().week]
    ).last()
    return sorted(semaines.tolist())


def moyenne_mobile(serie: pd.Series, n: int, jusqu_a: pd.Timestamp) -> float | None:
    fenetre = serie.loc[:jusqu_a].dropna()
    if len(fenetre) < n:
        return None
    return float(fenetre.iloc[-n:].mean())


def volatilite(serie: pd.Series, n: int, jusqu_a: pd.Timestamp) -> float | None:
    fenetre = serie.loc[:jusqu_a].dropna()
    if len(fenetre) < n + 1:
        return None
    rendements = fenetre.iloc[-n - 1:].pct_change().dropna()
    return float(rendements.std() * (252 ** 0.5))


def allocation_socle_satellites(table, date, p) -> dict[str, float]:
    cible = p["equity_target_pct"]
    part_socle = cible * p["core_share_of_equity_pct"] / 100
    reste = cible - part_socle
    par_theme = min(reste / max(len(THEMES), 1), p["max_theme_weight_pct"])

    poids, exclus = {}, 0.0
    for actif, part in [(SOCLE, part_socle)] + [(t, par_theme) for t in THEMES]:
        if actif not in table.columns:
            exclus += part
            continue
        serie = table[actif]
        mm = moyenne_mobile(serie, p["trend_filter_days"], date)
        dernier = serie.loc[:date].dropna()
        if mm is None or dernier.empty or float(dernier.iloc[-1]) < mm:
            exclus += part
        else:
            poids[actif] = part

    poids[MONETAIRE] = poids.get(MONETAIRE, 0.0) + exclus
    poids[FONDS_EUROS] = 100 - cible
    return poids


def allocation_risque_cible(table, date, p) -> dict[str, float]:
    vol = volatilite(table[SOCLE], p["realized_vol_window_days"], date) if SOCLE in table else None
    if vol is None or vol <= 0:
        part = p["equity_min_pct"]
    else:
        brut = (p["target_volatility_pct"] / 100) / vol * 100
        part = max(p["equity_min_pct"], min(p["equity_max_pct"], brut))

    sous = dict(p)
    sous["equity_target_pct"] = round(part, 1)
    sous.setdefault("core_share_of_equity_pct", 60)
    sous.setdefault("max_theme_weight_pct", 8)
    sous.setdefault("trend_filter_days", 200)
    return allocation_socle_satellites(table, date, sous)


def allocation_double_filtre(table, date, p) -> dict[str, float]:
    def au_dessus(actif: str) -> bool | None:
        if actif not in table.columns:
            return None
        serie = table[actif]
        mm = moyenne_mobile(serie, p["trend_filter_days"], date)
        dernier = serie.loc[:date].dropna()
        if mm is None or dernier.empty:
            return None
        return float(dernier.iloc[-1]) > mm

    tendance = au_dessus(SOCLE)
    etats = [au_dessus(t) for t in THEMES]
    connus = [e for e in etats if e is not None]
    ampleur = (sum(connus) / len(connus) * 100) >= p["breadth_threshold_pct"] if connus else False

    if tendance and ampleur:
        part = p["equity_target_pct"]
    elif tendance or ampleur:
        part = p["equity_target_pct"] * p["partial_exposure_pct"] / 100
    else:
        part = 0.0

    if part == 0:
        return {MONETAIRE: p["equity_target_pct"], FONDS_EUROS: 100 - p["equity_target_pct"]}

    sous = dict(p)
    sous["equity_target_pct"] = part
    sous.setdefault("core_share_of_equity_pct", 60)
    sous.setdefault("max_theme_weight_pct", 8)
    return allocation_socle_satellites(table, date, sous)


MOTEURS = {
    "claude-socle-satellites": allocation_socle_satellites,
    "claude-risque-cible": allocation_risque_cible,
    "claude-double-filtre": allocation_double_filtre,
}


def simuler(table: pd.DataFrame, strategie: dict) -> tuple[pd.DataFrame, list[dict]]:
    identifiant = strategie["id"]
    version = strategie["active_version"]
    p = dict(strategie["parameters"][version])
    p.setdefault("trend_filter_days", 200)

    moteur = MOTEURS[identifiant]
    index = table.index
    decisions_dates = dates_de_decision(index)

    valeur = 100.0
    poids: dict[str, float] = {}
    lignes, decisions = [], []
    derniere_alloc: dict[str, float] = {}

    for i in range(1, len(index)):
        hier, aujourd_hui = index[i - 1], index[i]

        # Rendement du jour applique a l'allocation decidee AVANT ce jour
        if poids:
            rendement = 0.0
            for actif, part in poids.items():
                if actif not in table.columns:
                    continue
                p0, p1 = table.at[hier, actif], table.at[aujourd_hui, actif]
                if pd.notna(p0) and pd.notna(p1) and p0 > 0:
                    rendement += part / 100 * (p1 / p0 - 1)
            valeur *= 1 + rendement

        # La courbe demarre a la premiere decision : la periode de chauffe des
        # indicateurs ne doit pas diluer la performance affichee.
        if poids:
            lignes.append({"date": aujourd_hui.date().isoformat(), "valeur": round(valeur, 4)})

        # Decision prise a la cloture, appliquee a partir de la seance suivante
        if hier in decisions_dates:
            visible = table.loc[:hier]
            if len(visible) >= HISTORIQUE_MINIMAL_JOURS:
                nouvelle = moteur(table, hier, p)
                total = sum(nouvelle.values())
                if total > 0:
                    nouvelle = {k: round(v / total * 100, 2) for k, v in nouvelle.items() if v > 0}
                    ecart = sum(abs(nouvelle.get(k, 0) - derniere_alloc.get(k, 0))
                                for k in set(nouvelle) | set(derniere_alloc))
                    if ecart >= p.get("rebalance_band_pct", 3):
                        decisions.append({
                            "date": hier.date().isoformat(),
                            "strategy_id": identifiant,
                            "strategy_version": version,
                            "comment": f"Revue hebdomadaire, ecart d'allocation {ecart:.1f} points",
                            "allocations": [
                                {"asset_id": k, "weight_pct": v} for k, v in sorted(nouvelle.items())
                            ],
                        })
                        derniere_alloc = nouvelle
                    poids = derniere_alloc or nouvelle

    return pd.DataFrame(lignes), decisions


def indicateurs(courbe: pd.DataFrame, nb_arbitrages: int) -> dict:
    if courbe.empty:
        return {}
    v = courbe["valeur"]
    rendements = v.pct_change().dropna()
    plus_haut = v.cummax()
    return {
        "perf_origine_pct": round((v.iloc[-1] / v.iloc[0] - 1) * 100, 2),
        "perf_5j_pct": round((v.iloc[-1] / v.iloc[-6] - 1) * 100, 2) if len(v) > 6 else None,
        "perf_20j_pct": round((v.iloc[-1] / v.iloc[-21] - 1) * 100, 2) if len(v) > 21 else None,
        "drawdown_max_pct": round(((v / plus_haut) - 1).min() * 100, 2),
        "vol_20j_pct": round(rendements.iloc[-20:].std() * (252 ** 0.5) * 100, 2) if len(rendements) >= 20 else None,
        "nb_arbitrages": nb_arbitrages,
        "valeur_base_100": round(v.iloc[-1], 2),
    }


def main() -> int:
    parseur = argparse.ArgumentParser()
    parseur.add_argument("--strategie", default=None)
    args = parseur.parse_args()

    table = ajouter_fonds_euros(charger_prix())
    if len(table) < HISTORIQUE_MINIMAL_JOURS:
        raise SystemExit(
            f"Historique insuffisant : {len(table)} seances disponibles, "
            f"{HISTORIQUE_MINIMAL_JOURS} necessaires pour une moyenne 200 jours.\n"
            "Augmentez la periode de collecte initiale dans scripts/update_market_data.py."
        )

    resultats = {}
    for chemin in sorted(ESPACE.glob("*/strategy.yml")):
        strategie = yaml.safe_load(chemin.read_text(encoding="utf-8"))
        if args.strategie and strategie["id"] != args.strategie:
            continue
        if strategie["id"] not in MOTEURS:
            continue

        courbe, decisions = simuler(table, strategie)
        version = strategie["active_version"]
        courbe.to_csv(chemin.parent / f"backtest_{version}.csv", index=False)

        with HISTORIQUE.open("a", encoding="utf-8") as f:
            for d in decisions:
                f.write(json.dumps(d, ensure_ascii=False) + "\n")

        resultats[strategie["id"]] = {
            "label": strategie["label"],
            "status": strategie["status"],
            "version": version,
            "objectif": strategie["objective"].strip(),
            "regle": strategie["main_rule"].strip(),
            "faiblesse": strategie.get("known_weakness", "").strip(),
            "allocation_courante": decisions[-1]["allocations"] if decisions else [],
            "indicateurs": indicateurs(courbe, len(decisions)),
            "courbe": courbe.to_dict("records"),
            "nb_decisions": len(decisions),
        }
        print(f"{strategie['id']:28s} {len(decisions):>3} decisions  "
              f"base 100 -> {resultats[strategie['id']]['indicateurs'].get('valeur_base_100')}")

    charge = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "seances_disponibles": len(table),
        "rendement_fonds_euros_modelise_pct": RENDEMENT_FONDS_EUROS_ANNUEL * 100,
        "strategies": resultats,
    }
    texte = json.dumps(charge, ensure_ascii=False, indent=2)

    sortie = ESPACE / "strategies.json"
    sortie.write_text(texte, encoding="utf-8")
    print(f"\nEcrit : {sortie}")

    # Copie lisible par la page publiee, GitHub Pages ne servant que docs/.
    # Ce chemin sort des espaces Claude declares dans config/access-policy.yml
    # et doit y etre ajoute par l'administrateur du depot.
    web = RACINE / "docs" / "data" / "claude-history.json"
    if web.parent.exists():
        web.write_text(texte, encoding="utf-8")
        print(f"Ecrit : {web}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
