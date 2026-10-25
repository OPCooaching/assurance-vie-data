import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import compute_academic_strategies as academic
from record_pipeline_failure import record_failure


class CatalogueAndFailureTests(unittest.TestCase):
    def test_new_catalogue_cannot_change_past_momentum(self):
        dates = pd.bdate_range("2024-01-01", "2026-10-23")
        px = pd.DataFrame({"old": np.linspace(100, 150, len(dates)),
                           "new": np.linspace(100, 1000, len(dates)),
                           "cash": 100.0}, index=dates)
        old = pd.DataFrame({"asset_id": ["old", "cash"], "category": ["ETF", "ETF"]})
        new = pd.concat([old, pd.DataFrame({"asset_id": ["new"], "category": ["ETF"]})])
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            with patch.object(academic, "UNIVERSE_HISTORY", root):
                expected, _ = academic.momentum_curve(px, old, "cash", pd.Timestamp("2026-09-09"), 1)
                old.to_csv(root / "2024-01-01.csv", index=False)
                new.to_csv(root / "2026-10-23.csv", index=False)
                actual, _ = academic.momentum_curve(px, new, "cash", pd.Timestamp("2026-09-09"), 1)
                pd.testing.assert_series_equal(expected, actual)
                self.assertNotIn("new", set(academic.universe_on("2026-10-22", new).asset_id))
                self.assertIn("new", set(academic.universe_on("2026-10-23", new).asset_id))

    def test_failure_closes_running_review_and_keeps_last_data_date(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "review.json"
            path.write_text(json.dumps({"status": "in_progress", "review_date": "2026-10-24",
                                        "data_as_of_date": "2026-10-19"}))
            record_failure(path)
            result = json.loads(path.read_text())
            self.assertEqual(result["status"], "failed")
            self.assertEqual(result["data_as_of_date"], "2026-10-19")
            self.assertEqual(result["review_date"], "2026-10-24")

    def test_later_refresh_failure_does_not_rewrite_completed_review(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "review.json"
            path.write_text(json.dumps({"status": "completed", "review_date": "2026-10-17"}))
            record_failure(path)
            result = json.loads(path.read_text())
            self.assertEqual(result["status"], "completed")
            self.assertEqual(result["data_update_status"], "failed")
