from __future__ import annotations

from html.parser import HTMLParser
import json
import re
import unittest
from urllib.parse import urljoin, urlparse

from codex_reset_benchmark.http import AccessDenied, FetchError, HttpClient


TARGET = "https://www.willcodexquotareset.com/"
FORECAST_API = urljoin(TARGET, "/api/forecast")


class _ScriptParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.sources: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() != "script":
            return
        src = dict(attrs).get("src")
        if src:
            self.sources.append(src)


def _candidate_scalars(payload: object, prefix: str = "") -> dict[str, object]:
    output: dict[str, object] = {}
    if isinstance(payload, dict):
        for key, value in payload.items():
            path = f"{prefix}.{key}" if prefix else str(key)
            if isinstance(value, (dict, list)):
                output.update(_candidate_scalars(value, path))
            elif any(token in str(key).lower() for token in ("forecast", "score", "likelihood", "probab", "percent", "updated", "generated", "checked", "timestamp", "horizon")):
                output[path] = value
    elif isinstance(payload, list):
        for index, value in enumerate(payload[:8]):
            output.update(_candidate_scalars(value, f"{prefix}[{index}]"))
    return output


class LiveWillQuotaDiagnostic(unittest.TestCase):
    def test_find_public_forecast_api_schema(self) -> None:
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
        path_hits: set[str] = set()
        for match in endpoint_re.finditer(raw):
            path_hits.add(match.group("path"))

        for script_url in scripts[:16]:
            try:
                script = client.get(script_url, respect_robots=True)
            except (AccessDenied, FetchError):
                continue
            for match in endpoint_re.finditer(script.text):
                path_hits.add(match.group("path"))

        api_response = client.get(FORECAST_API, respect_robots=True)
        api_payload = json.loads(api_response.text)
        if isinstance(api_payload, dict):
            top_level = sorted(api_payload.keys())
        else:
            top_level = [type(api_payload).__name__]

        diagnostic = {
            "page_status": response.status,
            "page_has_placeholder": "--%" in raw or "Reading the signals" in raw,
            "api_or_data_paths": sorted(path_hits),
            "forecast_api_status": api_response.status,
            "forecast_api_url": api_response.url,
            "forecast_api_len": len(api_response.text),
            "forecast_api_top_level": top_level,
            "forecast_candidate_scalars": _candidate_scalars(api_payload),
        }
        print("WILLQUOTA_DIAGNOSTIC=" + json.dumps(diagnostic, ensure_ascii=False, sort_keys=True))
        self.assertEqual(api_response.status, 200)
        self.assertIsInstance(api_payload, dict)


if __name__ == "__main__":
    unittest.main()
