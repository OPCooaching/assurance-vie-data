# Stratégies de référence

Ces stratégies servent de **témoins externes**. Elles ne sont ni ChatGPT ni Claude et leurs règles ne doivent pas être modifiées a posteriori pour améliorer leurs résultats.

## Bernard origine

Le portefeuille du 07/09/2026 est figé comme référence. La courbe indique ce qu'il serait devenu sans nouvelle décision de gestion. Les retraits mensuels sont exclus de la comparaison de performance.

## 60/40 mondial adapté

Principe : conserver 60 % d'actions mondiales et 40 % d'obligations d'entreprises en euros.

Adaptation Altaprofits :
- 60 % Amundi MSCI World II UCITS ETF Dist ;
- 40 % Xtrackers II EUR Corporate Bond UCITS ETF.

La répartition est rééquilibrée une fois par mois vers 60/40. La stratégie ne sélectionne pas les actifs en fonction de leurs performances récentes.

## Harry Browne - Permanent Portfolio adapté

Principe d'origine :
- 25 % actions ;
- 25 % obligations longues ;
- 25 % cash / monétaire ;
- 25 % or.

Adaptation Altaprofits :
- 25 % Amundi MSCI World II UCITS ETF ;
- 25 % Xtrackers II Eurozone Government Bond 25+ ;
- 25 % Xtrackers II EUR Overnight Rate Swap ;
- 25 % Amundi NYSE Arca Gold Bugs.

Rééquilibrage : annuel.

**Attention :** le dernier quart n'est pas de l'or physique. Il s'agit d'un ETF d'actions minières aurifères. La version Altaprofits n'est donc pas une réplication exacte du Permanent Portfolio.

## Faber Trend 10 mois - World

La stratégie observe une fois par mois l'ETF Monde.

Règle :
- si son cours de fin de mois est au-dessus de sa moyenne mobile simple des 10 derniers mois, la stratégie reste à 100 % sur l'ETF Monde ;
- sinon, elle bascule à 100 % sur le support monétaire ;
- le signal calculé à la fin d'un mois s'applique au mois suivant afin d'éviter un biais d'anticipation.

Cette stratégie cherche donc à rester exposée aux actions pendant une tendance haussière et à devenir défensive lorsque la tendance longue se dégrade.

## Momentum académique 12 mois - adaptation long-only

Une fois par mois :
1. tous les ETF Altaprofits disposant d'un historique suffisant sont comparés sur leur performance des 12 derniers mois ;
2. les ETF dont la performance sur 12 mois est négative sont exclus ;
3. jusqu'aux 5 ETF ayant les meilleures performances restantes sont retenus ;
4. les ETF sélectionnés reçoivent des pondérations égales ;
5. si aucun ETF n'a un momentum positif, le portefeuille est placé à 100 % sur le support monétaire.

Exemples de pondération :
- 5 ETF retenus : 20 % chacun ;
- 4 ETF : 25 % chacun ;
- 2 ETF : 50 % chacun.

**Long-only** signifie qu'aucune vente à découvert ni position négative n'est autorisée. La stratégie ne peut qu'acheter ou conserver les supports disponibles dans le contrat.

Cette version est une adaptation applicable à Altaprofits. Elle ne reproduit pas le portefeuille futures long/short utilisé dans l'étude académique originale.

## Sources

- Vanguard, portefeuille global 60/40.
- Harry Browne, Permanent Portfolio ; synthèse documentée par Bogleheads.
- Meb Faber, *A Quantitative Approach to Tactical Asset Allocation*.
- Moskowitz, Ooi & Pedersen, *Time Series Momentum*, Journal of Financial Economics, 2012.
