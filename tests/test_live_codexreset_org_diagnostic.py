from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import unittest

from codex_reset_benchmark.collectors import collect_source
from codex_reset_benchmark.http import HttpClient


ROOT = Path(__file__).resolve().parents[1]


class LiveCodexResetOrgDiagnostic(unittest.TestCase):
    def test_live_registered_collector(self) -> None:
        registry = json.loads((ROOT / "data" / "sources.json").read_text(encoding="utf-8"))
        source = next(item for item in registry["sources"] if item["id"] == "codexreset-org")
        snapshot = collect_source(source, HttpClient(), now=datetime.now(timezone.utc))
        print("CODEXRESET_ORG_LIVE=" + json.dumps({
            "forecasts": snapshot.forecasts,
            "source_url": snapshot.source_url,
            "configured_max_response_bytes": source["collector"].get("max_response_bytes"),
        }, sort_keys=True))
        self.assertEqual(set(snapshot.forecasts), {"24h", "48h"})


if __name__ == "__main__":
    unittest.main()
