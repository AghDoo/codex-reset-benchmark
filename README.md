# Codex Reset Benchmark

English | [繁體中文](./README.zh-TW.md)

Independent benchmark for tracking and comparing community Codex reset prediction accuracy.

> **Status:** early public benchmark. Forecasts are archived as issued; ranking remains provisional until each horizon reaches the minimum resolved sample size.

## Why this exists

Several independent community sites publish probabilities or estimates for unscheduled Codex usage-limit resets. This project records those public forecasts before outcomes are known, resolves them against a documented public-event definition, and scores them under one reproducible methodology.

The repository itself is the audit trail: forecast snapshots are append-only NDJSON committed by GitHub Actions, while derived leaderboard JSON can always be rebuilt from the archive.

## Principles

- **As-issued evidence:** score what a site actually published at collection time, not reconstructed history.
- **Common checkpoints:** high-frequency publishers do not receive extra weight.
- **Probabilistic scoring:** Brier Score is the primary metric; calibration, log loss, binary hit rate, sample count, and availability are secondary diagnostics.
- **Horizon separation:** 5h, 24h, and 48h forecasts are scored separately.
- **Public-only collection:** no login, cookies, credentials, CAPTCHA bypass, anti-bot bypass, or private account data.
- **Reproducibility:** source data and scoring code are public and deterministic.

## Current benchmark horizons

| Horizon | Primary metric | Formal checkpoints | Rank eligibility |
|---|---|---|---|
| 5h | Mean Brier Score ↓ | 00:00, 06:00, 12:00, 18:00 UTC | 10 resolved forecasts |
| 24h | Mean Brier Score ↓ | 00:00, 06:00, 12:00, 18:00 UTC | 10 resolved forecasts |
| 48h | Mean Brier Score ↓ | 00:00, 06:00, 12:00, 18:00 UTC | 10 resolved forecasts |

A 5h forecast must be no more than one hour old at a checkpoint; 24h and 48h forecasts may be no more than six hours old. Outcomes are resolved only after the full horizon has elapsed. V1 fully supports 5h, 24h, and 48h scoring even though the initial source set currently exposes no reliable machine-readable 5h forecast.

## Repository layout

```text
.github/workflows/       CI, hourly collection, Pages deployment
src/codex_reset_benchmark/
                         collectors, storage, validation, scoring
scripts/                 CLI entry points
data/
  sources.json           source registry
  forecasts/             append-only forecast archive
  events/resets.json     reviewed ground truth
  status/                collector health state
docs/                    static GitHub Pages site
tests/                   unit tests
```

`data/` is the audit/source layer. `docs/data/` contains derived files and may be regenerated at any time.

## Local development

```bash
python -m pip install -e .
python -m unittest discover -s tests -v
python scripts/validate_data.py
python scripts/score.py
python scripts/build_site_data.py
```

To run the public collectors once:

```bash
python scripts/collect.py
```

This writes new snapshots under `data/forecasts/YYYY/MM/DD.ndjson`; it never stores a copy of the source webpage, only normalized probabilities plus provenance hashes and timestamps.

## Methodology and data model

- [Benchmark methodology](./docs/reference-methodology.md)
- [Data schema](./docs/reference-data-schema.md)
- [Source inventory](./docs/reference-sources.md)
- [Collection, correction, and opt-out policy](./docs/reference-policies.md)

## GitHub Pages

Static site files live in `/docs`, matching the repository Pages source (`main:/docs`). Because commits made by a scheduled workflow with `GITHUB_TOKEN` do not trigger a branch-based Pages rebuild, the live UI reads the newest generated JSON directly from `main` on `raw.githubusercontent.com`, with the deployed `/docs/data` files as a fallback.

## Contributing

See [CONTRIBUTING.md](./CONTRIBUTING.md). New sources should expose a public probability or estimate with an identifiable forecast horizon. Submissions that require authentication, session cookies, CAPTCHA/anti-bot bypass, or invasive crawling are not accepted.

## Disclaimer

This is an independent community research project. It is not affiliated with, endorsed by, sponsored by, or operated by OpenAI or any tracked forecast site. “Codex”, “ChatGPT”, and related marks belong to their respective owners. Forecasts are experimental estimates and should not be used as guarantees of service availability or account quota state.

## License

Software in this repository is licensed under the [MIT License](./LICENSE). Third-party facts, URLs, names, and forecast values retain any rights applicable at their source; this repository does not claim ownership over third-party services or branding.
