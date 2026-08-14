from __future__ import annotations

import json
import re
import unittest

from codex_reset_benchmark.collectors import _visible_html_text
from codex_reset_benchmark.http import HttpClient


class LiveRadarDiagnostic(unittest.TestCase):
    def test_dump_sanitized_radar_structure(self) -> None:
        response = HttpClient().get("https://codexresetradar.com/", respect_robots=True)
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
            "raw_has_next_f": "__next_f" in raw.lower(),
            "visible_has_next_48h": "next 48h" in visible.lower(),
            "visible_has_reset_chance": "reset chance" in visible.lower(),
            "raw_percent_tokens": re.findall(r"\b\d{1,3}%", raw)[:20],
            "visible_percent_tokens": re.findall(r"\b\d{1,3}%", visible)[:20],
            "raw_48_snippets": snippets(raw, "48"),
            "visible_48_snippets": snippets(visible, "48"),
            "raw_chance_snippets": snippets(raw, "chance"),
        }
        print("RADAR_DIAGNOSTIC=" + json.dumps(payload, ensure_ascii=False))
        self.assertEqual(response.status, 200)


if __name__ == "__main__":
    unittest.main()
