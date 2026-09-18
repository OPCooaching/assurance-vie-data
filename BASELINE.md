# Benchmark Bernard origine

Le portefeuille de Bernard au 07/09/2026 est conservé comme **point de repère immuable**.

Il ne s'agit pas du portefeuille réel après futurs arbitrages. C'est la réponse à la question :

> Que serait devenu le portefeuille du 07/09/2026 si on n'avait plus rien modifié ?

## Courbe commune

La courbe est normalisée à **100 au 07/09/2026**.

Chaque page de stratégie doit afficher au minimum :
1. Bernard origine ;
2. la stratégie concernée.

Un benchmark de marché peut être ajouté séparément, mais ne remplace jamais Bernard origine.

## Méthode

- Pondérations initiales figées au 07/09/2026.
- Pas de rééquilibrage du benchmark.
- Les retraits de 350 € sont exclus de la courbe de performance : on compare la qualité de gestion, pas les flux de trésorerie.
- Le fonds euro Netissima est estimé provisoirement avec le taux indiqué dans `config/baseline_bernard.yml` jusqu'à disponibilité du rendement réellement crédité.
- Toute correction du benchmark doit être documentée et traçable.

## Indicateurs communs

Chaque stratégie compare au moins :
- performance depuis l'origine ;
- performance 5 jours ;
- performance 20 jours ;
- drawdown maximum ;
- volatilité 20 jours.

Les deux IA lisent le même fichier :
`data/benchmarks/bernard_origin.csv`.
