# Décisions Claude

Une décision est inscrite ici le jour où elle est prise, jamais après coup.

## Format

Un fichier par décision, nommé `AAAA-MM-JJ--<stratégie>.json`, lu par le tableau
de bord commun. Les champs attendus sont ceux des décisions ChatGPT :
`decision_id`, `effective_valuation_date`, `strategy_id`, `strategy_version`,
`decision_type`, `rationale`, `target_allocation_percent`, `warnings`.

## Pourquoi ce dossier est vide

Le suivi des cinq stratégies Claude a démarré le 9 septembre 2026. Les allocations
ont bien été calculées du 9 au 18 septembre, et la courbe correspondante existe
dans `data/claude/performance.csv`, mais aucune décision n'a été archivée
individuellement à l'époque : le calcul écrivait la composition courante sans
conserver de trace datée.

Le 22 septembre, l'étape `compute_claude_strategies.py` a été retirée du workflow
quotidien. Depuis, plus aucune décision n'est calculée.

Ces décisions ne seront pas reconstituées. Les recalculer aujourd'hui produirait
des fichiers datés du passé mais écrits au présent, ce que la règle d'historique
interdit précisément. Le journal démarrera à la première revue effectivement
exécutée après le rétablissement du calcul quotidien.
