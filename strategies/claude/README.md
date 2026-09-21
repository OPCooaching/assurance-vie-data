# Stratégies Claude

Espace réservé aux stratégies définies par Claude. Les décisions et versions sont
conservées séparément de celles de ChatGPT et des stratégies académiques.

## État au 21 septembre 2026

Aucune stratégie n'est validée. Les trois définitions portent le statut
`research_hypothesis`.

Les données communes ont été corrigées par l'administrateur du dépôt : historique
porté à cinq ans, du 20 septembre 2021 au 18 septembre 2026, et ticks aberrants
traités. Les backtests ont été refaits sur ces données. Les résultats sont dans
`resultats-v03.md`.

Les devises de cotation ne sont pas homogénéisées dans le fichier commun. Les
stratégies Claude n'utilisent donc que des lignes cotées en euros sur une place
de la zone euro, ce qui évite toute conversion de change dans la simulation.

`resultats-preliminaires-v02.md`, qui portait sur un an de données, reste en
place comme trace et ne sera pas supprimé. `constats-donnees.md` conserve les
constats qui avaient motivé la correction des données.

## Contenu

| Chemin | Rôle |
|---|---|
| `socle-satellites/strategy.yml` | Claude A, socle mondial et thèmes plafonnés, active en v0.3 |
| `momentum-multi/strategy.yml` | Claude D, classement des supports, six lignes, active en v0.1 |
| `momentum-prudent/strategy.yml` | Claude E, même classement sous garde-fou, active en v0.1 |
| `risque-cible/strategy.yml` | Claude B, risque cible constant, active en v0.2 |
| `double-filtre/strategy.yml` | Claude C, tendance confirmée par l'ampleur, active en v0.2 |
| `backtest.py` | Simulation walk-forward, sans données futures |
| `strategies.json` | Résultats produits par `backtest.py` |
| `<stratégie>/backtest_<version>.csv` | Courbe base 100 d'une version |
| `resultats-v03.md` | Résultats de Claude A sur cinq ans |
| `resultats-momentum.md` | Résultats de Claude D et Claude E |
| `resultats-preliminaires-v02.md` | Résultats sur un an, trace conservée |
| `constats-donnees.md` | Constats sur les données communes |

## Univers

Deux univers, sous la même contrainte de devise : uniquement des lignes cotées
en euros sur une place de la zone euro.

Claude A, B et C suivent une liste de six supports fixée à l'avance.
Claude D et E classent chaque semaine tous les fonds cotés en euros du contrat
disposant de cinq ans de cours, soit quarante-quatre supports. Cet ensemble est
celui des fonds encore référencés aujourd'hui : un fonds retiré depuis 2021 n'y
figure pas, ce qui flatte légèrement le classement.

### Les six supports de Claude A, B et C

| Rôle | Support | Cotation |
|---|---|---|
| Socle monde large | iShares Core MSCI World | IWLE.DE |
| Socle volatilité minimale | Xtrackers MSCI World Minimum Volatility | XDEB.DE |
| Thème | iShares MSCI Global Semiconductors | SEMI.AS |
| Thème | Amundi Euro Stoxx Banks | BNKE.PA |
| Thème | iShares MSCI EM ex-China | EXCH.AS |
| Support de repli | Xtrackers II EUR Overnight Rate Swap | XEON.DE |

La santé mondiale reste hors de ces stratégies : le seul support de l'univers
est coté à Londres. Il y a donc trois thèmes et non quatre.

## Lancer une simulation

```bash
python strategies/claude/backtest.py
python strategies/claude/backtest.py --strategie claude-socle-satellites
```

Le script refuse de tourner si les supports retenus partagent moins de 260
séances, une moyenne mobile 200 jours demandant cette profondeur avec une marge.

Les deux cents premières séances amorcent les moyennes mobiles et n'entrent pas
dans la mesure. Cette fenêtre d'amorçage est la même pour toutes les versions :
sans cela, une version à moyenne courte démarrerait plus tôt qu'une version à
moyenne longue et les deux ne seraient plus comparables.

## Absence de données futures

À chaque date de décision, seules les séances antérieures ou égales à cette date
sont visibles. L'allocation décidée s'applique à partir de la séance suivante,
ce qui reproduit le fait qu'un arbitrage d'assurance vie s'exécute à une valeur
liquidative inconnue au moment de l'ordre.

Altaprofits applique une date de valeur à J+1 ouvré pour un ordre passé avant 23 h.

## Versions

Un changement de logique crée une nouvelle version. Les versions sont
cumulatives : une version reprend les paramètres de la précédente et ne redéfinit
que ce qui change. Les résultats restent rattachés à la version qui les a
produits. Aucune décision passée n'est réécrite, et `backtest.py` n'ajoute au
journal que les décisions qui n'y figurent pas déjà.

Une version dont les paramètres ne portent pas `currency_universe: eur_quoted_only`
repose sur un univers qui n'existe pas en cotation euro. Elle reste documentée
mais n'est pas simulée. C'est le cas des trois v0.1.

## Modélisation du fonds en euros

Le fonds en euros n'a aucune cotation publique. Le script lui applique un
rendement fixe de 3,00 % par an, ajustable quand le taux 2026 sera connu.
La page publique annonce cette modélisation.

## Points à valider par l'administrateur du dépôt

`backtest.py` écrit une copie de ses résultats dans `docs/data/claude-history.json`,
GitHub Pages ne servant que le dossier `docs/`. Ce chemin ne figure pas dans
`config/access-policy.yml`, qui n'autorise à Claude que `docs/data/claude.json`.
ChatGPT dispose de deux fichiers équivalents. Ajouter ce chemin à la politique,
ou indiquer un autre emplacement.

Le script met aussi à jour la seule clé `strategies` de `docs/data/claude.json`,
celle que `scripts/build_dashboard_data.py` conserve d'un passage à l'autre. Le
reste de ce fichier reste produit par le script commun.
