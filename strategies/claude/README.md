# Espace Claude : recherche, stratégies et suivi

Cet espace appartient à Claude. Il est séparé des espaces ChatGPT et académique afin que les approches puissent être comparées honnêtement.

## État au 24 septembre 2026

Les dossiers existants `socle-satellites/`, `risque-cible/`, `double-filtre/`, `momentum-multi/` et `momentum-prudent/` sont des **archives de recherche et de simulation**. Ils ne constituent pas un suivi hebdomadaire Claude actif.

Ils sont conservés comme trace : ils ne doivent être ni supprimés, ni présentés comme de nouvelles décisions, ni prolongés par défaut.

En particulier, `momentum-multi` et `momentum-prudent` sont deux variations d'une même famille momentum. Ils ne satisfont pas à eux seuls l'objectif de disposer de stratégies vraiment différentes.

La page `docs/claude.html` affiche encore ces simulations historiques. Elle devra être refondue lorsque Claude aura défini ses propres stratégies actives et enregistré leurs premières décisions vérifiables. Jusqu'à cette refonte, elle doit clairement parler d'archives de simulation, pas de suivi hebdomadaire en cours.

## Objectif de Bernard

Bernard souhaite un portefeuille théorique dynamique, réexaminé chaque semaine, afin de rechercher le meilleur résultat possible à court terme. Les arbitrages sont supposés gratuits.

Il ne veut pas une allocation figée : chaque semaine, une stratégie peut conserver ou modifier les actifs de son portefeuille théorique. Aucun ordre réel n'est passé.

Les stratégies doivent être différentes par leur hypothèse et leur méthode, et non de simples versions plus ou moins prudentes d'un même classement momentum.

## Sources à utiliser

Avant toute analyse, lire :

- `config/access-policy.yml` ;
- `STRATEGY_INTERFACE.md` ;
- `config/universe.csv`, `config/symbol_map.csv` et les fichiers de référence Bernard ;
- `data/prices/daily.csv`, en utilisant `close_eur` lorsque les supports sont comparés ;
- `data/indicators/latest.csv` ;
- `data/context/` ;
- `docs/screener.html` ;
- `strategies/chatgpt/` et `history/chatgpt/`, en lecture seule, uniquement pour comparer.

Ne pas restreindre arbitrairement l'étude à une liste de thèmes ou à un nombre fixe de supports. Examiner tout l'univers réellement exploitable, puis exclure explicitement les supports dont les données sont insuffisantes ou non comparables.

## Construire de nouvelles stratégies Claude

Avant d'en déclarer une active :

1. décrire son hypothèse économique et les recherches ou raisons vérifiables qui la soutiennent ;
2. expliquer ses indicateurs, sa sélection, ses pondérations et ses sorties dans un français accessible ;
3. montrer en quoi elle diffère des autres stratégies Claude : données déterminantes, horizon, logique d'allocation et réaction aux régimes de marché ;
4. tester séparément sa règle historique quand les données le permettent, sans utiliser de données futures ;
5. distinguer sans ambiguïté le résultat de test et le futur suivi hebdomadaire.

Le nombre de stratégies dépend de la diversité réellement démontrée, non d'un quota. Une stratégie peut être ouverte et adaptative, à condition que chaque décision hebdomadaire explique clairement les éléments observés et la raison de l'allocation.

## Démarrer un suivi hebdomadaire

Une fois une stratégie définie et validée comme stratégie active :

- placer sa règle et sa version dans `strategies/claude/` ;
- enregistrer chaque décision dans `history/claude/` avec une date d'analyse et une date de prise d'effet ;
- ne jamais modifier une décision passée ;
- vérifier que l'allocation totalise exactement 100 % ;
- construire les sorties calculées propres à Claude dans `data/claude/`, si nécessaire ;
- projeter les informations utiles pour la page dans `docs/data/claude.json` ;
- mettre à jour `docs/claude.html` sans modifier les pages partagées ;
- vérifier la page GitHub Pages après publication.

La source durable de l'historique est `history/claude/`. Ne pas créer ni maintenir un deuxième historique indépendant dans `docs/data/claude-history.json` : les données web sont une projection de l'historique, pas une source concurrente.

## Revue du samedi

Le dépôt actualise les cours et indicateurs en semaine. Une revue Claude doit être exécutée le samedi seulement si une tâche Claude a effectivement été programmée ou si Olivier la déclenche.

À chaque revue :

1. vérifier la fraîcheur des données ;
2. analyser les supports comparables et les indicateurs disponibles ;
3. décider l'allocation théorique applicable la semaine suivante ;
4. expliquer les actifs entrés, sortis, renforcés ou conservés ;
5. archiver la décision ;
6. mettre à jour la page et vérifier sa publication.

Sans tâche Claude réellement active, ne jamais écrire que Claude suit le portefeuille automatiquement.

## Droits et confidentialité

Claude peut écrire uniquement dans `strategies/claude/`, `history/claude/`, `data/claude/`, `docs/data/claude.json` et `docs/claude.html`.

Il ne modifie ni les données communes ni les espaces ChatGPT ou académiques. Il ne publie aucune donnée personnelle. L'alias Bernard et les montants exacts anonymisés sont autorisés par `config/access-policy.yml`.
