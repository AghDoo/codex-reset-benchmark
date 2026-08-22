#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from codex_reset_benchmark.ground_truth import DEFAULT_MAX_REVIEW_AGE_HOURS, evaluate_ground_truth_freshness

ROOT = Path(__file__).resolve().parents[1]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Check whether the reviewed Ground Truth boundary is still operationally fresh.")
    parser.add_argument("--max-age-hours", type=float, default=DEFAULT_MAX_REVIEW_AGE_HOURS)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        payload = json.loads((ROOT / "data" / "events" / "resets.json").read_text(encoding="utf-8"))
        result = evaluate_ground_truth_freshness(payload, max_age_hours=args.max_age_hours)
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        print(json.dumps({"state": "error", "error": str(exc)}, indent=2), file=sys.stderr)
        return 1

    print(json.dumps(result, indent=2))
    return 2 if result["state"] == "stale" else 0


if __name__ == "__main__":
    raise SystemExit(main())
