import sys
import unittest
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from portfolio_accounting import simulate


class AccountingTests(unittest.TestCase):
    def setUp(self):
        self.dates = pd.date_range("2026-10-12", periods=3)
        self.px = pd.DataFrame({"a": [100, 200, 100], "b": [100, 100, 100]}, index=self.dates)

    def test_no_trade_round_trip(self):
        curve, _ = simulate(self.px, self.dates, [
            {"date": self.dates[0], "weights": {"a": .5, "b": .5}}])
        for actual, expected in zip(curve, [100, 150, 100]):
            self.assertAlmostEqual(actual, expected)

    def test_execution_after_valuation(self):
        curve, _ = simulate(self.px, self.dates, [
            {"date": self.dates[0], "weights": {"b": 1}},
            {"date": self.dates[1], "weights": {"a": 1}}])
        self.assertEqual(curve.tolist(), [100, 100, 50])

    def test_maintenance_does_not_rebalance(self):
        curve, weights = simulate(self.px, self.dates, [
            {"date": self.dates[0], "weights": {"a": .5, "b": .5}},
            {"date": self.dates[1], "weights": {"a": .5, "b": .5}, "maintain": True}])
        for actual, expected in zip(curve, [100, 150, 100]):
            self.assertAlmostEqual(actual, expected)
        self.assertAlmostEqual(weights["a"], .5)

    def test_missing_price_fails(self):
        with self.assertRaises(ValueError):
            simulate(self.px, self.dates, [{"date": self.dates[0], "weights": {"missing": 1}}])

    def test_future_prices_never_backfilled(self):
        self.px.loc[self.dates[0], "a"] = float("nan")
        with self.assertRaises(ValueError):
            simulate(self.px, self.dates, [{"date": self.dates[0], "weights": {"a": 1}}])

    def test_incomplete_allocation_fails(self):
        with self.assertRaises(ValueError):
            simulate(self.px, self.dates, [{"date": self.dates[0], "weights": {"a": .5}}])


if __name__ == "__main__":
    unittest.main()
