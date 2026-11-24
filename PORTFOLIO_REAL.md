# Portefeuille de Bernard : origine, réel courant et arbitrages

## Deux objets différents

- `config/portfolio_origin_2026-09-07.csv` est le portefeuille d'origine figé. Il sert exclusivement au benchmark `Bernard origine` : « que serait devenu le portefeuille du 07/09/2026 sans arbitrage ? ».
- `config/portfolio_current.csv` représente le portefeuille réel courant de référence après les arbitrages connus.
- `config/portfolio_events.csv` est le journal append-only des arbitrages réels.

Le benchmark historique ne doit jamais être recalculé à partir de `portfolio_current.csv`.

## Arbitrage du 24/09/2026

Désinvesti :
- Netissima : 5 998,10 EUR.
- Amundi STOXX Europe Defense UCITS ETF — LU3038520774 : 770,2116 parts à 5,85 EUR, soit 4 505,74 EUR.
- iShares Agribusiness UCITS ETF — IE00B6R52143 : 148,9992 parts à 49,82 EUR, soit 7 423,14 EUR.

Réinvesti :
- iShares MSCI Brazil UCITS ETF (DE) — DE000A0Q4R85 : 129,4660 parts à 46,11 EUR, soit 5 969,68 EUR.
- Xtrackers Russell 2000 UCITS ETF — IE00BJZ2DD79 : 16,2550 parts à 367,25 EUR, soit 5 969,68 EUR.
- Xtrackers MSCI World Value UCITS ETF — IE00BL25JM42 : 80,7826 parts à 74,12 EUR, soit 5 987,62 EUR.

Total désinvesti = total réinvesti = 17 926,98 EUR.

## Limite de la référence courante

Le document d'arbitrage donne les quantités vendues et achetées mais pas les quantités totales détenues avant l'arbitrage pour les deux ETF vendus.

Par conséquent, `portfolio_current.csv` conserve une **référence comptable** construite ainsi : valeur du snapshot du 07/09 moins le montant exact vendu, plus les montants exacts réinvestis. Les petits reliquats calculés sur Defense et Agribusiness ne doivent pas être interprétés comme la preuve qu'il reste réellement ces montants au contrat.

Dès qu'un relevé post-arbitrage donnant les positions exactes est disponible, il doit remplacer cette référence comptable pour le portefeuille réel, sans modifier le benchmark d'origine ni l'événement du 24/09.

Les retraits mensuels de 350 EUR restent exclus des courbes de performance.


## Relevé du 21/11/2026, reçu le 24/11/2026

La transcription anonymisée complète des neuf positions observées est conservée
dans `config/portfolio_snapshots/2026-11-21.json`. Leur somme est exactement
264 457,05 EUR. `config/portfolio_current.csv` contient désormais les poids calculés
sur ce relevé ; son état antérieur du 10/10/2026 est archivé sans modification dans
`config/portfolio_snapshots/2026-10-10.csv`. Les anciennes versions restent dans Git.

`scripts/compute_real_portfolio.py` produit `data/benchmarks/bernard_real.csv` et
`docs/data/bernard-real.json` lors du traitement quotidien, après les courbes
théoriques. Un graphique distinct sur les quatre pages compare les variations
depuis ce relevé en base 100. Les cours des comparateurs sont recalés au dernier
point publié avant le relevé (le samedi ne crée pas un cours de marché).

Le point du relevé est observé ; les points suivants sont des estimations des
positions connues, utilisant les montants constatés multipliés par le rapport
entre le nouveau cours en EUR et le prix de référence affiché. Les prix arrondis
du relevé, les éventuels frais et les mouvements non encore communiqués limitent
la précision. Netissima ne reçoit pas de rendement quotidien inventé. Le retrait
programmé de 350 EUR le 16/12 reste une programmation, pas un flux exécuté.

Chaque prochain relevé daté crée un nouveau segment prospectif. On ne raccorde
pas artificiellement les segments en performance nette de flux inconnus. Les
intervalles sans historique complet d'arbitrages restent estimés et explicités.
Le témoin `Bernard origine`, les anciennes décisions ChatGPT/Claude et les règles
académiques ne sont pas modifiés. Les pronostics hebdomadaires continuent dans
leurs espaces séparés ; ils ne constituent pas des ordres réels.

Le suivi réel est aussi calculé et publié juste après le contrôle des prix,
avant la validation des indicateurs macroéconomiques. Ainsi un indicateur
macro périmé bloque toujours les stratégies qui en dépendent, mais pas la
valorisation indépendante des positions observées. Seuls les deux fichiers
du suivi réel sont publiés à cette étape ; les contrôles restent actifs.
