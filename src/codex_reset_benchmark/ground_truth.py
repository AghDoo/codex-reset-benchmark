from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from .models import isoformat_z, parse_datetime

DEFAULT_MAX_REVIEW_AGE_HOURS = 36.0


def evaluate_ground_truth_freshness(
    payload: dict[str, Any],
    *,
    now: datetime | None = None,
    max_age_hours: float = DEFAULT_MAX_REVIEW_AGE_HOURS,
) -> dict[str, Any]:
    if isinstance(max_age_hours, bool) or not isinstance(max_age_hours, (int, float)) or max_age_hours <= 0:
        raise ValueError("max_age_hours must be a positive number")

    checked_at = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    reviewed_at = parse_datetime(payload["reviewed_at"]).astimezone(timezone.utc)
    if reviewed_at > checked_at:
        raise ValueError("ground truth reviewed_at is in the future")

    age_hours = (checked_at - reviewed_at).total_seconds() / 3600
    stale = age_hours > float(max_age_hours)
    return {
        "state": "stale" if stale else "fresh",
        "reviewed_at": isoformat_z(reviewed_at),
        "checked_at": isoformat_z(checked_at),
        "age_hours": round(age_hours, 3),
        "max_age_hours": float(max_age_hours),
    }
