# Protocole de backtest ChatGPT v1

_Date : 23 septembre 2026. Ce document prépare les tests des quatre familles ChatGPT. Il ne constitue ni une allocation active ni une recommandation d'arbitrage._

## Ce que le backtest doit répondre

Une règle précise aurait-elle produit un parcours acceptable **en ne connaissant que les données disponibles à chaque date de décision** ? Il ne doit pas chercher la règle qui paraît la meilleure après coup.

Les anciennes variantes momentum ont été retirées du suivi public. Elles ne servent pas de preuve pour les quatre nouvelles familles.

## Règle commune de calendrier

- Les prix sont lus jusqu'à la dernière valorisation réellement disponible.
- Une décision hebdomadaire est calculée après la dernière valorisation disponible du vendredi.
- Une décision mensuelle est calculée après la dernière valorisation disponible du mois.
- L'allocation décidée s'applique à la **valorisation disponible suivante**, inconnue au moment de décider.
- Les rendements sont ensuite calculés jour par jour à partir de cette allocation, jusqu'à la prochaine décision.
- Un support sans prix nécessaire n'est pas sélectionnable. Il ne reçoit ni prix inventé ni interpolation fictive.

Cette séparation interdit le biais le plus grave : décider avec la valeur de la séance qui n'était pas encore connue.

## Conditions avant l'exécution d'un test

Chaque stratégie doit posséder un fichier de version immuable avec :

1. l'univers autorisé et le support défensif éventuel ;
2. tous les seuils et fenêtres chiffrés ;
3. la fréquence et la règle de passage à l'allocation suivante ;
4. les règles de données manquantes ;
5. la période testée, les coûts et l'hypothèse de valorisation.

Modifier un seul de ces éléments crée une nouvelle version. On ne remplace jamais un résultat v0.1 par un résultat « amélioré ».

## Nature des quatre tests

| Famille | Test possible immédiatement ? | Condition spécifique |
| --- | --- | --- |
| Momentum mensuel | Oui, sur les prix EUR | Figer horizons, rang, filtre et règle défensive. |
| Exposition pilotée par le risque | Oui, sur les prix EUR et le VIX | Figer la poche, la fenêtre de risque, la cible et les limites sans levier. |
| Régime macro-financier | Seulement provisoirement avec les fichiers actuels | Employer les données macro telles qu'elles étaient publiées à chaque date, pas leur version révisée aujourd'hui. |
| Hybride sélection/protection | Oui pour la sélection prix ; provisoire si la protection utilise du macro révisé | Figer séparément sélection mensuelle et garde-fous hebdomadaires. |

Les données FRED actuelles donnent la dernière révision connue. Pour un backtest macro strict, la collecte devra utiliser les versions datées ALFRED : FRED/ALFRED conserve les périodes « real-time » permettant de savoir ce qui était connu à une date passée. Source : https://fred.stlouisfed.org/docs/api/fred/realtime_period.html

Tant que cette étape n'est pas ajoutée, un résultat macro sera explicitement étiqueté **provisoire — données révisées** et ne pourra pas déclencher un suivi simulé.

## Sorties reproductibles

Un lancement de test enregistrera, sous son propre dossier :

```
history/chatgpt/backtests/<strategy_id>/<version>/
  specification.yml
  performance.csv
  decisions.jsonl
  metrics.json
  README.md
```

- `specification.yml` : copie immuable de la règle testée ;
- `performance.csv` : indice base 100 et dates réellement valorisées ;
- `decisions.jsonl` : chaque allocation de test, sa date et ses signaux ;
- `metrics.json` : résultats calculés, période, couverture et avertissements ;
- `README.md` : limites et conclusion, y compris si le résultat est négatif.

## Mesures à comparer

Une stratégie ne sera pas retenue parce qu'elle finit seulement plus haut. Le rapport comparera au minimum :

- rendement cumulé et annualisé ;
- volatilité et pire baisse ;
- temps passé en baisse ;
- nombre de décisions et rotation du portefeuille ;
- couverture effective des données ;
- comparaison au portefeuille Bernard et à des repères simples ;
- sensibilité à une période différente et aux paramètres voisins.

Les coûts d'arbitrage étant annoncés gratuits, ils seront notés à zéro dans le scénario de base, mais le délai de valorisation et l'absence de garantie sur la prochaine valeur liquidative restent modélisés.

## Passage à la page publique

1. **Aujourd'hui** : la page ChatGPT affiche Bernard comme repère, les quatre hypothèses, leur statut et un historique vide.
2. **Après un test** : elle affichera un résultat de backtest clairement séparé du suivi réel, avec période, version, hypothèses et avertissements.
3. **Après validation explicite** : une stratégie passe en suivi simulé ; ses décisions hebdomadaires et sa courbe à partir de cette date seulement sont ajoutées.
4. **Chaque semaine, plus tard** : le futur automate produira l'instantané de données, la décision JSON append-only, la performance et les fichiers de page. Il ne sera planifié qu'après les tests et les contrôles.

## Contrôles automatiques obligatoires

- allocations égales à 100 % ;
- aucun support hors univers ;
- prix et indicateurs disponibles avant la décision ;
- application à la valorisation suivante ;
- aucun fichier de décision ou de résultat antérieur écrasé ;
- statut visible sur la page : hypothèse, backtest, suivi simulé ou suspendue.

## Conclusion opérationnelle

Le prochain développement est le moteur de backtest des règles prix, à commencer par la stratégie momentum mensuelle une fois ses paramètres v0.1 figés. Le moteur macro viendra avec une collecte ALFRED « point dans le temps » ; sans elle, il ne sera jamais présenté comme un test historique strict.
