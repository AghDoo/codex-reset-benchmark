from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import unittest

from codex_reset_benchmark.models import parse_datetime
from codex_reset_benchmark.validation import validate_events


ROOT = Path(__file__).resolve().parents[1]


class GroundTruthValidationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.payload = json.loads((ROOT / "data" / "events" / "resets.json").read_text(encoding="utf-8"))

    def test_reviewed_ground_truth_covers_current_hard_resets_and_exclusions(self) -> None:
        event_ids = {event["id"] for event in self.payload["events"]}
        excluded = {event["id"]: event for event in self.payload.get("excluded_events", [])}

        for event_id in (
            "x-2091688655828246890",
            "x-2092311059197808936",
            "x-2093014447833116908",
            "x-2093801758665715784",
            "x-2094252447271366730",
        ):
            self.assertIn(event_id, event_ids)

        self.assertIn("signal-2026-08-19T05:03:48Z", excluded)
        self.assertEqual(excluded["signal-2026-08-19T05:03:48Z"]["type"], "reset_signal_only")
        self.assertIn("x-2090766694897619318", excluded)
        self.assertIn("x-2090964822422949999", excluded)
        self.assertIn("x-2095651088502591861", excluded)
        self.assertIn("x-2096035437299237298", excluded)
        for event_id in (
            "x-2090766694897619318",
            "x-2090964822422949999",
            "x-2095651088502591861",
            "x-2096035437299237298",
        ):
            self.assertTrue(excluded[event_id]["type"].startswith("banked_reset"))

        self.assertGreaterEqual(
            parse_datetime(self.payload["reviewed_at"]),
            parse_datetime("2026-09-07T08:44:00Z"),
        )
        self.assertEqual(validate_events(self.payload), [])

    def test_duplicate_id_across_scoring_and_excluded_events_is_rejected(self) -> None:
        payload = deepcopy(self.payload)
        payload["excluded_events"][0]["id"] = payload["events"][0]["id"]
        errors = validate_events(payload)
        self.assertTrue(any("duplicate excluded event id" in error for error in errors))

    def test_excluded_event_cannot_extend_beyond_review_boundary(self) -> None:
        payload = deepcopy(self.payload)
        payload["reviewed_at"] = "2026-08-20T00:00:00Z"
        errors = validate_events(payload)
        self.assertTrue(any("excluded event" in error and "exceeds reviewed_at" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
