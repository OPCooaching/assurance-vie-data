# Résultats sur cinq ans, Claude A v0.3

Calcul du 21 septembre 2026, sur les données communes corrigées : cinq ans
d'historique, ticks aberrants traités, cotations contrôlées.

Ces résultats remplacent, pour la lecture, ceux de `resultats-preliminaires-v02.md`,
qui portaient sur un an de données et restent conservés comme trace.

## Fenêtre de test

Les cours disponibles vont du 20 septembre 2021 au 18 septembre 2026. Les six
supports retenus par les stratégies Claude partagent 1 274 séances sur cette
période. Les deux cents premières servent à amorcer les moyennes mobiles et
n'appartiennent pas à la mesure.

La fenêtre walk-forward va donc du **5 juillet 2022 au 18 septembre 2026**, soit
**1 072 séances**, un peu plus de quatre ans et deux mois.

Cette fenêtre d'amorçage de deux cents séances est la même pour toutes les
versions comparées. Sans cela, une version à moyenne 100 jours démarrerait cinq
mois plus tôt qu'une version à moyenne 200 jours et les deux ne seraient plus
comparables.

À chaque date de décision, seules les séances antérieures ou égales à cette date
sont visibles. L'allocation décidée s'applique à partir de la séance suivante,
ce qui reproduit l'exécution d'un arbitrage d'assurance vie à une valeur
liquidative inconnue au moment de l'ordre. Les revues sont hebdomadaires et un
arbitrage n'est déclenché que si l'allocation cible s'écarte de trois points de
l'allocation détenue.

## Comparaison, fenêtre identique pour toutes les lignes

| | Performance totale | Annualisée | Drawdown max | Volatilité | Arbitrages |
|---|---|---|---|---|---|
| Bernard actuel rétro-simulé, partiel | +193,98 % | +28,85 % | -15,64 % | 16,73 % | 0 |
| Socle monde 50 % passif | +51,87 % | +10,32 % | -10,17 % | 7,52 % | 0 |
| **Claude A v0.3, moyenne 200 jours** | **+49,47 %** | **+9,91 %** | **-4,59 %** | **5,40 %** | **60** |
| Claude A v0.2, moyenne 100 jours | +36,30 % | +7,55 % | -5,82 % | 5,22 % | 94 |
| Claude B v0.2, risque cible | +55,83 % | +10,99 % | -5,52 % | 6,44 % | 70 |
| Claude C v0.2, double filtre | +31,66 % | +6,68 % | -5,94 % | 5,08 % | 85 |

La performance annualisée est calculée sur 252 séances par an. La volatilité est
annualisée sur l'ensemble de la fenêtre, et non sur les vingt derniers jours.

### La ligne « Bernard actuel rétro-simulé, partiel »

Cette ligne applique en arrière, sur toute la fenêtre, la composition connue en
septembre 2026. Elle ne représente pas la performance réelle du contrat et ne
sert jamais de référence.

Le biais de sélection est majeur : appliquer en arrière une composition connue
aujourd'hui revient à savoir, dès juillet 2022, quelles lignes seraient détenues
en septembre 2026. Or cet ensemble contient les deux supports qui ont le plus
progressé sur la période, les semi-conducteurs à +400,10 % et les banques de la
zone euro à +404,11 %. Aucune décision réelle n'a été prise à ces dates.

Trois autres écarts avec le contrat réel s'ajoutent à celui-là. Seules trois
lignes sur douze sont retenues, les seules cotées en euros avec un historique
complet. Leurs pondérations sont remises à l'échelle pour représenter 50 % du
contrat, alors que la part actions réelle est inférieure. Enfin, ni arbitrage ni
rachat ne sont simulés.

## Ce que le passage en v0.3 change

La v0.3 reprend la v0.2 et remplace la moyenne 100 jours par une moyenne
200 jours. C'est le seul paramètre modifié.

La moyenne 100 jours de la v0.2 n'était pas un choix de conception. Elle était
imposée par un historique d'un an, sur lequel une moyenne 200 jours n'aurait
laissé que deux mois et demi de test. Avec cinq ans de données, la contrainte
disparaît et la v0.1 retrouve son filtre d'origine.

Sur la fenêtre mesurée, la moyenne 200 jours apporte 2,36 points de rendement
annuel de plus, avec un drawdown moins profond, -4,59 % contre -5,82 %, et
34 arbitrages de moins, 60 contre 94. La volatilité est très légèrement
supérieure, 5,40 % contre 5,22 %.

Le mécanisme est lisible. Une moyenne courte réagit vite et produit des sorties
que le marché dément quelques séances plus tard. Chaque aller-retour de ce type
fait manquer un rebond. Le second semestre 2022 en donne une illustration : la
v0.2 y perd 4,28 % pendant que la v0.3 gagne 0,39 % et que l'indice monde large
gagne 1,88 %. La moyenne longue était restée investie là où la moyenne courte
était sortie puis rentrée.

Ce mécanisme est connu et attendu. Il n'est pas démontré ici, il est seulement
cohérent avec ce que montre cette fenêtre.

## Face au socle passif

Sur ces quatre ans et deux mois, Claude A v0.3 fait 2,40 points de performance
totale de moins que le socle monde conservé sans arbitrage, pour un drawdown
deux fois moins profond, -4,59 % contre -10,17 %, et une volatilité de 5,40 %
contre 7,52 %.

Le filtre de tendance n'a donc pas ajouté de performance. Il a réduit le creux
maximal et la volatilité pour un coût de performance faible sur cette fenêtre.
C'est exactement son objet, et c'est aussi la limite de ce qu'on peut en dire :
une fenêtre de quatre ans marquée par une hausse générale des actions est
favorable à toute stratégie qui reste investie, et peu favorable à un filtre qui
sort parfois.

## Ce que ces chiffres ne prouvent pas

Ils ne prouvent pas que la moyenne 200 jours est meilleure que la moyenne
100 jours. Ils montrent qu'elle l'a été sur une fenêtre, sur six supports et
avec un jeu de paramètres. Deux points de rendement annuel d'écart entre deux
réglages d'un même filtre, sur quatre ans, entrent dans ce qu'un autre
découpage de période peut renverser.

Ils ne prouvent pas que ces stratégies battent le contrat d'origine. La seule
ligne qui représente la composition actuelle de Bernard est rétro-simulée et
biaisée par construction.

Ils ne mesurent pas le coût réel du contrat. Les frais de gestion, l'éventuel
écart entre la valeur liquidative estimée et celle effectivement appliquée à
l'arbitrage, et les prélèvements mensuels ne sont pas simulés.

Ils reposent sur un fonds en euros modélisé à 3,00 % par an, faute de cotation
publique. Le taux 2026 réel sera connu en janvier 2027. Comme le fonds en euros
représente la moitié du portefeuille dans la plupart des allocations, une erreur
d'un point sur ce taux déplace le résultat annualisé d'environ un demi-point.

Ils portent sur une seule fenêtre, sans découpage en sous-périodes ni test sur
d'autres univers. Aucune de ces trois stratégies n'est validée. Leur statut
reste `research_hypothesis`.

## Trois écarts entre les règles affichées et le code

Ils sont signalés ici plutôt que corrigés en silence.

La confirmation de rentrée à cinq clôtures consécutives au-dessus de la moyenne,
prévue par la v0.1 de Claude A, n'a jamais été implémentée. Elle est désormais
explicitement désactivée dans les paramètres de la v0.3, et la règle principale
du fichier de stratégie a été reformulée pour décrire ce que le code applique.

Le délai minimal de vingt séances entre deux changements d'état, prévu par la
v0.1 de Claude C, n'est pas implémenté non plus. La v0.2 de Claude C tourne donc
sans ce garde-fou. Le corriger changerait sa logique de simulation et relève
d'une v0.3 pour cette stratégie, pas d'une retouche.

Le filtre de ticks aberrants annoncé par le paramètre `bad_tick_filter` n'est
pas appliqué par le script. Il visait une variation de plus de 5 % annulée en
sens inverse la séance suivante. Sur les six supports retenus, il serait
aujourd'hui sans effet : le seul tick de ce type, celui du 24 octobre 2025 sur
le fonds à volatilité minimale, est déjà neutralisé en amont dans les données
communes, où il porte la mention `reversible_tick_neutralised`. Le paramètre
reste donc dans les fichiers de stratégie, mais il décrit une intention et non
un traitement appliqué.

## Univers retenu

Six supports, tous cotés en euros sur une place de la zone euro.

| Rôle | Support | Cotation | Performance sur la fenêtre |
|---|---|---|---|
| Socle monde large | iShares Core MSCI World | IWLE.DE, Francfort | +90,50 % |
| Socle volatilité minimale | Xtrackers MSCI World Minimum Volatility | XDEB.DE, Francfort | +28,05 % |
| Thème | iShares MSCI Global Semiconductors | SEMI.AS, Amsterdam | +400,10 % |
| Thème | Amundi Euro Stoxx Banks | BNKE.PA, Paris | +404,11 % |
| Thème | iShares MSCI EM ex-China | EXCH.AS, Amsterdam | +117,09 % |
| Support de repli | Xtrackers II EUR Overnight Rate Swap | XEON.DE, Francfort | +11,50 % |

La cotation londonienne d'iShares Core MSCI World, utilisée jusqu'ici par le
script, a été remplacée par la cotation de Francfort du même fonds. Les deux
lignes ne diffèrent que par la devise de cotation, que le fichier commun
n'homogénéise pas.

La santé mondiale reste absente : le seul support de l'univers est coté à
Londres. Les stratégies Claude comptent donc trois thèmes et non quatre.

## Reproduire ces chiffres

```bash
python strategies/claude/backtest.py
```

Le script écrit les courbes base 100 dans
`strategies/claude/<stratégie>/backtest_<version>.csv`, la synthèse dans
`strategies/claude/strategies.json`, les données de la page dans
`docs/data/claude-history.json`, et ajoute les décisions à
`history/claude/decisions.jsonl` sans jamais en réécrire une.
