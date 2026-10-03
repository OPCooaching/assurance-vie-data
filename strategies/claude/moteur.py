"""Calcul quotidien des stratégies Claude, sur prix réels uniquement.

Ce moteur remplace scripts/compute_claude_strategies.py et vit dans l'espace
Claude, pour qu'une règle nouvelle n'exige plus de modifier un fichier commun.
Il produit exactement les mêmes fichiers, aux mêmes formats.

Garanties tenues ici, et vérifiées avant toute écriture :

  - une valeur déjà publiée n'est jamais recalculée ni modifiée ;
  - aucune date n'est inventée : seules les dates de valorisation réellement
    présentes dans data/benchmarks/bernard_origin.csv sont utilisées ;
  - le trou de suivi du 18 au 30 septembre 2026 reste un trou ;
  - une stratégie nouvelle démarre à 100 le jour de son premier calcul, et
    laisse vides les dates antérieures à son existence ;
  - une décision prise lors d'une revue s'applique à la valorisation suivante.

Sorties :
  data/claude/performance.csv        une colonne par stratégie, base 100
  data/claude/latest_allocations.csv composition de la dernière revue
  history/claude/decisions/          une décision par fichier, les jours de revue
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import yaml

RACINE = Path(__file__).resolve().parents[2]
UNIVERS = RACINE / "config" / "universe.csv"
SYMBOLES = RACINE / "config" / "symbol_map.csv"
PRIX = RACINE / "data" / "prices" / "daily.csv"
REFERENCE = RACINE / "data" / "benchmarks" / "bernard_origin.csv"
CONTEXTE = RACINE / "data" / "context" / "daily.csv"
ESPACE = RACINE / "strategies" / "claude"
SORTIE = RACINE / "data" / "claude" / "performance.csv"
ALLOCATIONS = RACINE / "data" / "claude" / "latest_allocations.csv"
ETAT = RACINE / "data" / "claude" / "tracking_state.json"
DECISIONS = RACINE / "history" / "claude" / "decisions"

PART_MARCHE = 0.50
SOCLE, SOCLE_MIN_VOL, MONETAIRE = "IE00BKBF6H24", "IE00BL25JN58", "LU0290358497"
FONDS_EURO = "ALTAPROFITS:FONDS-EN-EURO-NETISSIMA"
THEMES = ["IE000I8KRLL9", "LU1829219390", "IE00BMG6Z448"]
PLACES_ZONE_EURO = {"PAR", "GER", "AMS", "MIL", "BRU", "FRA", "MUN", "LIS",
                    "VIE", "STU", "HAM", "BER", "DUS", "MCE", "HEL", "LUX"}
PROFONDEUR_MINIMALE = 1250
SEANCES_PAR_AN = 252


# --------------------------------------------------------------------------
# Lecture des données communes, en lecture seule
# --------------------------------------------------------------------------

def charger_prix():
    lignes = pd.read_csv(PRIX)
    if "close_eur" not in lignes.columns:
        raise ValueError("Le moteur Claude exige des prix normalisés en euros.")
    lignes["date"] = pd.to_datetime(lignes["date"])
    table = lignes.pivot_table(index="date", columns="asset_id", values="close_eur", aggfunc="last")
    return table.sort_index().ffill(), lignes


def charger_contexte() -> pd.DataFrame:
    if not CONTEXTE.exists():
        return pd.DataFrame()
    contexte = pd.read_csv(CONTEXTE, parse_dates=["date"])
    return contexte.set_index("date").sort_index()


def univers_euro(lignes, table) -> list[str]:
    symboles = pd.read_csv(SYMBOLES)
    univers = pd.read_csv(UNIVERS)
    fusion = symboles.merge(univers[["asset_id", "category"]], on="asset_id", how="left")
    autorises = fusion[
        (fusion["status"] == "resolved")
        & fusion["exchange"].isin(PLACES_ZONE_EURO)
        & fusion["category"].fillna("").str.upper().isin({"ETF", "OPCVM/FI"})
    ]["asset_id"]
    profondeur = lignes[lignes["asset_id"].isin(set(autorises))].groupby("asset_id")["date"].count()
    return sorted(
        a for a in profondeur[profondeur >= PROFONDEUR_MINIMALE].index
        if a in table.columns and a != MONETAIRE
    )


def passe(table, date):
    return table.loc[:date]


def au_dessus_moyenne(table, actif, date, jours) -> bool:
    valeurs = passe(table, date)[actif].dropna()
    return len(valeurs) >= jours and float(valeurs.iloc[-1]) >= float(valeurs.iloc[-jours:].mean())


def volatilite_annuelle(table, actif, date, jours):
    valeurs = passe(table, date)[actif].dropna()
    if len(valeurs) < jours + 1:
        return None
    return float(valeurs.iloc[-jours - 1:].pct_change().dropna().std() * SEANCES_PAR_AN ** 0.5)


def derniere_valeur_publiee(contexte, colonne, date, latence_max_jours):
    """Dernière valeur réellement publiée à cette date, si elle n'est pas périmée."""
    if contexte.empty or colonne not in contexte.columns:
        return None, None
    serie = contexte.loc[:date, colonne].dropna()
    if serie.empty:
        return None, None
    publiee = serie.index[-1]
    if (date - publiee).days > latence_max_jours:
        return None, publiee
    return float(serie.iloc[-1]), publiee


# --------------------------------------------------------------------------
# Les cinq témoins, logique inchangée depuis le 9 septembre 2026
# --------------------------------------------------------------------------

def poids_socle(table, date, part_marche, jours_tendance):
    socle = part_marche * 0.60
    theme = min((part_marche * 0.40) / len(THEMES), part_marche * 0.16)
    cibles = [(SOCLE, socle * 0.70), (SOCLE_MIN_VOL, socle * 0.30)] + [(a, theme) for a in THEMES]
    poids, reserve = {}, 0.0
    for actif, poids_cible in cibles:
        if au_dessus_moyenne(table, actif, date, jours_tendance):
            poids[actif] = poids_cible
        else:
            reserve += poids_cible
    if reserve:
        poids[MONETAIRE] = poids.get(MONETAIRE, 0.0) + reserve
    return poids


def completer(poids: dict) -> dict:
    """Le solde non investi rejoint le support monétaire."""
    reste = PART_MARCHE - sum(poids.values())
    if reste > 1e-9:
        poids[MONETAIRE] = poids.get(MONETAIRE, 0.0) + reste
    return {a: w for a, w in poids.items() if w > 0}


def claude_socle_satellites(table, date, univers, contexte):
    return poids_socle(table, date, PART_MARCHE, 200)


def claude_risque_cible(table, date, univers, contexte):
    vol = volatilite_annuelle(table, SOCLE, date, 40)
    cible = 0.20 if not vol or vol <= 0 else max(0.20, min(0.60, 0.10 / vol))
    return completer(poids_socle(table, date, cible, 200))


def claude_double_filtre(table, date, univers, contexte):
    tendance = au_dessus_moyenne(table, SOCLE, date, 100)
    ampleur = sum(au_dessus_moyenne(table, a, date, 100) for a in THEMES) / len(THEMES) >= 0.50
    cible = PART_MARCHE if tendance and ampleur else PART_MARCHE * 0.50 if tendance or ampleur else 0.0
    if not cible:
        return {MONETAIRE: PART_MARCHE}
    return completer(poids_socle(table, date, cible, 100))


def classement_momentum(table, date, univers, garde: bool) -> list[str]:
    if garde and not au_dessus_moyenne(table, SOCLE, date, 200):
        return []
    histoire = passe(table, date)[univers]
    if len(histoire) <= 252:
        return []
    dernier = histoire.iloc[-1]
    scores = {}
    for actif in univers:
        anterieurs = [histoire[actif].iloc[-127], histoire[actif].iloc[-253]]
        if pd.notna(dernier[actif]) and all(pd.notna(x) and x > 0 for x in anterieurs):
            scores[actif] = sum(float(dernier[actif]) / float(x) - 1 for x in anterieurs) / 2
    return [a for a, s in sorted(scores.items(), key=lambda kv: -kv[1]) if s > 0][:6]


def claude_momentum_multi(table, date, univers, contexte):
    retenus = classement_momentum(table, date, univers, False)
    return completer({a: PART_MARCHE / 6 for a in retenus})


def claude_momentum_prudent(table, date, univers, contexte):
    retenus = classement_momentum(table, date, univers, True)
    poids = {}
    if retenus:
        inverses = {a: 1 / max(volatilite_annuelle(table, a, date, 60) or 0.02, 0.02) for a in retenus}
        montant, total = PART_MARCHE * len(retenus) / 6, sum(inverses.values())
        poids = {a: montant * v / total for a, v in inverses.items()}
    return completer(poids)


# --------------------------------------------------------------------------
# Claude F — structure du marché
# --------------------------------------------------------------------------

def claude_dispersion(table, date, univers, contexte):
    fenetre = 60
    histoire = passe(table, date)[univers].tail(fenetre + 1)
    rendements = histoire.pct_change().dropna(how="all").dropna(axis=1, how="any")
    if rendements.shape[1] < 10 or len(rendements) < fenetre:
        return {MONETAIRE: PART_MARCHE}

    matrice = rendements.corr()
    n = len(matrice)
    correlation_moyenne = (matrice.values.sum() - n) / (n * (n - 1))
    dispersion = float(rendements.std(axis=1).mean()) * 100

    if correlation_moyenne >= 0.55:
        lignes, part = 3, PART_MARCHE * 0.50
    elif correlation_moyenne <= 0.35 and dispersion >= 0.55:
        lignes, part = 10, PART_MARCHE
    else:
        lignes, part = 6, PART_MARCHE

    # Les supports retenus sont les moins liés aux autres, pas les plus hauts.
    liens = ((matrice.sum() - 1) / (n - 1)).sort_values()
    retenus = list(liens.index[:lignes])
    return completer({a: part / lignes for a in retenus})


# --------------------------------------------------------------------------
# Claude G — retour à la moyenne
# --------------------------------------------------------------------------

def claude_contrarien(table, date, univers, contexte):
    histoire = passe(table, date)[univers]
    if len(histoire) <= 253:
        return {MONETAIRE: PART_MARCHE}
    dernier = histoire.iloc[-1]
    candidats = {}
    for actif in univers:
        longue, courte = histoire[actif].iloc[-253], histoire[actif].iloc[-21]
        if not (pd.notna(dernier[actif]) and pd.notna(longue) and pd.notna(courte)):
            continue
        if longue <= 0 or courte <= 0:
            continue
        tendance = float(dernier[actif]) / float(longue) - 1
        recul = float(dernier[actif]) / float(courte) - 1
        if tendance > 0 and -0.20 <= recul <= -0.01:
            candidats[actif] = recul
    retenus = [a for a, _ in sorted(candidats.items(), key=lambda kv: kv[1])][:5]
    return completer({a: PART_MARCHE / 5 for a in retenus})


# --------------------------------------------------------------------------
# Claude H — dollar et énergie
# --------------------------------------------------------------------------

REGIMES = yaml.safe_load((ESPACE / "dollar-energie" / "strategy.yml").read_text(encoding="utf-8"))
REGIMES = REGIMES["parameters"]["v0.1"]["regimes"]
_axes = {"dollar": None, "energie": None}


def _axe(valeur, serie, fenetre, seuil, etat, positif, negatif):
    """Un axe ne bascule qu'au-delà de son seuil ; sinon il garde son état.

    À la première décision, faute d'état précédent, le signe de la variation
    suffit : sans cela aucun régime ne s'établirait jamais.
    """
    if valeur is None or len(serie) <= fenetre:
        return etat
    variation = (valeur / float(serie.iloc[-fenetre - 1]) - 1) * 100
    if abs(variation) >= seuil or etat is None:
        return positif if variation > 0 else negatif
    return etat


def claude_dollar_energie(table, date, univers, contexte):
    fenetre, latence = 60, 10
    if contexte.empty:
        return {MONETAIRE: PART_MARCHE}
    dollar, _ = derniere_valeur_publiee(contexte, "broad_us_dollar", date, latence)
    brent, _ = derniere_valeur_publiee(contexte, "brent_europe_usd", date, latence)

    _axes["dollar"] = _axe(dollar, contexte.loc[:date, "broad_us_dollar"].dropna(),
                           fenetre, 2.0, _axes["dollar"], "dollar_fort", "dollar_faible")
    _axes["energie"] = _axe(brent, contexte.loc[:date, "brent_europe_usd"].dropna(),
                            fenetre, 10.0, _axes["energie"], "energie_chere", "energie_basse")

    if not _axes["dollar"] or not _axes["energie"]:
        # Données trop anciennes et aucun régime encore établi : rien n'est investi.
        return {MONETAIRE: PART_MARCHE}

    composition = REGIMES[f'{_axes["dollar"]}_{_axes["energie"]}']["composition"]
    return completer({a: w / 100 for a, w in composition.items() if a in table.columns})


# --------------------------------------------------------------------------

STRATEGIES = {
    "claude_socle_satellites": claude_socle_satellites,
    "claude_risque_cible": claude_risque_cible,
    "claude_double_filtre": claude_double_filtre,
    "claude_momentum_multi": claude_momentum_multi,
    "claude_momentum_prudent": claude_momentum_prudent,
    "claude_dispersion": claude_dispersion,
    "claude_contrarien": claude_contrarien,
    "claude_dollar_energie": claude_dollar_energie,
}
VERSIONS = {
    "claude_socle_satellites": "v0.3", "claude_risque_cible": "v0.2",
    "claude_double_filtre": "v0.2", "claude_momentum_multi": "v0.1",
    "claude_momentum_prudent": "v0.1", "claude_dispersion": "v0.1",
    "claude_contrarien": "v0.1", "claude_dollar_energie": "v0.1",
}


def courbe(table, dates, signal, univers, contexte, valeur_depart):
    """Base 100 au départ, décision le lundi, application à la valorisation suivante."""
    valeur = float(valeur_depart)
    poids, veille, derniere = None, None, {}
    points = []
    for rang, date in enumerate(dates):
        prix = table.loc[date]
        if rang == 0:
            poids = signal(table, date, univers, contexte)
            derniere = dict(poids)
            points.append((date, valeur))
            veille = prix
            continue
        if poids:
            rendement = sum(
                float(w) * (float(prix[a]) / float(veille[a]) - 1)
                for a, w in poids.items()
                if a in prix and pd.notna(prix[a]) and pd.notna(veille[a]) and veille[a] > 0
            )
            valeur *= 1 + rendement
        if date.weekday() == 0:
            poids = signal(table, date, univers, contexte)
            derniere = dict(poids)
        points.append((date, valeur))
        veille = prix
    return pd.Series(dict(points)), derniere


def main() -> int:
    obligatoires = (UNIVERS, SYMBOLES, PRIX, REFERENCE, SORTIE)
    manquants = [str(p) for p in obligatoires if not p.exists()]
    if manquants:
        print("Moteur Claude ignoré, fichiers absents : " + ", ".join(manquants))
        return 0

    table, lignes = charger_prix()
    contexte = charger_contexte()
    univers = univers_euro(lignes, table)
    dates = [d for d in pd.to_datetime(pd.read_csv(REFERENCE)["date"]) if d in table.index]
    if not dates:
        print("Moteur Claude ignoré : aucune date de valorisation commune.")
        return 0

    publie = pd.read_csv(SORTIE, parse_dates=["date"]).sort_values("date")
    dernier_publie = pd.Timestamp(publie["date"].max())
    etat = json.loads(ETAT.read_text(encoding="utf-8")) if ETAT.exists() else {}
    reprise = pd.Timestamp(etat["resume_date"]) if etat.get("resume_date") else None

    a_calculer = [d for d in dates if d >= (reprise or dernier_publie)]
    if len(a_calculer) < 2:
        print("Moteur Claude : aucune date nouvelle à calculer.")
        return 0

    # Chaque colonne reprend à sa dernière valeur publiée ; une colonne nouvelle
    # part de 100 à sa première date de calcul, et reste vide avant.
    courbes, allocations, decisions = {}, [], []
    for identifiant, signal in STRATEGIES.items():
        if identifiant in publie.columns:
            connues = publie[["date", identifiant]].dropna()
            depart = float(connues[identifiant].iloc[-1]) if not connues.empty else 100.0
        else:
            depart = 100.0
        serie, derniere = courbe(table, a_calculer, signal, univers, contexte, depart)
        courbes[identifiant] = serie
        liquide = 1.0 - sum(derniere.values())
        for actif, poids in sorted(derniere.items()):
            allocations.append({"strategy_id": identifiant, "asset_id": actif,
                                "weight_pct": round(100 * poids, 6)})
        allocations.append({"strategy_id": identifiant, "asset_id": FONDS_EURO,
                            "weight_pct": round(100 * liquide, 6)})
        decisions.append((identifiant, a_calculer[-1], derniere, liquide))

    nouveau = pd.DataFrame(courbes)
    nouveau.index.name = "date"
    nouvelles_lignes = nouveau.loc[nouveau.index > dernier_publie]
    # Une stratégie publiée pour la première fois naît à la dernière date déjà
    # valorisée : sa base 100 est posée ce jour-là, et rien avant.
    naissances = {c: nouveau[c] for c in nouveau.columns if c not in publie.columns}

    # Contrôle avant écriture : aucune valeur déjà publiée ne doit changer.
    complet = publie.set_index("date")
    for colonne in nouvelles_lignes.columns:
        if colonne not in complet.columns:
            complet[colonne] = pd.NA
    complet = pd.concat([complet, nouvelles_lignes.reindex(columns=complet.columns)])
    for colonne, serie in naissances.items():
        for date, valeur in serie.items():
            if date in complet.index:
                complet.loc[date, colonne] = valeur
    verification = complet.loc[complet.index <= dernier_publie]
    origine = publie.set_index("date")
    for colonne in origine.columns:
        avant = origine[colonne].dropna()
        apres = verification[colonne].reindex(avant.index)
        if not avant.round(10).equals(apres.round(10)):
            raise RuntimeError(f"Valeur publiée modifiée sur {colonne} : écriture refusée.")

    complet.sort_index().to_csv(SORTIE, date_format="%Y-%m-%d")
    pd.DataFrame(allocations).to_csv(ALLOCATIONS, index=False)

    # Journal des décisions, uniquement les jours de revue effectivement calculés.
    inscrites = 0
    if a_calculer[-1].weekday() == 0:
        DECISIONS.mkdir(parents=True, exist_ok=True)
        jour = a_calculer[-1].date().isoformat()
        maintenant = datetime.now(timezone.utc).isoformat(timespec="seconds")
        for identifiant, date, poids, liquide in decisions:
            chemin = DECISIONS / f"{jour}--{identifiant.replace('_', '-')}.json"
            if chemin.exists():
                continue
            cible = {a: round(100 * w, 2) for a, w in sorted(poids.items())}
            cible[FONDS_EURO] = round(100 - sum(cible.values()), 2)
            chemin.write_text(json.dumps({
                "schema_version": "1.0",
                "record_kind": "weekly_strategy_decision",
                "status": "decided_on_published_prices",
                "decision_id": f"{jour}--{identifiant}",
                "decided_at_utc": maintenant,
                "effective_valuation_date": jour,
                "author": "claude",
                "strategy_id": identifiant,
                "strategy_version": VERSIONS[identifiant],
                "decision_type": "weekly_allocation",
                "rationale": "Revue hebdomadaire sur les prix et le contexte publiés à cette date.",
                "target_allocation_percent": cible,
                "warnings": [],
            }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            inscrites += 1

    print(f"Moteur Claude : {len(STRATEGIES)} stratégies, "
          f"{len(nouvelles_lignes)} date(s) ajoutée(s), {inscrites} décision(s) inscrite(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
