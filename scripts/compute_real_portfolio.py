"""Prospective tracking from dated account observations; never rewrite origin."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

SNAPSHOTS = Path('config/portfolio_snapshots')
OUT = Path('docs/data/bernard-real.json')


def project(snapshot, prices):
    """Use only closes after each observed line's price date, never backfill."""
    start = str(snapshot['as_of_date'])
    total = float(snapshot['total_eur'])
    holdings = snapshot['holdings']
    if abs(sum(float(h['value_eur']) for h in holdings) - total) > 0.005:
        raise ValueError('Snapshot holdings do not reconcile to account total')
    if total <= 0 or len({h['asset_id'] for h in holdings}) != len(holdings):
        raise ValueError('Invalid total or duplicate holding')
    usable = prices.copy()
    usable['date'] = usable['date'].astype(str)
    usable = usable.dropna(subset=['close_eur'])
    market = [h for h in holdings if h.get('reference_price') is not None]
    series = {}
    for h in market:
        if float(h['reference_price']) <= 0:
            raise ValueError('Reference prices must be positive')
        rows = usable[(usable.asset_id == h['asset_id']) & (usable.date > h['price_date'])]
        series[h['asset_id']] = rows.sort_values('date').drop_duplicates('date', keep='last')
    dates = sorted({start} | {str(d) for rows in series.values() for d in rows.date if d > start})
    result = []
    for day in dates:
        value, stale, missing = 0., [], []
        for h in holdings:
            amount = float(h['value_eur'])
            if h.get('reference_price') is None:
                value += amount  # Actual credited euro-fund return remains unknown.
                continue
            rows = series[h['asset_id']]
            known = rows[(rows.date > start) & (rows.date <= day)]
            price, price_day = float(h['reference_price']), h['price_date']
            if not known.empty:
                price, price_day = float(known.iloc[-1].close_eur), str(known.iloc[-1].date)
            value += amount * price / float(h['reference_price'])
            if day != start and price_day < day:
                stale.append({'asset_id': h['asset_id'], 'price_date': price_day})
                if rows.empty:
                    missing.append(h['asset_id'])
        result.append({'date': day, 'value_eur': round(value, 2),
                       'index': 100. if day == start else 100 * value / total,
                       'status': 'observed' if day == start else 'estimated',
                       'pending_supports': stale, 'missing_market_series': missing})
    return result


def comparisons(snapshot, rows, payloads):
    """Rebase every comparator at the last published value known at observation."""
    dates = [r['date'] for r in rows]
    start = snapshot['as_of_date']
    curves = [{'label': 'Bernard réel — suivi estimé', 'values': [r['index'] for r in rows]}]
    seen = {curves[0]['label']}
    for payload in payloads:
        for curve in payload.get('series', []):
            label = curve['label']
            if label in seen:
                continue
            values = {str(d): v for d, v in zip(payload.get('dates', []), curve.get('values', []))
                      if v is not None and float(v) > 0}
            before = sorted(d for d in values if d <= start)
            if not before:
                continue
            anchor_date = before[-1]
            # An old comparator is not silently carried over weeks or months.
            if (pd.Timestamp(start) - pd.Timestamp(anchor_date)).days > 7:
                continue
            anchor = float(values[anchor_date])
            curves.append({'label': label, 'anchor_price_date': anchor_date,
                           'values': [100. if day == start else
                                      100 * float(values[day]) / anchor if day in values else None
                                      for day in dates]})
            seen.add(label)
    return dates, curves


def main():
    files = sorted(SNAPSHOTS.glob('*.json'))
    if not files:
        raise SystemExit('No observed real portfolio snapshot')
    snapshots = [json.loads(p.read_text()) for p in files]
    snapshots.sort(key=lambda s: s['as_of_date'])
    if len({s['as_of_date'] for s in snapshots}) != len(snapshots):
        raise ValueError('Duplicate observation dates')
    prices = pd.read_csv('data/prices/daily.csv', usecols=['date', 'asset_id', 'close_eur'])
    # Earlier observations remain immutable. Each new statement starts a new
    # forward segment: unknown inter-statement cashflows are never called returns.
    segments = []
    payloads = [json.loads(p.read_text()) for p in
                (Path('docs/data') / f'{actor}.json' for actor in ('academic', 'chatgpt', 'claude')) if p.exists()]
    for i, snapshot in enumerate(snapshots):
        rows = project(snapshot, prices)
        if i + 1 < len(snapshots):
            rows = [r for r in rows if r['date'] < snapshots[i+1]['as_of_date']]
        dates, curves = comparisons(snapshot, rows, payloads)
        segments.append({'as_of_date': snapshot['as_of_date'], 'dates': dates, 'series': curves,
                         'valuations': rows, 'observed_total_eur': snapshot['total_eur']})
    latest = snapshots[-1]
    output = {'generated_at': datetime.now(timezone.utc).isoformat(timespec='seconds'),
              'latest_snapshot': latest, 'segments': segments,
              'method': 'Dated observed positions; subsequent indicative valuation using EUR prices. '
                        'No retroactive trades. Displayed reference prices are rounded; projections '
                        'use observed line amounts multiplied by price ratios. Netissima is held '
                        'at observed value pending confirmed interest credit. Fees and future '
                        'withdrawals are not invented; a programmed withdrawal is not a confirmed flow.'}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(output, ensure_ascii=False, indent=2) + '\n')
    Path('data/benchmarks').mkdir(parents=True, exist_ok=True)
    Path('data/benchmarks/bernard_real.csv').write_text(pd.DataFrame(segments[-1]['valuations']).drop(
        columns=['pending_supports', 'missing_market_series']).to_csv(index=False))
    print(f'Real portfolio: {latest["as_of_date"]}, {len(segments[-1]["dates"])} points')


if __name__ == '__main__':
    main()
