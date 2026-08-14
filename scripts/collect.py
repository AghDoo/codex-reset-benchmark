#!/usr/bin/env python3
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import json

from codex_reset_benchmark.collectors import CollectorError, collect_source
from codex_reset_benchmark.http import AccessDenied, FetchError, HttpClient
from codex_reset_benchmark.models import isoformat_z
from codex_reset_benchmark.storage import append_snapshot, load_sources, write_json

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    registry = load_sources(ROOT)
    client = HttpClient()
    now = datetime.now(timezone.utc)
    status = {"schema_version": 1, "updated_at": isoformat_z(now), "sources": {}}
    added = 0

    for source in registry.get("sources", []):
        sid = source["id"]
        if not source.get("enabled"):
            status["sources"][sid] = {"state": "disabled", "checked_at": isoformat_z(now)}
            continue
        try:
            snapshot = collect_source(source, client, now=now)
            path, inserted = append_snapshot(ROOT, snapshot)
            added += int(inserted)
            status["sources"][sid] = {
                "state": "ok",
                "checked_at": isoformat_z(now),
                "snapshot_id": snapshot.snapshot_id,
                "archive_path": str(path.relative_to(ROOT)),
                "inserted": inserted,
                "forecasts": snapshot.forecasts,
            }
        except (CollectorError, FetchError, AccessDenied, ValueError) as exc:
            status["sources"][sid] = {
                "state": "error",
                "checked_at": isoformat_z(now),
                "error": str(exc)[:500],
            }

    write_json(ROOT / "data" / "status" / "collectors.json", status)
    print(json.dumps({"snapshots_added": added, "status": status}, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
