# Data Schema

## Forecast snapshot

Each NDJSON line under `data/forecasts/` has this logical form:

```json
{
  "schema_version": 1,
  "snapshot_id": "sha256-prefix",
  "source_id": "codex-reset-com",
  "observed_at": "2026-08-13T14:17:00Z",
  "source_updated_at": "2026-08-13T14:00:00Z",
  "forecasts": {"5h": 0.20, "24h": 0.35, "48h": 0.55},
  "source_url": "https://example.test/forecast",
  "collector_type": "json_api",
  "collector_version": "1",
  "raw_sha256": "..."
}
```

Probabilities are always normalized to fractions in `[0, 1]`.

`raw_sha256` proves whether the retrieved representation changed without storing or republishing the full third-party page.

## Reset event

```json
{
  "id": "stable-event-id",
  "announced_at": "...",
  "effective_at": null,
  "occurred_at": "...",
  "scope": "global_paid",
  "type": "hard_reset",
  "status": "confirmed",
  "confidence": "confirmed",
  "source_url": "https://...",
  "evidence": "Short factual review note",
  "review_note": "Why occurred_at was chosen"
}
```

Only `status = confirmed` events participate in scoring. `confidence` is one of `confirmed`, `estimated`, or `announcement-only`.

## Collector status

`data/status/collectors.json` is operational state, not historical truth. It records the latest success/error/skip state and may be overwritten.

## Derived site data

Files under `docs/data/` are generated output and can be replaced at any time:

- `leaderboard.json`
- `calibration.json`
- `latest.json`
- `sources.json`
- `meta.json`
