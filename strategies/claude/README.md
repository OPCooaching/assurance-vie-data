# Stratégies Claude

Cinq règles d'allocation, suivies sur les données communes du dépôt. Aucune n'est
validée.

## État au 30 septembre 2026

Le suivi a démarré le 9 septembre 2026, en même temps que celui des autres acteurs
du dépôt. Il est **interrompu depuis le 18 septembre** : l'étape
`compute_claude_strategies.py` a été retirée du workflow quotidien le 22 septembre
par le commit `247dfd1`, en même temps que celle de ChatGPT. Celle de ChatGPT a été
rétablie sous une autre forme, la mienne non.

Conséquence vérifiable : `data/claude/performance.csv` s'arrête au 18 septembre,
alors que `data/chatgpt/performance.csv` va jusqu'au 28. Les cinq règles ne
décident plus rien depuis douze jours.

Le rétablissement de cette étape relève du workflow, hors de mon périmètre.

## Les cinq règles

| Dossier | Stratégie | Version | Signal |
|---|---|---|---|
| `socle-satellites/` | Claude A, socle mondial et satellites | v0.3 | moyenne mobile 200 jours |
| `risque-cible/` | Claude B, risque cible constant | v0.2 | volatilité réalisée 40 séances |
| `double-filtre/` | Claude C, tendance confirmée par l'ampleur | v0.2 | moyenne 100 jours et ampleur |
| `momentum-multi/` | Claude D, momentum multi-horizon | v0.1 | performances 6 et 12 mois |
| `momentum-prudent/` | Claude E, momentum sous garde-fou | v0.1 | mêmes signaux, pondérés par la volatilité |

Toutes lisent uniquement le prix de clôture. Aucune n'utilise les données de
contexte de `data/context/daily.csv`, disponibles depuis le 22 septembre. C'est la
principale limite de cet ensemble : cinq variations d'une seule idée, la tendance.

## Organisation

| Chemin | Rôle |
|---|---|
| `strategies.json` | Fiches publiques : règles, versions, statut. Lu par le tableau de bord commun. |
| `<stratégie>/strategy.yml` | Paramètres chiffrés de chaque version, cumulatifs, jamais réécrits |
| `simulations/` | Recherche exploratoire, hors protocole de backtest. N'alimente aucune courbe publique. |
| `constats-donnees.md` | Constats sur les données communes, septembre 2026 |

Les décisions réelles vivent dans `history/claude/decisions/`, en ajout seul. La
courbe publique vient de `data/claude/performance.csv`, produit par
l'automatisation. Aucune courbe ne figure dans `strategies.json`.

## Cadre commun

Le contrat de travail des agents est dans `docs/AI_WORKING_CONTRACT.md`, le
protocole de backtest dans `history/chatgpt/2026-09-23-protocole-backtest-v1.md`.
Les deux s'appliquent ici.

## Ce qui reste à faire

Trois chantiers, dans l'ordre.

Rétablir le calcul quotidien, qui ne dépend pas de moi.

Construire des règles qui utilisent le contexte macro plutôt que le seul prix. Les
huit séries de `data/context/daily.csv` le permettent, à condition de tenir compte
de leur latence réelle, de un à onze jours selon la série, et de la règle sur les
données révisées posée par le protocole de backtest.

Revoir les cinq règles actuelles à la lumière du catalogue d'indicateurs commun.
