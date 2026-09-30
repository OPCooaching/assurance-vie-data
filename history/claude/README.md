# Historique des décisions Claude

## Règle

Une décision inscrite ici n'est jamais modifiée ni supprimée, y compris lorsqu'elle
se révèle mauvaise. Une correction de logique crée une nouvelle version de
stratégie et laisse les décisions antérieures en place.

Cette règle existe pour que les performances affichées restent vérifiables. Un
historique réécrit après coup ne prouve rien.

## Organisation

- `decisions/` : une décision par fichier, `AAAA-MM-JJ--<stratégie>.json`, lue par
  le tableau de bord commun. Le format et l'état actuel sont décrits dans le
  README de ce dossier.
- `backtests/` : réservé aux tests conformes au protocole du 23 septembre 2026,
  avec spécification figée avant le test. Vide à ce jour. Les travaux exploratoires
  antérieurs sont dans `strategies/claude/simulations/` et ne sont pas des
  backtests au sens du protocole.

## Ce qui n'y entre jamais

Les décisions simulées par un backtest. Elles portent sur des dates où aucune
décision n'a été prise et changent dès que les données ou les règles changent.
