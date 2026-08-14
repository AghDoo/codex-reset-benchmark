from __future__ import annotations

from datetime import datetime, timedelta, timezone
import re
from pathlib import Path
from typing import Any

from .models import parse_datetime
from .storage import load_events, load_snapshots, load_sources


def validate_source_registry(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    ids: set[str] = set()
    for source in payload.get("sources", []):
        sid = source.get("id")
        if not sid or sid in ids:
            errors.append(f"invalid or duplicate source id: {sid!r}")
        ids.add(sid)
        if not str(source.get("url", "")).startswith("https://"):
            errors.append(f"{sid}: source URL must use HTTPS")
        forecast_url = source.get("forecast_url") or source.get("url", "")
        if not str(forecast_url).startswith("https://"):
            errors.append(f"{sid}: forecast URL must use HTTPS")
        collector = source.get("collector") or {}
        if source.get("enabled") and collector.get("type") not in {"json_api", "html_regex"}:
            errors.append(f"{sid}: enabled source has unsupported collector")
        for horizon, rule in (collector.get("probabilities") or {}).items():
            if horizon not in {"5h", "24h", "48h"}:
                errors.append(f"{sid}: unsupported V1 horizon {horizon}")
            if not isinstance(rule, dict):
                errors.append(f"{sid}: invalid rule for {horizon}")
    return errors


def validate_snapshot(snapshot: dict[str, Any], source_ids: set[str]) -> list[str]:
    errors: list[str] = []
    required = {"schema_version", "snapshot_id", "source_id", "observed_at", "forecasts", "source_url", "raw_sha256"}
    missing = required - set(snapshot)
    if missing:
        errors.append(f"snapshot {snapshot.get('snapshot_id')}: missing {sorted(missing)}")
        return errors
    if snapshot.get("schema_version") != 1:
        errors.append(f"snapshot {snapshot.get('snapshot_id')}: unsupported schema_version")
    if snapshot["source_id"] not in source_ids:
        errors.append(f"snapshot {snapshot['snapshot_id']}: unknown source {snapshot['source_id']}")
    if not str(snapshot.get("source_url", "")).startswith("https://"):
        errors.append(f"snapshot {snapshot['snapshot_id']}: source_url must use HTTPS")
    try:
        observed_at = parse_datetime(snapshot["observed_at"])
        if observed_at > datetime.now(timezone.utc) + timedelta(minutes=5):
            errors.append(f"snapshot {snapshot['snapshot_id']}: observed_at is in the future")
    except ValueError as exc:
        errors.append(str(exc))
    if not snapshot.get("forecasts"):
        errors.append(f"snapshot {snapshot['snapshot_id']}: forecasts must not be empty")
    source_updated_at = snapshot.get("source_updated_at")
    if source_updated_at:
        try:
            updated_at = parse_datetime(source_updated_at)
            if updated_at > datetime.now(timezone.utc) + timedelta(minutes=5):
                errors.append(f"snapshot {snapshot['snapshot_id']}: source_updated_at is in the future")
        except ValueError as exc:
            errors.append(str(exc))
    for horizon, probability in (snapshot.get("forecasts") or {}).items():
        if horizon not in {"5h", "24h", "48h"}:
            errors.append(f"snapshot {snapshot['snapshot_id']}: invalid horizon {horizon}")
        if isinstance(probability, bool) or not isinstance(probability, (int, float)) or not 0 <= float(probability) <= 1:
            errors.append(f"snapshot {snapshot['snapshot_id']}: invalid probability {probability!r}")
    if not re.fullmatch(r"[0-9a-f]{64}", str(snapshot.get("raw_sha256", ""))):
        errors.append(f"snapshot {snapshot['snapshot_id']}: invalid raw_sha256")
    return errors


def validate_events(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    seen: set[str] = set()
    for event in payload.get("events", []):
        event_id = event.get("id")
        if not event_id or event_id in seen:
            errors.append(f"invalid or duplicate event id: {event_id!r}")
        seen.add(event_id)
        try:
            parse_datetime(event["occurred_at"])
            parse_datetime(event["announced_at"])
            if event.get("effective_at"):
                parse_datetime(event["effective_at"])
        except (KeyError, ValueError) as exc:
            errors.append(f"event {event_id}: invalid timestamp: {exc}")
        if event.get("status") not in {"confirmed", "pending", "superseded"}:
            errors.append(f"event {event_id}: invalid status")
        if event.get("confidence") not in {"confirmed", "estimated", "announcement-only"}:
            errors.append(f"event {event_id}: invalid confidence")
        if not str(event.get("source_url", "")).startswith("https://"):
            errors.append(f"event {event_id}: source_url must use HTTPS")
    return errors


def validate_repository(repo_root: Path) -> list[str]:
    sources = load_sources(repo_root)
    events = load_events(repo_root)
    snapshots = load_snapshots(repo_root)
    errors = validate_source_registry(sources)
    source_ids = {source["id"] for source in sources.get("sources", []) if source.get("id")}
    for snapshot in snapshots:
        errors.extend(validate_snapshot(snapshot, source_ids))
    errors.extend(validate_events(events))
    return errors
