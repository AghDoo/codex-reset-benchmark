from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .models import isoformat_z, parse_datetime
from .score_engine import score_archive
from .storage import load_events, load_snapshots, load_sources, write_json


def build_site_data(repo_root: Path, *, now: datetime | None = None) -> dict[str, Any]:
    now = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    source_payload = load_sources(repo_root)
    event_payload = load_events(repo_root)
    snapshots = load_snapshots(repo_root)
    sources = source_payload.get("sources", [])
    events = event_payload.get("events", [])
    ground_truth_reviewed_at = parse_datetime(event_payload["reviewed_at"])

    scoring = score_archive(
        snapshots,
        events,
        sources,
        as_of=now,
        ground_truth_reviewed_at=ground_truth_reviewed_at,
    )
    generated = repo_root / "docs" / "generated"
    leaderboard_payload = {
        key: scoring[key]
        for key in (
            "schema_version",
            "methodology_version",
            "generated_at",
            "ground_truth_reviewed_at",
            "checkpoint_hours_utc",
            "max_forecast_age_hours",
            "minimum_rank_samples",
            "rankings",
            "baselines",
        )
    }
    write_json(generated / "leaderboard.json", leaderboard_payload)
    calibration_payload = {
        "schema_version": 1,
        "methodology_version": scoring["methodology_version"],
        "generated_at": scoring["generated_at"],
        "ground_truth_reviewed_at": scoring["ground_truth_reviewed_at"],
        "sources": {
            source_id: {
                horizon: {"samples": metrics["samples"], "calibration": metrics["calibration"]}
                for horizon, metrics in horizons.items()
                if metrics["samples"] > 0
            }
            for source_id, horizons in scoring["sources"].items()
            if any(metrics["samples"] > 0 for metrics in horizons.values())
        },
    }
    write_json(generated / "calibration.json", calibration_payload)

    by_source: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for snapshot in snapshots:
        by_source[snapshot["source_id"]].append(snapshot)

    latest_sources = []
    for source in sources:
        source_snaps = sorted(by_source.get(source["id"], []), key=lambda row: row["observed_at"])
        latest = source_snaps[-1] if source_snaps else None
        age_hours = None
        stale = None
        if latest:
            age_hours = (now - parse_datetime(latest["observed_at"])).total_seconds() / 3600
            stale = age_hours > 2.5
        latest_sources.append({
            "id": source["id"],
            "name": source["name"],
            "url": source["url"],
            "enabled": bool(source.get("enabled")),
            "latest": latest,
            "age_hours": round(age_hours, 2) if age_hours is not None else None,
            "stale": stale,
        })

    confirmed_events = [event for event in events if event.get("status") == "confirmed"]
    confirmed_events.sort(key=lambda event: event["occurred_at"])
    latest_payload = {
        "schema_version": 1,
        "generated_at": isoformat_z(now),
        "ground_truth_reviewed_at": scoring["ground_truth_reviewed_at"],
        "latest_confirmed_reset": confirmed_events[-1] if confirmed_events else None,
        "sources": latest_sources,
    }
    write_json(generated / "latest.json", latest_payload)

    public_sources = [
        {
            "id": source["id"],
            "name": source["name"],
            "url": source["url"],
            "enabled": bool(source.get("enabled")),
            "access": source.get("access", {}),
        }
        for source in sources
    ]
    write_json(generated / "sources.json", {"schema_version": 1, "generated_at": isoformat_z(now), "sources": public_sources})
    write_json(generated / "meta.json", {
        "schema_version": 1,
        "generated_at": isoformat_z(now),
        "ground_truth_reviewed_at": scoring["ground_truth_reviewed_at"],
        "methodology_version": scoring["methodology_version"],
        "snapshot_count": len(snapshots),
        "confirmed_event_count": len(confirmed_events),
    })
    return scoring
