# Stratégies ChatGPT

Ce dossier sépare explicitement les hypothèses de recherche des stratégies qui pourront un jour être suivies en portefeuille.

## Familles nouvelles, réellement distinctes

Les quatre fiches ci-dessous sont des **hypothèses à tester**. Elles ne produisent encore aucune allocation active.

- [Momentum mensuel multi-horizons](momentum-mensuel/strategy.yml) : sélection mensuelle des supports les plus solides.
- [Exposition pilotée par le risque](volatilite-pilotee/strategy.yml) : ajustement hebdomadaire du niveau de risque, sans levier.
- [Allocation par régime macro-financier](regime-macro-financier/strategy.yml) : allocation hebdomadaire issue des conditions macro-financières publiées.
- [Sélection mensuelle et protection hebdomadaire](hybride-selection-protection/strategy.yml) : sélection lente, garde-fous rapides.

Chaque fiche indique son objectif, ses données nécessaires, sa fréquence, ses garde-fous et ce qui doit être figé avant un backtest. Une règle ne devient suivie qu'après : règle chiffrée et versionnée, test sans donnée future, puis validation explicite pour un suivi simulé.

## Travaux antérieurs

Les dossiers `impulsion`, `adaptative` et `rotation-diversifiee` sont les trois hypothèses historiques, principalement apparentées à la famille momentum. Ils sont conservés pour comparaison ; ils ne doivent pas être confondus avec les quatre familles ci-dessus.

Les décisions, allocations et changements de version seront conservés de façon append-only dans `history/chatgpt/`. Le cadre commun est décrit dans [le modèle opérationnel](../../history/chatgpt/2026-09-23-modele-operationnel-v1.md).
