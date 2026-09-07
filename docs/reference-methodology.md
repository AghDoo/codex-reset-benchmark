# Benchmark Methodology

## Methodology version

The current scoring methodology is **1.1.0**.

Version 1.1 changes official ranking comparisons from source-specific available cases to a common-case intersection. Version 1.0 remains reproducible from the repository commits that generated those historical scores.

## Forecast target

The benchmark scores the probability of a **new qualifying public Codex reset event** within a stated horizon after a formal checkpoint.

A qualifying event is a broad/global Codex usage-limit reset that is explicitly completed or confirmed by an authoritative public source. Personal rolling-window resets, individual credits, banked reset grants, model-only resets, ordinary scheduled quota recovery, vague wishes, reset-button hints, and unfulfilled promises are excluded.

When an independently verifiable `effective_at` exists, it is preferred. Otherwise the timestamp of an explicit completed reset announcement or public completion confirmation is used as `occurred_at`. This is an operational ground-truth definition; it does not claim every account received the quota change at that exact instant.

## Checkpoints

Formal checkpoints occur daily at 00:00, 06:00, 12:00, and 18:00 UTC.

For each source and horizon, the latest snapshot observed at or before the checkpoint is selected only when it is fresh enough: at most one hour old for 5h, and at most six hours old for 24h/48h. Multiple intermediate updates are archived but do not create extra scoring cases.

A case is resolved only after its full horizon has elapsed **and** the complete forecast window falls at or before the Ground Truth dataset's `reviewed_at` timestamp. This prevents unreviewed time from being silently scored as a negative outcome.

## Horizons

5-hour, 24-hour, and 48-hour probabilities are scored separately. A source can participate in any subset of horizons. Variable-window forecasts such as “by end of Monday” are archived as issued but are not coerced into a fixed horizon.

## Official comparison set

Missing forecasts are never imputed.

For each horizon, a currently enabled source becomes a ranking-cohort candidate after it has at least 10 resolved source-specific forecast cases. The official comparison set is then the **intersection of resolved checkpoints for which every source in that cohort has a fresh forecast**.

Official Brier Score, log loss, hit rate, calibration, and the displayed score sample count are computed from that identical common-case set for every ranked source. This prevents a source from improving its rank merely because it happened to miss difficult checkpoints.

Two counts are therefore distinct:

- **Score samples (`samples`)**: cases in the common comparison intersection used for official metrics.
- **Coverage samples (`coverage_samples`)**: all fresh resolved cases the source actually published under the checkpoint rules.

A source outside the ranking cohort may still show source-specific provisional metrics. If the common intersection itself contains fewer than 10 cases, cohort members remain provisional until enough common cases exist.

## Primary metric: Brier Score

For probability `p` and binary outcome `o`:

```text
Brier = (p - o)^2
```

Lower is better. The official leaderboard reports the mean Brier Score across the common comparison set.

## Secondary diagnostics

- **Calibration:** forecasts are grouped into 0–20%, 20–40%, 40–60%, 60–80%, and 80–100% bins and compared with observed event frequency on the same score cases.
- **Log loss:** included as a diagnostic and clipped only for numerical stability.
- **Binary hit rate:** probability >= 50% is treated as a positive call; this is intentionally secondary because it discards probabilistic information.
- **Availability:** source-specific fraction of resolved formal checkpoints for which a fresh forecast was available after the source first entered that horizon. Availability is not restricted to the common comparison set.
- **Coverage sample count:** number of source-specific fresh resolved cases.
- **Score sample count:** number of common cases used for ranked metrics.

The descriptive climatology baseline is also computed once on the common comparison set rather than weighting an outcome multiple times because more sources happened to publish it.

## Missing and stale data

A missing, failed, stale, or unparsable source has no case for that checkpoint. Collector failures never replace the last archived snapshot and never create a synthetic 0% probability.

Because official ranks use a common-case intersection, missing data reduces the shared comparison set instead of selectively removing a difficult outcome from only one ranked source. Availability remains visible so persistent collection gaps are still measurable.

## Ground truth

`data/events/resets.json` is the reviewed scoring dataset. Its top-level `reviewed_at` timestamp is the latest instant through which the event history has been reviewed. Events must include a public source URL, explicit scope, status, and review note. Ambiguous promises remain excluded until a completed event can be verified.

Reset-like announcements that were reviewed but intentionally excluded from the target, such as banked reset grants or signal-only reset-button hints, are retained under `excluded_events` with their source URL and exclusion reason. They are audit evidence only and never participate in scoring.

Advancing `reviewed_at` means reset-like evidence through that instant has been reviewed. Scoring never advances beyond this boundary even when newer forecasts have already been archived.

Corrections are non-destructive: a historical decision is superseded with an auditable correction rather than silently rewritten.

## Known limitations

Community forecast sites may define “reset” or its effective time differently. This benchmark intentionally chooses a single public-event definition so every source is scored against the same observable target.

GitHub Actions schedules are best-effort and can be delayed. Collection gaps reduce availability and, under methodology 1.1, can also reduce the common comparison set. The archive preserves the actual observation timestamps rather than pretending a missed collection occurred on schedule.

Changes that alter ranking semantics require a methodology version change. Historical generated scores remain reproducible from the commit and methodology version that produced them.
