from __future__ import annotations

from datetime import datetime
import json
from pathlib import Path
from typing import Any, Iterable

from .models import ForecastSnapshot, parse_datetime


def append_snapshot(repo_root: Path, snapshot: ForecastSnapshot) -> tuple[Path, bool]:
    snapshot.validate()
    dt = parse_datetime(snapshot.observed_at)
    path = repo_root / "data" / "forecasts" / f"{dt:%Y}" / f"{dt:%m}" / f"{dt:%d}.ndjson"
    path.parent.mkdir(parents=True, exist_ok=True)
    existing_ids: set[str] = set()
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                existing_ids.add(json.loads(line)["snapshot_id"])
    if snapshot.snapshot_id in existing_ids:
        return path, False
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(snapshot.to_dict(), sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n")
    return path, True


def iter_snapshot_files(repo_root: Path) -> Iterable[Path]:
    root = repo_root / "data" / "forecasts"
    if not root.exists():
        return []
    return sorted(path for path in root.rglob("*.ndjson") if path.is_file())


def load_snapshots(repo_root: Path) -> list[dict[str, Any]]:
    snapshots: list[dict[str, Any]] = []
    for path in iter_snapshot_files(repo_root):
        for index, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            if not line.strip():
                continue
            try:
                snapshots.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValueError(f"invalid NDJSON in {path}:{index}") from exc
    snapshots.sort(key=lambda item: (item["observed_at"], item["source_id"]))
    return snapshots


def load_sources(repo_root: Path) -> dict[str, Any]:
    return json.loads((repo_root / "data" / "sources.json").read_text(encoding="utf-8"))


def load_events(repo_root: Path) -> dict[str, Any]:
    return json.loads((repo_root / "data" / "events" / "resets.json").read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
