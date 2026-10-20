# Convention de calcul applicable depuis le 20 octobre 2026

Version du moteur : accounting-20261020. Les règles de sélection ne sont pas optimisées à l'occasion de cette correction.

Les décisions enregistrées restent immuables. Les quantités sont conservées entre arbitrages et les poids évoluent avec les cours. Une revue de maintien ne déclenche aucun retour aux proportions cibles.

Une décision est exécutée au cours de clôture de la séance d'exécution, au plus tôt le jour ouvré suivant sa réception. Le rendement qui précède cette clôture appartient aux anciennes positions. La convention de jour ouvré utilise lundi à vendredi ; un calendrier assureur et les heures de réception réelles restent nécessaires pour reproduire exactement le contrat.

Les décisions anciennes dont la date d'effet est incompatible avec la réception sont conservées ; le moteur reporte l'exécution et la page le signale. Les pondérations initiales de la fenêtre sont une condition de départ reconstituée, pas une preuve d'arbitrage réel.

Pour A et la sélection de D, les paramètres numériques sont ceux de `config/chatgpt_backtests_v0_1.yml`. Les anciennes fiches décrivent des hypothèses initiales. La sélection doit avoir lieu en fin de mois ; la revue hebdomadaire peut la contrôler sans la refaire. La sélection hors calendrier du 09/10 reste une dérogation historique explicitement affichée. B et C sont revues chaque semaine ; D contrôle sa protection chaque semaine ; E reste une analyse discrétionnaire documentée.

Un prix initial absent bloque le calcul. Un prix publié avec retard peut être conservé provisoirement ; sa date doit être affichée. Ne jamais compléter un prix initial avec une observation future.

Les données macro anciennes, l'univers courant, les ticks corrigés après observation et les frais nuls limitent les backtests. Ne pas les qualifier de validation prospective. Les frais et heures d'exécution absents ne doivent pas être inventés.

Le journal académique est un journal de contrôle. Les allocations réellement calculées par les règles académiques constituent la source des positions simulées. La page distingue ces positions des cibles du journal.

Le traitement du relevé réel de Bernard, lorsqu'il est transmis, reste distinct de la revue des stratégies simulées.
