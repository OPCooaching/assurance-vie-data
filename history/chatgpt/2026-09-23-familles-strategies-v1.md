# Familles de stratégies à tester — v1

Statut : hypothèses de recherche. Aucune de ces pistes ne constitue encore une décision d'allocation pour Bernard.

## Objectif commun

Chercher une proposition dynamique et réactive, susceptible d'améliorer le résultat du portefeuille Bernard origine. Les arbitrages sont possibles chaque semaine, mais une fréquence élevée n'est pas un objectif en soi. Chaque règle doit être testée avec une décision prise sur les données alors publiées et appliquée à la valorisation suivante.

## Données communes déjà suffisantes

- Prix EUR, volumes lorsqu'ils existent, performances et volatilités des supports.
- Contexte externe : incertitude économique, conditions financières NFCI, dollar large, Brent, activité hebdomadaire, VIX, EUR/USD et taux de dépôt BCE.
- Fonds euro et support monétaire comme allocations défensives.

Les séries hebdomadaires restent vides les jours sans publication. Une stratégie doit utiliser uniquement la dernière publication disponible à sa date de décision et conserver sa date de publication.

## 1. Momentum mensuel multi-horizons

**Règle à tester.** À la fin de chaque mois, classer les supports ayant un historique et une valeur liquidative utilisables selon leurs performances sur 3, 6 et 12 mois ; exclure les tendances négatives ; répartir la poche risquée entre les meilleurs, le solde allant au support défensif.

**Pourquoi.** Il s'agit du mécanisme le plus direct pour poursuivre les tendances de moyen terme. Une revue mensuelle réduit les rotations causées par le bruit quotidien. Elle sert de référence face aux variantes hebdomadaires.

**Données nécessaires.** Prix EUR uniquement. Aucune donnée supplémentaire.

**Risque.** Retournements brutaux et concentration involontaire dans des supports proches.

## 2. Exposition pilotée par le risque et la volatilité

**Règle à tester.** Conserver un panier diversifié fixe ou sélectionné mensuellement. Chaque semaine, ajuster seulement la part risquée selon la volatilité réalisée du panier et le VIX ; le complément va au fonds euro ou au monétaire. Des bandes minimales empêchent les petits arbitrages.

**Pourquoi.** L'objectif n'est pas de prédire le meilleur actif, mais de prendre moins de risque lorsque le marché devient instable et davantage lorsque le risque observé est faible.

**Données nécessaires.** Prix EUR et VIX, déjà disponibles. Aucune donnée supplémentaire.

**Risque.** Le signal réduit souvent l'exposition après le début d'une baisse et peut manquer un rebond rapide.

## 3. Régime macro-financier hebdomadaire

**Règle à tester.** Définir à l'avance un score de prudence fondé sur plusieurs alertes : conditions financières, VIX, incertitude, dollar et, si pertinent, activité économique. En régime normal, conserver une allocation dynamique diversifiée ; en régime de stress, réduire la poche risquée et privilégier les supports défensifs. La sélection des supports n'est pas forcément modifiée chaque semaine.

**Pourquoi.** Cette famille répond directement à la demande de réactivité de Bernard : elle adapte le niveau de risque lorsque plusieurs informations différentes se détériorent simultanément, plutôt que de ne regarder que les prix.

**Données nécessaires.** Les huit séries externes existantes suffisent. Les dates de publication et les révisions, notamment du NFCI, doivent être respectées.

**Risque.** Les seuils peuvent être arbitraires ; ils doivent être fixés avant les tests et ne pas être ajustés pour embellir le passé.

## 4. Hybride : sélection mensuelle, protection hebdomadaire

**Règle à tester.** Choisir les supports une fois par mois avec une règle de tendance ou de diversification. Chaque semaine, ne toucher au portefeuille que si un garde-fou objectif est déclenché : effondrement de la largeur de marché, hausse forte de volatilité ou régime macro-financier défavorable. Sans garde-fou, ne rien changer.

**Pourquoi.** Cette stratégie sépare deux décisions qui n'ont pas la même vitesse : sélectionner les thèmes ou actifs de moyen terme, puis protéger le portefeuille contre une détérioration rapide. Elle évite de transformer une stratégie de tendance en machine à changer d'avis chaque semaine.

**Données nécessaires.** Prix EUR, indicateurs communs et huit séries externes. Aucune donnée supplémentaire.

**Risque.** La protection peut sortir trop tôt ou revenir trop tard ; la condition de sortie doit être testée seule puis avec la sélection mensuelle.

## Donnée à enrichir plus tard, non bloquante

Pour créer une vraie stratégie de rotation sectorielle ou géographique, il faudra une table statique et vérifiée qui classe chaque support par type d'actif, région, secteur, devise et couverture de change. Ce n'est pas une donnée quotidienne à télécharger. Sans elle, des règles de plafond sectoriel seraient fictives.

## Ce qui ne doit pas être fait maintenant

- Ajouter des indicateurs fondamentaux ou de valorisation sans source gratuite, stable et couvrant réellement les fonds et ETF du contrat.
- Déclarer une famille gagnante avant les tests.
- Automatiser une allocation réelle avant d'avoir fixé et versionné la règle.
