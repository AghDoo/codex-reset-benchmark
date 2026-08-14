# Benchmark Methodology

## Forecast target

V1 scores the probability of a **new qualifying public Codex reset event** within a stated horizon after a formal checkpoint.

A qualifying event is a broad/global Codex usage-limit reset that is explicitly completed or confirmed by an authoritative public source. Personal rolling-window resets, individual credits, banked reset grants, model-only resets, ordinary scheduled quota recovery, vague wishes, and unfulfilled promises are excluded.

When an independently verifiable `effective_at` exists, it is preferred. Otherwise the timestamp of an explicit completed reset announcement is used as `occurred_at`. This is an operational ground-truth definition; it does not claim every account received the quota change at that exact instant.

## Checkpoints

Formal checkpoints occur daily at 00:00, 06:00, 12:00, and 18:00 UTC.

For each source and horizon, the latest snapshot observed at or before the checkpoint is selected only when it is fresh enough: at most one hour old for 5h, and at most six hours old for 24h/48h. Multiple intermediate updates are archived but do not create extra scoring cases.

## Horizons

V1 scores 5-hour, 24-hour, and 48-hour probabilities separately. A source can participate in any subset of horizons. The initial source set currently exposes no reliable machine-readable 5h forecast, so the 5h leaderboard begins with zero samples but the schema and scoring path are active from V1.

A case is resolved only after its full horizon has elapsed **and** the complete forecast window falls at or before the Ground Truth dataset's `reviewed_at` timestamp. This prevents unreviewed time from being silently scored as a negative outcome.

## Primary metric: Brier Score

For probability `p` and binary outcome `o`:

```text
Brier = (p - o)^2
```

Lower is better. The leaderboard reports the mean Brier Score across resolved common-checkpoint cases.

## Secondary diagnostics

- **Calibration:** forecasts are grouped into 0–20%, 20–40%, 40–60%, 60–80%, and 80–100% bins and compared with observed event frequency.
- **Log loss:** included as a diagnostic and clipped only for numerical stability.
- **Binary hit rate:** probability >= 50% is treated as a positive call; this is intentionally secondary because it discards probabilistic information.
- **Availability:** fraction of resolved formal checkpoints for which a fresh forecast was available after the source first entered the archive.
- **Sample count:** number of resolved forecast cases.

A source becomes rank-eligible for a horizon after 10 resolved forecasts. Before then, metrics are shown as provisional.

## Missing and stale data

No forecast is imputed. A missing, failed, stale, or unparsable source simply has no case for that checkpoint. Collector failures never replace the last archived snapshot and never create a synthetic 0% probability.

## Ground truth

`data/events/resets.json` is the reviewed scoring dataset. Its top-level `reviewed_at` timestamp is the latest instant through which the event history has been reviewed. Events must include a public source URL, explicit scope, status, and review note. Ambiguous promises remain excluded until a completed event can be verified.

Corrections are non-destructive: a historical decision is superseded with an auditable correction rather than silently rewritten.

## Known limitation

Community forecast sites may define “reset” or its effective time differently. V1 intentionally chooses a single public-event definition so every source is scored against the same observable target. The methodology may version in the future, but old scores must remain reproducible under the version that produced them.
