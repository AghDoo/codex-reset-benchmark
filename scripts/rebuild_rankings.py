#!/usr/bin/env python3
from datetime import datetime, timezone
from pathlib import Path
import json

from codex_reset_benchmark.score_engine import score_archive
from codex_reset_benchmark.storage import load_events, load_snapshots, load_sources

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    sources = load_sources(ROOT).get("sources", [])
    events = load_events(ROOT).get("events", [])
    snapshots = load_snapshots(ROOT)
    result = score_archive(snapshots, events, sources, as_of=datetime.now(timezone.utc))
    print(json.dumps(result["rankings"], indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
