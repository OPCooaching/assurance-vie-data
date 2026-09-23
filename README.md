# assurance-vie-data

Dépôt unique, public et anonymisé pour les données, stratégies, historiques et pages de suivi de l'assurance-vie.

## État initial

- **473 supports Altaprofits** importés depuis la liste du 08/09/2026.
- Répartition et valorisation anonymisées du portefeuille au 07/09/2026 ; total de départ : 323 892,53 €.
- Benchmark immuable **Bernard origine** en base 100.
- Mise à jour automatique prévue les jours ouvrés.
- Aucune donnée personnelle, numéro de contrat ou document contractuel brut stocké.

## Organisation

```text
config/                 configuration commune
data/                   cours, indicateurs, benchmarks et résultats calculés
strategies/
  academic/             stratégies externes de référence
  chatgpt/
    impulsion/
    adaptative/
    rotation-diversifiee/
  claude/               stratégies Claude
history/
  chatgpt/              historique append-only ChatGPT
  claude/               historique append-only Claude
scripts/                moteurs de calcul
docs/                   site GitHub Pages
```

## Principe

Toutes les stratégies utilisent exactement les mêmes données de marché et le même point de départ.

Les familles suivies sont :
- **Bernard origine** : portefeuille initial figé ;
- **Académiques** : 60/40, Harry Browne adapté, Faber Trend et momentum académique adapté ;
- **ChatGPT** : Impulsion, Adaptative, Rotation diversifiée ;
- **Claude** : espace séparé dans le même dépôt.

## Historique

Les décisions passées ne sont jamais réécrites. Une modification de logique crée une nouvelle version. Les résultats restent rattachés à la version qui les a produits.

## Pages publiques

- `docs/index.html` : synthèse générale ;
- `docs/academic.html` : stratégies académiques ;
- `docs/chatgpt.html` : stratégies ChatGPT ;
- `docs/claude.html` : stratégies Claude.\n- `docs/screener.html` : observatoire commun des données et de leur disponibilité.

## Mise à jour automatique

Le workflow `Daily market data update` tourne du lundi au vendredi et peut aussi être lancé manuellement depuis l'onglet **Actions**.

Il :
1. reconstruit l'univers ;
2. contrôle l'absence de données personnelles ;
3. tente de résoudre les symboles de marché ;
4. récupère les cours ;
5. recalcule les indicateurs ;
6. construit le screener commun des données exploitables ;\n7. recalcule Bernard origine ;
7. recalcule les stratégies académiques ;
8. reconstruit les données du tableau de bord ;
9. commit les nouvelles données.

La collecte utilise Yahoo Finance via `yfinance`, sans clé API. Les supports non couverts restent explicitement marqués comme non résolus ou manuels ; aucune donnée n'est inventée.

## Confidentialité

Interdit dans le dépôt :
- nom de famille ;
- adresse ;
- e-mail ;
- téléphone ;
- date de naissance complète ;
- numéro de contrat ;
- identifiant client ;
- document contractuel brut ;
- clause bénéficiaire ;
- aucune donnée personnelle ; les montants par support sont autorisés par le propriétaire et restent dissociés de toute identité.

Le prénom **Bernard** peut être utilisé comme alias.

## Convention

- Identifiant principal : ISIN quand il existe.
- Date : `YYYY-MM-DD`.
- Devise : code ISO 4217.
- Donnée manquante : champ vide.
- Historique : append-only autant que possible.
- Toute correction manuelle reste traçable par commit Git.
