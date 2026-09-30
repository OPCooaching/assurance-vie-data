# Stratégies ChatGPT

## Règle d'univers à partir du 30/09/2026

Par défaut, une stratégie ChatGPT qui sélectionne des supports doit examiner **tout l'univers du contrat disposant de données de marché exploitables**, sans filtre implicite « ETF seulement ». Une restriction à une catégorie n'est admise que si elle fait partie explicitement de l'hypothèse testée.

Le premier contrôle univers complet du 30/09/2026 a trouvé 333 supports avec au moins 260 observations EUR exploitables : 156 OPCVM/FI, 98 actions et 79 ETF. Les résultats reproductibles sont dans `history/chatgpt/full-universe-research/2026-09-30/`.

Le premier passage montre que le momentum 12 mois simple, appliqué à l'univers complet et aux cinq meilleurs supports positifs, mérite une validation de robustesse supplémentaire. Ce résultat reste un backtest de recherche : il comporte notamment un biais possible d'univers actuel/survivants et ne devient pas automatiquement une allocation suivie.

Ce dossier sépare explicitement les hypothèses de recherche des stratégies qui pourront un jour être suivies en portefeuille.

## Familles nouvelles, réellement distinctes

Les quatre fiches ci-dessous sont des **hypothèses à tester**. Elles ne produisent encore aucune allocation active.

- [Momentum mensuel multi-horizons](momentum-mensuel/strategy.yml) : sélection mensuelle des supports les plus solides.
- [Exposition pilotée par le risque](volatilite-pilotee/strategy.yml) : ajustement hebdomadaire du niveau de risque, sans levier.
- [Allocation par régime macro-financier](regime-macro-financier/strategy.yml) : allocation hebdomadaire issue des conditions macro-financières publiées.
- [Sélection mensuelle et protection hebdomadaire](hybride-selection-protection/strategy.yml) : sélection lente, garde-fous rapides.

Chaque fiche indique son objectif, ses données nécessaires, sa fréquence, ses garde-fous et ce qui doit être figé avant un backtest. Une règle ne devient suivie qu'après : règle chiffrée et versionnée, test sans donnée future, puis validation explicite pour un suivi simulé.

## Historique nettoyé

Les trois anciennes variantes momentum ont été retirées, avec leurs courbes et leur moteur de calcul. Elles ne sont plus présentées comme un suivi actif et ne participent plus aux pages publiques.

Les décisions, allocations et changements de version seront conservés de façon append-only dans `history/chatgpt/`. Le cadre commun est décrit dans [le modèle opérationnel](../../history/chatgpt/2026-09-23-modele-operationnel-v1.md) et le test est encadré par [le protocole de backtest](../../history/chatgpt/2026-09-23-protocole-backtest-v1.md).
