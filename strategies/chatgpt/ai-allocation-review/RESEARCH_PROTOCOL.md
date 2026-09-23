# Stratégie qui réapprend chaque semaine — protocole de recherche v0.2

## Ce que cette stratégie essaie de faire

Chaque semaine, elle examine tous les supports pour lesquels les données sont suffisantes. Elle ne prend pas par principe les cinq meilleurs, ni toujours le même nombre de lignes. Elle cherche quels éléments ont effectivement aidé à prévoir les semaines suivantes dans des situations de marché comparables, puis elle construit l'allocation de la semaine suivante à partir de cette constatation.

Le point fixe est la **procédure contrôlable**, pas une note immuable. Les poids attribués aux informations, les supports retenus et le nombre de lignes peuvent changer d'une semaine à l'autre.

Cette fiche définit une hypothèse à tester. Elle ne crée encore aucun arbitrage et ne prétend pas battre Bernard ou les autres stratégies.

## Informations examinées

Pour chaque support comparable en euros, le calcul reconstruit, à chaque date passée :

- ses variations sur 5, 20, 60 et 120 séances ;
- sa position par rapport aux moyennes 20, 50 et 200 séances ;
- sa volatilité et ses baisses passées ;
- son volume relatif lorsque ce volume est réellement disponible ;
- les huit données de contexte : VIX, incertitude, conditions financières, dollar global, EUR/USD, taux BCE, Brent et activité hebdomadaire.

Les données de contexte n'ordonnent pas directement les supports. Elles servent à vérifier si, dans un certain contexte, une information comme la tendance, la volatilité ou le dollar avait plus ou moins de valeur prédictive pour une catégorie de support.

## Ce qui change réellement chaque semaine

À la date de décision `T`, le calcul ne peut utiliser que les données publiées avant `T`.

1. Il reconstitue plusieurs périodes historiques comparables avec les données alors connues.
2. Il mesure, sur ces périodes passées, quels signaux ont apporté une information utile après prise en compte des autres signaux. Un signal sans résultat assez stable est ramené vers zéro, au lieu d'être conservé parce qu'il paraît séduisant.
3. Il applique les poids ainsi appris aux supports disponibles à `T` et estime plusieurs portefeuilles possibles.
4. Il choisit le portefeuille dont la qualité a été la plus régulière sur des semaines jamais utilisées pour l'apprentissage : rendement, baisse maximale, instabilité, concentration et ressemblance avec le portefeuille de Bernard sont examinés ensemble.

Ainsi, une semaine, la tendance peut compter beaucoup et le VIX peu ; une autre semaine, le résultat historique peut indiquer l'inverse. Ce n'est donc pas « on applique chaque samedi la même note ».

## Pas de nombre de lignes décidé à l'avance

Le calcul produit des portefeuilles allant d'une forte concentration à une large répartition. Il n'emploie pas un paramètre `top 5`, `top 10` ou `top 50` décidé à l'avance.

La largeur retenue résulte du test hors échantillon : si ajouter des supports améliore réellement le couple rendement-risque et réduit une concentration inutile, ils restent ; si cela dilue le résultat sans réduire le risque, ils sortent. Une allocation peut donc comporter une seule ligne, vingt lignes ou toutes les lignes admissibles. Le rapport hebdomadaire devra indiquer le nombre final et pourquoi le test a retenu ce niveau de diversification.

## Ce que devient l'observation sur les courbes actuelles

Les courbes actuelles montent et baissent souvent ensemble : elles sont toutes exposées, à des degrés différents, aux mêmes marchés. La courbe de Bernard est plus lisse surtout parce que le fonds en euros y tient une grande place. Ce constat devient une condition de sélection, pas un commentaire.

Pour chaque portefeuille candidat, le test calcule :

- la corrélation roulante avec Bernard et avec les autres stratégies ;
- la part du risque venant de chaque support et de chaque catégorie connue ;
- la concentration sur des supports qui évoluent presque pareil ;
- le gain réel apporté par le portefeuille lorsqu'il est combiné à Bernard.

Un portefeuille presque identique à Bernard n'est conservé que s'il apporte un bénéfice mesurable : meilleur rendement à risque comparable, ou baisse/risk sensiblement moindre. Il n'est pas rejeté simplement parce qu'il est corrélé ; il est rejeté s'il ne fait que dupliquer Bernard sans bénéfice démontré.

## Test à construire avant tout suivi à blanc

Le test avancera semaine par semaine. Pour une semaine ancienne, il bloque les données à cette semaine, apprend uniquement sur les semaines précédentes, décide l'allocation suivante, puis enregistre le résultat observé. Les données publiées après la décision, y compris les séries hebdomadaires pas encore publiées, sont exclues.

Le résultat devra comparer cette stratégie aux références existantes sur : rendement, volatilité, baisse maximale, nombre et ampleur des arbitrages, concentration et corrélation avec Bernard. Une amélioration visible sur une seule courte période ne suffira pas. Si le test ne montre pas d'avantage robuste, la stratégie restera un échec documenté et ne deviendra pas une allocation suivie.

## Conditions avant la première décision réelle suivie

1. Le programme doit produire la même décision lorsqu'on lui redonne les mêmes données datées.
2. Les poids appris, les supports retenus, les données consultées et la version du programme doivent être archivés.
3. Le test hors échantillon doit être terminé et lisible, y compris ses périodes défavorables.
4. La stratégie ne peut modifier que son portefeuille de suivi ; elle ne passe aucun ordre sur le contrat.
