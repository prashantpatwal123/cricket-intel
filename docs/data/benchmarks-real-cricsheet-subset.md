# Benchmarks: real-cricsheet-subset

Dataset `cricsheet` (real): 10,247 matches · 3,298,987 deliveries · 134,143 wickets. Machine: 4 vCPU, x86_64, DuckDB in-process.

API cold start (load Parquet + materialise working tables): **2.54s**

| Query | Median | Max (of 7) |
|---|---|---|
| player page: profile | 142.1 ms | 152.7 ms |
| player page: dismissals | 37.9 ms | 38.9 ms |
| player page: situations | 147.9 ms | 157.0 ms |
| matchup: by bowler | 32.1 ms | 34.7 ms |
| matchup: by bowler family (T20 death) | 25.1 ms | 56.7 ms |
| dismissal drill-down (route → deliveries) | 225.2 ms | 263.3 ms |
| delivery drill-down (batter v bowler, 20 cards) | 197.1 ms | 235.5 ms |
| records: highest T20 SR v spin at death (min 100 balls) | 17.1 ms | 18.0 ms |
