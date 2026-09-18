# assurance-vie-data

Source commune, neutre et anonymisée des données utilisées pour le suivi de l'assurance-vie.

## Rôle du dépôt

Ce dépôt contient uniquement :
- l'univers des supports disponibles ;
- les correspondances ISIN / symboles de marché ;
- les historiques de cours récupérés automatiquement ;
- les indicateurs de marché communs ;
- une représentation anonymisée du portefeuille courant ;
- les journaux techniques de mise à jour.

Il ne contient **aucune stratégie d'investissement propre à une IA**.

Les deux moteurs utilisent exactement la même base :
- **ChatGPT**
- **strategie-claude**

## Règles d'accès

| Espace | ChatGPT | strategie-claude | Automatisation |
|---|---|---|---|
| `assurance-vie-data` | lecture | lecture | lecture + écriture des données générées |
| `strategie-chatgpt` | lecture + écriture | lecture | selon son propre workflow |
| `strategie-claude` | lecture | lecture + écriture | selon son propre workflow |

Dans **ce dépôt**, ChatGPT et strategie-claude peuvent analyser tout le contenu mais ne doivent pas écrire leurs décisions, scores propriétaires, portefeuilles proposés ou résultats de stratégie.

Chaque IA écrit uniquement dans son dépôt de stratégie. Les deux peuvent lire les résultats de l'autre pour comparaison.

## Anonymisation obligatoire

Ce dépôt est conçu pour pouvoir être public.

**Interdit :**
- nom de famille ;
- adresse ;
- e-mail ;
- téléphone ;
- date de naissance complète ;
- numéro de contrat ;
- identifiant client ;
- document contractuel brut ;
- montant exact du contrat ou du patrimoine ;
- clause bénéficiaire ;
- toute donnée permettant d'identifier Bernard.

Le prénom **Bernard** peut être utilisé comme alias.

Le portefeuille courant est stocké uniquement en **pourcentages / base 100**.

## Arborescence

```text
config/
  universe.csv
  portfolio_current.csv
  symbol_map.csv
  access-policy.yml

data/
  prices/
  indicators/
  snapshots/
  logs/

scripts/
  resolve_symbols.py
  update_market_data.py
  compute_indicators.py
  validate_public_data.py

.github/workflows/
  daily-update.yml
```

## Principe de fonctionnement

1. `config/universe.csv` contient les supports Altaprofits disponibles.
2. `resolve_symbols.py` cherche progressivement les symboles de marché à partir des ISIN.
3. `update_market_data.py` récupère chaque jour les cours des supports résolus.
4. `compute_indicators.py` calcule les indicateurs communs et reproductibles.
5. GitHub Actions enregistre les mises à jour.
6. ChatGPT et strategie-claude lisent ces mêmes données et écrivent leurs stratégies dans leurs dépôts respectifs.

## Ce qui est commun et ce qui ne l'est pas

Les données communes peuvent contenir : cours, rendements 5/20/60/120 jours, volatilité, drawdown, moyennes mobiles, momentum et métadonnées objectives.

Les pondérations d'une stratégie, ses règles de décision, ses arbitrages et ses scores propriétaires restent dans `strategie-chatgpt` ou `strategie-claude`.

## Mise à jour

Le workflow quotidien est prévu pour :
- contrôler l'absence de données personnelles ;
- résoudre progressivement les symboles manquants ;
- récupérer les nouveaux cours ;
- recalculer les indicateurs ;
- produire un snapshot ;
- commit les fichiers générés.

La collecte utilise par défaut Yahoo Finance via `yfinance`, sans clé API. Les symboles non résolus restent explicitement marqués comme tels ; aucune donnée n'est inventée.

## Source initiale

L'univers initial provient de la liste Altaprofits Vie datée du 08/09/2026 fournie par Olivier. Les documents source ne sont volontairement pas stockés ici.

## Convention

- Identifiant principal : ISIN quand il existe.
- Date : `YYYY-MM-DD`.
- Devise : code ISO 4217.
- Donnée manquante : champ vide.
- Historique : append-only autant que possible.
- Toute correction manuelle reste traçable par commit Git.
