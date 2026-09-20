# Constats sur les données communes

Vérifications faites le 20 septembre 2026 sur le dépôt, avant tout calcul.
Aucun fichier commun n'a été modifié. Ces constats sont posés ici pour information.

## Ce qui fonctionne

416 supports sur 473 ont un symbole résolu, 53 restent `unresolved`, 4 sont `manual`.
`data/prices/daily.csv` contient 83 638 lignes pour 396 actifs.
Les douze lignes cotées du portefeuille de Bernard sont toutes présentes.

## Quatre points qui limitent les conclusions

### 1. Un an d'historique, pas cinq

`scripts/update_market_data.py` demande `BOOTSTRAP_PERIOD = "5y"`. Les données
livrées couvrent du 18 septembre 2025 au 18 septembre 2026, soit 253 à 256
séances selon les supports. Aucun actif n'atteint 260 séances.

Conséquence directe sur les moyennes mobiles :

| Filtre | Séances d'amorçage | Séances walk-forward restantes |
|---|---|---|
| Moyenne 200 jours | 200 | 53 |
| Moyenne 150 jours | 150 | 103 |
| Moyenne 100 jours | 100 | 153 |

Une moyenne 200 jours laisse deux mois et demi de test. Les stratégies Claude
passent donc en v0.2 avec une moyenne 100 jours, ce qui reste court.

Cause probable à vérifier dans le journal du workflow : Yahoo renvoie rarement
cinq ans sur les lignes européennes secondaires, et le téléchargement par lots
de 40 symboles s'aligne sur le plus court.

### 2. Mélange de devises de cotation

29 supports résolus sont cotés hors zone euro. Les combiner avec des supports
cotés en euros introduit un effet de change dans le backtest.

Démonstration sur un même fonds coté à deux endroits :

| Support | Symbole | Performance 1 an |
|---|---|---|
| iShares Core MSCI World | IWDA.L | +15,72 % |
| iShares Core MSCI World | IWLE.DE | +13,24 % |

Écart de 2,19 points sur douze mois, uniquement dû à la devise de cotation.

Les stratégies Claude n'utilisent donc que des lignes cotées en euros.
Conséquence : aucun ETF santé mondiale coté en euros n'existe dans l'univers,
le seul disponible étant `XDWH.L`. Le thème santé sort des stratégies Claude
v0.2 et laisse trois thèmes au lieu de quatre.

### 3. Ticks aberrants non filtrés

`IE00BL25JN58`, Xtrackers MSCI World Minimum Volatility, présente une variation
de +16,06 % le 24 octobre 2025, annulée par -13,84 % le 27 octobre.

| Mesure | Valeur |
|---|---|
| Volatilité annualisée avec le tick | 22,71 % |
| Volatilité annualisée sans le tick | 8,08 % |

Un fonds à volatilité minimale ne bouge pas de 16 % en une séance. Ce point
seul multiplie par près de trois la volatilité mesurée du support.

Les stratégies Claude appliquent un filtre : toute variation supérieure à 5 %
annulée en sens inverse la séance suivante est traitée comme une erreur de
cotation et interpolée. Ce filtre agit en lecture seule, sur une copie.

Les stratégies académiques et celles de ChatGPT lisent le même fichier non
filtré. Un filtre placé dans les scripts communs bénéficierait à tout le monde.

### 4. Benchmark de dix séances

`data/benchmarks/bernard_origin.csv` et `data/academic/performance.csv`
démarrent au 7 septembre 2026 et comptent dix points au 18 septembre.

Toute comparaison au benchmark porte donc aujourd'hui sur deux semaines.

## Un biais de fenêtre qui domine tout le reste

Performances sur l'unique année disponible, du 18 septembre 2025 au
18 septembre 2026, cotations en euros :

| Support | Performance | Volatilité |
|---|---|---|
| iShares MSCI Global Semiconductors | +109,95 % | 41,78 % |
| iShares MSCI EM ex-China | +48,50 % | 26,62 % |
| Amundi Euro Stoxx Banks | +41,62 % | 23,91 % |
| iShares Core MSCI World | +13,24 % | 11,74 % |
| Xtrackers World Minimum Volatility | +7,57 % | 8,08 % |
| Xtrackers EUR Overnight | +2,06 % | 0,20 % |

Les semi-conducteurs ont plus que doublé en douze mois. Toute stratégie testée
sur cette seule fenêtre et qui surpondère ce thème paraîtra excellente, et toute
stratégie qui diversifie paraîtra médiocre.

Ce biais n'est pas corrigeable avec un an de données. Il se corrige en allongeant
l'historique.
