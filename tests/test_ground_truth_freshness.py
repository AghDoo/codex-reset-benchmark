from __future__ import annotations

from datetime import datetime, timezone
import unittest

from codex_reset_benchmark.ground_truth import evaluate_ground_truth_freshness


class GroundTruthFreshnessTests(unittest.TestCase):
    def setUp(self) -> None:
        self.now = datetime(2026, 8, 22, 12, 0, tzinfo=timezone.utc)

    def test_fresh_within_threshold(self) -> None:
        result = evaluate_ground_truth_freshness(
            {"reviewed_at": "2026-08-21T12:00:00Z"},
            now=self.now,
            max_age_hours=36,
        )
        self.assertEqual(result["state"], "fresh")
        self.assertEqual(result["age_hours"], 24.0)

    def test_stale_beyond_threshold(self) -> None:
        result = evaluate_ground_truth_freshness(
            {"reviewed_at": "2026-08-20T23:59:59Z"},
            now=self.now,
            max_age_hours=36,
        )
        self.assertEqual(result["state"], "stale")
        self.assertGreater(result["age_hours"], 36.0)

    def test_exact_threshold_is_still_fresh(self) -> None:
        result = evaluate_ground_truth_freshness(
            {"reviewed_at": "2026-08-21T00:00:00Z"},
            now=self.now,
            max_age_hours=36,
        )
        self.assertEqual(result["state"], "fresh")

    def test_future_review_boundary_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            evaluate_ground_truth_freshness(
                {"reviewed_at": "2026-08-22T12:00:01Z"},
                now=self.now,
                max_age_hours=36,
            )

    def test_invalid_threshold_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            evaluate_ground_truth_freshness(
                {"reviewed_at": "2026-08-22T00:00:00Z"},
                now=self.now,
                max_age_hours=True,
            )


if __name__ == "__main__":
    unittest.main()
