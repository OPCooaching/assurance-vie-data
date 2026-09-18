# Interface commune des stratégies

ChatGPT, Claude et les stratégies académiques utilisent les mêmes données de marché dans ce dépôt unique.

## Entrées communes

- `config/universe.csv`
- `config/portfolio_current.csv`
- `config/symbol_map.csv`
- `data/prices/daily.csv`
- `data/indicators/latest.csv`
- `data/benchmarks/`
- `data/snapshots/`

## Arborescence

```text
strategies/
  academic/
  chatgpt/
    impulsion/
    adaptative/
    rotation-diversifiee/
  claude/

history/
  chatgpt/
  claude/

docs/
  index.html
  academic.html
  chatgpt.html
  claude.html
```

## Contenu attendu pour chaque stratégie

Chaque stratégie conserve au minimum :
- sa règle et son objectif ;
- sa version active ;
- ses paramètres ;
- son portefeuille courant ;
- ses décisions datées ;
- ses performances ;
- son historique de versions.

## Règle d'historique

Une décision passée ne doit jamais être réécrite a posteriori. Si la logique change, créer une nouvelle version.

## Comparaison

Toutes les stratégies sont comparées au même point de départ et au benchmark `Bernard origine`.

Les indicateurs communs sont au minimum :
- performance depuis l'origine ;
- performance 5 jours ;
- performance 20 jours ;
- drawdown maximum ;
- volatilité 20 jours ;
- nombre d'arbitrages ;
- valeur théorique courante.
