# Phase 5 performance: Historical Live Lab

Profiled first, then optimised. Reproduce with `python -m cricintel.live.bench --dataset cricsheet [--match ID]`
(server side) and the UI probe in the Phase 5 checkpoint. Machine: the development container, with other jobs running.

## Profile-driven fixes (per-ball server response)

| Step | Cost found by cProfile | Fix | Median per ball |
|---|---|---|---|
| Baseline implementation | Every request re-read the match and replayed it | — | ~150 ms |
| Provider queries scanned 3.3M deliveries to find one match | 92% of time in `duckdb.execute` | Match-sorted copies (`live_deliveries`, `live_wickets`, `live_fielders`, `live_players`) in the working DB, so zone maps skip to one match | ~80 ms |
| Driver imported a module per bound parameter (`IN (?,?,…)` with ~250 ids) | 17k imports per 20 requests | Bounded subquery instead of id lists | ~43 ms |
| Event log rebuilt from the database each request | 53 ms of 71 ms | Log kept and grown incrementally like a live consumer; provider caches the rows it has read (never past the cursor); earlier cursors are truncated replays from the nearest checkpoint | rewind 5 ms · forward 33 ms |
| Same state computed twice per forward step (novelty walk + response) | — | Response reuses the walk's state | forward 37 ms (under concurrent load) |

## Stage timings after optimisation

| Stage | Pakistan v India, MCG (T20, 251 balls) | Women's WC final (ODI, 591 balls) |
|---|---|---|
| As-of baselines, once per match (batched) | 1.1 s | 1.3 s |
| Event ingestion (dedupe, ordering) per event | 11.6 µs median · 23 µs p95 | 11.8 µs · 22 µs |
| State update, one delivery | 21 µs median. The p95 of 1.6 ms is the end-of-over checkpoint copy. | 22 µs · 2.3 ms |
| Late correction: recompute from checkpoint v full replay | 19 ms (35 balls re-applied) v 56 ms; identical hash | 31 ms (30 balls) v 209 ms; identical hash |
| Right Now generation, per ball | 0.12 ms median · 0.25 ms p95 | 0.19 ms · 0.29 ms |
| Next-ball prediction (model only) | 4.4 µs | 4.3 µs |
| Server response, forward step (ball arrives) | **37 ms** median · 63 ms p95 | **42 ms** · 67 ms |
| Server response, rewind | 3.9 ms · 7.5 ms | 7.6 ms · 15 ms |
| Play: pick and reveal | 7.8 ms | 14 ms |

Historical rows are never rebuilt per delivery. Career, battle, pair and competition baselines are computed once per
match (only from matches before it), and match state is incremental.

## UI update on a phone

Tap "next ball" until the new position shows: 390 × 844 viewport, Chromium, 25 taps, WPL final.

| CPU | Median | p95 | Max |
|---|---|---|---|
| Unthrottled | 74 ms | 99 ms | 118 ms |
| 4× throttled (an ordinary phone) | 132 ms | 162 ms | 193 ms |

Autoplay intervals are 3 s (1×), 1.5 s (2×) and 0.6 s (5×), all well above the update cost. "End" jumps straight to the final state.

## Reconciliation throughput

Replaying every event through the engine and reconciling with Cricsheet's recorded innings totals: see
`docs/data/live-replay-validation.md`.
