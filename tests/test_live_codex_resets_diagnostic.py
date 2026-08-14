from __future__ import annotations

import json
import re
import unittest

from codex_reset_benchmark.http import AccessDenied, FetchError, HttpClient


BASE = "https://codex-resets.com"


class LiveCodexResetsDiagnostic(unittest.TestCase):
    def test_discover_public_api(self) -> None:
        client = HttpClient(max_bytes=2_000_000)
        result: dict[str, object] = {}

        docs = client.get(f"{BASE}/api/docs", respect_robots=True)
        result["docs_status"] = docs.status
        result["docs_len"] = len(docs.text)
        result["docs_api_paths"] = sorted(set(re.findall(r"/api/[A-Za-z0-9_./?={}-]+", docs.text)))[:80]

        specs: dict[str, object] = {}
        for path in ("/api/openapi.json", "/openapi.json", "/api/docs/openapi.json", "/api/swagger.json"):
            try:
                response = client.get(f"{BASE}{path}", respect_robots=True)
            except (AccessDenied, FetchError) as exc:
                specs[path] = {"error": str(exc)[:160]}
                continue
            entry: dict[str, object] = {"status": response.status, "len": len(response.text)}
            try:
                payload = json.loads(response.text)
            except json.JSONDecodeError:
                entry["json"] = False
            else:
                entry["json"] = True
                entry["top_level"] = sorted(payload.keys()) if isinstance(payload, dict) else type(payload).__name__
                if isinstance(payload, dict) and isinstance(payload.get("paths"), dict):
                    entry["paths"] = sorted(payload["paths"].keys())
            specs[path] = entry
        result["spec_candidates"] = specs

        homepage = client.get(f"{BASE}/", respect_robots=True)
        result["homepage_has_reset_watch"] = "Reset watch" in homepage.text
        result["homepage_has_reset_chance"] = "Reset chance" in homepage.text
        result["homepage_api_paths"] = sorted(set(re.findall(r"/api/[A-Za-z0-9_./?={}-]+", homepage.text)))[:80]

        print("CODEX_RESETS_DIAGNOSTIC=" + json.dumps(result, sort_keys=True))
        self.assertEqual(docs.status, 200)
        self.assertEqual(homepage.status, 200)


if __name__ == "__main__":
    unittest.main()
