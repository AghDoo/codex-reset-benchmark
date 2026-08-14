from __future__ import annotations

from html.parser import HTMLParser
import json
import re
import unittest
from urllib.parse import urljoin, urlparse

from codex_reset_benchmark.http import AccessDenied, FetchError, HttpClient


TARGET = "https://www.willcodexquotareset.com/"


class _ScriptParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.sources: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() != "script":
            return
        values = dict(attrs)
        src = values.get("src")
        if src:
            self.sources.append(src)


class LiveWillQuotaDiagnostic(unittest.TestCase):
    def test_find_public_data_paths(self) -> None:
        client = HttpClient(max_bytes=2_000_000)
        response = client.get(TARGET, respect_robots=True)
        raw = response.text

        parser = _ScriptParser()
        parser.feed(raw)
        parser.close()

        host = urlparse(TARGET).netloc
        scripts = []
        for src in parser.sources:
            absolute = urljoin(TARGET, src)
            if urlparse(absolute).netloc == host and absolute not in scripts:
                scripts.append(absolute)

        endpoint_re = re.compile(r"(?P<q>['\"])(?P<path>/(?:api|data)/[^'\"\\\s]{0,160})(?P=q)")
        fetch_re = re.compile(r"fetch\(\s*['\"]([^'\"]+)['\"]")
        path_hits: set[str] = set()
        fetch_hits: set[str] = set()
        scanned: list[dict[str, object]] = []

        for match in endpoint_re.finditer(raw):
            path_hits.add(match.group("path"))
        for match in fetch_re.finditer(raw):
            fetch_hits.add(match.group(1))

        for script_url in scripts[:16]:
            try:
                script = client.get(script_url, respect_robots=True)
            except (AccessDenied, FetchError) as exc:
                scanned.append({"url": script_url, "error": str(exc)[:160]})
                continue
            text = script.text
            for match in endpoint_re.finditer(text):
                path_hits.add(match.group("path"))
            for match in fetch_re.finditer(text):
                fetch_hits.add(match.group(1))
            keywords = [word for word in ("forecast", "likelihood", "score", "signals", "history") if word in text.lower()]
            scanned.append({"url": script_url, "len": len(text), "keywords": keywords})

        payload = {
            "status": response.status,
            "url": response.url,
            "raw_len": len(raw),
            "script_count": len(scripts),
            "scripts_scanned": scanned,
            "api_or_data_paths": sorted(path_hits),
            "literal_fetch_targets": sorted(fetch_hits),
            "raw_contains_placeholder": "--%" in raw or "Reading the signals" in raw,
        }
        print("WILLQUOTA_DIAGNOSTIC=" + json.dumps(payload, ensure_ascii=False))
        self.assertEqual(response.status, 200)


if __name__ == "__main__":
    unittest.main()
