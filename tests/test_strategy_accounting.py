import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd

from test_portfolio_accounting import simulate
from compute_academic_strategies import portfolio_curve
import rebuild_chatgpt_tracking as tracking


class StrategyAccountingTests(unittest.TestCase):
    def test_monthly_reset_preserves_old_holdings_return(self):
        dates = pd.to_datetime(["2026-09-29", "2026-09-30", "2026-10-01"])
        px = pd.DataFrame({"a": [100, 200, 100], "b": [100, 100, 100]}, index=dates)
        curve = portfolio_curve(px, {"a": .5, "b": .5}, dates[0], "monthly")
        self.assertAlmostEqual(curve.iloc[-1], 100)
        self.assertAlmostEqual(curve.attrs["latest_allocation"]["a"], .5)

    def test_late_monday_review_executes_tuesday(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "review.json"
            path.write_text(json.dumps({
                "strategy_id": "test", "decided_at_utc": "2026-10-19T10:18:54Z",
                "effective_valuation_date": "2026-10-19",
                "decision_type": "maintain",
                "target_allocation_percent": {"a": 100},
            }))
            with patch.object(tracking, "WEEKLY_DECISIONS", Path(folder)):
                result = tracking.weekly_decisions("test")
            self.assertEqual(result[0]["effective_date"], "2026-10-20")
            self.assertTrue(result[0]["maintain"])

    def test_weekly_handoff_stops_legacy_signals(self):
        with patch.object(tracking, "weekly_decisions", return_value=[
            {"effective_date": "2026-10-12", "target_allocation_percent": {"b": 100}}
        ]), patch.object(tracking, "legacy_decisions", return_value=[
            {"effective_date": "2026-10-09", "target_allocation_percent": {"a": 100}},
            {"effective_date": "2026-10-16", "target_allocation_percent": {"a": 100}}
        ]):
            rows = tracking.read_decisions("test")
        self.assertEqual([r["effective_date"] for r in rows], ["2026-10-09", "2026-10-12"])

    def test_future_event_does_not_change_current_holdings(self):
        dates = pd.to_datetime(["2026-10-16", "2026-10-19"])
        px = pd.DataFrame({"a": [100, 110], "b": [100, 100]}, index=dates)
        curve, weights = simulate(px, dates, [
            {"date": dates[0], "weights": {"a": 1}},
            {"date": "2026-10-20", "weights": {"b": 1}},
        ])
        self.assertAlmostEqual(curve.iloc[-1], 110)
        self.assertEqual(weights, {"a": 1})
