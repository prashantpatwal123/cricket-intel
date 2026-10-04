# Phase 8 performance-budget report

**Budget (Phase 8 brief):** API under 500 ms cold and under 50 ms warm; bundle size; page render.

**Method:**
- API: `python -m cricintel.fan.bench` (raw numbers in `docs/data/benchmarks-phase8.json`). Run after an API restart and only once `/api/health` reported the background warm-up finished (`warmed: true`, 63–71 s), so cold numbers are not measured under warm-up contention.
  - Cold = first request for that exact URL.
  - Warm = median of 5 repeats.
- Page render: `scripts/perf-phase8.mjs`. Phone 390 px, fresh browser per load, median of 3, unthrottled and with 4× CPU throttle.
- Bundles: `next build` output.

## API (final run, measured 2026-10-04 18:31:31)

All 28 measured endpoints are **under 500 ms cold** (worst 355.1 ms). 27 of 28 are **under 50 ms warm**; the one exception is Play next-moment (below).

| Endpoint | Cold ms | Warm ms (median of 5) |
|---|---|---|
| Home (first 60 seconds) | 8.2 | 3.5 |
| Battle: every meeting + halves (not pre-warmed) | 28.4 | 3.5 |
| Battle: every meeting (Kohli v Zampa) | 23.9 | 4.8 |
| Ask with follow-ups: dismissed by | 49.4 | 41.5 |
| Play: next moment | 104.4 | 58.7 ⚠️ exception |
| Rabbit-Hole: player (not pre-warmed) | 33.9 | 3.5 |
| Rabbit-Hole: player, with session memory | 3.6 | 3.0 |
| Rabbit-Hole: battle | 84.8 | 3.4 |
| Rabbit-Hole: match | 126.4 | 3.5 |
| Rabbit-Hole: innings | 62.7 | 2.6 |
| Rabbit-Hole: record | 2.7 | 2.3 |
| Player home (not pre-warmed) | 349.9 | 4.6 |
| Player home (Kohli) | 7.1 | 6.8 |
| Matchup discovery | 119.1 | 4.0 |
| Similar players | 7.2 | 2.6 |
| Compare V2 (Kohli v Rohit) | 205.3 | 4.0 |
| Compare V2 (Bumrah v Starc) | 355.1 | 3.8 |
| Record book catalogue | 7.7 | 6.2 |
| One record | 3.6 | 2.8 |
| Daily discovery (Explore) | 6.4 | 5.8 |
| On This Day | 345.4 | 2.4 |
| Play moment (innings) | 20.6 | 1.6 |
| Ask: scored fastest against | 24.7 | 21.7 |
| Ask: compare in chases | 34.3 | 33.6 |
| Reference: match page | 332.5 | 4.9 |
| Reference: player profile | 239.0 | 3.5 |
| Reference: battle | 124.7 | 3.0 |
| Reference: live replay step | 239.3 | 8.5 |

### Changes made (profiled first)

| Endpoint | Profile finding | Change | Warm before → after |
|---|---|---|---|
| `/api/players/{id}/profile` | full recompute of a static historical profile on every request | bounded response memo keyed by the full query (`_memo` in `api.py`, max 2,048 entries, cleared on restart, i.e. on every data rebuild) | 242 → 3.9 ms |
| `/api/battle` | same | same memo | 191 → 2.8 ms |
| `/api/whn/next` (Play) | per-moment state = 4 queries. Two genuine bottlenecks: a point lookup `WHERE delivery_id = ?` scanning all 3.3M balls (20–84 ms) and the bowler-figures query (22–51 ms) | adds `match_id = ?` (the delivery id's prefix: verified 0 exceptions across 3,298,136 balls) so DuckDB prunes row groups; lookup 25 → 9 ms. Same fix on reveal. The bowler-figures rewrite saved only ~8 ms and risked double-counting on the 24 deliveries with two dismissal rows, so it was **not** applied | 137 → 58 ms |
| `/api/health` | no way to know warm-up had finished | new endpoint: `{ok, warmed, warm_seconds}`; Phase 8 Home now pre-built by the warm-up | — |

### Justified exception: Play next-moment, ~59 ms warm

- Each request draws a **new random moment** by design, so a "warm" request is still a cold computation for a different moment. Caching by moment ID would not help; serving from a precomputed pool would change the random draw just to win a synthetic number. The brief forbids both.
- Its remaining cost is the bowler's figures so far and the recent-balls window, both pruned to one match.
- The UI already **prefetches the next moment during each reveal**, so after the first ball the user never waits on this call.
- Its effect on the experience is measured directly below: prediction controls are usable 0.4 s after opening Play.

## Page render (phone, 390 px)

Time from navigation to the hero's first meaningful element.

| Page (element) | Unthrottled | 4× CPU throttle |
|---|---|---|
| Home (five examples) | 281 ms | 1,148 ms |
| Player (defining insight) | 432 ms | 1,329 ms |
| Battle (battle hero) | 437 ms | 1,546 ms |
| Match (story beats) | 350 ms | 1,364 ms |
| Ask (answer + follow-ups) | 398 ms | 1,142 ms |
| **Play: prediction controls usable** | **336 ms** | 1,060 ms |
| **Play: first reveal after one tap** | 694 ms | 1,629 ms |

The Phase 8 target for a new user (under 5 s from opening Play to the first prediction) is met with a wide margin even at 4× throttle.

## Bundles (First Load JS)

| Route | Phase 7 (48acece) | Phase 8 |
|---|---|---|
| shared by all | 102 kB | 102 kB |
| `/` | 112 kB | 110 kB |
| `/players/[id]` | 137 kB | 139 kB |
| `/battle` | 123 kB | 124 kB |
| `/match/[id]` | 112 kB | 113 kB |
| `/ask` | 120 kB | 121 kB |
| `/play` | 121 kB | 121 kB |

No new runtime dependency was added. Every hero route is ≤ 139 kB First Load JS.
