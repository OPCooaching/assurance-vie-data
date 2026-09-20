# Stratégies Claude

Espace réservé aux stratégies définies par Claude. Les décisions et versions sont
conservées séparément de celles de ChatGPT et des stratégies académiques.

## État au 20 septembre 2026

Aucune stratégie n'est validée. Les trois définitions portent le statut
`research_hypothesis`.

Un premier backtest walk-forward a tourné le 20 septembre 2026 sur les données
alors disponibles, soit un an d'historique. Ses résultats sont marqués
préliminaires dans `resultats-preliminaires-v02.md` et ne seront pas supprimés.

Les données communes sont en cours de correction par l'administrateur du dépôt :
historique porté à cinq ans, traitement des ticks aberrants, contrôle des devises
et des places de cotation. Les backtests seront refaits à l'identique sur ces
données, et les résultats préliminaires conservés à côté.

Les constats ayant motivé ces corrections sont dans `constats-donnees.md`.

## Contenu

| Chemin | Rôle |
|---|---|
| `socle-satellites/strategy.yml` | Claude A, socle mondial et thèmes plafonnés |
| `risque-cible/strategy.yml` | Claude B, risque cible constant |
| `double-filtre/strategy.yml` | Claude C, tendance confirmée par l'ampleur |
| `backtest.py` | Simulation walk-forward, sans données futures |
| `strategies.json` | Résultats produits par `backtest.py` |
|  Courbe base 100 d.une version | Courbe base 100 d'une version |

## Lancer une simulation

```bash
python strategies/claude/backtest.py
python strategies/claude/backtest.py --strategie claude-socle-satellites
```

Le script refuse de tourner si l'historique compte moins de 260 séances, une
moyenne mobile 200 jours nécessitant au minimum cette profondeur.

## Absence de données futures

À chaque date de décision, seules les séances antérieures ou égales à cette date
sont visibles. L'allocation décidée s'applique à partir de la séance suivante,
ce qui reproduit le fait qu'un arbitrage d'assurance vie s'exécute à une valeur
liquidative inconnue au moment de l'ordre.

Altaprofits applique une date de valeur à J+1 ouvré pour un ordre passé avant 23 h.

## Versions

Un changement de logique crée une nouvelle version. Les résultats restent
rattachés à la version qui les a produits. Aucune décision passée n'est réécrite.

## Modélisation du fonds en euros

Le fonds en euros n'a aucune cotation publique. Le script lui applique un
rendement fixe de 3,00 % par an, ajustable quand le taux 2026 sera connu.
La page publique annonce cette modélisation.

## Point à valider par l'administrateur du dépôt

`backtest.py` écrit une copie de ses résultats dans `docs/data/claude-history.json`,
GitHub Pages ne servant que le dossier `docs/`. Ce chemin ne figure pas dans
`config/access-policy.yml`, qui n'autorise à Claude que `docs/data/claude.json`.
ChatGPT dispose de deux fichiers équivalents. Ajouter ce chemin à la politique,
ou indiquer un autre emplacement.
