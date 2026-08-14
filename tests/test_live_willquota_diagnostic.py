from __future__ import annotations

import json
import unittest

from codex_reset_benchmark.collectors import collect_source
from codex_reset_benchmark.http import HttpClient


SOURCE = {
    "id": "willcodexquotareset",
    "name": "Will Codex Quota Reset",
    "url": "https://www.willcodexquotareset.com/",
    "forecast_url": "https://www.willcodexquotareset.com/api/forecast",
    "enabled": True,
    "collector": {
        "type": "json_api",
        "respect_robots": True,
        "probabilities": {
            "48h": {"path": "forecast.score", "unit": "percent"},
        },
        "source_updated_path": "fetchedAt",
        "max_source_age_hours": 6,
    },
}


class LiveWillQuotaDiagnostic(unittest.TestCase):
    def test_live_forecast_works_with_production_collector(self) -> None:
        snapshot = collect_source(SOURCE, HttpClient(max_bytes=2_000_000))
        print(
            "WILLQUOTA_LIVE="
            + json.dumps(
                {
                    "forecasts": snapshot.forecasts,
                    "source_updated_at": snapshot.source_updated_at,
                    "source_url": snapshot.source_url,
                },
                sort_keys=True,
            )
        )
        self.assertIn("48h", snapshot.forecasts)
        self.assertGreaterEqual(snapshot.forecasts["48h"], 0.0)
        self.assertLessEqual(snapshot.forecasts["48h"], 1.0)
        self.assertIsNotNone(snapshot.source_updated_at)


if __name__ == "__main__":
    unittest.main()
