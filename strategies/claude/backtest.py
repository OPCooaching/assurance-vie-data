#!/usr/bin/env python3
"""
Backtest walk-forward des strategies Claude.

Principe : a chaque date de decision, seules les donnees anterieures ou egales
a cette date sont visibles. L'allocation decidee s'applique a partir de la
seance suivante, ce qui reproduit le fait qu'un arbitrage d'assurance vie
s'execute a une valeur liquidative inconnue au moment de l'ordre.

Entrees, toutes en lecture seule :
  config/universe.csv
  config/portfolio_current.csv
  config/symbol_map.csv
  data/prices/daily.csv          colonnes date, asset_id, symbol, close, quote_currency...
  data/benchmarks/bernard_origin.csv

Sorties, uniquement dans les espaces Claude :
  strategies/claude/<id>/backtest_<version>.csv
  strategies/claude/strategies.json
  history/claude/decisions.jsonl      (ajout seul, sans doublon)
  docs/data/claude-history.json       (copie lue par docs/claude.html)
  docs/data/claude.json               (seule la cle "strategies" est mise a jour)

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
UNIVERS = RACINE / "config" / "universe.csv"
PORTEFEUILLE = RACINE / "config" / "portfolio_current.csv"
ESPACE = RACINE / "strategies" / "claude"
HISTORIQUE = RACINE / "history" / "claude" / "decisions.jsonl"
SORTIE_WEB = RACINE / "docs" / "data" / "claude-history.json"
SORTIE_WEB_TABLEAU = RACINE / "docs" / "data" / "claude.json"

# Supports utilises par les strategies Claude.
# Contrainte conservee : uniquement des lignes cotees en euros sur une place de
# la zone euro. Les cotations hors zone euro du meme fonds introduisent un effet
# de change que le fichier commun n'homogeneise pas.
SOCLE = "IE00BKBF6H24"           # iShares Core MSCI World, IWLE.DE, Francfort
SOCLE_MIN_VOL = "IE00BL25JN58"   # Xtrackers MSCI World Minimum Volatility, XDEB.DE
MONETAIRE = "LU0290358497"       # Xtrackers II EUR Overnight Rate Swap, XEON.DE
FONDS_EUROS = "ALTAPROFITS:FONDS-EN-EURO-NETISSIMA"
THEMES = [
    "IE000I8KRLL9",  # semi-conducteurs, SEMI.AS, Amsterdam
    "LU1829219390",  # banques zone euro, BNKE.PA, Paris
    "IE00BMG6Z448",  # emergents hors Chine, EXCH.AS, Amsterdam
]
# La sante mondiale n'existe dans l'univers qu'en cotation londonienne
# (XDWH.L) et reste donc hors des strategies Claude depuis la v0.2.

SUPPORTS_COTES = [SOCLE, SOCLE_MIN_VOL, MONETAIRE] + THEMES

# Univers elargi, utilise par les strategies qui classent les supports au lieu
# de suivre une liste de themes fixee d'avance. Meme contrainte de devise :
# uniquement des fonds cotes en euros sur une place de la zone euro.
PLACES_ZONE_EURO = {"PAR", "GER", "AMS", "MIL", "BRU", "FRA", "MUN", "LIS",
                    "VIE", "STU", "HAM", "BER", "DUS", "MCE", "HEL", "LUX"}
CATEGORIES_ELARGIES = {"ETF", "Opcvm/FI"}
SEANCES_MINIMALES_ELARGI = 1250
DEBUT_MAXIMAL_ELARGI = "2021-09-24"

# Repartition par defaut du socle entre indice large et volatilite minimale,
# utilisee quand une version ne precise pas core_split.
CORE_SPLIT_DEFAUT = {"world_index_pct": 70, "min_volatility_pct": 30}

# Le fonds en euros n'a aucune cotation publique. Rendement modelise, annonce
# comme tel sur la page. A ajuster quand le taux 2026 sera connu.
RENDEMENT_FONDS_EUROS_ANNUEL = 0.03

HISTORIQUE_MINIMAL_JOURS = 260  # une moyenne 200 jours plus une marge
SEANCES_AMORCAGE = 200          # amorcage minimal, avant exigence propre a la version
SEANCES_PAR_AN = 252

# Les versions dont les parametres ne portent pas cette mention ont ete definies
# sur un univers qui n'est pas disponible en cotation euro. Elles restent
# documentees dans les fichiers de strategie mais ne sont pas simulees.
MARQUEUR_UNIVERS = "eur_quoted_only"


def charger_prix() -> pd.DataFrame:
    """Table des cours limitee aux supports Claude, sur leurs seances communes."""
    if not PRIX.exists():
        raise SystemExit(
            f"Fichier absent : {PRIX}\n"
            "La collecte automatique n'a encore produit aucun cours. "
            "Lancez le workflow 'Daily market data update' avant ce script."
        )
    df = pd.read_csv(PRIX, parse_dates=["date"])
    manquants = [a for a in SUPPORTS_COTES if a not in set(df["asset_id"])]
    if manquants:
        raise SystemExit(
            "Supports absents du fichier de cours : " + ", ".join(manquants) + "\n"
            "Les strategies Claude ne peuvent pas etre simulees sans eux."
        )
    table = df.pivot_table(index="date", columns="asset_id", values="close", aggfunc="last")
    # Le calendrier de reference est celui des six supports de Claude A : une
    # seance ou l'un d'eux ne cote pas est ecartee. Les supports de l'univers
    # elargi sont ensuite alignes sur ce calendrier, leur dernier cours connu
    # etant reporte les rares seances ou leur place est fermee.
    calendrier = table[SUPPORTS_COTES].dropna(how="any").sort_index().index
    colonnes = SUPPORTS_COTES + [a for a in univers_elargi(df) if a not in SUPPORTS_COTES]
    return table[colonnes].reindex(calendrier).ffill()


def univers_elargi(df: pd.DataFrame) -> list[str]:
    """Fonds cotes en euros sur une place de la zone euro, avec cinq ans de cours."""
    carte = pd.read_csv(RACINE / "config" / "symbol_map.csv")
    univers = pd.read_csv(UNIVERS)
    fusion = carte.merge(univers[["asset_id", "category"]], on="asset_id", how="left")
    eligibles = fusion[
        (fusion["status"] == "resolved")
        & (fusion["exchange"].isin(PLACES_ZONE_EURO))
        & (fusion["category"].isin(CATEGORIES_ELARGIES))
    ]["asset_id"]

    cours = df[df["asset_id"].isin(set(eligibles))]
    profondeur = cours.groupby("asset_id")["date"].agg(["count", "min"])
    retenus = profondeur[
        (profondeur["count"] >= SEANCES_MINIMALES_ELARGI)
        & (profondeur["min"] <= pd.Timestamp(DEBUT_MAXIMAL_ELARGI))
    ]
    return sorted(retenus.index)


def ajouter_fonds_euros(table: pd.DataFrame) -> pd.DataFrame:
    """Ajoute une colonne synthetique pour le fonds en euros."""
    jours = (table.index - table.index[0]).days
    table[FONDS_EUROS] = 100.0 * (1 + RENDEMENT_FONDS_EUROS_ANNUEL) ** (jours / 365.25)
    return table


def dates_de_decision(index: pd.DatetimeIndex) -> list[pd.Timestamp]:
    """La derniere seance de chaque semaine."""
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
    return float(rendements.std() * (SEANCES_PAR_AN ** 0.5))


def ordre_versions(versions) -> list[str]:
    """v0.1, v0.2, v0.3... dans l'ordre de publication."""
    def cle(v: str):
        return [int(x) for x in str(v).lstrip("v").split(".") if x.isdigit()]
    return sorted(versions, key=cle)


def parametres_effectifs(strategie: dict, version: str) -> dict:
    """Parametres d'une version.

    Les versions sont cumulatives : une version reprend les parametres des
    versions anterieures et ne redefinit que ce qui change. Les defauts du
    moteur completent ce qui n'a jamais ete defini.
    """
    p: dict = {}
    for v in ordre_versions(strategie["parameters"]):
        bloc = strategie["parameters"][v]
        if isinstance(bloc, dict):
            p.update(bloc)
        if v == version:
            break
    # La stratégie B exprime sa bande d'arbitrage sous un autre nom.
    if "action_threshold_pct" in p:
        p.setdefault("rebalance_band_pct", p["action_threshold_pct"])
    filtre = str(p.get("trend_filter", "sma_200"))
    p["trend_filter_days"] = int(filtre.split("_")[-1]) if filtre.startswith("sma_") else 200
    p.setdefault("equity_target_pct", 50)
    p.setdefault("core_share_of_equity_pct", 60)
    p.setdefault("max_theme_weight_pct", 8)
    p.setdefault("rebalance_band_pct", 3)
    p.setdefault("core_split", CORE_SPLIT_DEFAUT)
    p.setdefault("themes", THEMES)
    p.pop("note", None)
    p.pop("motif", None)
    return p


def seances_amorcage(p: dict) -> int:
    """Profondeur de donnees exigee avant la premiere decision d'une version."""
    besoin = [SEANCES_AMORCAGE, int(p.get("trend_filter_days", 0))]
    if p.get("lookbacks_sessions"):
        besoin.append(max(int(h) for h in p["lookbacks_sessions"]) + 1)
    if p.get("market_guard"):
        besoin.append(int(str(p["market_guard"]).split("_")[1]))
    if p.get("realized_vol_window_days"):
        besoin.append(int(p["realized_vol_window_days"]) + 1)
    return max(besoin)


def allocation_socle_satellites(table, date, p) -> dict[str, float]:
    cible = p["equity_target_pct"]
    part_socle = cible * p["core_share_of_equity_pct"] / 100
    reste = cible - part_socle
    themes = [t for t in p.get("themes", THEMES) if t in table.columns]
    par_theme = min(reste / max(len(themes), 1), p["max_theme_weight_pct"])

    split = p.get("core_split") or CORE_SPLIT_DEFAUT
    lignes_socle = [
        (SOCLE, part_socle * split["world_index_pct"] / 100),
        (SOCLE_MIN_VOL, part_socle * split["min_volatility_pct"] / 100),
    ]

    poids, exclus = {}, 0.0
    for actif, part in lignes_socle + [(t, par_theme) for t in themes]:
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
    etats = [au_dessus(t) for t in p.get("themes", THEMES)]
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
    return allocation_socle_satellites(table, date, sous)


def supports_classables(table: pd.DataFrame) -> list[str]:
    """Univers de classement : tout sauf le monetaire et le fonds en euros."""
    return [c for c in table.columns if c not in (MONETAIRE, FONDS_EUROS)]


def score_momentum(table, date, actifs, horizons) -> dict[str, float]:
    """Moyenne des performances sur plusieurs horizons, vue a cette date."""
    scores = {}
    for actif in actifs:
        serie = table[actif].loc[:date].dropna()
        if len(serie) <= max(horizons):
            continue
        parts = [float(serie.iloc[-1] / serie.iloc[-1 - h] - 1) for h in horizons]
        scores[actif] = sum(parts) / len(parts)
    return scores


def volatilite_recente(table, date, actif, n) -> float:
    serie = table[actif].loc[:date].dropna()
    if len(serie) < n + 1:
        return 0.0
    rendements = serie.iloc[-n - 1:].pct_change().dropna()
    return float(rendements.std() * (SEANCES_PAR_AN ** 0.5))


def allocation_momentum(table, date, p) -> dict[str, float]:
    cible = p["equity_target_pct"]
    poids = {FONDS_EUROS: 100 - cible}

    # Garde-fou de marche : sous sa moyenne longue, l'indice monde renvoie
    # toute la poche actions sur le support monetaire.
    if p.get("market_guard"):
        jours = int(str(p["market_guard"]).split("_")[1])
        serie = table[SOCLE]
        mm = moyenne_mobile(serie, jours, date)
        dernier = serie.loc[:date].dropna()
        if mm is None or dernier.empty or float(dernier.iloc[-1]) < mm:
            poids[MONETAIRE] = cible
            return poids

    horizons = [int(h) for h in p["lookbacks_sessions"]]
    scores = score_momentum(table, date, supports_classables(table), horizons)
    classes = sorted(scores.items(), key=lambda kv: -kv[1])
    retenus = [a for a, s in classes if s > 0][: int(p["top_k"])]

    part_disponible = cible * len(retenus) / int(p["top_k"])
    if retenus:
        if p.get("weighting") == "inverse_volatility":
            n = int(p.get("realized_vol_window_days", 60))
            brut = {a: 1 / max(volatilite_recente(table, date, a, n), 0.02) for a in retenus}
        else:
            brut = {a: 1.0 for a in retenus}
        total = sum(brut.values())
        for actif, valeur in brut.items():
            part = part_disponible * valeur / total
            plafond = p.get("max_line_weight_pct")
            poids[actif] = min(part, plafond) if plafond else part

    reste = cible - sum(v for k, v in poids.items() if k != FONDS_EUROS)
    if reste > 0:
        poids[MONETAIRE] = poids.get(MONETAIRE, 0.0) + reste
    return poids


MOTEURS = {
    "claude-socle-satellites": allocation_socle_satellites,
    "claude-risque-cible": allocation_risque_cible,
    "claude-double-filtre": allocation_double_filtre,
    "claude-momentum-multi": allocation_momentum,
    "claude-momentum-prudent": allocation_momentum,
}


def simuler(table: pd.DataFrame, strategie: dict, version: str) -> tuple[pd.DataFrame, list[dict]]:
    identifiant = strategie["id"]
    p = parametres_effectifs(strategie, version)

    moteur = MOTEURS[identifiant]
    amorcage = seances_amorcage(p)
    index = table.index
    decisions_dates = set(dates_de_decision(index))

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

        # Decision prise a la cloture, appliquee a partir de la seance suivante.
        # La fenetre d'amorcage est la meme pour toutes les versions, sinon une
        # version a moyenne courte demarrerait plus tot et ne serait pas
        # comparable a une version a moyenne longue.
        if hier in decisions_dates:
            visible = table.loc[:hier]
            if len(visible) >= amorcage:
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
    total = v.iloc[-1] / v.iloc[0]
    annualise = total ** (SEANCES_PAR_AN / len(v)) - 1
    return {
        "debut": courbe["date"].iloc[0],
        "fin": courbe["date"].iloc[-1],
        "nb_seances": len(v),
        "perf_origine_pct": round((total - 1) * 100, 2),
        "perf_annualisee_pct": round(annualise * 100, 2),
        "perf_5j_pct": round((v.iloc[-1] / v.iloc[-6] - 1) * 100, 2) if len(v) > 6 else None,
        "perf_20j_pct": round((v.iloc[-1] / v.iloc[-21] - 1) * 100, 2) if len(v) > 21 else None,
        "drawdown_max_pct": round(((v / plus_haut) - 1).min() * 100, 2),
        "vol_periode_pct": round(rendements.std() * (SEANCES_PAR_AN ** 0.5) * 100, 2),
        "vol_20j_pct": round(rendements.iloc[-20:].std() * (SEANCES_PAR_AN ** 0.5) * 100, 2)
        if len(rendements) >= 20 else None,
        "nb_arbitrages": nb_arbitrages,
        "valeur_base_100": round(v.iloc[-1], 2),
    }


def restreindre(courbe: list[dict], debut: str) -> pd.DataFrame:
    """Sous-partie d'une courbe a partir d'une date, rebasee a 100."""
    points = [p for p in courbe if p["date"] >= debut]
    if not points:
        return pd.DataFrame(columns=["date", "valeur"])
    base = points[0]["valeur"]
    return pd.DataFrame({
        "date": [p["date"] for p in points],
        "valeur": [round(p["valeur"] / base * 100, 4) for p in points],
    })


def courbe_buy_and_hold(table: pd.DataFrame, poids: dict[str, float],
                        depart: pd.Timestamp) -> pd.DataFrame:
    """Composition figee, sans arbitrage, base 100 au premier jour de la fenetre."""
    fenetre = table.loc[depart:]
    valeurs = None
    for actif, part in poids.items():
        serie = fenetre[actif]
        contribution = serie / serie.iloc[0] * part
        valeurs = contribution if valeurs is None else valeurs + contribution
    return pd.DataFrame({
        "date": [d.date().isoformat() for d in fenetre.index],
        "valeur": [round(float(x), 4) for x in valeurs],
    })


def comparaisons(table: pd.DataFrame, depart: pd.Timestamp) -> dict:
    """Deux reperes passifs, calcules sur la fenetre walk-forward."""
    resultats = {}

    socle = courbe_buy_and_hold(table, {SOCLE: 50.0, FONDS_EUROS: 50.0}, depart)
    resultats["socle-monde-50"] = {
        "label": "Socle monde 50 % passif",
        "description": "Cinquante pour cent d'indice monde large conserves sans arbitrage, "
                       "cinquante pour cent de fonds en euros modelise. Aucun filtre.",
        "indicateurs": indicateurs(socle, 0),
        "courbe": socle.to_dict("records"),
    }

    lignes = pd.read_csv(PORTEFEUILLE)
    retenues = lignes[lignes["asset_id"].isin(THEMES)]
    if not retenues.empty:
        somme = float(retenues["allocation_pct"].sum())
        poids = {r.asset_id: float(r.allocation_pct) / somme * 50.0 for r in retenues.itertuples()}
        poids[FONDS_EUROS] = 50.0
        retro = courbe_buy_and_hold(table, poids, depart)
        resultats["bernard-retro-partiel"] = {
            "label": "Bernard actuel rétro-simulé, partiel",
            "description": "La composition connue en septembre 2026 appliquée en arrière sur "
                           "toute la fenêtre. Trois lignes seulement, celles cotées en euros, "
                           "remises à l'échelle pour 50 % du contrat.",
            "reserves": [
                "Biais de sélection majeur : appliquer en arrière une composition connue "
                "aujourd'hui revient à savoir dès 2022 quelles lignes seraient détenues en 2026. "
                "Cet ensemble contient les deux thèmes qui ont le plus progressé sur la période.",
                "Trois lignes sur douze. Les neuf autres supports du contrat sont absents, "
                "faute de cotation en euros ou d'historique suffisant.",
                "Pondérations reconstruites à l'échelle de 50 % du contrat, alors que la part "
                "actions réelle est inférieure.",
                "Aucun arbitrage et aucun rachat ne sont simulés.",
                "Cette ligne ne représente pas la performance réelle du contrat et ne sert "
                "jamais de référence.",
            ],
            "indicateurs": indicateurs(retro, 0),
            "courbe": retro.to_dict("records"),
        }
    return resultats


def ecrire_historique(decisions: list[dict]) -> int:
    """Ajout seul. Une decision deja inscrite n'est ni reecrite ni dupliquee."""
    HISTORIQUE.parent.mkdir(parents=True, exist_ok=True)
    connues = set()
    if HISTORIQUE.exists():
        for ligne in HISTORIQUE.read_text(encoding="utf-8").splitlines():
            if not ligne.strip():
                continue
            try:
                d = json.loads(ligne)
            except json.JSONDecodeError:
                continue
            connues.add((d.get("date"), d.get("strategy_id"), d.get("strategy_version")))

    ajoutees = 0
    with HISTORIQUE.open("a", encoding="utf-8") as f:
        for d in decisions:
            cle = (d["date"], d["strategy_id"], d["strategy_version"])
            if cle in connues:
                continue
            f.write(json.dumps(d, ensure_ascii=False) + "\n")
            connues.add(cle)
            ajoutees += 1
    return ajoutees


def noms_supports() -> dict[str, str]:
    noms = {FONDS_EUROS: "Fonds en euros, rendement modelise"}
    if UNIVERS.exists():
        u = pd.read_csv(UNIVERS)
        for r in u.itertuples():
            noms.setdefault(str(r.asset_id), str(r.support_name))
    return noms


def mettre_a_jour_tableau_de_bord(resultats: dict, noms: dict[str, str]) -> None:
    """Met a jour la seule cle 'strategies' de docs/data/claude.json.

    Le reste du fichier est produit par le script commun de tableau de bord et
    n'est pas touche ici.
    """
    if not SORTIE_WEB_TABLEAU.exists():
        return
    try:
        charge = json.loads(SORTIE_WEB_TABLEAU.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return
    charge["strategies"] = [
        {
            "id": identifiant,
            "label": s["label"],
            "version": f"hypothese {s['version']}",
            "short": s["resume"],
            "objective": s["objectif"],
            "main_rule": s["regle"],
            "details": s["explication"],
            "holdings": [
                {"asset_id": a["asset_id"], "name": noms.get(a["asset_id"], a["asset_id"]),
                 "weight_pct": a["weight_pct"]}
                for a in s["allocation_courante"]
            ],
            "status": s["statut_public"],
        }
        for identifiant, s in resultats.items()
    ]
    SORTIE_WEB_TABLEAU.write_text(json.dumps(charge, ensure_ascii=False), encoding="utf-8")


def main() -> int:
    parseur = argparse.ArgumentParser()
    parseur.add_argument("--strategie", default=None)
    args = parseur.parse_args()

    table = ajouter_fonds_euros(charger_prix())
    if len(table) < HISTORIQUE_MINIMAL_JOURS:
        raise SystemExit(
            f"Historique insuffisant : {len(table)} seances communes aux supports Claude, "
            f"{HISTORIQUE_MINIMAL_JOURS} necessaires pour une moyenne 200 jours.\n"
            "Augmentez la periode de collecte initiale dans scripts/update_market_data.py."
        )

    noms = noms_supports()
    resultats = {}
    toutes_decisions: list[dict] = []
    departs: list[str] = []

    for chemin in sorted(ESPACE.glob("*/strategy.yml")):
        strategie = yaml.safe_load(chemin.read_text(encoding="utf-8"))
        if args.strategie and strategie["id"] != args.strategie:
            continue
        if strategie["id"] not in MOTEURS:
            continue

        active = strategie["active_version"]
        simulables = [
            v for v, p in strategie["parameters"].items()
            if isinstance(p, dict) and p.get("currency_universe") == MARQUEUR_UNIVERS
        ]
        if active not in simulables:
            simulables.append(active)

        versions = {}
        for version in sorted(simulables):
            courbe, decisions = simuler(table, strategie, version)
            if courbe.empty:
                continue
            courbe.to_csv(chemin.parent / f"backtest_{version}.csv", index=False)
            toutes_decisions.extend(decisions)
            departs.append(courbe["date"].iloc[0])
            versions[version] = {
                "indicateurs": indicateurs(courbe, len(decisions)),
                "note": str(strategie["parameters"][version].get("note", "")).strip(),
                "filtre_tendance": strategie["parameters"][version].get("trend_filter", "sma_200"),
                "nb_decisions": len(decisions),
                "courbe": courbe.to_dict("records"),
                "allocation_finale": decisions[-1]["allocations"] if decisions else [],
            }

        non_simulees = sorted(set(strategie["parameters"]) - set(versions))
        courante = versions.get(active, {})
        resultats[strategie["id"]] = {
            "label": strategie["label"],
            "status": strategie["status"],
            "statut_public": "Hypothèse de recherche. Résultat de simulation, "
                             "aucune décision réelle n'a été prise à ces dates.",
            "version": active,
            "resume": str(strategie.get("summary", "")).strip()
            or str(strategie.get("main_rule", "")).strip().split(".")[0] + ".",
            "objectif": strategie["objective"].strip(),
            "regle": strategie["main_rule"].strip(),
            "explication": str(strategie.get("main_rule_scope", "")).strip()
            or str(strategie["parameters"][active].get("note", "")).strip(),
            "motif_version": str(strategie["parameters"][active].get("motif", "")).strip(),
            "faiblesse": strategie.get("known_weakness", "").strip(),
            "allocation_courante": courante.get("allocation_finale", []),
            "indicateurs": courante.get("indicateurs", {}),
            "nb_decisions": courante.get("nb_decisions", 0),
            "versions": versions,
            "versions_non_simulees": non_simulees,
            "decisions_recentes": [
                d for d in toutes_decisions
                if d["strategy_id"] == strategie["id"] and d["strategy_version"] == active
            ][-8:],
        }
        for version, v in versions.items():
            marque = " (active)" if version == active else ""
            print(f"{strategie['id']:28s} {version}{marque:9s} "
                  f"{v['nb_decisions']:>3} decisions  "
                  f"base 100 -> {v['indicateurs'].get('valeur_base_100')}")

    # Claude A, puis B, puis C, dans l'ordre des libelles.
    resultats = dict(sorted(resultats.items(), key=lambda kv: kv[1]["label"]))

    ajoutees = ecrire_historique(toutes_decisions)
    print(f"\nhistory/claude/decisions.jsonl : {ajoutees} decisions ajoutees "
          f"sur {len(toutes_decisions)} simulees")

    depart = pd.Timestamp(min(departs)) if departs else table.index[0]
    reperes = comparaisons(table, depart)

    # Les strategies n'ont pas toutes besoin de la meme profondeur avant leur
    # premiere decision. Le tableau comparatif se lit donc sur la fenetre
    # commune a toutes les lignes, la plus courte, pendant que chaque courbe
    # garde sa longueur propre.
    debut_commun = max(departs) if departs else None
    if debut_commun:
        for s in resultats.values():
            for version in s["versions"].values():
                extrait = restreindre(version["courbe"], debut_commun)
                version["indicateurs_fenetre_commune"] = indicateurs(
                    extrait, version["indicateurs"]["nb_arbitrages"])
            active = s["versions"].get(s["version"], {})
            s["indicateurs_fenetre_commune"] = active.get("indicateurs_fenetre_commune", {})
        for c in reperes.values():
            c["indicateurs_fenetre_commune"] = indicateurs(
                restreindre(c["courbe"], debut_commun), 0)

    charge = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "seances_disponibles": len(table),
        "premiere_seance": table.index[0].date().isoformat(),
        "derniere_seance": table.index[-1].date().isoformat(),
        "seances_amorcage": SEANCES_AMORCAGE,
        "debut_fenetre_walk_forward": min(departs) if departs else None,
        "debut_fenetre_commune": debut_commun,
        "univers": {
            "regle": "Uniquement des lignes cotées en euros sur une place de la zone euro.",
            "supports": [{"asset_id": a, "nom": noms.get(a, a)} for a in SUPPORTS_COTES],
            "elargi": {
                "regle": "Tous les fonds cotés en euros sur une place de la zone euro "
                         "disposant de cinq ans de cours. Les stratégies qui classent les "
                         "supports choisissent dans cet ensemble.",
                "biais_connu": "Cet ensemble est celui des supports encore référencés "
                               "aujourd'hui. Un fonds fermé ou retiré du contrat depuis 2021 "
                               "n'y figure pas, ce qui flatte légèrement le classement.",
                "supports": [{"asset_id": a, "nom": noms.get(a, a)}
                             for a in table.columns
                             if a not in (FONDS_EUROS,)],
            },
        },
        "noms_supports": {a: noms.get(a, a) for a in list(table.columns) + [FONDS_EUROS]},
        "rendement_fonds_euros_modelise_pct": RENDEMENT_FONDS_EUROS_ANNUEL * 100,
        "strategies": resultats,
        "comparaisons": reperes,
    }
    # La page a besoin des courbes ; le fichier versionne du depot n'en a pas
    # besoin, les memes points etant deja dans les CSV.
    synthese = json.loads(json.dumps(charge, ensure_ascii=False))
    for s in synthese["strategies"].values():
        for v in s["versions"].values():
            v.pop("courbe", None)
    for c in synthese["comparaisons"].values():
        c.pop("courbe", None)

    sortie = ESPACE / "strategies.json"
    sortie.write_text(json.dumps(synthese, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Ecrit : {sortie}")

    # Copie lisible par la page publiee, GitHub Pages ne servant que docs/.
    # Ce chemin ne figure pas encore dans config/access-policy.yml, qui reste
    # a completer par l'administrateur du depot.
    if SORTIE_WEB.parent.exists():
        SORTIE_WEB.write_text(json.dumps(charge, ensure_ascii=False), encoding="utf-8")
        print(f"Ecrit : {SORTIE_WEB}")
        mettre_a_jour_tableau_de_bord(resultats, noms)
        print(f"Mis a jour : {SORTIE_WEB_TABLEAU} (cle strategies)")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
