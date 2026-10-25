import sys
import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import update_market_data as market


class EuroConversionTests(unittest.TestCase):
    def convert(self, asset_dates, fx_dates, rates):
        fx = pd.DataFrame({"Close": rates}, index=pd.DatetimeIndex(fx_dates))
        part = pd.DataFrame({"date": asset_dates, "close_native": [120.0] * len(asset_dates),
                             "quote_currency": ["USD"] * len(asset_dates)})
        with patch.object(market, "download_batch", return_value=fx):
            return market.normalise_to_eur([part], "7d")[0]

    def test_string_asset_dates_align_with_timestamp_fx(self):
        result = self.convert(["2026-10-22", "2026-10-23"],
                              ["2026-10-22", "2026-10-23"], [1.2, 1.25])
        self.assertEqual(result.close_eur.tolist(), [100.0, 96.0])
        self.assertEqual(result.close.tolist(), [100.0, 96.0])

    def test_uses_previous_fx_without_future_rate(self):
        result = self.convert(["2026-10-23"], ["2026-10-22", "2026-10-26"], [1.2, 2.0])
        self.assertEqual(result.close_eur.iloc[0], 100.0)

    def test_missing_prior_fx_is_rejected(self):
        with self.assertRaisesRegex(RuntimeError, "Invalid EUR conversion"):
            self.convert(["2026-10-22"], ["2026-10-23"], [1.2])

    def test_nonpositive_fx_is_rejected(self):
        with self.assertRaisesRegex(RuntimeError, "Invalid EUR conversion"):
            self.convert(["2026-10-23"], ["2026-10-23"], [0.0])

    def test_eur_prices_are_unchanged(self):
        part = pd.DataFrame({"date": ["2026-10-23"], "close_native": [42.0], "quote_currency": ["EUR"]})
        with patch.object(market, "download_batch", side_effect=AssertionError("No FX needed")):
            self.assertEqual(market.normalise_to_eur([part], "7d")[0].close_eur.iloc[0], 42.0)
