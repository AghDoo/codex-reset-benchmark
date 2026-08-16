from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import unittest

from codex_reset_benchmark.collectors import CollectorError, NoActiveForecast, collect_source
from codex_reset_benchmark.http import HttpResponse


ROOT = Path(__file__).resolve().parents[1]


class FakeClient:
    def __init__(self, body: str, url: str = "https://example.test/forecast"):
        self.body = body
        self.url = url
        self.last_max_bytes: int | None = None

    def get(self, url: str, *, respect_robots: bool = True, max_bytes: int | None = None) -> HttpResponse:
        self.last_max_bytes = max_bytes
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

    def test_registered_willquota_json_source_schema(self) -> None:
        registry = json.loads((ROOT / "data" / "sources.json").read_text(encoding="utf-8"))
        source = next(item for item in registry["sources"] if item["id"] == "willcodexquotareset")
        body = json.dumps({"fetchedAt": "2026-08-13T14:00:00Z", "forecast": {"score": 34}})
        snapshot = collect_source(source, FakeClient(body, source["forecast_url"]), now=self.now)
        self.assertEqual(snapshot.forecasts, {"48h": 0.34})
        self.assertEqual(snapshot.source_updated_at, "2026-08-13T14:00:00Z")

    def test_registered_codex_resets_watch_schema(self) -> None:
        registry = json.loads((ROOT / "data" / "sources.json").read_text(encoding="utf-8"))
        source = next(item for item in registry["sources"] if item["id"] == "codex-resets-com")
        body = json.dumps({
            "data": {
                "active_watch": {
                    "level": "strong",
                    "reset_chance_percent": 70,
                    "forecast_window": "by end of Thursday",
                    "observed_at": "2026-08-13T13:30:00Z",
                    "expires_at": "2026-08-14T23:59:59Z",
                    "text": "public signal",
                    "source": {"type": "x_post", "author": "thsottiaux", "url": "https://x.com/thsottiaux/status/1"},
                }
            },
            "meta": {"api_version": "v1", "generated_at": "2026-08-13T14:17:00Z"},
        })
        snapshot = collect_source(source, FakeClient(body, source["forecast_url"]), now=self.now)
        self.assertEqual(snapshot.forecasts, {})
        self.assertEqual(snapshot.source_updated_at, "2026-08-13T13:30:00Z")
        self.assertEqual(snapshot.window_forecast, {
            "probability": 0.7,
            "forecast_window": "by end of Thursday",
            "observed_at": "2026-08-13T13:30:00Z",
            "expires_at": "2026-08-14T23:59:59Z",
            "level": "strong",
        })

    def test_codex_resets_without_active_watch_is_idle(self) -> None:
        registry = json.loads((ROOT / "data" / "sources.json").read_text(encoding="utf-8"))
        source = next(item for item in registry["sources"] if item["id"] == "codex-resets-com")
        body = json.dumps({"data": {"active_watch": None}, "meta": {"api_version": "v1", "generated_at": "2026-08-13T14:17:00Z"}})
        with self.assertRaises(NoActiveForecast):
            collect_source(source, FakeClient(body, source["forecast_url"]), now=self.now)

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

    def test_html_regex_uses_visible_text_and_ignores_script_placeholders(self) -> None:
        source = {
            "id": "html-source",
            "enabled": True,
            "forecast_url": "https://example.test/",
            "collector": {
                "type": "html_regex",
                "probabilities": {
                    "24h": {"pattern": r"Reset\s*probability\s*([0-9.]+)%.*?Next\s*24\s*(?:h|hours?)", "unit": "percent"},
                },
            },
        }
        body = """
        <script>Reset probability 0% Next 24h</script>
        <section><h2>Reset <em>probability</em></h2><strong>40%</strong></section>
        <div>Cooldown watch · <span>Next <b>24h</b> public-signal likelihood</span></div>
        """
        snapshot = collect_source(source, FakeClient(body), now=self.now)
        self.assertEqual(snapshot.forecasts, {"24h": 0.4})

    def test_registered_codexreset_org_uses_scoped_response_cap(self) -> None:
        registry = json.loads((ROOT / "data" / "sources.json").read_text(encoding="utf-8"))
        source = next(item for item in registry["sources"] if item["id"] == "codexreset-org")
        body = (
            "<div>24 hours <span>0%</span><b>Final forecast: 18%</b></div>"
            "<div>48 hours <span>0%</span><b>Final forecast: 34%</b></div>"
        )
        client = FakeClient(body, source["forecast_url"])
        snapshot = collect_source(source, client, now=self.now)
        self.assertEqual(snapshot.forecasts, {"24h": 0.18, "48h": 0.34})
        self.assertEqual(client.last_max_bytes, 1_500_000)

    def test_registered_html_sources_match_current_visible_copy(self) -> None:
        registry = json.loads((ROOT / "data" / "sources.json").read_text(encoding="utf-8"))
        sources = {source["id"]: source for source in registry["sources"]}
        cases = {
            "codexreset-org": (
                "<div>24 hours <span>0%</span><b>Final forecast: 78%</b></div>"
                "<div>48 hours <span>0%</span><b>Final forecast: 84%</b></div>",
                {"24h": 0.78, "48h": 0.84},
            ),
            "codex-reset-radar": (
                "<div>Next <span>48h</span> reset chance <strong>34<!-- -->%</strong> WATCH · auto-updated</div>",
                {"48h": 0.34},
            ),
            "codexreset-today": (
                "<h2>Reset probability</h2><strong>40%</strong><div>Cooldown watch · Next 24h public-signal likelihood</div>",
                {"24h": 0.4},
            ),
        }
        for source_id, (body, expected) in cases.items():
            with self.subTest(source_id=source_id):
                snapshot = collect_source(sources[source_id], FakeClient(body, sources[source_id]["forecast_url"]), now=self.now)
                self.assertEqual(snapshot.forecasts, expected)

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
