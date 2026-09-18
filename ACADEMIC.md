# Stratégies de référence

Ces stratégies servent de **témoins externes**. Elles ne sont ni ChatGPT ni strategie-claude et leurs règles ne doivent pas être modifiées pour améliorer rétroactivement leurs résultats.

## 60/40 mondial adapté

Référence simple : 60 % actions mondiales / 40 % obligations.

Adaptation Altaprofits :
- 60 % Amundi MSCI World II UCITS ETF ;
- 40 % Xtrackers II EUR Corporate Bond UCITS ETF.

Source de contexte : Vanguard décrit encore des portefeuilles 60/40 globalement diversifiés comme allocation stratégique de long terme.

## Harry Browne - Permanent Portfolio adapté

Règle d'origine :
- 25 % actions ;
- 25 % obligations longues ;
- 25 % cash ;
- 25 % or.

Adaptation Altaprofits :
- actions mondiales ;
- obligations d'État zone euro 25+ ;
- monétaire overnight euro ;
- proxy actions minières aurifères.

**Attention :** le dernier quart n'est pas de l'or physique. La version Altaprofits ne peut donc pas être considérée comme une réplication exacte du Permanent Portfolio.

Référence : Harry Browne, Permanent Portfolio ; synthèse documentée par Bogleheads.

## Faber Trend 10 mois - World

Règle :
- à la fin du mois, si le prix est au-dessus de sa moyenne mobile simple 10 mois : World ;
- sinon : actif défensif ;
- le signal du mois précédent s'applique au mois suivant afin d'éviter le biais d'anticipation.

Référence : Meb Faber, *A Quantitative Approach to Tactical Asset Allocation*.

## Momentum académique 12 mois - adaptation long-only

La littérature sur le time-series momentum documente une persistance des rendements sur des horizons d'environ 1 à 12 mois dans plusieurs classes d'actifs.

Notre adaptation au contrat :
- univers : ETF Altaprofits disposant de suffisamment d'historique ;
- classement mensuel par performance sur environ 12 mois ;
- conservation des 5 meilleurs ETF uniquement si leur momentum est positif ;
- pondération égale ;
- part non investie placée sur le support monétaire.

Cette version est **long-only** et n'est pas la réplication du portefeuille futures long/short de l'étude originale.

Référence : Moskowitz, Ooi & Pedersen, *Time Series Momentum*, Journal of Financial Economics, 2012.

## Sources

- https://workplace.vanguard.com/insights-and-research/perspective/the-global-60-40-portfolio-steady-as-it-goes.html
- https://www.bogleheads.org/blog/2014/09/11/harry-brownes-permanent-portfolio/
- https://mebfaber.com/2009/02/19/a-quantitative-approach-to-tactical-asset-allocation-updated/
- https://www.sciencedirect.com/science/article/pii/S0304405X11002613
