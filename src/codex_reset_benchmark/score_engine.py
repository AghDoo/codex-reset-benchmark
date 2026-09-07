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
METHODOLOGY_VERSION = "1.1.0"
COMPARISON_MODE = "common_case_intersection"


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


def _metrics(
    cases: list[dict[str, Any]],
    possible_checkpoints: int,
    *,
    eligibility_sample_count: int | None = None,
) -> dict[str, Any]:
    count = len(cases)
    eligible_count = count if eligibility_sample_count is None else eligibility_sample_count
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
        "eligible": eligible_count >= MIN_RANK_SAMPLES,
        "brier": round(brier, 6),
        "log_loss": round(log_loss / count, 6),
        "hit_rate": round(hits / count, 6),
        "availability": round(count / possible_checkpoints, 6) if possible_checkpoints else None,
        "calibration": _calibration(cases),
    }


def _source_cases(
    source: dict[str, Any],
    source_snaps: list[dict[str, Any]],
    horizon: str,
    delta: timedelta,
    resolution_as_of: datetime,
    events: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], int]:
    horizon_snaps = [item for item in source_snaps if horizon in item.get("forecasts", {})]
    first_observed = parse_datetime(horizon_snaps[0]["observed_at"]) if horizon_snaps else resolution_as_of
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
        cases.append(
            {
                "source_id": source["id"],
                "horizon": horizon,
                "checkpoint": isoformat_z(checkpoint),
                "window_end": isoformat_z(end),
                "snapshot_id": snapshot["snapshot_id"],
                "probability": float(snapshot["forecasts"][horizon]),
                "outcome": _outcome(events, checkpoint, end),
            }
        )
    return cases, len(checkpoints)


def _common_checkpoints(raw_cases: dict[str, list[dict[str, Any]]], cohort: list[str]) -> set[str]:
    if not cohort:
        return set()
    checkpoint_sets = [{case["checkpoint"] for case in raw_cases[source_id]} for source_id in cohort]
    return set.intersection(*checkpoint_sets) if checkpoint_sets else set()


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

    raw_cases_by_horizon: dict[str, dict[str, list[dict[str, Any]]]] = {
        horizon: {} for horizon in SUPPORTED_HORIZONS
    }
    possible_by_horizon: dict[str, dict[str, int]] = {
        horizon: {} for horizon in SUPPORTED_HORIZONS
    }

    for source in sources:
        source_snaps = by_source.get(source["id"], [])
        for horizon, delta in SUPPORTED_HORIZONS.items():
            cases, possible = _source_cases(
                source,
                source_snaps,
                horizon,
                delta,
                resolution_as_of,
                events,
            )
            raw_cases_by_horizon[horizon][source["id"]] = cases
            possible_by_horizon[horizon][source["id"]] = possible

    source_results: dict[str, dict[str, Any]] = {source["id"]: {} for source in sources}
    rankings: dict[str, list[dict[str, Any]]] = {}
    baselines: dict[str, Any] = {}
    ranking_cohorts: dict[str, list[str]] = {}
    common_checkpoint_counts: dict[str, int] = {}

    for horizon in SUPPORTED_HORIZONS:
        raw_cases = raw_cases_by_horizon[horizon]
        cohort = [
            source["id"]
            for source in sources
            if source.get("enabled", True) and len(raw_cases[source["id"]]) >= MIN_RANK_SAMPLES
        ]
        common = _common_checkpoints(raw_cases, cohort)
        common_sorted = sorted(common)
        ranking_cohorts[horizon] = cohort
        common_checkpoint_counts[horizon] = len(common_sorted)

        common_outcomes: dict[str, int] = {}
        if cohort:
            reference = {case["checkpoint"]: case for case in raw_cases[cohort[0]]}
            common_outcomes = {checkpoint: reference[checkpoint]["outcome"] for checkpoint in common_sorted}

        if common_outcomes:
            outcomes = list(common_outcomes.values())
            base_rate = sum(outcomes) / len(outcomes)
            baseline_brier = sum((base_rate - outcome) ** 2 for outcome in outcomes) / len(outcomes)
            baselines[horizon] = {
                "resolved_cases": len(outcomes),
                "descriptive_event_rate": round(base_rate, 6),
                "descriptive_brier": round(baseline_brier, 6),
                "note": "Descriptive in-sample climatology on the official common-case comparison set; not used to rank sources.",
            }
        else:
            baselines[horizon] = {
                "resolved_cases": 0,
                "descriptive_event_rate": None,
                "descriptive_brier": None,
            }

        rows: list[dict[str, Any]] = []
        for source in sources:
            sid = source["id"]
            source_raw = raw_cases[sid]
            possible = possible_by_horizon[horizon][sid]
            coverage_samples = len(source_raw)
            coverage_availability = round(coverage_samples / possible, 6) if possible else None

            if sid in cohort:
                comparison_cases = [case for case in source_raw if case["checkpoint"] in common]
                metrics = _metrics(
                    comparison_cases,
                    len(common_sorted),
                    eligibility_sample_count=len(common_sorted),
                )
                metrics["availability"] = coverage_availability
                comparison_basis = COMPARISON_MODE
            else:
                comparison_cases = source_raw
                metrics = _metrics(source_raw, possible)
                metrics["eligible"] = False
                comparison_basis = "source_specific_provisional"

            source_results[sid][horizon] = {
                **metrics,
                "coverage_samples": coverage_samples,
                "possible_checkpoints": possible,
                "comparison_basis": comparison_basis,
                "cases": comparison_cases,
            }

            rows.append(
                {
                    "source_id": sid,
                    "name": source["name"],
                    "url": source["url"],
                    **{
                        key: source_results[sid][horizon][key]
                        for key in (
                            "samples",
                            "coverage_samples",
                            "eligible",
                            "brier",
                            "log_loss",
                            "hit_rate",
                            "availability",
                            "comparison_basis",
                        )
                    },
                }
            )

        rows.sort(
            key=lambda row: (
                not row["eligible"],
                row["brier"] is None,
                row["brier"] if row["brier"] is not None else 999.0,
                row["name"],
            )
        )
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
        "methodology_version": METHODOLOGY_VERSION,
        "comparison_mode": COMPARISON_MODE,
        "generated_at": isoformat_z(as_of),
        "ground_truth_reviewed_at": isoformat_z(ground_truth_reviewed_at),
        "checkpoint_hours_utc": list(CHECKPOINT_HOURS),
        "max_forecast_age_hours": {
            horizon: int(age.total_seconds() / 3600) for horizon, age in MAX_FORECAST_AGE.items()
        },
        "minimum_rank_samples": MIN_RANK_SAMPLES,
        "ranking_cohorts": ranking_cohorts,
        "common_checkpoint_counts": common_checkpoint_counts,
        "rankings": rankings,
        "baselines": baselines,
        "sources": source_results,
    }
