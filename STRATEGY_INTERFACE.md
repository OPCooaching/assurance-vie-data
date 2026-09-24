# Interface commune des stratégies

ChatGPT, Claude et les stratégies académiques lisent les mêmes données de marché dans ce dépôt unique. Ils restent toutefois séparés : chacun possède ses règles, ses décisions, ses sorties de page et son historique.

## Données à lire

Les sources communes sont notamment :

- `config/universe.csv` : univers des supports du contrat ;
- `config/symbol_map.csv` : correspondance entre support et symbole de marché ;
- `config/portfolio_current.csv` et `config/baseline_bernard.yml` : point de départ et référence Bernard ;
- `data/prices/daily.csv` : cours historiques et statut de qualité ;
- `data/indicators/latest.csv` : indicateurs calculés ;
- `data/context/` : séries de contexte macro-financier ;
- `data/benchmarks/` et `data/snapshots/` : séries et instantanés calculés ;
- `docs/screener.html` : vue publique de la disponibilité des données.

Pour une comparaison transversale, utiliser le cours en euros validé (`close_eur`) et exclure explicitement tout support non comparable ou insuffisamment couvert. Ne jamais compléter une série manquante par une estimation.

## Espaces séparés

```text
strategies/
  academic/                 règles témoins fixes
  chatgpt/                  règles et documentation ChatGPT
  claude/                   règles, recherche et documentation Claude

history/
  chatgpt/                  décisions ChatGPT append-only
  claude/                   décisions Claude append-only

data/
  claude/                   calculs dérivés propres à Claude, si nécessaires

docs/
  index.html                synthèse partagée
  academic.html             témoins académiques
  chatgpt.html              suivi ChatGPT
  claude.html               suivi Claude
  data/chatgpt.json         projection publique ChatGPT
  data/claude.json          projection publique Claude
```

Les fichiers historiques restent à leur emplacement. Un agent ne les déplace pas ou ne les efface pas simplement pour imposer une nouvelle organisation.

## Contenu minimal d'une stratégie active

Chaque stratégie active conserve :

- son objectif et son hypothèse économique ;
- sa version et ses paramètres ;
- les données et indicateurs réellement utilisés ;
- ses règles d'entrée, de conservation, de sortie et de pondération ;
- son portefeuille théorique courant ;
- ses décisions datées et leur date de prise d'effet ;
- ses performances et limites ;
- son historique de versions ;
- une explication accessible à une personne non spécialiste.

Le nombre d'actifs n'est jamais fixé arbitrairement. Une stratégie peut retenir un, plusieurs ou aucun support risqué si sa propre logique le justifie.

## Décision hebdomadaire

Une décision est prise après la disponibilité des données de la semaine et porte effet à la valorisation suivante. Elle n'utilise que les informations connues au moment de l'analyse ; elle ne connaît ni les cours ni les indicateurs futurs.

Elle précise au minimum :

- date de l'analyse ;
- date de prise d'effet ;
- identifiant et version de la stratégie ;
- allocation détaillée, totalisant exactement 100 % ;
- changements par rapport à la décision précédente ;
- justification, limites et données disponibles.

Le dépôt actualise les données de marché les jours ouvrés. Une décision hebdomadaire d'agent n'existe que si une tâche planifiée distincte l'exécute réellement ; elle ne doit jamais être présentée comme automatique par simple convention.

## Historique et tests

Une décision passée est immuable. Un changement de logique crée une nouvelle version. Les backtests et reconstitutions servent à examiner une hypothèse ; ils restent distincts des décisions réelles de suivi hebdomadaire.

## Comparaison et page publique

La page publique montre, pour chaque courbe :

- sa nature : référence, backtest, reconstitution ou suivi hebdomadaire ;
- sa vraie date de départ ;
- sa valeur théorique en euros quand elle existe ;
- les allocations et décisions actuellement applicables ;
- une explication claire des règles et limites.

Une base 100 peut compléter l'analyse, mais elle ne remplace pas l'affichage en euros. Aucune page ne doit suggérer qu'un ordre réel a été passé.
