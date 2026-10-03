# Benchmarks: synthetic-15k

Dataset `synthetic` (SYNTHETIC): 15,340 matches · 4,160,315 deliveries · 211,194 wickets. Machine: 4 vCPU, x86_64, DuckDB in-process.

API cold start (load Parquet + materialise working tables): **3.78s**

| Query | Median | Max (of 7) |
|---|---|---|
| player page: profile | 103.4 ms | 118.7 ms |
| player page: dismissals | 37.6 ms | 40.3 ms |
| player page: situations | 150.2 ms | 164.6 ms |
| matchup: by bowler | 42.3 ms | 49.2 ms |
| matchup: by bowler family (T20 death) | 40.9 ms | 51.4 ms |
| dismissal drill-down (route → deliveries) | 155.1 ms | 169.3 ms |
| delivery drill-down (batter v bowler, 20 cards) | 145.0 ms | 163.2 ms |
| records: highest T20 SR v spin at death (min 100 balls) | 50.7 ms | 53.2 ms |
