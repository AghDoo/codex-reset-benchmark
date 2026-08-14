from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta, timezone
import math
from typing import Any

from .models import isoformat_z, parse_datetime

CHECKPOINT_HOURS = (0, 6, 12, 18)
MAX_FORECAST_AGE = {"5h": timedelta(hours=1), "24h": timedelta(hours=6), "48h": timedelta(hours=6)}
MIN_RANK_SAMPLES = 10
SUPPORTED_HORIZONS = {"5h": timedelta(hours=5), "24h": timedelta(hours=24), "48h": timedelta(hours=48)}
CALIBRATION_BINS = ((0.0, 0.2), (0.2, 0.4), (0.4, 0.6), (0.6, 0.8), (0.8, 1.0000001))


def _checkpoint_range(start: datetime, end: datetime) -> list[datetime]:
    start = start.astimezone(timezone.utc)
    end = end.astimezone(timezone.utc)
    day = datetime(start.year, start.month, start.day, tzinfo=timezone.utc)
    points: list[datetime] = []
    while day <= end:
        for hour in CHECKPOINT_HOURS:
            point = day.replace(hour=hour)
            if start <= point <= end:
                points.append(point)
        day += timedelta(days=1)
    return points


def _select_snapshot(snapshots: list[dict[str, Any]], checkpoint: datetime, max_age: timedelta) -> dict[str, Any] | None:
    eligible = []
    for item in snapshots:
        observed = parse_datetime(item["observed_at"])
        if observed <= checkpoint and checkpoint - observed <= max_age:
            eligible.append((observed, item))
    if not eligible:
        return None
    eligible.sort(key=lambda pair: pair[0])
    return eligible[-1][1]


def _outcome(events: list[dict[str, Any]], checkpoint: datetime, end: datetime) -> int:
    for event in events:
        if event.get("status") != "confirmed":
            continue
        occurred = parse_datetime(event["occurred_at"])
        if checkpoint < occurred <= end:
            return 1
    return 0


def _calibration(cases: list[dict[str, Any]]) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    for low, high in CALIBRATION_BINS:
        selected = [case for case in cases if low <= case["probability"] < high]
        output.append(
            {
                "range": [round(low, 2), 1.0 if high > 1 else round(high, 2)],
                "count": len(selected),
                "mean_forecast": round(sum(c["probability"] for c in selected) / len(selected), 6) if selected else None,
                "event_rate": round(sum(c["outcome"] for c in selected) / len(selected), 6) if selected else None,
            }
        )
    return output


def _metrics(cases: list[dict[str, Any]], possible_checkpoints: int) -> dict[str, Any]:
    count = len(cases)
    if not count:
        return {
            "samples": 0,
            "eligible": False,
            "brier": None,
            "log_loss": None,
            "hit_rate": None,
            "availability": 0.0 if possible_checkpoints else None,
            "calibration": _calibration([]),
        }
    brier = sum((c["probability"] - c["outcome"]) ** 2 for c in cases) / count
    eps = 1e-6
    log_loss = 0.0
    hits = 0
    for case in cases:
        p = min(max(case["probability"], eps), 1 - eps)
        o = case["outcome"]
        log_loss += -(o * math.log(p) + (1 - o) * math.log(1 - p))
        hits += int((case["probability"] >= 0.5) == bool(o))
    return {
        "samples": count,
        "eligible": count >= MIN_RANK_SAMPLES,
        "brier": round(brier, 6),
        "log_loss": round(log_loss / count, 6),
        "hit_rate": round(hits / count, 6),
        "availability": round(count / possible_checkpoints, 6) if possible_checkpoints else None,
        "calibration": _calibration(cases),
    }


def score_archive(
    snapshots: list[dict[str, Any]],
    events: list[dict[str, Any]],
    sources: list[dict[str, Any]],
    *,
    as_of: datetime | None = None,
    ground_truth_reviewed_at: datetime | None = None,
) -> dict[str, Any]:
    as_of = (as_of or datetime.now(timezone.utc)).astimezone(timezone.utc)
    if ground_truth_reviewed_at is None:
        ground_truth_reviewed_at = as_of
    elif ground_truth_reviewed_at.tzinfo is None:
        raise ValueError("ground_truth_reviewed_at must be timezone-aware")
    else:
        ground_truth_reviewed_at = ground_truth_reviewed_at.astimezone(timezone.utc)
    resolution_as_of = min(as_of, ground_truth_reviewed_at)

    by_source: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in snapshots:
        by_source[item["source_id"]].append(item)
    for items in by_source.values():
        items.sort(key=lambda row: row["observed_at"])

    source_results: dict[str, dict[str, Any]] = {}
    all_cases: dict[str, list[dict[str, Any]]] = {h: [] for h in SUPPORTED_HORIZONS}

    for source in sources:
        sid = source["id"]
        source_snaps = by_source.get(sid, [])
        per_horizon: dict[str, Any] = {}

        for horizon, delta in SUPPORTED_HORIZONS.items():
            horizon_snaps = [item for item in source_snaps if horizon in item.get("forecasts", {})]
            first_observed = parse_datetime(horizon_snaps[0]["observed_at"]) if horizon_snaps else as_of
            resolution_cutoff = resolution_as_of - delta
            if first_observed > resolution_cutoff:
                checkpoints: list[datetime] = []
            else:
                checkpoints = _checkpoint_range(first_observed, resolution_cutoff)
            cases: list[dict[str, Any]] = []
            for checkpoint in checkpoints:
                snapshot = _select_snapshot(horizon_snaps, checkpoint, MAX_FORECAST_AGE[horizon])
                if not snapshot:
                    continue
                end = checkpoint + delta
                case = {
                    "source_id": sid,
                    "horizon": horizon,
                    "checkpoint": isoformat_z(checkpoint),
                    "window_end": isoformat_z(end),
                    "snapshot_id": snapshot["snapshot_id"],
                    "probability": float(snapshot["forecasts"][horizon]),
                    "outcome": _outcome(events, checkpoint, end),
                }
                cases.append(case)
                all_cases[horizon].append(case)
            per_horizon[horizon] = {**_metrics(cases, len(checkpoints)), "cases": cases}
        source_results[sid] = per_horizon

    rankings: dict[str, list[dict[str, Any]]] = {}
    baselines: dict[str, Any] = {}
    for horizon, cases in all_cases.items():
        if cases:
            base_rate = sum(c["outcome"] for c in cases) / len(cases)
            baseline_brier = sum((base_rate - c["outcome"]) ** 2 for c in cases) / len(cases)
            baselines[horizon] = {
                "resolved_cases": len(cases),
                "descriptive_event_rate": round(base_rate, 6),
                "descriptive_brier": round(baseline_brier, 6),
                "note": "Descriptive in-sample climatology; not used to rank sources.",
            }
        else:
            baselines[horizon] = {"resolved_cases": 0, "descriptive_event_rate": None, "descriptive_brier": None}

        rows = []
        for source in sources:
            metrics = source_results[source["id"]][horizon]
            rows.append(
                {
                    "source_id": source["id"],
                    "name": source["name"],
                    "url": source["url"],
                    **{key: metrics[key] for key in ("samples", "eligible", "brier", "log_loss", "hit_rate", "availability")},
                }
            )
        rows.sort(key=lambda row: (not row["eligible"], row["brier"] is None, row["brier"] if row["brier"] is not None else 999.0, row["name"]))
        rank = 0
        for row in rows:
            if row["eligible"]:
                rank += 1
                row["rank"] = rank
            else:
                row["rank"] = None
        rankings[horizon] = rows

    return {
        "schema_version": 1,
        "methodology_version": "1.0.0",
        "generated_at": isoformat_z(as_of),
        "ground_truth_reviewed_at": isoformat_z(ground_truth_reviewed_at),
        "checkpoint_hours_utc": list(CHECKPOINT_HOURS),
        "max_forecast_age_hours": {h: int(age.total_seconds() / 3600) for h, age in MAX_FORECAST_AGE.items()},
        "minimum_rank_samples": MIN_RANK_SAMPLES,
        "rankings": rankings,
        "baselines": baselines,
        "sources": source_results,
    }
