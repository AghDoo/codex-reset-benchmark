# Forecast archive

This directory is append-only benchmark evidence.

Hourly collection writes UTC daily NDJSON files at:

```text
data/forecasts/YYYY/MM/DD.ndjson
```

Each line is one normalized source snapshot. Do not rewrite a historical forecast to fix a parser or source mistake. Use the documented correction/supersession process instead.
