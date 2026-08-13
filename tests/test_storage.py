from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from codex_reset_benchmark.models import ForecastSnapshot
from codex_reset_benchmark.storage import append_snapshot, load_snapshots


class StorageTests(unittest.TestCase):
    def test_append_is_idempotent_for_same_snapshot_id(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            snapshot = ForecastSnapshot(
                snapshot_id="abc",
                source_id="source",
                observed_at="2026-08-13T14:17:00Z",
                source_updated_at=None,
                forecasts={"24h": 0.5},
                source_url="https://example.test/",
                collector_type="html_regex",
                collector_version="1",
                raw_sha256="a" * 64,
            )
            _, first = append_snapshot(root, snapshot)
            _, second = append_snapshot(root, snapshot)
            self.assertTrue(first)
            self.assertFalse(second)
            self.assertEqual(len(load_snapshots(root)), 1)


if __name__ == "__main__":
    unittest.main()
