# Modèle opérationnel v1 — stratégies et suivi

_Date : 23 septembre 2026. Statut : architecture décidée pour préparer les tests ; aucune allocation réelle ni ordre de courtage n'est déclenché._

## But concret

Chaque semaine, après la dernière valorisation disponible du vendredi, le système doit pouvoir :

1. utiliser les données communes les plus récentes ;
2. appliquer chaque règle de stratégie déjà testée et versionnée ;
3. enregistrer une décision : modifier, ne rien modifier ou ne pas intervenir faute de données fiables ;
4. conserver pour toujours l'explication, les données employées et l'allocation avant/après ;
5. afficher simplement la situation et l'historique de ChatGPT, de Claude et du portefeuille d'origine de Bernard.

Le but est un suivi dynamique et réactif, pas un portefeuille figé. Une stratégie peut être hebdomadaire, mensuelle, ou hybride ; sa propre fiche le dit.

## 1. Données : deux rythmes distincts

### Tous les jours ouvrés

L'automatisation GitHub existante actualise les prix et les indicateurs externes. Elle conserve les données brutes disponibles et n'invente pas de valeur lorsqu'une série n'est publiée que chaque semaine ou est révisée.

Les indicateurs de contexte sont conservés dans `data/context/daily.csv`. Les instantanés journaliers de contexte sont conservés quatorze jours afin de diagnostiquer une mise à jour récente.

### À chaque revue hebdomadaire

Une automatisation dédiée sera ajoutée après les tests des règles. Elle s'exécutera le samedi, après la valorisation disponible du vendredi. Son premier acte sera de figer un **instantané permanent** des données réellement utilisées pour la revue, par exemple :

```
data/review-snapshots/2026-W39/
  prices.csv
  context.csv
  metadata.json
```

Cet instantané ne remplace jamais l'historique quotidien : il prouve simplement, des années plus tard, ce que la stratégie pouvait connaître au moment où elle a décidé.

La revue hebdomadaire ne remplace pas la collecte quotidienne. Elle part des données déjà téléchargées ; elle ne modifie pas une stratégie qui n'a pas de revue prévue cette semaine.

## 2. Vie d'une stratégie

Une stratégie passe obligatoirement par les états suivants :

```
hypothèse documentée
  -> règle chiffrée figée (version v0.x)
  -> backtest rejouable, sans donnée future
  -> validation explicite pour le suivi simulé
  -> stratégie suivie (version v1.x)
  -> évolution : nouvelle version, jamais réécriture du passé
```

La fiche `strategies/<auteur>/<identifiant>/strategy.yml` explique l'intention, les données et les garde-fous. Une version mise en suivi devra être immuable, par exemple :

```
strategies/chatgpt/<identifiant>/versions/v1.0.yml
```

Une amélioration crée `v1.1.yml` ou `v2.0.yml`. Elle ne modifie ni les décisions déjà archivées ni leur courbe historique.

## 3. Journal des décisions : la mémoire qui compte

Toute revue d'une stratégie suivie produira un fichier append-only :

```
history/<auteur>/decisions/2026-W39/<identifiant>.json
```

Même l'absence de mouvement est enregistrée. Cela évite de réécrire l'histoire et permet de distinguer :

- `rebalance` : allocation effectivement modifiée dans le suivi ;
- `no_change` : la règle a été appliquée et maintient l'allocation ;
- `no_trade` : la règle refuse de décider, par exemple à cause d'une donnée manquante ;
- `research_only` : résultat de test, sans suivi de portefeuille.

Le modèle de fichier est fourni dans `history/chatgpt/TEMPLATE-decision-hebdomadaire.json`. Il contient au minimum :

- date de décision et date de valorisation effective ;
- identifiant et version de la stratégie ;
- référence exacte de l'instantané de données ;
- état, allocation précédente et allocation cible ;
- différences à arbitrer ;
- règles déclenchées et explication lisible ;
- anomalies, données manquantes et hypothèses ;
- auteur du calcul et horodatage.

L'automatisation vérifiera que les allocations totalisent 100 %, que chaque support appartient à l'univers courant et que les prix nécessaires existent avant d'écrire une décision.

## 4. Pages GitHub : ce que Bernard doit voir

Les pages ne calculeront pas les stratégies dans le navigateur. Elles liront uniquement des fichiers générés et contrôlés sous `docs/data/`.

### Accueil

- fraîcheur des prix et des indicateurs ;
- date de la dernière revue hebdomadaire réussie ;
- portefeuille d'origine de Bernard, ChatGPT et Claude côte à côte ;
- avertissement clair s'il n'y a pas de décision récente ou si une donnée est incomplète.

### Page ChatGPT et page Claude

Pour chaque stratégie :

- statut visible : hypothèse, en test, suivi simulé ou interrompue ;
- fréquence (hebdomadaire, mensuelle, hybride) et version en cours ;
- allocation courante seulement si elle est effectivement suivie ;
- dernière décision, motif et données datées ;
- tableau des décisions antérieures ;
- courbe depuis le début du suivi de cette version, sans mélanger les versions.

Les stratégies de Claude resteront séparées de celles de ChatGPT. Elles liront les mêmes données communes mais leurs décisions et historiques seront rangés sous `history/claude/`.

### Page indicateurs

Elle décrira chaque série : nom clair, source, fréquence de publication, dernière valeur réellement disponible, rôle possible et limites. Une valeur hebdomadaire ne sera jamais affichée comme si elle était une observation quotidienne nouvelle.

## 5. Automatisations à construire dans le bon ordre

1. **Définir et figer chaque règle chiffrée** des quatre familles ChatGPT.
2. **Écrire les backtests rejouables**, avec dates de publication des indicateurs, coûts/hypothèses et contrôles anti-fuite.
3. **Choisir les stratégies qui méritent le suivi simulé** et leur version initiale.
4. **Créer le générateur de revue hebdomadaire** : instantané, calcul, validations, décision JSON, historique de performance et données des pages.
5. **Ajouter le workflow GitHub hebdomadaire** séparé du workflow quotidien, puis le tester manuellement avant sa planification.
6. **Brancher les pages** sur les fichiers générés et afficher explicitement les erreurs ou le `no_trade`.
7. **Définir l'import Claude** lorsque son format de décision réel sera connu, sans l'obliger à écrire directement dans GitHub.

## 6. Garde-fous non négociables

- Jamais de donnée future dans un test ni dans une décision.
- Une donnée non publiée, manquante ou révisée est signalée ; elle n'est pas inventée.
- Chaque décision est reliée à son instantané de données et à une version immuable.
- Les historiques sont ajoutés, jamais remplacés.
- Une stratégie ne passe pas en suivi sans règle précise, testée et explicitement acceptée.
- Aucun ordre chez l'assureur n'est passé par ce dépôt : il s'agit d'abord d'analyse et de suivi simulé.

## Situation au 23 septembre 2026

Les prix et huit indicateurs externes communs sont déjà collectés automatiquement les jours ouvrés. Les quatre nouvelles familles ChatGPT sont maintenant documentées comme hypothèses distinctes. La prochaine étape n'est donc pas de lancer une allocation automatique : c'est de rendre chacune de ces règles suffisamment précise pour un test honnête.
