# Contrat de travail des IA

Ce document fixe les règles communes pour tout agent qui lit ou modifie ce dépôt.
Il prévaut sur les interprétations implicites d'un fichier isolé.

## 1. Séparation des responsabilités

- Les données de marché communes, leur contrôle qualité, les benchmarks communs et
  les fichiers générés sont gérés par l'automatisation du dépôt.
- Chaque espace d'agent ne gère que sa stratégie, ses hypothèses, ses résultats et
  son historique de décisions :
  - ChatGPT : `strategies/chatgpt/` et `history/chatgpt/`
  - Claude : `strategies/claude/` et `history/claude/`
  - Académique : `config/academic_strategies.yml` et sorties générées associées.
- Aucun agent ne modifie l'historique de décisions d'un autre espace, ni ne réécrit
  une décision passée pour la faire correspondre à un résultat ultérieur.

## 2. Prix, devises et qualité

- `data/prices/daily.csv` est la source unique des calculs communs.
- Les stratégies et calculs communs utilisent obligatoirement `close_eur` (ou
  l'alias historique `close`, qui est strictement égal à `close_eur`).
  `close_native` et `close_raw` sont des colonnes d'audit, pas des bases de
  comparaison de performance.
- La devise ne se déduit jamais de la place de cotation : elle doit être vérifiée
  dans les métadonnées du fournisseur ou dans une source officielle de l'émetteur.
  Une place Amsterdam, Londres ou Francfort peut proposer une ligne négociée dans
  une autre devise que l'EUR.
- Une anomalie de cotation n'est neutralisée que par la règle commune documentée ;
  l'observation brute reste enregistrée dans
  `data/quality/reversible_raw_ticks.csv`.
- Si un support n'a pas de série valide, il est signalé comme manquant. Il ne doit
  être ni remplacé silencieusement ni complété par une donnée inventée.

## 3. Calendriers et comparaison

- Chaque stratégie multi-supports construit son calendrier commun à partir des
  cours effectivement disponibles pour les actifs qu'elle utilise. Elle documente
  les dates ou lignes écartées.
- Des historiques de longueur différente ne justifient ni remplissage artificiel
  avant la première cotation, ni comparaison de rendements sur des fenêtres
  différentes sans le dire.

## 4. Bernard : réel et simulation ne se confondent jamais

- `data/benchmarks/bernard_origin.csv` est le suivi réel démarré le
  07/09/2026. Il ne doit jamais être rétrodaté.
- Une simulation historique de la composition actuelle de Bernard est une courbe
  séparée, explicitement étiquetée « simulation » et accompagnée de ses hypothèses
  de pondération, de rééquilibrage et de rendement du fonds en euros.
- Aucun résultat de simulation ne doit être présenté comme une performance réelle
  de Bernard.

## 5. Données destinées aux pages publiques

- Les fichiers `docs/data/chatgpt.json` et `docs/data/claude.json` sont
  générés par `scripts/build_dashboard_data.py`. Aucun agent ne les modifie
  directement.
- Un agent enregistre sa courbe source dans son propre espace
  (`strategies/<agent>/strategies.json`). Le générateur commun lit cette source
  et produit le JSON public sans effacer les courbes.
- Les pages propres aux agents peuvent lire leurs fichiers autorisés par
  `config/access-policy.yml`, notamment `docs/data/claude-history.json` pour
  Claude.

## 6. Règle de preuve

Avant d'affirmer qu'un problème existe ou qu'une correction est faite, un agent :

1. vérifie le fichier publié sur la branche principale ;
2. cite la donnée ou la ligne observée ;
3. distingue un fait, une hypothèse et une recommandation ;
4. ne déclare jamais une exécution, un commit ou un résultat comme réalisé sans
   vérification effective.

## 7. Changements hors périmètre

Un agent n'édite pas les scripts communs, les politiques d'accès, les données
générées ou l'espace d'un autre agent sans demande explicite. S'il identifie un
problème hors de son périmètre, il le documente précisément et propose une
correction ; il ne réécrit pas les résultats des autres espaces.
