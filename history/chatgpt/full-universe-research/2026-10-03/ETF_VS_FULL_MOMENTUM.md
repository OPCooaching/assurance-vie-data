# Comparaison vérifiée — momentum relatif : ETF seuls contre univers complet

**Date de l'analyse : 03/10/2026**  
**Statut : résultat de recherche, pas une allocation et pas un ordre.**

## Question

L'ajout des actions directes et fonds au classement momentum améliore-t-il la même règle par rapport aux ETF seuls ?

## Règle identique comparée

- revue mensuelle ;
- prise d'effet à la valorisation suivante ;
- 260 séances d'historique minimum ;
- classement égal des rendements à 3, 6 et 12 mois ;
- filtre : cours au-dessus de la moyenne mobile 200 séances et score positif ;
- cinq lignes équipondérées ;
- support monétaire de repli ;
- hypothèse d'arbitrages gratuits.

Les deux résultats ne sont pas confondus avec la variante « 12 mois seul » de l'univers complet : celle-ci n'est pas la même règle et n'est donc pas utilisée pour cette comparaison.

## Résultats disponibles

| Même règle momentum multi-horizons | ETF seuls | Univers complet |
|---|---:|---:|
| Période publiée | 19/09/2022 → 22/09/2026 | 03/10/2022 → 30/09/2026 |
| Supports éligibles | ETF avec historique suffisant | 333 : 98 actions, 156 fonds, 79 ETF |
| Décisions | 49 | 48 |
| Rendement annualisé | **22,3 %** | 18,5 % |
| Volatilité annualisée | **21,3 %** | 28,1 % |
| Drawdown maximal | **−18,6 %** | −27,1 % |

Les extrémités de période diffèrent de quatorze jours, car les deux recherches ont été lancées à des dates différentes. C'est une limite explicitement conservée ; elle n'inverse toutefois pas le constat descriptif actuel.

## Décision de recherche

**Ne pas créer de stratégie “actions” ni de quota d'actions.**

Dans ce premier test directement comparable, inclure automatiquement les actions et fonds a réduit le rendement annualisé historique et accru à la fois la volatilité et la pire baisse. Il n'existe donc aucune base empirique actuelle pour dire que les actions doivent être ajoutées à l'allocation de Bernard.

Les actions restent autorisées dans l'univers complet des recherches futures, mais uniquement si une autre famille de règles démontre un résultat robuste. Elles ne sont pas retenues parce qu'elles sont des actions, ni écartées par principe.

## Suite verrouillée

La famille momentum est désormais traitée comme une seule famille de recherche. Les prochaines études ne chercheront pas de nouvelles variantes momentum ; elles testeront uniquement les deux mécanismes distincts définis dans `strategies/chatgpt/RESEARCH_SELECTION.md` :

1. tendance absolue avec repli monétaire ;
2. exposition pilotée par la volatilité.

Leurs règles, univers et mesures seront écrits avant calcul ; elles seront comparées à la fois à l'univers complet et aux ETF seuls.

## Sources internes

- `history/chatgpt/backtests/chatgpt-momentum-mensuel/v0.1/metrics.json`
- `history/chatgpt/backtests/chatgpt-momentum-mensuel/v0.1/specification.yml`
- `history/chatgpt/full-universe-research/2026-09-30/results.json`
- `scripts/backtest_chatgpt_v0_1.py`
- `scripts/backtest_full_universe_20260930.py`
