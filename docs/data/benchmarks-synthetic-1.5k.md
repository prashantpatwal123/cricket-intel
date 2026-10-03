# Benchmarks: synthetic-1.5k

Dataset `synthetic` (SYNTHETIC): 1,534 matches · 415,676 deliveries · 21,408 wickets. Machine: 4 vCPU, x86_64, DuckDB in-process.

API cold start (load Parquet + materialise working tables): **0.93s**

| Query | Median | Max (of 7) |
|---|---|---|
| player page: profile | 40.9 ms | 44.7 ms |
| player page: dismissals | 15.1 ms | 15.8 ms |
| player page: situations | 51.0 ms | 57.3 ms |
| matchup: by bowler | 10.7 ms | 11.8 ms |
| matchup: by bowler family (T20 death) | 10.8 ms | 11.5 ms |
| dismissal drill-down (route → deliveries) | 62.5 ms | 64.0 ms |
| delivery drill-down (batter v bowler, 20 cards) | 64.9 ms | 66.6 ms |
| records: highest T20 SR v spin at death (min 100 balls) | 8.2 ms | 9.2 ms |
