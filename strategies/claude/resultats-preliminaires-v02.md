# Résultats préliminaires, v0.2

**Statut : préliminaires. Ne pas citer comme résultats.**

Calcul du 20 septembre 2026, sur la version des données communes disponible ce
jour-là. Ces données sont en cours de correction par l'administrateur du dépôt.
Ce fichier est conservé comme trace, et ne sera pas supprimé quand les backtests
seront refaits sur les données propres.

Fenêtre walk-forward : 17 février 2026 au 18 septembre 2026, 150 séances.
Les 100 séances antérieures servent à l'amorçage des indicateurs.

## Comparaison à fenêtre identique

| | Performance | Drawdown max | Volatilité |
|---|---|---|---|
| Bernard actuel rétro-simulé, partiel | +19,63 % | -12,31 % | 20,49 % |
| Socle monde 50 % conservé | +5,15 % | -3,83 % | 6,29 % |
| Claude A v0.2, filtre de tendance | +7,20 % | -3,51 % | 7,42 % |

Claude A a réalisé 15 arbitrages sur la période.

## Ce que recouvre exactement la ligne « Bernard actuel rétro-simulé, partiel »

Cette ligne ne représente en aucun cas la performance réelle du contrat.

Méthode employée : la composition connue au 7 septembre 2026 a été appliquée
en arrière à partir du 17 février 2026, sans arbitrage et sans rachat.

Cinq écarts avec le contrat réel, à connaître avant toute lecture.

**Trois lignes sur douze.** Seuls les supports cotés en euros ont été retenus :
semi-conducteurs, banques zone euro, émergents hors Chine. Les neuf autres
lignes du contrat sont absentes, dont ArcelorMittal, la santé mondiale, les
matières premières, l'informatique mondiale, l'agriculture, la robotique, la
défense, le Nasdaq et le fonds Lazard.

**Pondérations reconstruites.** Les trois poids d'origine, 8,78 %, 5,13 % et
1,45 %, ont été mis à l'échelle pour totaliser 50 % du contrat. La part actions
réelle est de 41,14 %.

**Fonds en euros modélisé.** 50 % du portefeuille rémunérés à 3,00 % par an,
faute de cotation publique. Le taux 2026 réel sera connu en janvier 2027.

**Aucun rachat.** Le prélèvement mensuel de 350 € n'est pas simulé.

**Biais de sélection sur la composition.** C'est le point le plus lourd.
Appliquer en arrière une composition connue aujourd'hui revient à savoir, dès
février, quelles lignes seraient détenues en septembre. Cet ensemble contient
le thème qui a plus que doublé sur la période. Aucune décision réelle n'a été
prise à ces dates.

Une rétro-simulation de ce type flatte mécaniquement la composition testée.
Elle sert de repère grossier, pas de référence.

## Lecture des écarts

Sur cette fenêtre, la composition concentrée rétro-simulée dépasse Claude A de
12,4 points, en supportant une volatilité presque trois fois supérieure et un
drawdown 3,5 fois plus profond.

Claude A dépasse le socle mondial passif de 2,05 points, avec un drawdown
légèrement inférieur. L'écart est faible et porte sur sept mois.

## Ce que ces chiffres ne prouvent pas

Sept mois ne valident aucune stratégie.

La fenêtre couvre une période où les semi-conducteurs ont plus que doublé.
Une stratégie qui diversifie ne pouvait pas gagner ce match. Le résultat
inverse sur une fenêtre de baisse serait tout aussi peu concluant.

## Ce qu'ils indiquent quand même

Le filtre de tendance a réduit le drawdown sans coûter de performance face au
socle passif. C'est son objet.

Il n'a pas compensé l'écart face à la concentration, et rien ne dit qu'il le
ferait sur une autre fenêtre.

## Reprise prévue

Quand les données communes corrigées seront disponibles, avec cinq ans
d'historique, les ticks traités et les devises homogénéisées, les backtests
seront refaits à l'identique sur ces nouvelles données.

Ce fichier restera en place. Les nouveaux résultats seront écrits séparément.
