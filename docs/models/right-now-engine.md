# "Right Now" intelligence, Record Watch and Timeline (Phase 5)

Code: `pipeline/cricintel/live/insights.py` (ranking, Record Watch, timeline), `baselines.py` (history) and
`service.py` (novelty walk). Status: DERIVED. Deterministic, with no language model.

## Inputs, and the leakage rule

- The engine state at the cursor: only balls 1..N, plus the identity of who faces and bowls next.
- Baselines (`baselines.py`), built only from covered matches that **started before the replayed match**, in the same
  format and gender:
  - batter strike rates by innings stage (new 0–9, settling 10–29, set 30+ balls faced) and by phase;
  - bowler economy by phase;
  - battle and pair histories;
  - covered competition records;
  - reference distributions: score and wickets at each over, the 99th percentile of the longest dot-ball run per innings, and the 99th percentile of runs per over.
- They are built once per match in a handful of batched scans (about 2–4 s), then held in memory. Per-ball work is dictionary lookups (Right Now: 0.13 ms median per ball).

## Candidate types

| Type | Shown when | Unusualness | Minimum evidence |
|---|---|---|---|
| battle | striker v bowler about to meet | log SR ratio v batter's usual (scaled at ×1.6), or dismissals v expected | 12 prior balls; batter usual ≥ 120 balls |
| batter_stage | batter has faced ≥ 10 balls | log ratio of SR now v usual at the same stage | 100 prior balls at that stage |
| bowler_spell | current spell ≥ 12 balls | economy difference v usual in this phase (scaled by 3 in T20, 2 in ODI) | 120 prior balls in the phase |
| partnership | stand ≥ 6 balls | above the pair's average (bonus when above their best) | 3 prior stands |
| wickets_down | ≥ 2 down | share of covered innings this many down by this over ≤ 20% | 200 innings |
| score_rate | from over 2 | difference from the average score at this over (25 T20 / 40 ODI scale) | 200 innings |
| chase | required rate differs from current by ≥ 1.5 | gap ÷ 6 | n/a (factual) |
| dot_sequence | dot run ≥ the 99th percentile | fixed 0.9 | reference set |
| big_over | over runs ≥ the 99th percentile | fixed 0.85 | reference set |
| wicket_burst | 3 wickets in ≤ 18 legal balls for ≤ 20 runs (the Phase 4 collapse rule) | fixed 0.8 | n/a (factual) |

There are no chase-success-from-this-position frequencies. That would be a win probability under another name, and
win probability is research-gated (see `win-probability-research.md`).

## Ranking

```
score = 0.35 relevance + 0.20 sample + 0.30 unusualness + 0.05 recency + 0.10 recognisability
```

- Each dimension is 0–1. A candidate is shown only if score ≥ 0.45 and unusualness ≥ 0.25.
- **Diversity:** at most one item per type and one per subject (player, pair or team); top 4.
- **Novelty:** a candidate's key includes the bucket that makes it true (e.g. `stage|kohli|31+|down`). An item is **New** only if that key has never qualified earlier in the match.
  - This is a causal walk over balls 1..N, so ball n's flags depend only on balls 1..n (tested).
  - If nothing is new, the Match Centre says "Nothing statistically new on this ball" and keeps the earlier items, muted.

Every item shows its dimension scores, the method, and an evidence link (which leaves the replay and says so).

## Measured frequency (real data, whole matches)

| Match | Balls | Balls with something new | Share |
|---|---|---|---|
| Pakistan v India, MCG 2022 (T20I) | 251 | 37 | 14.7% |
| IPL 2023 final (D/L) | 216 | 46 | 21.3% |
| WPL 2026 final | 246 | 43 | 17.5% |
| Women's World Cup 2025 final (ODI) | 591 | 102 | 17.3% |
| Men's World Cup 2023 final (ODI) | 569 | 79 | 13.9% |
| MI v Kings XI Punjab 2020 (two super overs) | 269 | 47 | 17.5% |
| Women's T20 World Cup 2026 final | 235 | 34 | 14.5% |

A first draft only compared each ball with the previous ball. It flagged 76 of 251 balls (30%) as new, because strike rotation kept re-announcing the same battle. The match-long memory replaced it.

## Record Watch

- **Approaching** (milestones, not records): batter within 10 of 50/100/150/200; bowler on 4 wickets.
- **Covered-data records:**
  - individual score or team total within 25–30 of the covered competition record;
  - stand within 25 of the covered record for that wicket;
  - most wickets in an innings;
  - moving up the covered competition run-scoring list.
- **Wording:** always "in covered … data before this match", with Cricsheet's completeness status. Example: "Within CRICINTEL's covered data, not an official record (Cricsheet completeness for this competition: unknown)". No item claims an official record.
- **Caveat:** Cricsheet files early editions of some tournaments under different names, so a covered-data "record" can understate the official one. That is why the wording never claims "official".

## Timeline

Factual events only, newest first, each linked to its delivery:
- wickets (with how out), retirements;
- batter 50/100/150/200, partnership 50/100/150/200/250, team landmarks every 50, bowler reaching 3+ wickets;
- innings start/end, target revisions;
- overs and dot-ball runs at or above the 99th percentile of covered matches before this one.

There are no editorial labels such as "game-changing", "turning point" or "momentum".
