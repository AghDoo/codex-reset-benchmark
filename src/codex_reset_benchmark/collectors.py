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


class NoActiveForecast(CollectorError):
    """The source is healthy but currently publishes no active forecast."""


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
    if collector_type not in {"json_api", "html_regex", "status_watch_json"}:
        raise CollectorError(f"unsupported collector type: {collector_type}")
    url = source.get("forecast_url") or source.get("url")
    if not isinstance(url, str) or not url.startswith(("https://", "http://")):
        raise CollectorError("source forecast_url must be public HTTP(S)")

    response = client.get(url, respect_robots=bool(config.get("respect_robots", True)))
    raw = response.text
    raw_sha256 = hashlib.sha256(raw.encode("utf-8")).hexdigest()
    forecasts: dict[str, float] = {}
    window_forecast: dict[str, Any] | None = None
    source_updated_at: str | None = None

    if collector_type in {"json_api", "status_watch_json"}:
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise CollectorError("source did not return valid JSON") from exc

        if collector_type == "json_api":
            for horizon, rule in (config.get("probabilities") or {}).items():
                value = nested_get(payload, rule["path"])
                forecasts[horizon] = normalize_probability(value, rule.get("unit", "fraction"))
            updated_path = config.get("source_updated_path")
            if updated_path:
                value = nested_get(payload, updated_path)
                if value is not None:
                    source_updated_at = isoformat_z(parse_datetime(str(value)))
        else:
            watch = nested_get(payload, config["watch_path"])
            if watch is None:
                raise NoActiveForecast("source is healthy; no active forecast watch")
            if not isinstance(watch, dict):
                raise CollectorError("active forecast watch must be a JSON object")

            probability_rule = config["probability"]
            probability_value = nested_get(watch, probability_rule["path"])
            probability = (
                None
                if probability_value is None
                else normalize_probability(probability_value, probability_rule.get("unit", "fraction"))
            )
            forecast_window = str(nested_get(watch, config["forecast_window_path"])).strip()
            watch_observed_at = isoformat_z(parse_datetime(str(nested_get(watch, config["observed_at_path"]))))
            expires_at = isoformat_z(parse_datetime(str(nested_get(watch, config["expires_at_path"]))))
            if parse_datetime(expires_at) <= now.astimezone(timezone.utc):
                raise CollectorError("active forecast watch is already expired")
            level = None
            if config.get("level_path"):
                raw_level = nested_get(watch, config["level_path"])
                level = str(raw_level) if raw_level is not None else None
            window_forecast = {
                "probability": probability,
                "forecast_window": forecast_window,
                "observed_at": watch_observed_at,
                "expires_at": expires_at,
                "level": level,
            }
            source_updated_at = watch_observed_at
    else:
        visible_text = _visible_html_text(raw)
        for horizon, rule in (config.get("probabilities") or {}).items():
            match = re.search(rule["pattern"], visible_text, flags=re.IGNORECASE | re.DOTALL)
            if not match:
                continue
            forecasts[horizon] = normalize_probability(match.group(1), rule.get("unit", "percent"))

    if not forecasts and window_forecast is None:
        raise CollectorError("no forecast values were extracted; placeholders are not archived")

    _validate_source_freshness(source, source_updated_at, now)
    observed_at = isoformat_z(now)
    snapshot_id = stable_snapshot_id(source["id"], observed_at, raw_sha256, forecasts, window_forecast)
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
        window_forecast=window_forecast,
    )
    snapshot.validate()
    return snapshot
