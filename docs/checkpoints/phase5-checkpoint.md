# Phase 5 checkpoint: Historical Live Lab, Match Centre and second-screen intelligence

**Status: internal preview only.** Nothing is deployed. The Cricsheet licence question is drafted but **not sent**.
Attribution and internal-preview marks are unchanged, and every replay screen says **HISTORICAL REPLAY — NOT LIVE**.

The baseline was `e4f6553` (Phase 4). All evidence is from real Cricsheet data. Synthetic events are used only in engineering tests.

## Gate result

| Check | Result |
|---|---|
| Phase 5 phone and desktop journeys (`scripts/screenshots-phase5.mjs`) | 0 errors, 0 failed assertions, 0 px horizontal overflow, **0 spoiler leaks** in every `/api/live` response the browser received |
| Phase 2 / 3 / 4 regression journeys | 0 errors each; Phase 4 also 0 failed assertions |
| `pytest` | **89 passed**: 63 existing, 17 engine (`test_phase5_engine.py`), 9 service (`test_phase5_live.py`) |
| Engine reconciliation with Cricsheet's recorded innings totals | **All 10,247 T20/ODI matches, 20,475 innings, 3,298,987 deliveries (super overs included): 0 mismatches** in runs, wickets and legal balls (`python -m cricintel.live.validate`, 28 min) |
| Edge-case reconciliation (real matches) | 0 mismatches in every case (table below) |
| `tsc`, `next build` | pass |

Cancelled prefetches (`net::ERR_ABORTED`, caused by the test's own navigation) are counted separately and are not failures.

## The 20 gate items

1. **Event-driven match-state engine:** `live/engine.py`.
   - A pure fold, one delivery at a time.
   - Derives score, wickets, overs, striker and non-striker, bowler, partnership, run rates, target, balls remaining, batter and bowler spell state, recent balls, phase and the current battle.
   - Look-ahead tests: state at N is unchanged when every later ball is mutated, and equals a log that never contained them.
2. **Historical live replay:** `/live-lab` and `/live-lab/[id]`.
   - Seven matches: Pakistan v India (MCG 2022), IPL 2023 final (D/L), WPL 2026 final, Women's World Cup 2025 final (women's ODI), Men's World Cup 2023 final (ODI), MI v Kings XI Punjab 2020 (two super overs), Women's T20 World Cup 2026 final.
   - Controls: play/pause, ‹ › ball, « » over, speed 1×/2×/5×, jump to innings or End (instant).
3. **Match Centre:** above the fold on a 390 px phone are the replay flag, score, overs, target and requirement, striker v bowler on a schematic pitch, non-striker, recent balls and partnership. Then come "What matters now", the battle, batter and bowler states, and the prediction.
4. **Right Now ranking:** `live/insights.py`.
   - Ten candidate types, five transparent dimensions, thresholds, one per type and per subject.
   - Novelty is causal and match-long; "Nothing statistically new on this ball" when nothing changed.
   - Measured: something new on 14–21% of balls (`docs/models/right-now-engine.md`).
5. **Current Battle:** covered history before this match (balls, runs, SR v usual, outs v expected, date range, small-sample flag) and this match's balls. "Open battle" keeps the context (`from=live:<id>:<ball>`), shows a back-to-replay banner, and warns that the full page includes later meetings.
6. **Batter State:** runs (balls), SR, 4s/6s, dots, last balls faced, and a neutral stage (new / settling / set). Compared with the batter's usual SR at that stage before this match. No psychological words; a test scans for them.
7. **Bowler State:** figures, spell number and overs, spell runs, wickets, dots and boundaries, economy v usual in this phase, and the current or last over (labelled with whose over it was). Links to the bowler fingerprint and the full spell (marked as leaving the replay).
8. **Partnership live:** runs, balls, scoring split, strike split, boundary runs, extras, and covered history for the pair before this match. "Observed outcomes only", with no chemistry claim.
9. **Chase:** target, needed, balls left, required and current rate, with D/L targets labelled. Situation Difficulty — Experimental is shown ball by ball only with the experimental flag on, labelled "not pressure, not a win probability" and in-sample where applicable.
10. **What Happens Next V3:** "Play this match".
    - Pick DOT/1/2/3/4/6/WICKET, then exactly one ball is revealed. Shown: outcome, your points, the model's pick and points, its probability for what happened, and a session score.
    - The model is labelled in-sample for matches before its 2024 cutoff.
11. **Spoiler-safe API and leakage tests:**
    - The server reads only balls up to the cursor (tested) and sends nothing later.
    - No result, later delivery id or match length appears before the end (tested, including in the browser).
    - The jump menu lists only innings 1–2 and innings already under way, because listing later innings would reveal a super over.
12. **Event timeline:** factual events newest first, each linked to its delivery. No editorial labels; a test scans for them.
13. **Record Watch:** milestones (labelled "not a record") and covered-data records, always worded "in covered … data before this match" with Cricsheet's completeness status. Never "official".
14. **Contextual Match Ask:**
    - "this batter / bowler / pair / team / match" resolve deterministically and appear as chips.
    - Every answer is limited to matches before this one (`before_date`).
    - "This match" is answered from the replay so far.
    - Found and fixed: some Ask question types silently ignored filters, so a mid-replay answer cited a later match. Every type now declares the filters it supports and refuses others with an explanation.
15. **Provider-neutral live-data contract:** `live/contract.py`, `docs/architecture/live-data-contract.md`. It covers duplicates, out-of-order and delayed events, corrections, retractions, inserts, changed attribution, super overs, revised targets and abandonment.
16. **Correction and replay determinism:** insert, update and retract tests; arrival-order shuffles with duplicates give identical hashes; recompute from a checkpoint equals a full replay (and is 3–7× faster after a late correction).
17. **Win-probability verdict: not shipped.** See `docs/models/win-probability-research.md`.
    - Chronological holdout (test from 2024), match bootstrap, rules fixed in advance.
    - ODI men and ODI women REJECT: over-confident, slope 0.75 and 0.84.
    - T20 men and women pass the pre-registered rules (Brier 0.163 / 0.161, slope 0.99 / 1.00, ECE 0.013 / 0.013) but are still not displayed:
      - a wicket can raise the probability in some states;
      - club T20 is poorly calibrated (ECE 0.07 men);
      - the start of a chase is the weakest moment;
      - display needs owner approval.
18. **Competitive research:** `docs/research/second-screen-competitive-review.md`. Every product site was blocked by the network policy, so all evidence is SECONDARY (search-index summaries) and labelled. Above-the-fold layouts are "unverified", and the doc includes a manual audit checklist. Findings:
    - Published win-probability models disclose no calibration.
    - Pressure and Luck indices are shown as headline numbers.
    - No documented live batter-v-bowler module was found.
19. **Performance:** `docs/data/benchmarks-phase5.md`.
    - Server forward step 37–42 ms median (from about 150 ms after profiling); rewind 4–8 ms.
    - Tap-to-screen 74 ms (132 ms at 4× CPU throttle).
    - Event ingestion 12 µs, state update 21 µs, Right Now 0.12 ms.
20. **Screenshots:** `docs/screenshots/phase5/`, 18 phone and 6 desktop, inspected.

## Edge cases replayed on real matches (`python -m cricintel.live.validate --edge`)

| Case | Matches | Innings | Deliveries | Mismatches |
|---|---|---|---|---|
| Retired hurt | 25 | 49 | 10,173 | 0 |
| Retired out | 25 | 50 | 5,920 | 0 |
| Retired not out | 11 | 22 | 3,965 | 0 |
| Obstructing the field | 20 | 42 | 7,297 | 0 |
| Timed out | 2 | 4 | 812 | 0 |
| Hit the ball twice | 1 | 2 | 243 | 0 |
| Stumped | 25 | 50 | 12,561 | 0 |
| Run out | 25 | 50 | 10,862 | 0 |
| Hit wicket | 25 | 50 | 8,634 | 0 |
| Super overs (all 73 covered matches) | 73 | 298 | 22,360 | 0 |
| D/L revised targets | 100 | 200 | 36,456 | 0 |

Wides, no-balls, byes, leg-byes, a non-striker run out, a stumping, retired hurt (and return), innings transitions,
chase completion, ties and super overs, revised targets, duplicates, out-of-order arrival and corrections are also
covered by engine unit tests on hand-built events.

## Bugs found and fixed during the phase

- The `balls` view excludes super overs, so the first replays silently dropped them. The provider now reads raw deliveries; all 73 super-over matches reconcile.
- Super-over chases have no stored target. It is derived from the previous super over at the break, so "target reached" is correct.
- `ball_in_over` repeats after a wide, so it is not an ordering key. The provider computes a true per-over delivery index. 144 real overs have more than six legal balls, and labels count within the over.
- Novelty compared only with the previous ball and flagged 30% of balls as new. A match-long causal memory brought it to 14–21%.
- Ask V3 paths dropped unsupported filters silently, a future-data leak in Match Ask. Fixed with a supported-filter guard and a shared builder.
- `body { overflow-x: hidden }` made the body the scroll container and broke sticky headers. Changed to `clip`.
- The sticky header took about 43% of a phone screen. It was compacted to one score line and one control row.
- The bowler panel showed the previous over (another bowler's) as if it were his. It is now labelled with the bowler's name.
- Probabilities shown after a reveal looked like they belonged to the revealed ball. They are now labelled "Model, next ball".
- The notification budget counted wickets and suppressed a 50 in wicket-heavy innings. Wickets are now excluded.
- Performance: full-table scans per request, per-parameter driver imports and per-request log rebuilds were profiled and removed.

## Rejected or deliberately limited

- **Win probability:** not shipped (item 17).
- **Chase-success-from-this-position frequencies:** not used in Right Now, because they are a win probability under another name.
- **Notifications:** design and planner only, nothing sent. Measured 9–19 per match with the default opt-in and 14–32 with every type (`docs/architecture/notifications.md`).
- **Spatial visuals:** no trajectories, shot directions, field positions, line/length or contact points. The pitch is schematic and says so.
- **Not built (per brief):** accounts, social features, comments, fantasy, betting odds, payments, native apps, push, AI commentary, 3D.
- **Phase 2–4 rejections stand:** clutch, WWYD, momentum, turning points, pace/spin.

## Known limitations

- Next-ball model (trained before 2024-01-01) and SDX (before 2025-01-01) are in-sample for earlier matches; the UI says so.
- Cricsheet records only the final D/L target, so a revised target applies from the start of the chase and is labelled.
- Covered-data "records" can understate official ones where Cricsheet files early editions under different competition names.
- Spells are defined as overs with at most one over between them (bowling alternate overs). The data does not record ends.
- A competition's first replay costs 1–2 s for baselines. Featured matches are pre-built at startup.
