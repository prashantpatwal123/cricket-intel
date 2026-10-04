# Phase 4 checkpoint — knowledge graph, stories & exploration

Status: **INTERNAL PREVIEW ONLY.** The licensing gate still stands. The Cricsheet match-data licence position is
unresolved, the question to Cricsheet is drafted but **not sent**, and nothing is deployed or published. Attribution
and internal-preview marks are on every page and every share card.

All evidence below is from the real Cricsheet dataset (10,247 matches, 3,298,136 deliveries, 8,469 players), captured
by `scripts/screenshots-phase4.mjs`. Raw log: `docs/screenshots/phase4/report.json`.

## Gate result

| Check | Result |
|---|---|
| Phase 4 phone + desktop journeys (`screenshots-phase4.mjs`) | 0 errors, 0 failed assertions, 0 px horizontal overflow on every step |
| Console errors / page errors / HTTP ≥ 400 / failed requests | 0. (248 `net::ERR_ABORTED` were counted separately: these are Next.js prefetches cancelled by the test's own navigation, not failures.) |
| Phase 2 regression (`screenshots-phase2.mjs`) | 0 errors, no overflow |
| Phase 3 regression (`screenshots-phase3.mjs`) | 0 errors, no overflow |
| `pytest` (adapter, analytics, Ask/game, import, QA, Phase 3, Phase 4) | 63 passed |
| `tsc --noEmit`, `next build` | pass |

## Evidence by item

1. **Universal Search** is distinct from Ask; each page says which does what. Grouped results (real queries → top group):
   "Virat Kohli" → Players; "Kohli vs Zampa" → Battles; "India Pakistan 2022" → Matches: Pakistan v India;
   "Bumrah 6/19" → Spells: Jasprit Bumrah 6/19 v England; "Mandhana partnerships" → Partnerships;
   "2023 World Cup" → Editions: ICC Cricket World Cup 2023/24; "death overs economy" → Records;
   "RCB v CSK" → Rivalries: Chennai Super Kings v Royal Challengers Bengaluru. Index of ~92k entities; 2–19 ms per query.
2. **Knowledge graph** is relational: `bat_innings`, `bowl_innings`, `battles`, `team_results` (canonical franchise names),
   `partnerships`, `spells`, all in DuckDB. No graph DB: every traversal needed is a 1–2 hop indexed join that runs
   in milliseconds, so there was no benchmark case for one. Tests check that innings runs equal ball sums, wickets
   equal credited dismissals, and canonical team names.
3. **Match page** (Pakistan v India, MCG 2022-10-23; WPL final 2026): scoreboard, worm and Manhattan, factual key
   events (biggest over, collapse, milestones, 4-wicket hauls), now **sorted chronologically**, each with its
   definition. **Turning points are not shown** (see Rejected). The experimental SDX swings are labelled MODELLED and
   "not a validated turning-point measure".
4. **Competitions respect coverage**: IPL "Cricsheet holds 1243 of the 1243 … (100.0%)" (COMPLETE); WPL 88/88;
   ICC Men's T20 World Cup shows "COMPLETENESS UNKNOWN … covered-data totals, not official tournament history".
   Edition chips show the recorded final's winner, or stay blank where no final is in the data.
5. **Rivalries**: India v Australia, RCB v CSK (35 matches, renamed franchises grouped with a visible note), and an
   India women team overview. Results by year now show **gap years** (CSK–RCB 2016–17, when CSK were suspended) as
   dashed stubs, never as zeros.
6. **Career Explorer**: selecting 2016 for Kohli rewrites the page (739 ODI runs, 1,614 T20 runs, 28 innings).
   Gaps are hatched and not interpolated. Low-coverage player (Kartik Sharma, 2 covered years) renders with "unknown"
   metadata chips rather than guesses.
7. **Innings Library**: 8 defined categories with format minimums. The default scope is "full members & leagues",
   shown as a visible toggle (associate fixtures otherwise dominated). WPL example: Georgia Wareham 31* (10).
8. **Spell Library**: 7 categories; rows open the spell story.
9. **Battle Universe** and **Similar battles**: unusual battles (e.g. Shane Watson v Axar Patel, 7 out v 1.9
   expected). Similar battles are validated by split-half self-retrieval: median rank 13.3% (men) and 17.8% (women)
   v 50% chance (`docs/research/similar-battles.md`). Low-sample battle (21 balls) says so and declines similarity.
10. **Records V2**: composable filters (format, phase, batter stage, wickets down, team for/against, min matches) with
    the **exact SQL definition** shown, e.g. "Bowling average = sum(runs_batter + wides + noballs) * 1.0 / nullif(sum(wk), 0)
    … sample = count(*) FILTER (WHERE legal) ≥ 300; matches ≥ 20".
11. **Ask V3**: all 8 example questions answer deterministically with interpretation chips and evidence lists (e.g.
    "What happened in India v Pakistan in Melbourne in 2022?" → result, top score Kohli 82* (53), best bowling).
12. **Stories** (innings, battle, match): deterministic card sequences, each card with its evidence link. The journey
    test asserts no causal words ("why", "because") in titles. The battle story title is "What the X–Y battle shows",
    plus a caveat card.
13. **Share cards**: 1080×1350 and 1080×1920, generated in the browser and exported as PNG (≈1.3 MB each). There are no
    posting integrations. Every card carries the INTERNAL PREVIEW mark, coverage wording, provenance and Cricsheet
    attribution. Layout now stacks every block from the one above, so titles of any length don't collide.
14. **Daily feed**: 14 items, deterministic by date (seeded), from 14 typed slots; no player, team or competition repeats; genders alternate where possible; every item with "Why this". Findings already in
    the feed are no longer repeated in the Discoveries grid.
15. **Explore next**: instrumented. The rabbit-hole test walked player → battle → delivery → spell → match → edition →
    records → another player. All 9 page types offer ≥ 3 onward links (player 7, battle 8, match 7, innings 4,
    spell 4, delivery 4, competition 5, rivalry 3, story 4).
16. **/data methodology centre**: licence status at the top, per-group coverage, Cricsheet's own completeness figures,
    definitions, models with versions, the experimental flag, rejected capabilities, and limitations.
17. **Performance**: profiled first. See `docs/data/benchmarks-phase4.md`; everything is < 500 ms server-side cold on
    measured entities, and 2–12 ms warm.
18. **Mobile IA**: still 5 tabs (Explore · Search · Battles · Ask · Play). See `docs/architecture/information-architecture.md`.
19. **Design**: typographic sections, ranked rows and display numerals replace card grids on all new pages.
20. **Licensing gate**: unchanged and enforced (see top).

## Coverage matrix

| Case | Where tested |
|---|---|
| Men's international | Pakistan v India 2022 match, story and share; India v Australia rivalry |
| Women's international | India women overview; Mandhana Ask/partners; fingerprint card |
| IPL | Competition page (20 editions), RCB v CSK rivalry, Bumrah spells |
| WPL | Competition page, 2026 final match page, innings-library WPL scope |
| Famous player | Virat Kohli: career, stories, rabbit hole |
| Less-covered player | Kartik Sharma (7b679de5): 2 covered years, unknown metadata |
| Famous match | MCG 2022 T20 WC, Pakistan v India |
| Low-sample battle | Kartik Sharma v Shahbaz Ahmed, 21 balls: small-sample warning, similarity declined |
| Incomplete metadata | "Bats/Bowls: unknown" chips; competitions with unknown completeness |

## Bugs found and fixed in this checkpoint

- Key events were grouped by type, not by time. They are now chronological (test added).
- Rivalry year chart scrolled sideways (2024–26 off-screen on phone) and dropped gap years. It now fits the width and
  shows gaps.
- The head-to-head bar collapsed to a sliver when team names were long.
- Share cards: one-line titles left a large gap; stats overlapped the big-number label; lines collided with the footer
  rule; the attribution ran off the fingerprint card; the record card showed meaningless "none / highest first" stats;
  the fingerprint's polar chart had no labels and was replaced by a labelled ranking.
- Player eyebrow listed "Royal Challengers Bangalore" and "… Bengaluru" separately; renamed franchises are now
  canonicalised.
- The feed heading hard-coded "Fourteen"; feed findings were duplicated in Discoveries; "1 wkts" grammar.
- Coverage badge and text were squeezed side by side on phone; they now stack.
- Earlier in the phase: startup 10.4 s, slow discovery and match page, search mis-ranking, franchise abbreviations,
  associate dominance in libraries and feed, the records team filter missing Bangalore-era seasons, the wicketkeeper
  flag, "dismissed them 0 times" links, and licence wording that implied a question had been sent.

## Rejected or deliberately limited

- **Narrative turning points**: rejected. No validated algorithm exists here. Phase 3 showed SDX is not validated as a
  turning-point measure, and picking moments by intuition is what the brief forbids. Shown instead: defined factual
  events and, behind the experimental flag, labelled SDX swings.
- **Collapse rule not tuned to anecdote**: India's 31/4 at the MCG is *not* flagged, because neither 3-wicket window
  meets the published rule (19 runs in 22 balls; 21 runs in 18 balls v "≤ 20 runs within ≤ 18 legal balls"). The
  rule stays as defined rather than being bent to fit one famous match.
- **Causal "why" in stories**: not used. Cards state what happened and link to the evidence.
- Phase 3 rejections stand: no "clutch" label, no What Would You Do game, no first-innings difficulty, no momentum
  model, no pace/spin splits (metadata too sparse).

## Known limitations

- Competitions and rivalries outside the warmed set take 0.5–0.8 s on first request.
- Cricsheet season labels are shown as recorded (IPL 2008 appears as "2007/08").
- Bowling-style and batting-hand metadata remain incomplete; features that need them are not offered.
