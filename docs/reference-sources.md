# Initial Source Inventory

Reviewed 2026-08-13; updated 2026-08-16. The machine-readable registry is `data/sources.json`.

| Source | V1 state | Extraction | Horizons | Initial review note |
|---|---|---|---|---|
| codex-reset.com | enabled | public JSON API | 24h, 48h | `/api/forecast` is publicly advertised by the site |
| codexreset.org | enabled | public HTML | 24h, 48h | server-rendered `Final forecast` values observed; source-scoped 1.5 MB fetch cap accommodates the current ~1 MB page without relaxing the global limit |
| codexresetradar.com | enabled | public HTML | 48h | public deterministic 48h percentage observed |
| codexreset.today | enabled | public HTML | 24h | headline probability explicitly labeled next-24h |
| willcodexquotareset.com | enabled | public JSON API | 48h | public client loads `forecast.score` from `/api/forecast`; homepage HTML can remain a loading placeholder |
| codex-resets.com | enabled | public JSON API | variable window, archive-only | documented `/api/v1/status` exposes optional `active_watch` with probability, forecast window, observed time, and expiry; `null` means no active watch |
| akiai.cn radar | disabled | public JSON | 24h, 48h | observed feed was stale during review |
| willcodexreset.com | disabled | public HTML | unknown | SSR can expose placeholder 0% while horizon fields are loading; needs stable endpoint |
| codex-tibo.codes | disabled | manual | n/a | observed 94% content is presented as a meme/archive card, not clearly a current forecast |

A registered source is not automatically benchmark-eligible. The collector must demonstrate that it can distinguish a published forecast from placeholders and stale output.

`codex-resets.com` is intentionally treated differently from the fixed-horizon sources. Its `active_watch.forecast_window` is source-defined text such as `by end of Monday`, not a guaranteed 5h/24h/48h horizon. ResetBench therefore archives the watch exactly as published, reports a healthy `idle` state while `active_watch` is `null`, and does not coerce the watch into a V1 ranking horizon.
