#!/usr/bin/env python3
from datetime import datetime, timezone
from pathlib import Path
import json

from codex_reset_benchmark.models import parse_datetime
from codex_reset_benchmark.score_engine import score_archive
from codex_reset_benchmark.storage import load_events, load_snapshots, load_sources

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    sources = load_sources(ROOT).get("sources", [])
    event_payload = load_events(ROOT)
    events = event_payload.get("events", [])
    snapshots = load_snapshots(ROOT)
    result = score_archive(
        snapshots,
        events,
        sources,
        as_of=datetime.now(timezone.utc),
        ground_truth_reviewed_at=parse_datetime(event_payload["reviewed_at"]),
    )
    print(json.dumps(result["rankings"], indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
