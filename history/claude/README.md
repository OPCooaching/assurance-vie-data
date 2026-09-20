# Historique des décisions Claude

## Format

Un fichier `decisions.jsonl`, une décision par ligne, au format JSON défini par
`contracts/strategy-decision.schema.json`.

```json
{"date":"2026-09-18","strategy_id":"claude-socle-satellites","strategy_version":"v0.1",
 "comment":"Revue hebdomadaire","allocations":[{"asset_id":"IE00B4L5Y983","weight_pct":30.0}]}
```

## Règle

Append only. Une décision inscrite n'est jamais modifiée ni supprimée, y compris
lorsqu'elle se révèle mauvaise. Une correction de logique crée une nouvelle
version de stratégie et laisse les décisions antérieures en place.

Cette règle existe pour que les performances affichées restent vérifiables.
Un historique réécrit après coup ne prouve rien.

## Alimentation

Le fichier est alimenté par `strategies/claude/backtest.py`, en ajout seul.
