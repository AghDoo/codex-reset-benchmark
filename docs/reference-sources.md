# Initial Source Inventory

Reviewed 2026-08-13. The machine-readable registry is `data/sources.json`.

| Source | V1 state | Extraction | Horizons | Initial review note |
|---|---|---|---|---|
| codex-reset.com | enabled | public JSON API | 24h, 48h | `/api/forecast` is publicly advertised by the site |
| codexreset.org | enabled | public HTML | 24h, 48h | server-rendered `Final forecast` values observed |
| codexresetradar.com | enabled | public HTML | 48h | public deterministic 48h percentage observed |
| codexreset.today | enabled | public HTML | 24h | headline probability explicitly labeled next-24h |
| akiai.cn radar | disabled | public JSON | 24h, 48h | observed feed was stale during review |
| willcodexreset.com | disabled | public HTML | unknown | SSR can expose placeholder 0% while horizon fields are loading; needs stable endpoint |
| codex-tibo.codes | disabled | manual | n/a | observed 94% content is presented as a meme/archive card, not clearly a current forecast |

A registered source is not automatically benchmark-eligible. The collector must demonstrate that it can distinguish a published forecast from placeholders and stale output.
