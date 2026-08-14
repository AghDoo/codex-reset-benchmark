from __future__ import annotations

from datetime import datetime, timezone
import json
import unittest

from codex_reset_benchmark.collectors import CollectorError, collect_source
from codex_reset_benchmark.http import HttpResponse


class FakeClient:
    def __init__(self, body: str, url: str = "https://example.test/forecast"):
        self.body = body
        self.url = url

    def get(self, url: str, *, respect_robots: bool = True) -> HttpResponse:
        return HttpResponse(self.url, 200, self.body)


class CollectorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.now = datetime(2026, 8, 13, 14, 17, tzinfo=timezone.utc)

    def test_json_api_normalizes_fraction_probabilities(self) -> None:
        source = {
            "id": "json-source",
            "enabled": True,
            "forecast_url": "https://example.test/api",
            "collector": {
                "type": "json_api",
                "respect_robots": True,
                "probabilities": {
                    "24h": {"path": "probabilities.raw_24h", "unit": "fraction"},
                    "48h": {"path": "probabilities.raw_48h", "unit": "fraction"},
                },
                "source_updated_path": "updated_at",
            },
        }
        body = json.dumps({"probabilities": {"raw_24h": 0.35, "raw_48h": 0.55}, "updated_at": "2026-08-13T14:00:00Z"})
        snapshot = collect_source(source, FakeClient(body), now=self.now)
        self.assertEqual(snapshot.forecasts, {"24h": 0.35, "48h": 0.55})
        self.assertEqual(snapshot.source_updated_at, "2026-08-13T14:00:00Z")

    def test_json_api_rejects_boolean_probability(self) -> None:
        source = {
            "id": "json-source",
            "enabled": True,
            "forecast_url": "https://example.test/api",
            "collector": {
                "type": "json_api",
                "probabilities": {"24h": {"path": "prob24h", "unit": "fraction"}},
            },
        }
        with self.assertRaises(ValueError):
            collect_source(source, FakeClient(json.dumps({"prob24h": True})), now=self.now)

    def test_html_regex_extracts_only_matching_horizons(self) -> None:
        source = {
            "id": "html-source",
            "enabled": True,
            "forecast_url": "https://example.test/",
            "collector": {
                "type": "html_regex",
                "probabilities": {
                    "24h": {"pattern": r"24 hours.*?Final forecast:\s*([0-9.]+)%", "unit": "percent"},
                    "48h": {"pattern": r"48 hours.*?Final forecast:\s*([0-9.]+)%", "unit": "percent"},
                },
            },
        }
        body = "24 hours <span>Final forecast: 78%</span> 48 hours <span>Final forecast: 84%</span>"
        snapshot = collect_source(source, FakeClient(body), now=self.now)
        self.assertEqual(snapshot.forecasts, {"24h": 0.78, "48h": 0.84})

    def test_placeholder_without_horizon_is_not_archived(self) -> None:
        source = {
            "id": "placeholder",
            "enabled": True,
            "forecast_url": "https://example.test/",
            "collector": {
                "type": "html_regex",
                "probabilities": {"24h": {"pattern": r"24h:\s*([0-9.]+)%", "unit": "percent"}},
            },
        }
        with self.assertRaises(CollectorError):
            collect_source(source, FakeClient("Reset chance 0%; 24h —%"), now=self.now)

    def test_stale_json_source_is_rejected(self) -> None:
        source = {
            "id": "stale",
            "enabled": True,
            "forecast_url": "https://example.test/api",
            "collector": {
                "type": "json_api",
                "probabilities": {"24h": {"path": "prob24h", "unit": "percent_or_fraction"}},
                "source_updated_path": "generatedAt",
                "max_source_age_hours": 24,
            },
        }
        body = json.dumps({"prob24h": 30, "generatedAt": "2026-08-10T00:00:00Z"})
        with self.assertRaises(CollectorError):
            collect_source(source, FakeClient(body), now=self.now)


if __name__ == "__main__":
    unittest.main()
