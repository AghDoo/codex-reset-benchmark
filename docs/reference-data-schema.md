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

For a source-defined variable forecast window, a snapshot may instead carry an empty fixed-horizon map plus `window_forecast`:

```json
{
  "schema_version": 1,
  "snapshot_id": "sha256-prefix",
  "source_id": "codex-resets-com",
  "observed_at": "2026-08-13T14:17:00Z",
  "source_updated_at": "2026-08-13T13:30:00Z",
  "forecasts": {},
  "window_forecast": {
    "probability": 0.70,
    "forecast_window": "by end of Monday",
    "observed_at": "2026-08-13T13:30:00Z",
    "expires_at": "2026-08-14T23:59:59Z",
    "level": "strong"
  },
  "source_url": "https://example.test/status",
  "collector_type": "status_watch_json",
  "collector_version": "1",
  "raw_sha256": "..."
}
```

Variable-window forecasts are preserved as-issued. V1 does not coerce source-defined text windows into the fixed 5h/24h/48h scoring buckets; they are archive/display data until a methodology explicitly defines a reproducible mapping.

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

`data/status/collectors.json` is operational state, not historical truth. It records the latest success/error/skip state and may be overwritten. A conditional source can report `idle` when its endpoint is healthy but it currently publishes no active forecast; `idle` is not a collection error.

## Derived site data

Files under `docs/generated/` are generated output and can be replaced at any time:

- `leaderboard.json`
- `calibration.json`
- `latest.json`
- `sources.json`
- `meta.json`
