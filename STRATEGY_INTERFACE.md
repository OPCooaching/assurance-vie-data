# Interface commune des stratégies

ChatGPT et strategie-claude lisent les mêmes données dans ce dépôt mais écrivent dans des dépôts séparés.

## Entrées communes à lire

- `config/universe.csv`
- `config/portfolio_current.csv`
- `config/symbol_map.csv`
- `data/prices/daily.csv`
- `data/indicators/latest.csv`
- `data/snapshots/`

## Sorties attendues dans chaque dépôt de stratégie

Chaque dépôt (`strategie-chatgpt` et `strategie-claude`) doit conserver :

```text
strategy/
  active.yml
  versions/

decisions/
  YYYY-MM-DD.json

portfolio/
  latest.csv
  history/

results/
  performance.csv
  comparison.csv

web/
  index.html
```

## Règle d'historique

Une décision passée ne doit jamais être réécrite a posteriori. Si la stratégie change, créer une nouvelle version.

## Comparaison entre IA

Chaque IA peut lire les fichiers `results/` et `decisions/` de l'autre dépôt, mais ne les modifie jamais.

La comparaison doit se faire sur des données normalisées : rendement en pourcentage, base 100, drawdown, volatilité et benchmark commun. Aucun montant exact en euros.
