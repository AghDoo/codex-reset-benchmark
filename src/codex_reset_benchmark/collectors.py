from __future__ import annotations

from datetime import datetime, timezone
from html.parser import HTMLParser
import hashlib
import json
import re
from typing import Any

from .http import HttpClient
from .models import (
    COLLECTOR_VERSION,
    ForecastSnapshot,
    isoformat_z,
    normalize_probability,
    parse_datetime,
    stable_snapshot_id,
)


class CollectorError(RuntimeError):
    pass


class _VisibleTextParser(HTMLParser):
    """Extract human-visible text while ignoring script/style/template payloads."""

    _HIDDEN_TAGS = {"script", "style", "noscript", "template"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._hidden_depth = 0
        self._parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() in self._HIDDEN_TAGS:
            self._hidden_depth += 1

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() in self._HIDDEN_TAGS and self._hidden_depth:
            self._hidden_depth -= 1

    def handle_data(self, data: str) -> None:
        if not self._hidden_depth and data.strip():
            self._parts.append(data)

    def text(self) -> str:
        return " ".join(" ".join(self._parts).split())


def _visible_html_text(raw: str) -> str:
    parser = _VisibleTextParser()
    try:
        parser.feed(raw)
        parser.close()
    except Exception as exc:
        raise CollectorError("source HTML could not be normalized") from exc
    return parser.text()


def nested_get(payload: Any, dotted_path: str) -> Any:
    current = payload
    for part in dotted_path.split("."):
        if isinstance(current, dict) and part in current:
            current = current[part]
        else:
            raise CollectorError(f"missing JSON path: {dotted_path}")
    return current


def _validate_source_freshness(source: dict[str, Any], source_updated_at: str | None, now: datetime) -> None:
    max_age = source.get("collector", {}).get("max_source_age_hours")
    if not max_age or not source_updated_at:
        return
    updated = parse_datetime(source_updated_at)
    age_hours = (now.astimezone(timezone.utc) - updated).total_seconds() / 3600
    if age_hours > float(max_age):
        raise CollectorError(f"source output is stale ({age_hours:.1f}h > {max_age}h)")


def collect_source(source: dict[str, Any], client: HttpClient, now: datetime | None = None) -> ForecastSnapshot:
    if not source.get("enabled", False):
        raise CollectorError("source is disabled")
    now = now or datetime.now(timezone.utc)
    config = source.get("collector") or {}
    collector_type = config.get("type")
    if collector_type not in {"json_api", "html_regex"}:
        raise CollectorError(f"unsupported collector type: {collector_type}")
    url = source.get("forecast_url") or source.get("url")
    if not isinstance(url, str) or not url.startswith(("https://", "http://")):
        raise CollectorError("source forecast_url must be public HTTP(S)")

    response = client.get(url, respect_robots=bool(config.get("respect_robots", True)))
    raw = response.text
    raw_sha256 = hashlib.sha256(raw.encode("utf-8")).hexdigest()
    forecasts: dict[str, float] = {}
    source_updated_at: str | None = None

    if collector_type == "json_api":
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise CollectorError("source did not return valid JSON") from exc
        for horizon, rule in (config.get("probabilities") or {}).items():
            value = nested_get(payload, rule["path"])
            forecasts[horizon] = normalize_probability(value, rule.get("unit", "fraction"))
        updated_path = config.get("source_updated_path")
        if updated_path:
            value = nested_get(payload, updated_path)
            if value is not None:
                source_updated_at = isoformat_z(parse_datetime(str(value)))
    else:
        visible_text = _visible_html_text(raw)
        for horizon, rule in (config.get("probabilities") or {}).items():
            match = re.search(rule["pattern"], visible_text, flags=re.IGNORECASE | re.DOTALL)
            if not match:
                continue
            forecasts[horizon] = normalize_probability(match.group(1), rule.get("unit", "percent"))

    if not forecasts:
        raise CollectorError("no forecast values were extracted; placeholders are not archived")

    _validate_source_freshness(source, source_updated_at, now)
    observed_at = isoformat_z(now)
    snapshot_id = stable_snapshot_id(source["id"], observed_at, raw_sha256, forecasts)
    snapshot = ForecastSnapshot(
        snapshot_id=snapshot_id,
        source_id=source["id"],
        observed_at=observed_at,
        source_updated_at=source_updated_at,
        forecasts=forecasts,
        source_url=response.url,
        collector_type=collector_type,
        collector_version=COLLECTOR_VERSION,
        raw_sha256=raw_sha256,
    )
    snapshot.validate()
    return snapshot
