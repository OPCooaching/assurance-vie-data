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
VALORISATION = RACINE / "data" / "benchmarks" / "bernard_valuation_status.json"
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
def versions_actives() -> dict[str, str]:
    """Version active de chaque stratégie, lue dans son fichier de règles."""
    correspondance = {}
    for chemin in sorted(ESPACE.glob("*/strategy.yml")):
        regle = yaml.safe_load(chemin.read_text(encoding="utf-8"))
        correspondance[regle["id"].replace("-", "_")] = regle["active_version"]
    return correspondance


VERSIONS = versions_actives()



def noms_lisibles() -> dict[str, str]:
    """Nom complet de chaque support, pour que les mouvements soient lisibles."""
    acronymes = {"Ishares": "iShares", "Msci": "MSCI", "Ucits": "UCITS", "Etf": "ETF",
                 "Eur": "EUR", "Em": "EM", "Ii": "II", "Esg": "ESG", "Sri": "SRI",
                 "Us": "US", "Usa": "USA", "Dax": "DAX", "Cac": "CAC", "Bnp": "BNP",
                 "Jpm": "JPM", "Pab": "PAB", "Stoxx": "STOXX", "Acc": "capitalisant",
                 "Dist": "distribuant", "Ex-China": "ex-Chine"}
    noms = {}
    if UNIVERS.exists():
        for ligne in pd.read_csv(UNIVERS).itertuples():
            mots = [acronymes.get(m, m) for m in str(ligne.support_name).title().split()]
            noms[str(ligne.asset_id)] = " ".join(mots).replace("(De)", "(Allemagne)")
    noms[FONDS_EURO] = "Fonds en euros du contrat"
    return noms


def derniere_decision(identifiant: str) -> dict:
    """Décision précédente d'une stratégie, pour mesurer ce qui a changé."""
    if not DECISIONS.exists():
        return {}
    fichiers = sorted(DECISIONS.glob(f"*--{identifiant.replace('_', '-')}.json"))
    if not fichiers:
        return {}
    try:
        return json.loads(fichiers[-1].read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def mouvements(avant: dict, apres: dict, noms: dict) -> tuple[dict, str]:
    """Ce qui entre, sort, est renforcé ou allégé entre deux allocations.

    Le fonds en euros est la poche non exposée : il n'est pas un choix de
    sélection et reste hors du récit des mouvements.
    """
    marche = lambda d: {a: w for a, w in d.items() if a != FONDS_EURO}
    a, b = marche(avant), marche(apres)
    entrees = sorted(set(b) - set(a))
    sorties = sorted(set(a) - set(b))
    communs = sorted(set(a) & set(b))
    renforces = [x for x in communs if b[x] - a[x] > 0.05]
    alleges = [x for x in communs if a[x] - b[x] > 0.05]
    inchanges = [x for x in communs if abs(b[x] - a[x]) <= 0.05]

    detail = {
        "entrees": [{"asset_id": x, "nom": noms.get(x, x), "poids_pct": b[x]} for x in entrees],
        "sorties": [{"asset_id": x, "nom": noms.get(x, x), "poids_pct_precedent": a[x]} for x in sorties],
        "renforces": [{"asset_id": x, "nom": noms.get(x, x), "de_pct": a[x], "a_pct": b[x]} for x in renforces],
        "alleges": [{"asset_id": x, "nom": noms.get(x, x), "de_pct": a[x], "a_pct": b[x]} for x in alleges],
        "inchanges": [{"asset_id": x, "nom": noms.get(x, x), "poids_pct": b[x]} for x in inchanges],
        "part_exposee_pct": round(sum(b.values()), 2),
        "part_exposee_precedente_pct": round(sum(a.values()), 2),
    }

    fr = lambda v: f"{v:.2f}".replace(".", ",") + " %"
    if not avant:
        if b:
            phrases = ["Première allocation : " + ", ".join(
                f"{noms.get(x, x)} à {fr(b[x])}" for x in sorted(b, key=lambda x: -b[x])) + ".",
                f"Part exposée aux marchés : {fr(detail['part_exposee_pct'])}."]
        else:
            phrases = ["Première allocation : aucun support exposé, "
                       "la totalité reste sur le fonds en euros."]
    else:
        phrases = []
        if entrees:
            phrases.append("Entrées : " + ", ".join(
                f"{noms.get(x, x)} à {fr(b[x])}" for x in entrees) + ".")
        if sorties:
            phrases.append("Sorties : " + ", ".join(
                f"{noms.get(x, x)}, qui pesait {fr(a[x])}" for x in sorties) + ".")
        if renforces:
            phrases.append("Renforcés : " + ", ".join(
                f"{noms.get(x, x)} de {fr(a[x])} à {fr(b[x])}" for x in renforces) + ".")
        if alleges:
            phrases.append("Allégés : " + ", ".join(
                f"{noms.get(x, x)} de {fr(a[x])} à {fr(b[x])}" for x in alleges) + ".")
        if inchanges:
            phrases.append(f"Inchangés : {len(inchanges)} support(s).")
        if not entrees and not sorties and not renforces and not alleges:
            phrases = ["Aucun mouvement : l'allocation de la semaine précédente est conservée."]
        ecart = detail["part_exposee_pct"] - detail["part_exposee_precedente_pct"]
        if abs(ecart) > 0.05:
            phrases.append(f"Part exposée aux marchés : {fr(detail['part_exposee_precedente_pct'])} "
                           f"puis {fr(detail['part_exposee_pct'])}.")
    return detail, " ".join(phrases)


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
        # La revue a lieu sur la dernière valorisation de la semaine, le
        # vendredi : la décision est prise sur cette clôture et s'applique à
        # la valorisation suivante, donc au lundi. C'est la convention du
        # protocole commun du 23 septembre 2026.
        if date.weekday() == 4:
            poids = signal(table, date, univers, contexte)
            derniere = dict(poids)
        points.append((date, valeur))
        veille = prix
    return pd.Series(dict(points)), derniere


def jour_de_revue(date_valorisation) -> bool:
    """La semaine est-elle close, de sorte que la décision puisse être prise ?

    La revue porte sur la dernière valorisation de la semaine. Le cas normal est
    le vendredi. Si le vendredi est férié ou si la collecte de vendredi soir a
    échoué, la revue du samedi rattrape sur la dernière clôture disponible,
    même vieille d'un ou deux jours : passé le vendredi, aucune cotation
    nouvelle n'arrivera pour cette semaine.
    """
    return date_valorisation.weekday() == 4 or datetime.now(timezone.utc).weekday() >= 5


def inscrire_decisions(decisions, date_valorisation) -> int:
    """Une décision par stratégie et par semaine, jamais réécrite.

    L'absence d'écriture est normale : hors jour de revue, ou si la semaine de
    cette valorisation a déjà sa décision.
    """
    if not jour_de_revue(date_valorisation):
        return 0
    semaine = date_valorisation.isocalendar()
    deja = list(DECISIONS.glob("*--claude-*.json")) if DECISIONS.exists() else []
    semaines_connues = {
        pd.Timestamp(f.name[:10]).isocalendar()[:2] for f in deja if f.name[:4].isdigit()
    }
    if (semaine.year, semaine.week) in semaines_connues:
        return 0

    DECISIONS.mkdir(parents=True, exist_ok=True)
    jour = date_valorisation.date().isoformat()
    maintenant = datetime.now(timezone.utc).isoformat(timespec="seconds")
    noms = noms_lisibles()
    inscrites = 0
    for identifiant, _date, poids, _liquide in decisions:
        chemin = DECISIONS / f"{jour}--{identifiant.replace('_', '-')}.json"
        if chemin.exists():
            continue
        cible = {a: round(100 * w, 2) for a, w in sorted(poids.items())}
        cible[FONDS_EURO] = round(100 - sum(cible.values()), 2)
        precedente = derniere_decision(identifiant)
        detail, recit = mouvements(
            precedente.get("target_allocation_percent", {}), cible, noms)
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
            "rationale": recit,
            "target_allocation_percent": cible,
            "mouvements": detail,
            "warnings": [],
        }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        inscrites += 1
    return inscrites


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

    # Une date reste provisoire tant qu'un support n'a pas publié son cours
    # officiel : sa valeur est alors calculée avec le dernier cours connu, puis
    # corrigée dès la publication. Le recalcul repart donc de la dernière date
    # réellement consolidée, et les lignes postérieures sont réécrites. Les
    # lignes antérieures, elles, sont définitives et jamais retouchées.
    socle = dernier_publie
    if VALORISATION.exists():
        statut = json.loads(VALORISATION.read_text(encoding="utf-8"))
        consolide = statut.get("latest_consolidated_date")
        if consolide:
            anterieures = publie.loc[publie["date"] <= pd.Timestamp(consolide), "date"]
            if not anterieures.empty:
                socle = pd.Timestamp(anterieures.max())

    a_calculer = [d for d in dates if d >= (reprise or socle)]
    # Le samedi, aucune valorisation nouvelle n'apparaît : il n'y a rien à
    # ajouter aux courbes, mais la décision de la semaine reste à prendre sur
    # la dernière clôture disponible. Le calcul des courbes est donc séparé de
    # l'inscription de la décision.
    nouvelles_valorisations = len(a_calculer) >= 2

    # Chaque colonne reprend à sa dernière valeur publiée ; une colonne nouvelle
    # part de 100 à sa première date de calcul, et reste vide avant.
    courbes, allocations, decisions = {}, [], []
    for identifiant, signal in STRATEGIES.items() if nouvelles_valorisations else ():
        if identifiant in publie.columns:
            connues = publie[["date", identifiant]].dropna()
            connues = connues[connues["date"] <= socle]
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

    if not nouvelles_valorisations:
        # Les règles sont des fonctions de la date : la même clôture donne la
        # même allocation, avec ou sans passage par les courbes.
        for identifiant, signal in STRATEGIES.items():
            poids = signal(table, dates[-1], univers, contexte)
            decisions.append((identifiant, dates[-1], poids, 1.0 - sum(poids.values())))
        nouvelles_lignes = pd.DataFrame()
        inscrites = inscrire_decisions(decisions, dates[-1])
        print(f"Moteur Claude : {len(STRATEGIES)} stratégies, aucune date nouvelle, "
              f"{inscrites} décision(s) inscrite(s).")
        return 0

    nouveau = pd.DataFrame(courbes)
    nouveau.index.name = "date"
    nouvelles_lignes = nouveau.loc[nouveau.index > socle]
    # Une stratégie publiée pour la première fois naît à la dernière date déjà
    # valorisée : sa base 100 est posée ce jour-là, et rien avant.
    naissances = {c: nouveau[c] for c in nouveau.columns if c not in publie.columns}

    # Contrôle avant écriture : aucune valeur déjà publiée ne doit changer.
    complet = publie.set_index("date")
    for colonne in nouvelles_lignes.columns:
        if colonne not in complet.columns:
            complet[colonne] = pd.NA
    complet = complet.loc[complet.index <= socle]
    complet = pd.concat([complet, nouvelles_lignes.reindex(columns=complet.columns)])
    for colonne, serie in naissances.items():
        for date, valeur in serie.items():
            if date in complet.index:
                complet.loc[date, colonne] = valeur
    verification = complet.loc[complet.index <= socle]
    origine = publie.set_index("date")
    origine = origine.loc[origine.index <= socle]
    for colonne in origine.columns:
        avant = origine[colonne].dropna()
        apres = verification[colonne].reindex(avant.index)
        if not avant.round(10).equals(apres.round(10)):
            raise RuntimeError(f"Valeur publiée modifiée sur {colonne} : écriture refusée.")

    complet.sort_index().to_csv(SORTIE, date_format="%Y-%m-%d")
    pd.DataFrame(allocations).to_csv(ALLOCATIONS, index=False)

    inscrites = inscrire_decisions(decisions, a_calculer[-1])

    print(f"Moteur Claude : {len(STRATEGIES)} stratégies, "
          f"{len(nouvelles_lignes)} date(s) ajoutée(s), {inscrites} décision(s) inscrite(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
