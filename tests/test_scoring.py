from __future__ import annotations

from datetime import datetime, timedelta, timezone
import unittest

from codex_reset_benchmark.score_engine import score_archive


class ScoringTests(unittest.TestCase):
    def test_common_checkpoint_brier_and_outcomes(self) -> None:
        sources = [{"id": "a", "name": "A", "url": "https://a.test", "enabled": True}]
        snapshots = [
            {
                "snapshot_id": "s1",
                "source_id": "a",
                "observed_at": "2026-08-01T00:00:00Z",
                "forecasts": {"24h": 0.8, "48h": 0.6},
            },
            {
                "snapshot_id": "s2",
                "source_id": "a",
                "observed_at": "2026-08-01T06:00:00Z",
                "forecasts": {"24h": 0.2, "48h": 0.4},
            },
        ]
        events = [{"id": "e1", "status": "confirmed", "occurred_at": "2026-08-01T12:00:00Z"}]
        result = score_archive(snapshots, events, sources, as_of=datetime(2026, 8, 4, 0, 0, tzinfo=timezone.utc))
        cases = result["sources"]["a"]["24h"]["cases"]
        first = next(case for case in cases if case["checkpoint"] == "2026-08-01T00:00:00Z")
        second = next(case for case in cases if case["checkpoint"] == "2026-08-01T06:00:00Z")
        self.assertEqual(first["outcome"], 1)
        self.assertEqual(second["outcome"], 1)
        self.assertEqual(len(cases), 3)
        self.assertAlmostEqual(result["sources"]["a"]["24h"]["brier"], (0.04 + 0.64 + 0.04) / 3, places=6)

    def test_forecast_older_than_six_hours_is_not_scored(self) -> None:
        sources = [{"id": "a", "name": "A", "url": "https://a.test", "enabled": True}]
        snapshots = [{"snapshot_id": "s1", "source_id": "a", "observed_at": "2026-08-01T00:00:00Z", "forecasts": {"24h": 0.5}}]
        result = score_archive(snapshots, [], sources, as_of=datetime(2026, 8, 3, 12, 0, tzinfo=timezone.utc))
        checkpoints = [case["checkpoint"] for case in result["sources"]["a"]["24h"]["cases"]]
        self.assertIn("2026-08-01T00:00:00Z", checkpoints)
        self.assertIn("2026-08-01T06:00:00Z", checkpoints)
        self.assertNotIn("2026-08-01T12:00:00Z", checkpoints)

    def test_rank_requires_minimum_samples(self) -> None:
        sources = [{"id": "a", "name": "A", "url": "https://a.test", "enabled": True}]
        snapshots = [{"snapshot_id": "s1", "source_id": "a", "observed_at": "2026-08-01T00:00:00Z", "forecasts": {"24h": 0.5}}]
        result = score_archive(snapshots, [], sources, as_of=datetime(2026, 8, 2, 12, 0, tzinfo=timezone.utc))
        self.assertFalse(result["rankings"]["24h"][0]["eligible"])
        self.assertIsNone(result["rankings"]["24h"][0]["rank"])

    def test_availability_starts_when_horizon_first_appears(self) -> None:
        as_of = datetime(2026, 8, 4, 12, tzinfo=timezone.utc)
        snapshots = [
            {"snapshot_id": "s0", "source_id": "site-a", "observed_at": "2026-08-01T00:00:00Z", "forecasts": {"48h": 0.2}},
            {"snapshot_id": "s1", "source_id": "site-a", "observed_at": "2026-08-02T00:00:00Z", "forecasts": {"24h": 0.3, "48h": 0.2}},
            {"snapshot_id": "s2", "source_id": "site-a", "observed_at": "2026-08-02T06:00:00Z", "forecasts": {"24h": 0.4, "48h": 0.2}},
        ]
        result = score_archive(snapshots, [], [{"id": "site-a", "name": "A", "url": "https://example.com"}], as_of=as_of)
        metrics = result["sources"]["site-a"]["24h"]
        self.assertEqual(metrics["samples"], 3)
        self.assertAlmostEqual(metrics["availability"], 3 / 7, places=6)

    def test_five_hour_horizon_is_scored_with_one_hour_freshness(self) -> None:
        sources = [{"id": "a", "name": "A", "url": "https://a.test", "enabled": True}]
        snapshots = [{"snapshot_id": "s1", "source_id": "a", "observed_at": "2026-08-01T00:00:00Z", "forecasts": {"5h": 0.7}}]
        events = [{"id": "e1", "status": "confirmed", "occurred_at": "2026-08-01T04:00:00Z"}]
        result = score_archive(snapshots, events, sources, as_of=datetime(2026, 8, 2, 0, tzinfo=timezone.utc))
        cases = result["sources"]["a"]["5h"]["cases"]
        self.assertEqual(len(cases), 1)
        self.assertEqual(cases[0]["outcome"], 1)
        self.assertAlmostEqual(result["sources"]["a"]["5h"]["brier"], 0.09, places=6)

    def test_ground_truth_review_time_bounds_resolution(self) -> None:
        sources = [{"id": "a", "name": "A", "url": "https://a.test", "enabled": True}]
        snapshots = [
            {"snapshot_id": "s1", "source_id": "a", "observed_at": "2026-08-01T00:00:00Z", "forecasts": {"24h": 0.5}},
            {"snapshot_id": "s2", "source_id": "a", "observed_at": "2026-08-01T06:00:00Z", "forecasts": {"24h": 0.5}},
        ]
        result = score_archive(
            snapshots,
            [],
            sources,
            as_of=datetime(2026, 8, 4, 0, 0, tzinfo=timezone.utc),
            ground_truth_reviewed_at=datetime(2026, 8, 2, 0, 0, tzinfo=timezone.utc),
        )
        checkpoints = [case["checkpoint"] for case in result["sources"]["a"]["24h"]["cases"]]
        self.assertEqual(checkpoints, ["2026-08-01T00:00:00Z"])
        self.assertEqual(result["ground_truth_reviewed_at"], "2026-08-02T00:00:00Z")


    def test_ranked_sources_use_identical_common_cases(self) -> None:
        sources = [
            {"id": "a", "name": "A", "url": "https://a.test", "enabled": True},
            {"id": "b", "name": "B", "url": "https://b.test", "enabled": True},
        ]
        start = datetime(2026, 8, 1, 0, 0, tzinfo=timezone.utc)
        snapshots = []
        for index in range(12):
            observed = start + timedelta(hours=6 * index)
            observed_at = observed.isoformat().replace("+00:00", "Z")
            snapshots.append(
                {
                    "snapshot_id": f"a-{index}",
                    "source_id": "a",
                    "observed_at": observed_at,
                    "forecasts": {"24h": 0.4},
                }
            )
            if index not in {3, 4}:
                snapshots.append(
                    {
                        "snapshot_id": f"b-{index}",
                        "source_id": "b",
                        "observed_at": observed_at,
                        "forecasts": {"24h": 0.6},
                    }
                )

        events = [{"id": "e1", "status": "confirmed", "occurred_at": "2026-08-02T01:00:00Z"}]
        result = score_archive(
            snapshots,
            events,
            sources,
            as_of=datetime(2026, 8, 4, 18, 0, tzinfo=timezone.utc),
        )

        metrics_a = result["sources"]["a"]["24h"]
        metrics_b = result["sources"]["b"]["24h"]
        self.assertEqual(result["methodology_version"], "1.1.0")
        self.assertEqual(result["comparison_mode"], "common_case_intersection")
        self.assertEqual(result["ranking_cohorts"]["24h"], ["a", "b"])
        self.assertEqual(result["common_checkpoint_counts"]["24h"], 11)
        self.assertEqual(metrics_a["coverage_samples"], 12)
        self.assertEqual(metrics_b["coverage_samples"], 11)
        self.assertEqual(metrics_a["samples"], 11)
        self.assertEqual(metrics_b["samples"], 11)
        self.assertEqual(
            [case["checkpoint"] for case in metrics_a["cases"]],
            [case["checkpoint"] for case in metrics_b["cases"]],
        )


if __name__ == "__main__":
    unittest.main()
