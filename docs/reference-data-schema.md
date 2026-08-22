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

Only entries under `events` can participate in scoring, and only when `status = confirmed`. `confidence` is one of `confirmed`, `estimated`, or `announcement-only`.

## Excluded event

A reviewed public reset-like announcement that does not satisfy the V1 target is preserved under top-level `excluded_events` instead of being discarded or inserted into scoring truth:

```json
{
  "id": "stable-event-id",
  "announced_at": "...",
  "scope": "global",
  "type": "banked_reset_grant",
  "source_url": "https://...",
  "reason": "Why this announcement is outside the benchmark target"
}
```

Excluded event IDs cannot overlap scoring-event IDs, and their timestamps must fall at or before the dataset's top-level `reviewed_at`. `excluded_events` are audit-only and never passed to the scoring engine.

The top-level `reviewed_at` is the latest instant through which both qualifying and excluded reset-like announcements have been reviewed. It is the resolution boundary used by scoring so unreviewed time is never silently treated as a negative outcome.

## Collector status

`data/status/collectors.json` is operational state, not historical truth. It records the latest success/error/skip state and may be overwritten. A conditional source can report `idle` when its endpoint is healthy but it currently publishes no active forecast; `idle` is not a collection error.

## Derived site data

Files under `docs/generated/` are generated output and can be replaced at any time:

- `leaderboard.json`
- `calibration.json`
- `latest.json`
- `sources.json`
- `meta.json`
