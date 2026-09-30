"""Daily Claude paper tracking on actual shared EUR market data only."""
from __future__ import annotations

from pathlib import Path
import json
import pandas as pd

UNIVERSE = Path("config/universe.csv")
SYMBOLS = Path("config/symbol_map.csv")
PRICES = Path("data/prices/daily.csv")
BASELINE = Path("data/benchmarks/bernard_origin.csv")
OUT = Path("data/claude/performance.csv")
ALLOC_OUT = Path("data/claude/latest_allocations.csv")
TRACKING_STATE = Path("data/claude/tracking_state.json")

# Same 50% market sleeve as Claude's documented rules; the other half is the
# uncredited fund-in-euros sleeve and consequently has a zero daily return.
PART_ACTIONS = 0.50
SOCLE, SOCLE_MIN_VOL, MONETAIRE = "IE00BKBF6H24", "IE00BL25JN58", "LU0290358497"
FONDS_EURO = "ALTAPROFITS:FONDS-EN-EURO-NETISSIMA"
THEMES = ["IE000I8KRLL9", "LU1829219390", "IE00BMG6Z448"]
EURO_EXCHANGES = {"PAR", "GER", "AMS", "MIL", "BRU", "FRA", "MUN", "LIS", "VIE", "STU", "HAM", "BER", "DUS", "MCE", "HEL", "LUX"}
TRADING_DAYS = 252


def load_prices():
    rows = pd.read_csv(PRICES)
    if "close_eur" not in rows.columns:
        raise ValueError("Claude tracker requires EUR-normalised prices.")
    rows["date"] = pd.to_datetime(rows["date"])
    table = rows.pivot_table(index="date", columns="asset_id", values="close_eur", aggfunc="last")
    return table.sort_index().ffill(), rows


def past(table, date):
    return table.loc[:date]


def above_sma(table, asset, date, days):
    values = past(table, date)[asset].dropna()
    return len(values) >= days and float(values.iloc[-1]) >= float(values.iloc[-days:].mean())


def annual_volatility(table, asset, date, days):
    values = past(table, date)[asset].dropna()
    if len(values) < days + 1:
        return None
    return float(values.iloc[-days - 1:].pct_change().dropna().std() * TRADING_DAYS ** 0.5)


def euro_universe(rows, table):
    symbols = pd.read_csv(SYMBOLS)
    universe = pd.read_csv(UNIVERSE)
    merged = symbols.merge(universe[["asset_id", "category"]], on="asset_id", how="left")
    allowed = merged[
        (merged["status"] == "resolved")
        & merged["exchange"].isin(EURO_EXCHANGES)
        & merged["category"].fillna("").str.upper().isin({"ETF", "OPCVM/FI"})
    ]["asset_id"]
    depth = rows[rows["asset_id"].isin(set(allowed))].groupby("asset_id")["date"].count()
    return sorted(a for a in depth[depth >= 1250].index if a in table.columns and a != MONETAIRE)


def core_weights(table, date, market_weight, trend_days):
    core, theme = market_weight * 0.60, min((market_weight * 0.40) / len(THEMES), market_weight * 0.16)
    targets = [(SOCLE, core * 0.70), (SOCLE_MIN_VOL, core * 0.30)] + [(a, theme) for a in THEMES]
    weights, reserve = {}, 0.0
    for asset, weight in targets:
        if above_sma(table, asset, date, trend_days):
            weights[asset] = weight
        else:
            reserve += weight
    if reserve:
        weights[MONETAIRE] = weights.get(MONETAIRE, 0.0) + reserve
    return weights


def socle_satellites(table, date, _universe):
    return core_weights(table, date, PART_ACTIONS, 200)


def risque_cible(table, date, _universe):
    vol = annual_volatility(table, SOCLE, date, 40)
    target = 0.20 if not vol or vol <= 0 else max(0.20, min(0.60, 0.10 / vol))
    weights = core_weights(table, date, target, 200)
    weights[MONETAIRE] = weights.get(MONETAIRE, 0.0) + PART_ACTIONS - sum(weights.values())
    return {a: w for a, w in weights.items() if w > 0}


def double_filtre(table, date, _universe):
    trend = above_sma(table, SOCLE, date, 100)
    breadth = sum(above_sma(table, asset, date, 100) for asset in THEMES) / len(THEMES) >= 0.50
    target = PART_ACTIONS if trend and breadth else PART_ACTIONS * 0.50 if trend or breadth else 0.0
    if not target:
        return {MONETAIRE: PART_ACTIONS}
    weights = core_weights(table, date, target, 100)
    weights[MONETAIRE] = weights.get(MONETAIRE, 0.0) + PART_ACTIONS - sum(weights.values())
    return {a: w for a, w in weights.items() if w > 0}


def ranked_momentum(table, date, universe, guarded):
    if guarded and not above_sma(table, SOCLE, date, 200):
        return []
    history = past(table, date)[universe]
    if len(history) <= 252:
        return []
    last = history.iloc[-1]
    scores = {}
    for asset in universe:
        previous = [history[asset].iloc[-127], history[asset].iloc[-253]]
        if pd.notna(last[asset]) and all(pd.notna(x) and x > 0 for x in previous):
            scores[asset] = sum(float(last[asset]) / float(x) - 1 for x in previous) / 2
    return [a for a, score in sorted(scores.items(), key=lambda item: -item[1]) if score > 0][:6]


def momentum_multi(table, date, universe):
    selected = ranked_momentum(table, date, universe, False)
    weights = {a: PART_ACTIONS / 6 for a in selected}
    weights[MONETAIRE] = weights.get(MONETAIRE, 0.0) + PART_ACTIONS - sum(weights.values())
    return {a: w for a, w in weights.items() if w > 0}


def momentum_prudent(table, date, universe):
    selected = ranked_momentum(table, date, universe, True)
    weights = {}
    if selected:
        inverse = {a: 1 / max(annual_volatility(table, a, date, 60) or 0.02, 0.02) for a in selected}
        amount, total = PART_ACTIONS * len(selected) / 6, sum(inverse.values())
        weights = {a: amount * value / total for a, value in inverse.items()}
    weights[MONETAIRE] = weights.get(MONETAIRE, 0.0) + PART_ACTIONS - sum(weights.values())
    return {a: w for a, w in weights.items() if w > 0}


def continuation_curve(table, dates, signal, universe, start_value):
    """Compute only the post-restart segment.

    The first restart date is an anchor: no return is invented across the gap.
    A fresh allocation is decided on that date and performance resumes from the
    following observed valuation date.
    """
    value = float(start_value)
    weights = None
    previous = None
    latest = {}
    points = []

    for index, date in enumerate(dates):
        prices = table.loc[date]
        if index == 0:
            weights = signal(table, date, universe)
            latest = dict(weights)
            points.append((date, value))
            previous = prices
            continue

        if weights:
            daily_return = sum(
                float(weight) * (float(prices[asset]) / float(previous[asset]) - 1)
                for asset, weight in weights.items()
                if asset in prices
                and pd.notna(prices[asset])
                and pd.notna(previous[asset])
                and previous[asset] > 0
            )
            value *= 1 + daily_return

        # Same convention as the historical tracker: Monday's close belongs to
        # the previous allocation, then the new weekly allocation applies.
        if date.weekday() == 0:
            weights = signal(table, date, universe)
            latest = dict(weights)

        points.append((date, value))
        previous = prices

    return pd.Series(dict(points)), latest


def load_existing():
    if not OUT.exists():
        raise RuntimeError(
            "Claude append-only recovery requires the existing performance.csv; "
            "refusing to recreate history from scratch."
        )
    existing = pd.read_csv(OUT)
    if existing.empty or "date" not in existing.columns:
        raise RuntimeError("Claude performance history is empty or malformed.")
    existing["date"] = pd.to_datetime(existing["date"])
    if existing["date"].duplicated().any():
        raise RuntimeError("Claude performance history contains duplicate dates.")
    return existing.sort_values("date")


def load_or_create_tracking_state(existing, available_dates):
    if TRACKING_STATE.exists():
        state = json.loads(TRACKING_STATE.read_text(encoding="utf-8"))
        anchor = pd.Timestamp(state["anchor_date"])
        resume = pd.Timestamp(state["resume_date"])
        return state, anchor, resume

    anchor = pd.Timestamp(existing["date"].max())
    candidates = [date for date in available_dates if date > anchor]
    if not candidates:
        return None, anchor, None

    # First restored execution starts at the latest actually available valuation
    # date. Intermediate dates are deliberately not backfilled.
    resume = pd.Timestamp(max(candidates))
    state = {
        "mode": "append_only_after_interruption",
        "anchor_date": anchor.date().isoformat(),
        "resume_date": resume.date().isoformat(),
        "gap_reason": (
            "Claude daily computation was absent from the repository workflow. "
            "No values or decisions are reconstructed for the interruption."
        ),
    }
    TRACKING_STATE.parent.mkdir(parents=True, exist_ok=True)
    TRACKING_STATE.write_text(
        json.dumps(state, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return state, anchor, resume


def append_new_rows(existing, candidate):
    last_existing = pd.Timestamp(existing["date"].max())
    new_rows = candidate.loc[candidate.index > last_existing]
    if new_rows.empty:
        return 0

    # Append bytes only: historical rows are not rewritten or reformatted.
    new_rows.to_csv(
        OUT,
        mode="a",
        header=False,
        index=True,
        date_format="%Y-%m-%d",
    )
    return len(new_rows)


def main():
    if not all(path.exists() for path in (UNIVERSE, SYMBOLS, PRICES, BASELINE, OUT)):
        print("Claude strategies skipped: required data not available yet.")
        return

    table, rows = load_prices()
    available_dates = [
        date
        for date in pd.to_datetime(pd.read_csv(BASELINE)["date"])
        if date in table.index
    ]
    if not available_dates:
        print("Claude strategies skipped: no common actual valuation dates.")
        return

    for asset in [SOCLE, SOCLE_MIN_VOL, MONETAIRE, *THEMES]:
        if asset not in table.columns:
            raise ValueError(f"Claude support missing from normalised prices: {asset}")

    universe = euro_universe(rows, table)
    signals = {
        "claude_socle_satellites": socle_satellites,
        "claude_risque_cible": risque_cible,
        "claude_double_filtre": double_filtre,
        "claude_momentum_multi": momentum_multi,
        "claude_momentum_prudent": momentum_prudent,
    }

    existing = load_existing()
    required_columns = {"date", *signals.keys()}
    if not required_columns.issubset(existing.columns):
        raise RuntimeError("Claude performance history does not contain all five strategies.")

    state, anchor, resume = load_or_create_tracking_state(existing, available_dates)
    if resume is None:
        print("Claude strategies: no valuation date available after the existing history yet.")
        return
    if resume <= anchor:
        raise RuntimeError("Claude tracking resume date must be after the historical anchor.")

    forbidden = existing.loc[
        (existing["date"] > anchor) & (existing["date"] < resume)
    ]
    if not forbidden.empty:
        raise RuntimeError(
            "Claude history already contains rows inside the declared interruption; "
            "manual review required."
        )

    run_dates = [date for date in available_dates if date >= resume]
    if not run_dates:
        print("Claude strategies: declared resume date is not available yet.")
        return

    anchor_row = existing.loc[existing["date"] == anchor]
    if len(anchor_row) != 1:
        raise RuntimeError("Claude anchor row is missing or ambiguous.")

    curves = {}
    allocations = []
    for strategy_id, signal in signals.items():
        start_value = float(anchor_row.iloc[0][strategy_id])
        curve, latest = continuation_curve(
            table, run_dates, signal, universe, start_value
        )
        curves[strategy_id] = curve
        allocations.extend(
            {
                "strategy_id": strategy_id,
                "asset_id": asset,
                "weight_pct": round(100 * weight, 6),
            }
            for asset, weight in latest.items()
        )
        allocations.append({
            "strategy_id": strategy_id,
            "asset_id": FONDS_EURO,
            "weight_pct": round(100 * (1 - sum(latest.values())), 6),
        })

    candidate = pd.DataFrame(curves)
    candidate.index.name = "date"
    appended = append_new_rows(existing, candidate)

    pd.DataFrame(allocations).to_csv(ALLOC_OUT, index=False)
    print(
        f"Claude append-only tracking: anchor={anchor.date()}, "
        f"resume={resume.date()}, appended={appended}, "
        f"latest={pd.Timestamp(run_dates[-1]).date()}."
    )


if __name__ == "__main__":
    main()
