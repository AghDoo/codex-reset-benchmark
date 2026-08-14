from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
from typing import Any

SCHEMA_VERSION = 1
COLLECTOR_VERSION = "1"


def parse_datetime(value: str) -> datetime:
    if not isinstance(value, str) or not value:
        raise ValueError("timestamp must be a non-empty string")
    text = value[:-1] + "+00:00" if value.endswith("Z") else value
    dt = datetime.fromisoformat(text)
    if dt.tzinfo is None:
        raise ValueError(f"timestamp must include timezone: {value}")
    return dt.astimezone(timezone.utc)


def isoformat_z(dt: datetime) -> str:
    if dt.tzinfo is None:
        raise ValueError("datetime must be timezone-aware")
    return dt.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def normalize_probability(value: Any, unit: str) -> float:
    if isinstance(value, bool):
        raise ValueError(f"invalid probability value: {value!r}")
    if not isinstance(value, (int, float)):
        try:
            value = float(value)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"invalid probability value: {value!r}") from exc
    number = float(value)
    if unit == "percent":
        number /= 100.0
    elif unit == "percent_or_fraction":
        if number > 1:
            number /= 100.0
    elif unit != "fraction":
        raise ValueError(f"unsupported probability unit: {unit}")
    if not 0.0 <= number <= 1.0:
        raise ValueError(f"probability outside [0, 1]: {number}")
    return round(number, 10)


def stable_snapshot_id(source_id: str, observed_at: str, raw_sha256: str, forecasts: dict[str, float]) -> str:
    payload = json.dumps(
        {
            "source_id": source_id,
            "observed_at": observed_at,
            "raw_sha256": raw_sha256,
            "forecasts": forecasts,
        },
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()[:24]


@dataclass(frozen=True)
class ForecastSnapshot:
    snapshot_id: str
    source_id: str
    observed_at: str
    source_updated_at: str | None
    forecasts: dict[str, float]
    source_url: str
    collector_type: str
    collector_version: str
    raw_sha256: str

    def validate(self) -> None:
        if not self.source_id:
            raise ValueError("source_id is required")
        parse_datetime(self.observed_at)
        if self.source_updated_at:
            parse_datetime(self.source_updated_at)
        if not self.forecasts:
            raise ValueError("at least one forecast horizon is required")
        for horizon, probability in self.forecasts.items():
            if horizon not in {"5h", "24h", "48h"}:
                raise ValueError(f"unsupported horizon: {horizon}")
            normalize_probability(probability, "fraction")
        if len(self.raw_sha256) != 64:
            raise ValueError("raw_sha256 must be a full SHA-256 hex digest")

    def to_dict(self) -> dict[str, Any]:
        self.validate()
        return {
            "schema_version": SCHEMA_VERSION,
            "snapshot_id": self.snapshot_id,
            "source_id": self.source_id,
            "observed_at": self.observed_at,
            "source_updated_at": self.source_updated_at,
            "forecasts": self.forecasts,
            "source_url": self.source_url,
            "collector_type": self.collector_type,
            "collector_version": self.collector_version,
            "raw_sha256": self.raw_sha256,
        }
