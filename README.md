# assurance-vie-data

Source commune, neutre et anonymisée des données utilisées pour le suivi de l'assurance-vie.

## État initial

- **473 supports Altaprofits** importés depuis la liste du 08/09/2026.
- Portefeuille courant stocké uniquement en pourcentages au 07/09/2026.
- Mise à jour automatique prévue les jours ouvrés.
- Aucune donnée personnelle ni numéro de contrat stocké.

## Rôle du dépôt

Ce dépôt contient uniquement :
- l'univers des supports disponibles ;
- les correspondances ISIN / symboles de marché ;
- les historiques de cours récupérés automatiquement ;
- les indicateurs de marché communs ;
- une représentation anonymisée du portefeuille courant ;
- les snapshots techniques.

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

En exploitation normale, ChatGPT et strategie-claude lisent ce dépôt mais n'y écrivent pas leurs décisions, scores propriétaires, portefeuilles proposés ou résultats.

Une IA peut modifier l'infrastructure de ce dépôt uniquement sur demande explicite d'Olivier.

Voir aussi `AGENTS.md`, `config/access-policy.yml` et `STRATEGY_INTERFACE.md`.

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
  universe_part_01.csv ... universe_part_05.csv
  universe.csv
  portfolio_current.csv
  symbol_map.csv
  access-policy.yml

data/
  prices/
  indicators/
  snapshots/

scripts/
  build_universe.py
  resolve_symbols.py
  update_market_data.py
  compute_indicators.py
  validate_public_data.py

contracts/
  strategy-decision.schema.json

.github/workflows/
  daily-update.yml
```

## Fonctionnement

1. Les fichiers `universe_part_*.csv` constituent le snapshot source anonymisé des 473 supports.
2. `build_universe.py` reconstruit `config/universe.csv` et préserve les correspondances déjà résolues.
3. `resolve_symbols.py` tente de relier les ISIN aux symboles de marché.
4. `update_market_data.py` récupère les cours des supports résolus.
5. `compute_indicators.py` calcule les indicateurs communs et reproductibles.
6. GitHub Actions enregistre les mises à jour.
7. ChatGPT et strategie-claude lisent les mêmes données et écrivent leurs stratégies dans leurs dépôts respectifs.

## Données communes

Les données communes peuvent contenir : cours, rendements 5/20/60/120 jours, volatilité, drawdown, moyennes mobiles et métadonnées objectives.

Les pondérations d'une stratégie, ses règles de décision, ses arbitrages et ses scores propriétaires restent dans `strategie-chatgpt` ou `strategie-claude`.

## Mise à jour automatique

Le workflow `Daily market data update` tourne du lundi au vendredi et peut aussi être lancé manuellement depuis l'onglet **Actions**.

Il :
- reconstruit l'univers ;
- contrôle l'absence de données personnelles ;
- tente de résoudre les symboles de marché ;
- récupère les cours ;
- recalcule les indicateurs ;
- produit un snapshot ;
- commit les nouvelles données.

La collecte utilise par défaut Yahoo Finance via `yfinance`, sans clé API. Les supports non couverts restent explicitement marqués comme non résolus ou manuels ; aucune donnée n'est inventée.

## Source initiale

L'univers initial provient de la liste Altaprofits Vie datée du 08/09/2026 fournie par Olivier. Les documents originaux ne sont volontairement pas stockés ici.

## Convention

- Identifiant principal : ISIN quand il existe.
- Date : `YYYY-MM-DD`.
- Devise : code ISO 4217.
- Donnée manquante : champ vide.
- Historique : append-only autant que possible.
- Toute correction manuelle reste traçable par commit Git.
