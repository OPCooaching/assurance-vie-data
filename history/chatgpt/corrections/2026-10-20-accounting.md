# Correction des calculs — 20 octobre 2026

Révision examinée : `293d02fa737e03e99c90fa09863b9a387c0459b6`.
Moteur corrigé : `accounting-20261020`.
Cette note est une correction de calcul, pas une nouvelle décision d'investissement.

## Dernière valeur en base 100 au 19 octobre

| Série | Avant | Après |
|---|---:|---:|
| ChatGPT A | 94,0680 | 94,4613 |
| ChatGPT B | 99,1768 | 99,0159 |
| ChatGPT C | 100,4669 | 100,4192 |
| ChatGPT D | 96,3240 | 96,4921 |
| ChatGPT E | 99,1783 | 99,4095 |
| 60/40 adapté | 102,0486 | 102,0467 |
| Harry Browne adapté | 98,8706 | 98,8706 |
| Faber | 103,5370 | 103,5370 |
| Momentum académique | 94,7422 | 94,6737 |

Les dates de départ propres aux séries sont conservées. Ces valeurs ne constituent pas un classement sur une durée identique.

## Corrections

- Conservation des quantités entre arbitrages, au lieu d'un retour implicite aux poids cibles chaque jour.
- Rendement de la séance d'exécution attribué aux anciennes positions ; nouvelles positions acquises à la clôture.
- Maintien explicite : aucun rééquilibrage.
- Revues du 17 octobre reçues le 19 : effet simulé au plus tôt le 20, sans modifier les archives.
- Fin de l'application des décisions de backtest anciennes après le relais des revues archivées.
- Backtests corrigés conservés dans une nouvelle version, sans écraser `v0.1`.
- Backtest macro C indisponible : prix manquant du support LU2533811910 le 03/10/2022. Aucun rendement de remplacement n'est inventé.
- Conversion de devises : interdiction de compléter les premiers taux absents avec des taux futurs.
- Affichage des positions valorisées séparé des cibles de revue ; dates de début réelles ; volatilité 20 séances indisponible avant 20 rendements.
- Synthèse comparée sur une fenêtre commune avec des membres constants et des indices ramenés à 100.

## Contrôles reproductibles

`python -m unittest discover -s tests -v` contrôle les invariants comptables,
le maintien, les dates d'exécution tardives, le relais des décisions,
les rééquilibrages mensuels et les prix initiaux absents.
Ces tests font désormais partie du traitement automatique.

## Limites conservées et signalées

Univers historique incomplet, publications macro révisables, corrections de ticks
rétrospectives, coûts propres au contrat non déduits et calendrier assureur non
disponible. Les backtests restent exploratoires.

La sélection historique hors calendrier d'octobre pour A/D reste archivée :
la corriger après coup serait réécrire une décision. Les règles académiques sont
des adaptations aux supports disponibles, pas des copies exactes des travaux cités.

Aucune décision ni règle Claude n'est modifiée. Le relevé réel de Bernard
et sa réconciliation restent indépendants de la revue des simulations.
