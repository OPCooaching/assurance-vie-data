# Règles pour les IA

Ce dépôt unique contient les données communes, les stratégies, les historiques et le site public anonymisé.

## ChatGPT
- Peut lire tous les fichiers.
- Écrit uniquement dans `strategies/chatgpt/`, `history/chatgpt/` et les fichiers web/générés nécessaires à ses propres résultats.
- Peut lire `strategies/claude/` et `history/claude/` pour comparer les résultats.
- Ne modifie jamais les décisions historiques de Claude.

## Claude
- Peut lire tous les fichiers.
- Écrit uniquement dans `strategies/claude/`, `history/claude/` et les fichiers web/générés nécessaires à ses propres résultats.
- Peut lire `strategies/chatgpt/` et `history/chatgpt/` pour comparer les résultats.
- Ne modifie jamais les décisions historiques de ChatGPT.

## Stratégies académiques
- Elles vivent dans `strategies/academic/` et servent de témoins.
- Leurs règles sont fixes et ne doivent pas être modifiées rétroactivement pour améliorer leurs résultats.

## Historique
- Une décision passée est append-only.
- Une évolution de logique crée une nouvelle version de stratégie.
- Les performances historiques restent rattachées à la version qui les a produites.

## Données communes
Les mises à jour régulières sont faites par les workflows automatiques. Olivier reste administrateur du dépôt.

## Confidentialité
Ne jamais ajouter : nom de famille, e-mail, adresse, téléphone, numéro de contrat, identifiant client, document contractuel brut, valeur exacte du contrat ou autre donnée permettant d'identifier Bernard.

Le prénom Bernard est un alias autorisé. Les données publiques sont exprimées en pourcentages, base 100 ou valeurs calculées à partir d'un secret de publication.
