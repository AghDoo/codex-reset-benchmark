#!/usr/bin/env python3
from pathlib import Path

from codex_reset_benchmark.site import build_site_data

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    result = build_site_data(ROOT)
    print(f"Generated leaderboard data ({result['generated_at']}).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
