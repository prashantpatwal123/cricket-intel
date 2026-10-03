# Benchmarks: synthetic-1.5k

Dataset `synthetic` (SYNTHETIC): 1,534 matches · 415,676 deliveries · 21,408 wickets. Machine: 4 vCPU, x86_64, DuckDB in-process.

API cold start (load Parquet + materialise working tables): **0.99s**

| Query | Median | Max (of 7) |
|---|---|---|
| player page: profile | 48.0 ms | 50.1 ms |
| player page: dismissals | 16.6 ms | 20.6 ms |
| player page: situations | 47.8 ms | 51.6 ms |
| matchup: by bowler | 11.6 ms | 14.6 ms |
| matchup: by bowler family (T20 death) | 12.4 ms | 15.5 ms |
| dismissal drill-down (route → deliveries) | 69.5 ms | 81.0 ms |
| delivery drill-down (batter v bowler, 20 cards) | 70.1 ms | 87.2 ms |
| records: highest T20 SR v spin at death (min 100 balls) | 10.8 ms | 11.4 ms |
