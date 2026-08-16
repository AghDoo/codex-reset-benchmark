from __future__ import annotations

import json
import re
import unittest

from codex_reset_benchmark.http import HttpClient


BASE = "https://codexreset.org"


class LiveCodexResetOrgDiagnostic(unittest.TestCase):
    def test_discover_smaller_forecast_source(self) -> None:
        client = HttpClient(max_bytes=3_000_000)
        response = client.get(f"{BASE}/", respect_robots=True)
        raw = response.text

        api_paths = sorted(set(re.findall(r"[\"'](/api/[^\"'?# ]+)", raw)))
        json_paths = sorted(set(re.findall(r"[\"'](/[^\"'?# ]+\.json(?:\?[^\"']*)?)", raw)))
        script_paths = sorted(set(re.findall(r"<script[^>]+src=[\"']([^\"']+)[\"']", raw, flags=re.I)))
        same_origin_scripts = [path for path in script_paths if path.startswith("/")]

        visible_markers = {
            "has_24h": bool(re.search(r"24\s*hours", raw, flags=re.I)),
            "has_48h": bool(re.search(r"48\s*hours", raw, flags=re.I)),
            "has_final_forecast": "Final forecast" in raw,
        }
        print("CODEXRESET_ORG_DIAGNOSTIC=" + json.dumps({
            "response_chars": len(raw),
            "api_paths": api_paths[:50],
            "json_paths": json_paths[:50],
            "same_origin_scripts": same_origin_scripts[:30],
            "visible_markers": visible_markers,
        }, sort_keys=True))

        self.assertEqual(response.status, 200)
        self.assertTrue(visible_markers["has_final_forecast"])


if __name__ == "__main__":
    unittest.main()
