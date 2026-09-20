# Données générées

Ce dossier est alimenté automatiquement.

- `prices/daily.csv` : historique quotidien disponible.
- `indicators/latest.csv` : derniers indicateurs communs.
- `snapshots/YYYY-MM-DD.csv` : photographie quotidienne des indicateurs.

Aucune décision de stratégie ne doit être écrite ici.

# Données de marché communes

`prices/daily.csv` est la seule source de prix utilisable par les calculs communs.
Chaque ligne conserve :

- `close_raw` : clôture Yahoo non ajustée, uniquement pour audit ;
- `close_native` : clôture Yahoo ajustée (splits/dividendes), nettoyée seulement lorsqu'un aller-retour suspect est structurellement identifié, dans la monnaie de cotation ;
- `close_eur` : clôture nettoyée puis convertie en EUR avec le taux de change Yahoo du même jour ;
- `close` : alias historique de `close_eur`, maintenu pour compatibilité.

Les indicateurs, le benchmark Bernard et les stratégies académiques exigent `close_eur`. Les espaces ChatGPT et Claude lisent donc la même série nettoyée, sans réécrire leurs décisions ni leurs résultats historiques.

Le workflow exécute `scripts/validate_market_data.py` avant tout calcul. Il refuse une série sans devise de cotation vérifiée ou avec un aller-retour de prix suspect encore présent dans la série EUR. Le critère de suspicion est volontairement étroit : retour quasi complet, avec volume nul ou mouvement d'au moins 50 %. Les autres mouvements, notamment une action volatile et traitée, ne sont pas réécrits. Toutes les inversions observées dans la clôture brute sont conservées dans `data/quality/reversible_raw_ticks.csv` à des fins d'audit.
