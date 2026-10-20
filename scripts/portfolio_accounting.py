"""Close execution accounting. Targets trade after the day's valuation."""
import math

import pandas as pd


def normalise(target):
    weights = {a: float(w) for a, w in target.items() if float(w) != 0}
    if not weights or any(not math.isfinite(w) or w < 0 for w in weights.values()):
        raise ValueError("Invalid allocation")
    total = sum(weights.values())
    if abs(total - 1) > 1e-6:
        raise ValueError(f"Allocation does not total 100%: {total}")
    return {a: w / total for a, w in weights.items()}


def simulate(prices, dates, events):
    """Events: date, weights (fractions), optional maintain flag.

    Missing initial prices fail explicitly. Subsequent published prices may be
    carried forward, never backward. A maintenance review does not trade.
    """
    dates = pd.DatetimeIndex(dates)
    px = prices.reindex(prices.index.union(dates)).sort_index().ffill().reindex(dates)
    events = sorted(events, key=lambda e: pd.Timestamp(e["date"]))
    weights, value, rows, previous, cursor = {}, None, [], None, 0
    for dt in dates:
        if value is not None and previous is not None:
            grown = {}
            for a, w in weights.items():
                if a not in px or not pd.notna(px.at[dt, a]) or not pd.notna(px.at[previous, a]):
                    raise ValueError(f"Missing valuation: {a} at {dt}")
                if px.at[previous, a] <= 0 or px.at[dt, a] <= 0:
                    raise ValueError(f"Non-positive price: {a}")
                grown[a] = w * px.at[dt, a] / px.at[previous, a]
            factor = sum(grown.values())
            value *= factor
            weights = {a: w / factor for a, w in grown.items()}
        while cursor < len(events) and pd.Timestamp(events[cursor]["date"]) <= dt:
            event = events[cursor]
            cursor += 1
            if value is not None and event.get("maintain"):
                continue
            target = normalise(event["weights"])
            for a in target:
                if a not in px or not pd.notna(px.at[dt, a]) or px.at[dt, a] <= 0:
                    raise ValueError(f"Missing execution price: {a} at {dt}")
            weights = target
            if value is None:
                value = 100.0
        rows.append(value)
        previous = dt
    return pd.Series(rows, index=dates, dtype=float), weights
