# Phase 4 performance pass — before / after

Profiled first, then fixed the measured hot spots. Server-side time from `curl -w %{time_total}` against the local
FastAPI process on the full Cricsheet dataset (10,247 matches, 3.30 M deliveries). Target: < 500 ms server-side for
cached and common requests.

## What was slow, and the fix

| Hot spot | Before | After | Fix |
|---|---|---|---|
| API startup (build in-memory views, materialise context) | 10.4 s | 0.02 s | Persisted read-only `derived/working.duckdb`, validated by a `_meta` table (version, build time, flags). Rebuilt by `python -m cricintel.precompute --dataset cricsheet`. |
| Discovery generators (cold) | states 3.5 s, comebacks 3.2 s | 3.4 s total, **at precompute time**; served in ~8 ms | `gen_comebacks` N+1 queries → one window query; results cached on disk. |
| Match page | 1.9 s | ~280–330 ms cold | Events and in-competition ranks computed in Python over one ball query instead of a query per event. |
| Search index | — | 2.1 s build at precompute; 2–19 ms per query | Inverted index with prefix matching, cached as `derived/search_index.json`. |
| Feed pools | — | precomputed (`feed_pools.json`); 5–8 ms per request | Pools built once per dataset; daily selection is cheap. |

## Endpoint timings after the pass

Cold = first request after an API restart, on entities the startup warm-up does **not** pre-load.
Warm = second request (in-process response cache keyed by dataset stamp).

| Endpoint | Cold | Warm |
|---|---|---|
| `/api/match/1513703` (WPL final) | 302 ms | 5 ms |
| `/api/story/match/1513703` | 258 ms | 4 ms |
| `/api/library/spells?cat=death_spells` | 392 ms | 5 ms |
| `/api/related?type=match` | 56 ms | 3 ms |
| `/api/players/{low-coverage}/career` | 28 ms | 3 ms |
| `/api/battles/similar` | 11 ms | 12 ms (not cached; computed from an in-memory feature space) |
| `/api/methodology` | 83 ms | 5 ms |
| `/api/feed` | 8 ms | 7 ms |
| `/api/search` | 3 ms | 3 ms |
| `/api/competition` (IPL, warmed at startup) | 685 ms before warm-up | 7 ms |
| `/api/rivalry` (India v Australia, warmed at startup) | 721 ms before warm-up | 9 ms |

Earlier cold measurements of first-time pages: career 270 ms, libraries 147–385 ms, related 156 ms, stories 77–243 ms.

Startup warm-up thread (non-blocking): names, search index, discovery, similar-battle feature spaces, the 10 largest
competitions and 8 most-played rivalries per gender.

## Remaining over-target cases

None measured over 500 ms once warm-up has run. Competitions and rivalries outside the warmed set take 0.5–0.8 s
on first request, then are cached.

## Precompute step

```
python -m cricintel.precompute --dataset cricsheet          # incremental: only stale steps
python -m cricintel.precompute --dataset cricsheet --full   # everything
```

Steps: context → situation_experimental → working_db → search_index → discovery (both scopes) → explore → feed_pools.
`derived/` is git-ignored; nothing derived is committed.
