# Espace Claude : recherche, stratégies et suivi

## Suivi quotidien technique

Le calcul quotidien des huit courbes Claude est assuré par `strategies/claude/moteur.py`, appelé par le workflow commun. Il a remplacé `scripts/compute_claude_strategies.py` le 3 octobre 2026, qui ne doit plus être exécuté. Une interruption technique après le 18/09/2026 est conservée comme un trou explicite : aucune valeur ni décision n'est rétroactivement fabriquée. La reprise est append-only et commence à la première date réellement calculée après rétablissement du workflow.

Cet espace appartient à Claude. Il est séparé des espaces ChatGPT et académique afin que les approches puissent être comparées honnêtement.

## Revue du samedi, programmée le 4 octobre 2026

Les huit stratégies passent à une version nouvelle. Seul le calendrier change,
aucun seuil ni aucun univers n'est touché, et les paramètres des versions
antérieures restent en place.

La revue hebdomadaire se calcule désormais **le samedi à 14 h**, sur la dernière
valorisation de la semaine, celle du vendredi. L'allocation décidée s'applique à
la valorisation suivante, donc au lundi. Bernard peut ainsi consulter dès le
dimanche ce qui a été retenu pour la semaine qui commence.

C'est aussi la convention du protocole commun du 23 septembre : décision calculée
après la dernière valorisation disponible de la semaine, application à la
valorisation suivante.

Une ligne a été ajoutée au workflow commun pour cette programmation :
`cron: "0 12 * * 6"`, soit samedi 12 h UTC, c'est-à-dire 14 h à Paris en heure
d'été et 13 h en heure d'hiver. Les deux lignes de collecte des jours ouvrés sont
inchangées.

Les marchés étant fermés le samedi, ce passage n'ajoute aucune date de
valorisation. Il décide, inscrit la décision dans `history/claude/decisions/` et
met à jour la page. Si une donnée manque, la dernière réellement publiée est
utilisée, même vieille d'un ou deux jours ; aucune valeur n'est inventée.

| Stratégie | Version |
|---|---|
| Claude A, socle mondial et satellites | v0.4 |
| Claude B, risque cible constant | v0.3 |
| Claude C, tendance confirmée par l'ampleur | v0.3 |
| Claude D, momentum multi-horizon | v0.2 |
| Claude E, momentum sous garde-fou | v0.2 |
| Claude F, structure du marché | v0.2 |
| Claude G, retour à la moyenne | v0.2 |
| Claude H, dollar et énergie | v0.2 |

## Modifications faites hors de l'espace Claude, le 3 octobre 2026

Olivier a demandé explicitement ces deux changements, n'ayant plus accès à
l'agent qui gère les fichiers communs. Ils sont consignés ici pour que cet agent
les retrouve. Les deux ne concernent que Claude et ont été vérifiés avant
publication : les sorties de ChatGPT et des stratégies académiques sont
rigoureusement identiques après exécution complète de la chaîne, horodatage mis
à part.

### `.github/workflows/daily-update.yml`

Deux interventions. Le 3 octobre, une ligne changée dans l'étape « Compute Claude
live strategies », qui appelle
désormais `strategies/claude/moteur.py` au lieu de
`scripts/compute_claude_strategies.py`. Six lignes de commentaire expliquent
pourquoi, juste au-dessus. Aucune autre étape n'est touchée.

Le 4 octobre, une ligne de programmation ajoutée pour la revue du samedi,
`cron: "0 12 * * 6"`, décrite plus haut. Les horaires des jours ouvrés ne sont pas
modifiés.

Motif de la première : Claude est passé de cinq à huit stratégies et en ajoutera d'autres.
Chaque ajout exigeait jusqu'ici de modifier un fichier commun. Le moteur déplacé
dans l'espace Claude supprime cette dépendance.

**Point de vigilance.** `scripts/compute_claude_strategies.py` ne doit plus être
exécuté. Il écrirait cinq colonnes sur un fichier qui en compte huit. Le fichier
est laissé en place, mais plus aucune étape ne l'appelle.

### `scripts/build_dashboard_data.py`

Trois entrées ajoutées au dictionnaire `labels`, pour que les stratégies F, G et
H s'affichent sous leur nom et non sous leur identifiant technique :

```python
"claude_dispersion": "Claude F — Structure du marché",
"claude_contrarien": "Claude G — Retour à la moyenne",
"claude_dollar_energie": "Claude H — Dollar et énergie",
```

Aucune ligne existante n'est modifiée.

Le 4 octobre, trois lignes ajoutées dans `load_decision_history`, pour que le
détail des mouvements enregistré par Claude soit recopié dans les données web :

```python
        if isinstance(record.get("mouvements"), dict):
            records[-1]["mouvements"] = record["mouvements"]
```

La clé `mouvements` n'existe que dans les décisions Claude. Pour tout autre
acteur, la condition est fausse et la sortie reste identique au caractère près.
Vérifié après exécution complète : `academic.json`, `chatgpt.json` et
`chatgpt-data.js` sont inchangés, horodatage mis à part.

### Une demande qui reste ouverte

Le workflow `full-universe-research.yml` se déclenche sur n'importe quelle
branche et y pousse ses résultats. Il s'est exécuté sur la branche de travail
Claude et y a écrit sept fichiers de l'espace ChatGPT. Sans gravité, mais le
limiter à la branche principale éviterait que les demandes d'intégration se
mélangent. Je n'y ai pas touché : cet espace n'est pas le mien.

## État au 3 octobre 2026

Le calcul quotidien est rétabli depuis le 30 septembre et couvre huit
stratégies. Les cinq premières sont conservées sans modification, comme
témoins : trois recouvrent des familles déjà traitées par ChatGPT, et deux sont
deux variations d'une même idée. Trois règles nouvelles les complètent, écrites
le 3 octobre et publiées avant tout résultat : Claude F lit la structure du
marché, Claude G parie contre le mouvement récent, Claude H décide par le dollar
et le prix de l'énergie. Chacune a son hypothèse économique, ses règles de
sélection, de conservation et de remplacement, et sa faiblesse connue, dans son
`strategy.yml` et dans `strategies.json`.

Aucune décision hebdomadaire n'est encore archivée dans
`history/claude/decisions/` : la première sera inscrite au prochain lundi
réellement calculé.

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
