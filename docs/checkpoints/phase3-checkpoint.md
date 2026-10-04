# Phase 3 checkpoint: visual cricket intelligence + context engine

Status: **internal preview only** (match-data licence pending). Real Cricsheet data in every screenshot.
Evidence: `docs/screenshots/phase3/` (`m*` 390 px phone, `d*` 1280 px desktop) from `scripts/screenshots-phase3.mjs`,
run with `CRICINTEL_EXPERIMENTAL=1`. Last run: **0 console errors, 0 HTTP errors, 0 px horizontal overflow** at every
step (`report.json`). Tests: 34 passed (11 new). Phase 2 drill-downs preserved.

## Product evidence

| # | Deliverable | Where | Demonstrated (real data) |
|---|---|---|---|
| 1 | Visual Cricket Engine | `web/lib/viz/model.ts`, `web/components/viz/*` | One typed model: every element carries OBSERVED / DERIVED / RECONSTRUCTED / MODELLED / ILLUSTRATIVE / UNKNOWN; tap any element to inspect it (m06). Renderers: Delivery Scene + Dismissal Theatre, Match Situation, Outcome Map, Innings Journey, Spell Journey. SVG only, no 3D. |
| 2 | Delivery Replay | `/delivery/[id]` | Kohli v Shaheen, 17.6, T20 World Cup 2022 (m05): match, competition, date, innings, over.ball, score before/after, batter, bowler, non-striker, runs, extras, wicket, fielder/keeper, recent and following balls, result. ← / → walks the innings. No ball path drawn. Theatre for keeper catch, bowled, LBW, stumped, run out, field catch (m07-*). |
| 3 | Innings Story | `/innings/[m]/[i]/[pid]` | Kohli 82* v Pakistan (m08, m09, d03): ball outcomes, cumulative runs, boundaries, dots, partner balls, partner wickets, strike changes (49), milestone (50 off 43), partnerships (113 with Pandya), phases, rolling SR; scrubber; ball → replay. Women: Meg Lanning 152* (m24). |
| 4 | Context Engine | `analytics/context.py`, `/context` | 27 per-delivery features for 3.3M deliveries, T20 and ODI rules kept separate (12- v 30-ball recent windows, ±1.0 v ±0.5 chase bands). |
| 5 | Batter state analysis | Player → When they change | Kohli T20 (m12): balls 1–10…51+, wickets down, setting/chasing, ahead/around/behind, phase; v own baseline and position-band peers; "clear" at 99% because ~20 states are tested. Low-sample player correctly gets no clear change (m14). |
| 6 | Partnership Intelligence | `/partnerships`, Player → Partners | Best pairs with sample thresholds (m15), pair history (m16), biggest stands, "who brings out the best" adjusted for phase and season (m13). |
| 7 | Bowler Fingerprint | Player → Bowling | 12 dimensions incl. new: wickets v new batters, economy v set batters (m10); bowler state analysis (batter stage, defending, chase state, spell over, wickets, phase). |
| 8 | Spell Story | `/spell/[m]/[i]/[pid]` | Bumrah 6-19 v England 2022 (m11): over-by-over runs/dots/boundaries/wickets, batters faced, state per over, longest dot run; Ecclestone, women's T20 World Cup 2026 (m25). |
| 9 | What Happens Next v2 | `/play` | Match Situation visual before the pick (m17); reveal animates only the recorded outcome and score change (m18); session analytics: predictions, accuracy, points, model accuracy, you v model, calibration bands, strongest/weakest call (m19). |
| 10 | Ask Cricket v2 | `/ask` | All 8 brief questions resolve (m20–m23): balls-faced ranges, required rate, overs ranges, chase state, batter stage, bowler summaries, partnership boards, dismissal lists (rendered as deliveries), middle→death change. First-name resolution ("Rohit"). Still parser → validated query → engines; no LLM. |
| 11 | Discovery engine | Explore (m03, m04) | ~730 candidates from 7 generators (matchups, dismissal patterns, partnerships, state changes, trends, records, comebacks); ranked by unusualness, sample, recency, recognisability; diversified; WHY + ranking parts; every card links to evidence. |
| 12 | Compact preview notice | Shell (m01, m02) | Full notice on first visit; then a 26 px pill "INTERNAL PREVIEW · DATA LICENCE PENDING" that expands to the same full text. |

## Separately reported

- **Pressure research & validation:** `docs/research/pressure-methods-review.md`, `docs/models/situation-difficulty.md`,
  `docs/models/situation-difficulty-validation.md`. SDX v0.1 is behind a flag, labelled "Situation Difficulty — Experimental".
- **Visual data-source research:** `docs/research/visual-data-sources.md`; dormant contracts in `docs/architecture/visual-data-contracts.md`.
- **Rejected:** "What Would You Do?" (`docs/research/what-would-you-do.md`); the word "clutch" (no split-half persistence);
  a first-innings difficulty measure (no objective anchor); momentum inputs; pace/spin/style splits (metadata coverage).
