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

    def test_reviewed_ground_truth_includes_recent_hard_resets_and_excludes_banked_grant(self) -> None:
        event_ids = {event["id"] for event in self.payload["events"]}
        excluded = {event["id"]: event for event in self.payload.get("excluded_events", [])}

        self.assertIn("x-2086972802457063486", event_ids)
        self.assertIn("x-2087706104814023111", event_ids)
        self.assertIn("x-2090766694897619318", excluded)
        self.assertEqual(excluded["x-2090766694897619318"]["type"], "banked_reset_grant")
        self.assertGreaterEqual(
            parse_datetime(self.payload["reviewed_at"]),
            parse_datetime(excluded["x-2090766694897619318"]["announced_at"]),
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
