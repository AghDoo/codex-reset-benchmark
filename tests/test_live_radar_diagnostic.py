from __future__ import annotations

import json
from pathlib import Path
import re
import unittest

from codex_reset_benchmark.collectors import _visible_html_text, collect_source
from codex_reset_benchmark.http import HttpClient


ROOT = Path(__file__).resolve().parents[1]


class LiveRadarDiagnostic(unittest.TestCase):
    def test_dump_sanitized_radar_structure(self) -> None:
        client = HttpClient()
        response = client.get("https://codexresetradar.com/", respect_robots=True)
        raw = response.text
        visible = _visible_html_text(raw)

        def snippets(text: str, needle: str) -> list[str]:
            output: list[str] = []
            lower = text.lower()
            start = 0
            while len(output) < 3:
                pos = lower.find(needle.lower(), start)
                if pos < 0:
                    break
                chunk = text[max(0, pos - 120): pos + 220]
                output.append(" ".join(chunk.split()))
                start = pos + len(needle)
            return output

        payload = {
            "status": response.status,
            "url": response.url,
            "raw_len": len(raw),
            "visible_len": len(visible),
            "raw_has_next_48h": "next 48h" in raw.lower(),
            "raw_has_reset_chance": "reset chance" in raw.lower(),
            "visible_has_next_48h": "next 48h" in visible.lower(),
            "visible_has_reset_chance": "reset chance" in visible.lower(),
            "raw_percent_tokens": re.findall(r"\b\d{1,3}%", raw)[:20],
            "visible_percent_tokens": re.findall(r"\b\d{1,3}\s*%", visible)[:20],
            "visible_48_snippets": snippets(visible, "48"),
        }
        print("RADAR_DIAGNOSTIC=" + json.dumps(payload, ensure_ascii=False))

        registry = json.loads((ROOT / "data" / "sources.json").read_text(encoding="utf-8"))
        source = next(item for item in registry["sources"] if item["id"] == "codex-reset-radar")
        snapshot = collect_source(source, client)
        print("RADAR_FORECAST=" + json.dumps(snapshot.forecasts, sort_keys=True))
        self.assertIn("48h", snapshot.forecasts)


if __name__ == "__main__":
    unittest.main()
