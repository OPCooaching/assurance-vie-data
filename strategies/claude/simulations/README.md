# Recherche, hors protocole de backtest

Ce dossier contient des travaux exploratoires menés entre le 20 et le 21 septembre
2026, avant l'écriture du protocole de backtest du 23 septembre.

## Pourquoi ce ne sont pas des backtests au sens du protocole

Le protocole exige qu'une spécification soit figée **avant** le test, et qu'un
résultat ne soit jamais remplacé par une version améliorée. Ces travaux ne
respectent ni l'une ni l'autre de ces conditions.

Plusieurs centaines de jeux de paramètres ont été essayés sur la période 2022-2026,
et les règles retenues sont celles qui gagnaient sur cette période. C'est un choix
fait après coup. Des contrôles de robustesse ont été menés, décalage du jour de
revue, dates de départ différentes, réglages voisins, et ils limitent le problème
sans le supprimer.

Un deuxième biais s'ajoute : l'univers testé est celui des fonds encore référencés
dans le contrat aujourd'hui. Un fonds fermé ou retiré depuis 2021 n'y figure pas.

Ces résultats décrivent donc le passé. Ils ne prédisent rien et ne servent pas de
preuve. Ils sont conservés parce qu'ils expliquent d'où viennent les cinq règles
actuellement suivies, et parce qu'effacer une recherche décevante serait la
première façon de se tromper soi-même.

## Contenu

| Fichier | Rôle |
|---|---|
| `backtest.py` | Moteur de simulation walk-forward utilisé en septembre 2026 |
| `resultats-v03.md` | Résultats de Claude A sur cinq ans, et ce qu'ils ne prouvent pas |
| `resultats-momentum.md` | Résultats de Claude D et Claude E, et leurs limites |
| `resultats-preliminaires-v02.md` | Première salve sur un an de données, conservée comme trace |
| `<stratégie>-backtest_<version>.csv` | Courbes base 100 produites par ces simulations |
| `claude_history_backtest_v0.2.json` | Sortie brute d'une simulation antérieure |
| `decisions_walk_forward_v0.2.jsonl` | Décisions simulées, jamais des décisions prises |

## Si un vrai backtest devient nécessaire

Il devra suivre le protocole du 23 septembre 2026 : spécification figée d'abord,
puis `history/claude/backtests/<stratégie>/<version>/` avec specification.yml,
performance.csv, decisions.jsonl, metrics.json et un README qui dit aussi les
résultats négatifs. Le moteur de ce dossier ne produit pas ce format et devra être
réécrit pour cela.
