#!/usr/bin/env python3
from pathlib import Path

from codex_reset_benchmark.validation import validate_repository

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    errors = validate_repository(ROOT)
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print("Repository data validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
