# Claude D et Claude E, sélection par classement

Calcul du 21 septembre 2026, sur cinq ans de données communes corrigées.

Les stratégies A, B et C suivent une liste de thèmes décidée à l'avance. D et E
ne décident rien à l'avance : chaque semaine, elles classent tous les fonds
cotés en euros accessibles dans le contrat et détiennent les six premiers.

## Comparaison, toutes lignes sur la même fenêtre

Du 20 septembre 2022 au 18 septembre 2026, 1 017 séances. Cette fenêtre commence
plus tard que celle des résultats de Claude A : une stratégie qui compare des
performances sur douze mois a besoin d'un an de données avant sa première
décision.

| | Performance | Annualisée | Drawdown max | Volatilité | Arbitrages |
|---|---|---|---|---|---|
| **Claude D, momentum multi-horizon** | **+64,94 %** | **+13,20 %** | -9,12 % | 8,82 % | 105 |
| **Claude E, momentum sous garde-fou** | **+57,33 %** | **+11,88 %** | -6,18 % | 7,76 % | 107 |
| Claude B, risque cible | +56,03 % | +11,65 % | -5,52 % | 6,61 % | 70 |
| Socle monde 50 % passif | +49,60 % | +10,50 % | -10,17 % | 7,43 % | 0 |
| Claude A v0.3 | +49,45 % | +10,47 % | -4,59 % | 5,54 % | 60 |
| Claude C v0.2 | +37,29 % | +8,17 % | -4,57 % | 5,09 % | 85 |

Toutes ces lignes gardent la moitié du contrat en fonds en euros, modélisé à
3,00 % par an. Seule l'autre moitié travaille.

Le résultat qui compte n'est pas le classement en performance seule. Claude E et
Claude B font mieux que le socle passif sur les deux axes à la fois : plus de
rendement et un creux maximal moins profond. Claude D paie sa performance par un
creux comparable à celui du socle passif.

## Ce qui a été vérifié avant de publier ces chiffres

Une stratégie qui ne marche qu'avec ses réglages exacts ne marche pas. Trois
contrôles ont été faits.

**Le jour de la revue.** En décalant la revue hebdomadaire de deux séances dans
un sens ou dans l'autre, Claude D reste entre 12,91 % et 14,37 % par an. Claude E
descend jusqu'à 9,34 %, ce qui la rend nettement plus fragile sur ce point.

**La date de départ.** En démarrant en janvier 2023, en juillet 2023 ou en
janvier 2024 au lieu de juillet 2022, Claude D donne 13,70 %, 14,79 % puis
15,52 % par an. Aucun de ces résultats ne dépend d'un point d'entrée particulier.

**Les réglages voisins.** Retenir cinq ou huit supports au lieu de six, ou
changer les horizons de calcul, déplace le résultat de moins de deux points par
an. Il s'agit d'un plateau, pas d'un pic isolé.

## Année par année

| | 2022 | 2023 | 2024 | 2025 | 2026 |
|---|---|---|---|---|---|
| Claude D | -0,3 % | +12,2 % | +12,1 % | +13,0 % | +16,4 % |
| Claude E | -0,1 % | +7,0 % | +12,7 % | +14,2 % | +14,4 % |
| Claude B | +0,2 % | +9,0 % | +10,6 % | +13,3 % | +13,9 % |
| Claude A v0.3 | +0,4 % | +8,2 % | +9,3 % | +12,3 % | +12,1 % |
| Socle monde 50 % passif | +0,1 % | +12,3 % | +12,1 % | +11,0 % | +6,9 % |

2022 ne couvre que trois mois et 2026 s'arrête au 18 septembre. En 2023 et 2024,
Claude D fait exactement comme le socle passif. L'écart se crée en 2025 et 2026,
années où l'indice monde ralentit pendant que certains thèmes accélèrent : c'est
la situation que la sélection par classement sait exploiter, et il n'y en a que
deux dans l'échantillon.

## Ce que ces chiffres ne prouvent pas

**L'univers est celui d'aujourd'hui.** Les supports testés sont ceux encore
référencés dans le contrat en septembre 2026. Un fonds fermé ou retiré depuis
2021 n'apparaît pas. Un classement qui ne peut choisir que parmi des survivants
est légèrement flatté. C'est la limite la plus sérieuse de ces deux stratégies,
et elle n'est pas corrigeable avec les données disponibles.

**Quatre ans ne valident rien.** La période testée est presque entièrement
haussière pour les actions. Une sélection par le classement se comporte mal dans
les retournements rapides : elle achète après la hausse et vend après le début de
la baisse. Le seul épisode de baisse de la période, fin 2022, est justement celui
où D et E font leur plus mauvais résultat.

**Deux supports très proches peuvent être retenus ensemble.** Le classement ne
sait pas que deux ETF sur le même indice font la même chose. Sur la période, cela
s'est produit avec deux fonds Nasdaq.

**Les frais du contrat ne sont pas simulés**, ni les prélèvements mensuels, ni
l'écart entre la valeur liquidative estimée et celle appliquée à l'arbitrage.

**105 arbitrages en quatre ans**, soit deux par mois. Les arbitrages sont
gratuits chez Altaprofits, mais ce rythme suppose une revue hebdomadaire tenue
sans exception. Une revue mensuelle a été essayée au banc d'essai : elle coûte
environ un demi-point de rendement annuel et divise le nombre d'arbitrages par
trois. Cette variante n'est pas publiée dans le dépôt ; elle le sera si le
rythme hebdomadaire s'avère trop lourd à tenir.

## Statut

Les deux stratégies portent le statut `research_hypothesis`. Aucune n'est
validée et aucune décision réelle n'a été prise à ces dates.
