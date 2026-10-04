# Phase 7 performance: fan layer

I profiled first, then optimised.

**Reproduce:**
- API: `python -m cricintel.fan.bench --base http://localhost:8000` (raw results in `benchmarks-phase7.json`).
- Phone UI: `scripts/uitime7.mjs` (see below).

**Setup:**
- Machine: the development container.
- Server: the API restarted, then measured after its startup warm-up finished.
- "Cold" means the first request for an entity. Where possible these are entities the warm-up does not pre-load (players outside the 40 most-capped).
- Target: under 500 ms server-side, as in Phase 4.

## Profile-driven fixes

| Hot spot (found by cProfile / per-query timing) | Before | Fix | After |
|---|---|---|---|
| Player role decided by counting balls faced/bowled in 3.3M deliveries (twice per player page) | ~200 ms of each player request | Sum the per-innings tables (≈170k rows); `lru_cache` per player | <5 ms |
| Player graph neighbours: ~10 keyed queries over innings, battles and partnerships | 300–700 ms cold | `fan/index.py`: in-memory indexes (best innings, best spells, battles by batter/bowler, partners, main competition, latest match, dismissal counts), built once in 1.9 s by the warm-up | 30–60 ms cold, 3 ms warm |
| Play moments scanned all deliveries for one innings | 100–200 ms | Read the match-sorted live tables (zone maps skip to one match) | ~20 ms |
| Player home: `hero` computed 3× per request; strengths-engine league baselines and fingerprint peer pools built on first use | 580–650 ms cold | `hero` cached; warm-up pre-builds the 12 league baselines and 16 peer pools (both scopes) | 323 ms cold |
| Explore daily discovery built on the first request of the day | 812 ms | Warm-up builds today's selection | 4 ms |

## Endpoint timings (after)

| Endpoint | Cold | Warm (median of 5) |
|---|---|---|
| Rabbit-Hole: player (not pre-warmed) | 52 ms | 2.9 ms |
| Rabbit-Hole: player, with session memory | 2.5 ms | 2.2 ms |
| Rabbit-Hole: battle | 86 ms | 2.9 ms |
| Rabbit-Hole: match | 118 ms | 2.7 ms |
| Rabbit-Hole: innings | 49 ms | 2.6 ms |
| Rabbit-Hole: record | 2.7 ms | 2.3 ms |
| Player home (not pre-warmed) | 323 ms | 3.1 ms |
| Player home (Kohli, pre-warmed) | 3.2 ms | 3.0 ms |
| Matchup discovery | 114 ms | 3.5 ms |
| Similar players | 6.1 ms | 2.0 ms |
| Compare V2: Kohli v Rohit | 188 ms | 3.4 ms |
| Compare V2: Bumrah v Starc | 333 ms | 5.3 ms |
| Record book catalogue | 9.8 ms | 6.0 ms |
| One record | 3.3 ms | 2.4 ms |
| Daily discovery (Explore) | 3.5 ms | 2.9 ms |
| On This Day | 282 ms | 2.7 ms |
| Play moment (innings) | 19 ms | 1.9 ms |
| Ask: "Who has Kohli scored fastest against?" | 138 ms | 21 ms |
| Ask: "Compare Kohli and Rohit in chases" | 31 ms | 34 ms |
| *Reference:* match page (Phase 4: 302 ms cold / 5 ms warm) | 298 ms | 4.6 ms |
| *Reference:* player profile | 206 ms | 203 ms |
| *Reference:* battle | 148 ms | 124 ms |
| *Reference:* live replay step (Phase 5: first load builds baselines) | 244 ms | 6.5 ms |

**Session awareness costs nothing measurable.** Neighbour lists are cached per entity, and the session-dependent ranking is pure Python over 8–30 edges (about 0.1 ms).

The reference endpoints match their Phase 4/5 figures, so the fan layer did not slow existing pages. Startup warm-up grew by about 25 s of background work. It is non-blocking: the server answers immediately.

**Precompute steps added:**
- similarity index with holdout validation: about 15 s;
- Records V2 (172 records): about 12 s.

## Phone UI: time until "Explore next" is rendered

Viewport 390 × 844, Chromium, median of 3 loads. Explore next is the last section of each page, so the content above it renders earlier.

| Page | Unthrottled | 4× CPU throttle |
|---|---|---|
| Player (Kohli) | 0.98 s | 1.45 s |
| Player (Bumrah) | 0.94 s | 1.32 s |
| Battle (Kohli v Zampa) | 0.44 s | 0.87 s |
| Match (MCG 2022) | 0.24 s | 0.80 s |
| Innings (Kohli 82*) | 0.45 s | 0.74 s |
| Record | 0.21 s | 0.61 s |
