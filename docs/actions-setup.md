# GitHub Actions setup

The active repository is designed to run two GitHub Actions workflows after their files are placed under `.github/workflows/`.

## CI

Copy `automation/ci.yml` to `.github/workflows/ci.yml`.

## Hourly collection

Create `.github/workflows/collect.yml` with an hourly schedule (minute 17 UTC), Python 3.12, `PYTHONPATH=src`, and these steps in order:

1. checkout `main`;
2. run `python -m unittest discover -s tests -v`;
3. run `python scripts/collect.py`;
4. run `python scripts/check_data.py`;
5. run `python scripts/build_site_data.py`;
6. stage only `data` and `docs/generated`;
7. commit only when those paths changed;
8. push the resulting commit to `main`.

The workflow requires repository `contents: write` only for the collection job. Its automated commit message must be:

```text
chore(data): [ChatGPT] 更新預測快照與排行榜
```

Use workflow concurrency group `codex-reset-collection` with `cancel-in-progress: false` so two scheduled runs do not update the archive simultaneously.
