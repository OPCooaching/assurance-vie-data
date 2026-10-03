# Sélection des stratégies à étudier — protocole verrouillé

**Statut : recherche.** Ce document ne crée aucune allocation, ne modifie aucune stratégie active et ne déclenche aucun arbitrage du contrat de Bernard.

## 1. Mandat auquel la recherche doit répondre

- Objectif de Bernard : améliorer le résultat sur un horizon d'environ un an, avec une revue possible chaque samedi.
- Une revue hebdomadaire n'implique pas un arbitrage hebdomadaire forcé : une règle peut conserver l'allocation si son signal ne change pas.
- Le montant-cible de Bernard est un repère de résultat ; il ne devient jamais un signal qui pousserait la stratégie à augmenter son risque.
- Tous les résultats restent théoriques jusqu'à une décision explicite de suivre une stratégie. Aucun ordre réel n'est envoyé.

## 2. Ce que les données permettent actuellement

Au 03/10/2026, le screener compte 473 supports, dont 337 comparables avec des prix journaliers normalisés en euros. Parmi les 333 supports ayant au moins 260 observations exploitables pour la recherche : 98 actions directes, 156 OPCVM/fonds et 79 ETF.

Les prix utilisés par les tests sont corrigés des divisions et dividendes lorsqu'ils sont fournis par la source, puis normalisés en euros. Les cours ou valeurs liquidatives publiés avec retard restent identifiés comme tels.

Aucune donnée fondamentale exploitable (bénéfices, valorisation, bilan, révisions d'analystes) n'est disponible dans le screener. Une stratégie « value », « qualité » ou « croissance » ne peut donc pas être étudiée honnêtement à ce stade.

## 3. Conclusion sur les actions

Les actions directes ne sont **ni obligatoires ni exclues**. Elles seront présentes dans une stratégie seulement si une règle validée les retient face aux fonds et ETF dans le même univers.

La question testée n'est donc pas « faut-il mettre des actions ? », mais : « une règle utilisant l'univers complet fait-elle mieux, de façon robuste, qu'une règle identique limitée aux ETF ou qu'un portefeuille mondial simple ? »

## 4. Trois familles seulement à étudier maintenant

Ces familles ne sont pas choisies parce qu'elles produisent aujourd'hui un joli graphique. Elles sont retenues car elles correspondent à trois mécanismes économiques différents, disposent d'une littérature identifiable et peuvent être calculées avec les données actuellement disponibles.

### M — Momentum relatif inter-supports

**Question :** parmi les supports comparables, les mieux classés par leur performance passée font-ils mieux que les autres lors de la période suivante ?

**Fondement :** Jegadeesh et Titman (1993) documentent un effet de momentum relatif sur les actions américaines à des horizons intermédiaires. La publication ne valide pas automatiquement une assurance-vie long only : c'est précisément l'objet du test de transposition.

**Règle à tester :** classement mensuel selon une combinaison écrite à l'avance des rendements à 3, 6 et 12 mois, avec comparaison explicite de l'univers complet et de l'univers ETF seul. Les tailles 5, 10 et 20 ne sont pas trois stratégies : ce sont des tests de robustesse du même mécanisme.

**Rôle des actions :** aucun quota d'actions. Elles peuvent être sélectionnées ou non selon le classement.

### T — Tendance absolue avec repli monétaire

**Question :** un support dont sa propre tendance devient négative doit-il être remplacé temporairement par le support monétaire, plutôt que par un autre « meilleur » support ?

**Fondement :** Moskowitz, Ooi et Pedersen (2012) documentent la persistance de tendance sur de nombreuses classes de contrats à terme. Une assurance-vie ne permet pas de vendre à découvert ni de reproduire ces contrats : le test sera donc une adaptation long only, explicitement séparée de la publication.

**Règle à tester :** chaque support n'est conservé que si son prix est au-dessus de sa moyenne mobile à 200 séances et si son rendement à 12 mois est positif ; sinon, son poids va au support monétaire. La sélection est revue chaque samedi, mais ne change que si le signal change.

**Rôle des actions :** possible, mais soumis au même filtre que fonds et ETF.

### V — Exposition pilotée par la volatilité

**Question :** faut-il diminuer l'exposition risquée lorsque la volatilité observée augmente, sans prétendre deviner quel actif montera ?

**Fondement :** Moreira et Muir (2017) étudient des portefeuilles qui réduisent leur risque quand la volatilité est élevée. Ce résultat ne justifie pas encore nos seuils : ceux-ci seront figés avant le test.

**Règle à tester :** portefeuille large, diversifié et défini avant simulation ; poids total risqué ajusté par volatilité observée sur 60 séances, surplus placé au monétaire. Aucun score de tendance ou classement de gagnants n'est utilisé dans cette famille.

**Rôle des actions :** elles peuvent figurer dans le portefeuille large, mais aucun actif individuel ne reçoit une place parce qu'il est une action.

## 5. Familles explicitement reportées

- **Value / qualité / bénéfices :** reportée jusqu'à l'ajout et la validation de données fondamentales.
- **Thèmes (semi-conducteurs, IA, défense, quantique, énergie) :** un thème est un univers, pas un mécanisme prédictif. Il peut devenir un sous-univers de test plus tard, jamais une stratégie autonome sans règle d'entrée et de sortie.
- **Retournement de court terme :** reporté. La littérature et les coûts/conditions de liquidité exigent une validation spécifique ; les données de volume ne couvrent aujourd'hui que 172 supports.

## 6. Protocole de test commun

1. Geler le code, les paramètres et les données utilisées avant de lire les résultats.
2. Utiliser les seules données connues à chaque date de décision ; prise d'effet à la valorisation suivante.
3. Séparer une période de conception et une période de vérification hors échantillon. L'historique utilisable étant court, l'incertitude restera explicitement affichée.
4. Comparer chaque famille à :
   - Bernard origine ;
   - un portefeuille World ;
   - le support monétaire ;
   - la même famille sur ETF seuls, lorsque cela est pertinent.
5. Rapporter pour chaque version : rendement annualisé, volatilité, drawdown maximal, rendement ajusté du risque, turnover, concentration maximale, nombre effectif de lignes, part du temps au monétaire et qualité des prix/VL.
6. Conserver toutes les variantes prévues, y compris celles qui échouent. Ne jamais retenir seulement celle dont le rendement brut historique est le plus élevé.
7. Hypothèse principale : arbitrages gratuits, conformément au contrat. Présenter en complément une sensibilité de robustesse à 10 et 25 points de base, sans la faire passer pour les frais du contrat.
8. Ne transformer une famille en stratégie affichée et suivie que si ses résultats hors échantillon sont cohérents avec ses variantes prévues et si ses limites sont comprises.

## 7. Résultat attendu de la prochaine étape

La prochaine étape produit **un tableau de recherche unique**, et non de nouvelles allocations :

| Famille | Univers complet | ETF seuls | Part d'actions retenues | Hors échantillon | Risque / drawdown | Conclusion |
|---|---:|---:|---:|---:|---:|---|
| M — Momentum relatif | à calculer | à calculer | à calculer | à calculer | à calculer | à décider |
| T — Tendance absolue | à calculer | n/a | à calculer | à calculer | à calculer | à décider |
| V — Volatilité pilotée | à calculer | à calculer | à calculer | à calculer | à calculer | à décider |

Aucune des trois familles n'est supposée gagnante avant les tests.

## Références

- Jegadeesh, N. & Titman, S. (1993), *Returns to Buying Winners and Selling Losers*, Journal of Finance. https://www.nber.org/papers/w19590.pdf
- Moskowitz, T., Ooi, Y.H. & Pedersen, L.H. (2012), *Time Series Momentum*, Journal of Financial Economics. https://doi.org/10.1016/j.jfineco.2011.11.003
- Moreira, A. & Muir, T. (2017), *Volatility-Managed Portfolios*, Journal of Finance. https://doi.org/10.1111/jofi.12513
- Bailey, D. et al. (2015), *The Probability of Backtest Overfitting*. https://ssrn.com/abstract=2326253
