# Règles pour les IA

Ce dépôt public et anonymisé rassemble les données communes, les stratégies, les décisions historiques et les pages de suivi de l'assurance-vie.

## Source de vérité

En cas de contradiction, l'ordre de priorité est :

1. `config/access-policy.yml` pour les droits d'écriture et la confidentialité ;
2. les données et décisions datées réellement présentes dans le dépôt ;
3. `contracts/` pour le format commun ;
4. les README et les pages explicatives.

Une documentation ancienne ne doit jamais justifier une modification des données, d'une décision passée ou de la politique de confidentialité.

## Données communes

Les workflows automatiques actualisent les données de marché les jours ouvrés. Les agents lisent les données communes mais ne les modifient pas.

Pour comparer des supports cotés dans des devises différentes, les calculs communs utilisent `close_eur`, après le contrôle de qualité. Une donnée manquante, trop courte ou non résolue reste explicitement indisponible : elle ne doit jamais être remplacée par une valeur inventée.

## ChatGPT

- Peut lire tous les fichiers.
- Écrit uniquement dans `strategies/chatgpt/`, `history/chatgpt/` et les sorties web propres à ChatGPT autorisées par `config/access-policy.yml`.
- Peut lire l'espace Claude pour comparer les résultats.
- Ne modifie jamais les décisions ni les règles historiques de Claude.

## Claude

- Peut lire tous les fichiers.
- Écrit uniquement dans `strategies/claude/`, `history/claude/`, `data/claude/`, `docs/data/claude.json` et `docs/claude.html`.
- Peut lire l'espace ChatGPT pour comparer les résultats.
- Ne modifie jamais les décisions ni les règles historiques de ChatGPT.
- Ne modifie pas les pages ou données partagées (`docs/index.html`, `docs/academic.html`, `docs/chatgpt.html`, `docs/assets/`, `config/`, `data/prices/`, `data/indicators/`) sans demande explicite d'Olivier.
- Ne doit jamais prétendre qu'une revue Claude est automatique tant qu'une automatisation Claude distincte n'a pas été réellement créée et vérifiée.

## Stratégies académiques

Les stratégies de `strategies/academic/` servent de témoins. Leurs règles et leurs résultats historiques ne sont pas réécrits pour améliorer une performance a posteriori.

## Décisions et versions

- Toute décision effectivement enregistrée est append-only.
- Toute modification de logique crée une nouvelle version de stratégie.
- Une reconstitution ou un backtest est clairement étiqueté comme tel ; il ne devient jamais une décision hebdomadaire réellement prise à l'époque.
- Une allocation de portefeuille doit totaliser exactement 100 %.
- Aucun ordre réel n'est jamais transmis depuis ce dépôt.

## Confidentialité

Le dépôt est public mais anonymisé. Il est interdit d'y ajouter : nom de famille, prénom réel, e-mail, adresse, téléphone, date de naissance complète, numéro de contrat, identifiant client, clause bénéficiaire ou document contractuel brut.

L'alias `Bernard` est autorisé. Les montants exacts en euros et leur affichage public sont autorisés, à condition qu'ils restent dissociés de toute identité personnelle. Les règles détaillées et à jour sont dans `config/access-policy.yml`.
