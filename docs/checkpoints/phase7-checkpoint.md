# Phase 7 checkpoint: The Fan Experience: rabbit holes, player stories, discovery and retention

**Status: internal preview only.**
- Nothing is deployed or purchased; no vendor was contacted.
- The Cricsheet licence email has not been sent.
- No data scope was added.
- Baseline: `20139f0` (Phase 6).

**Rule kept throughout:** use only the intelligence we can truthfully produce today. No line/length, shot, edge, trajectory or field position anywhere. Provenance, minimum samples, shrinkage, multiple-comparison protection and coverage warnings all stay; they moved behind WHY.

## Gate result

| Check | Result |
|---|---|
| `pytest` | **128 passed**: 110 existing plus 18 new in `test_phase7.py` (graph integrity, ranking determinism and diversity, session penalty, chains, Records V2, holdout-validated similarity, BH, causal-language guard, rivalry sample rule, Compare without a single score, On This Day anniversary rule, spoiler-safe moments, new Ask kinds) |
| Phase 7 phone and desktop journeys (`scripts/screenshots-phase7.mjs`) | 0 errors, **0 failed assertions**, 0 px horizontal overflow on every page. Covers the three journeys, Explore sections, the player-home sections, session-memory change and reset, a Play moment opening at its cursor with no result shown and no onward links before the end, 6 share-card types, Compare V2 lead/tie statements and no single score, Records V2, On This Day, the 10 Ask questions, no causal words and no illustrative frames. One earlier run stalled partway and was killed by its time limit (no error or assertion recorded); the re-run passed |
| Exploration crawl (70 pages, 14 seeds, 11 page types) | **0 dead ends, 0 broken pages**; every page type offered at least 3 next steps (players and matches 6) |
| Phase 2 / 3 / 4 / 5 / 6 regression journeys | Phase 2: 0 errors · Phase 3: 0 errors · Phase 4: 0 errors, 0 failed assertions · Phase 5: 0 errors, 0 failed assertions, **0 spoiler leaks** · Phase 6: 0 errors, 0 failed assertions |
| `tsc`, `next build` | pass |
| Performance | every new endpoint under 500 ms cold (worst 333 ms) and under 6 ms warm; references unchanged. See `docs/data/benchmarks-phase7.md` |

## The 20 deliverables

1. **Audit first:** `docs/product/phase7-fan-audit.md`, written from a 390 px walk *before* any change, with screenshots in `docs/screenshots/phase7-audit/`. The worst finding: Bumrah's page led with his batting. The document ends with the same walk re-measured after the build.
2. **Knowledge graph:** `fan/kg.py`, with 13 node types (player, team, match, innings, spell, battle, partnership, competition, rivalry, record, finding, delivery, moment). Every edge is a relationship in covered data and carries a human reason plus six features. See `docs/architecture/knowledge-graph-and-rabbit-hole.md`.
3. **Rabbit-Hole engine:** `fan/rabbit.py`.
   - Deterministic score from strength, unusualness, sample, recognisability, recency and relation.
   - Diversified, with one entity per list.
   - Visited destinations are excluded when enough fresh ones exist; destinations recommended repeatedly are down-weighted.
   - The component breakdown is in the API, and "WHY these?" is in the UI.
4. **Player home for fans:**
   - Hero: kind of cricketer, formats, covered span, three key numbers, known metadata only.
   - Then: compact fingerprint (readable trait chips) → what makes them different → how they get out / take wickets → biggest battles → best stories → partnerships → records → career journey → similar players → Explore next.
   - Role-ordered: bowlers lead with bowling. Percentiles are against leagues plus full-member internationals, for the player and peers alike.
5. **Player Stories:** "Kohli after 30 balls", "Bumrah at the death", "Mandhana when the asking rate is high", the longest batter-v-bowler battle, best day and best spell. Each has a headline, evidence, sample, comparison, a deliveries link, provenance and WHY. Causal words are blocked by an assertion and a test.
6. **"You probably didn't know":** discovery candidates that survive Benjamini–Hochberg (q = 0.01) across all 469 tests (156 survive; 144 shown after minimum samples). One tap to evidence, with a share card.
7. **Matchup discovery:**
   - Views: biggest, dismissed most by, dominated (shrunk), most balanced, unusual (|z| ≥ 2) and the bowler equivalents.
   - "Rivalry" requires 120+ balls across 5+ matches; under 60 balls is tagged "small sample".
   - Expected dismissals and 90% ranges are shown.
8. **Similar Players, validated:**
   - Shrunk, z-scored fingerprint distance, per role, format and gender.
   - Holdout self-match is 5–17× chance. 3 of 8 pools fail the bar and are not shown.
   - Shows why alike and where they differ; "style, not quality". See `docs/models/similar-players.md`.
9. **Compare V2:**
   - Scoring, survival, boundaries, dot balls, match states, career timeline, records and peer percentiles.
   - Per-dimension "A leads / B leads / too close to call" with a Bonferroni-corrected test. No overall score.
   - Suggested pairs when empty.
10. **Records V2:**
    - 31 definitions × scopes = 172 records in 13 categories, with human titles.
    - Each has a definition, minimum, filters, coverage and an evidence link per row.
    - Single-match records default to a "major teams" view, with "all covered" alongside.
    - The leaderboard builder is kept.
11. **Ask V3:** all 10 required questions answer correctly (list below), each with "How I interpreted your question" and an Explore next. New kinds: scored fastest against, before/after N balls, similar, compare two players under filters, team chases, dismissals within a battle. Every filter is applied or the question is refused.
12. **Daily discovery on Explore:**
    - Sections: continue where you left off, worth knowing today, great battles, on this day, record book, player rabbit hole (a deterministic chain), can you beat the model.
    - All from the database, deterministic by date and skipping what this browser has seen.
    - The internal ranking score is no longer shown.
13. **On This Day:** `/on-this-day` with previous/next day. "N years ago today" is claimed only for single-day matches; multi-day matches say "began on this day".
14. **Play integrated:**
    - Spoiler-safe moments in innings, matches, battles, player homes and Explore ("You are Virat Kohli, on 45 off 40. India need 51 from 22. What happened next?").
    - Each opens the Phase 5 replay at that cursor in game mode.
    - Onward links appear only after the reveal or the end of the replay. Phase 5 spoiler tests are unchanged and pass.
15. **Local session memory:**
    - Visited pages, recommendation counts and the Play score, in `localStorage` only.
    - Used by the ranker.
    - "Clear my history" on Explore and "Clear" on Search; the reset is tested.
16. **Share cards:** new finding, player story, record and prediction-result cards, alongside the existing innings, spell, matchup, partnership, match and fingerprint cards. One idea per card, CRICINTEL branding, attribution, provenance and the internal-preview mark.
17. **Mobile pass at 390 px:**
    - 0 horizontal overflow on every journey page.
    - 11 px floor for badges and labels; larger chart labels with staggered partner names.
    - Methodology moved behind WHY; the fingerprint has no 8 px petal labels on the home.
    - The filter wall is gone from the player home.
18. **Exploration-journey tests:**
    - J1: Explore → Kohli → dismissal DNA → bowler → battle → match → innings → another player.
    - J2: Mandhana → partner → match → record → another player.
    - J3: Bumrah → spell → match → opposing batter → battle.
    - Plus the crawl, which measures dead ends, broken pages and repetition.
19. **Performance:** profiled, then fixed with in-memory indexes, the live tables for moments, hero caching and warm-up of peer pools, league baselines and the day's selection. See `docs/data/benchmarks-phase7.md`.
20. **Phase 2–6 regressions:** see the gate table.

### Ask: the ten questions (real data)

| Question | Answer (abridged) |
|---|---|
| Who dismisses Kohli most? | Adam Zampa and Tim Southee, 9 times each |
| Who has Kohli scored fastest against? | Umesh Yadav: 168 off 96 (SR 175 v usual 110); ranked on a shrunk estimate |
| What changes after Kohli faces 30 balls? | SR 104 → 118; dots 44.0% → 33.9%; dismissals 2.23 → 2.12 per 100 balls |
| Who are the best death-over bowlers since 2020? | Men: Sunil Narine 6.56; women: K Ramharack 5.92 (economy, minimum 300 balls in the phase, full members and leagues) |
| Which players are most similar to Rohit? | Fakhar Zaman, Dawid Malan, Evin Lewis, David Warner (ODI batting style, validated) |
| What is Bumrah's best spell? | 6/19 v England, 2022-07-12 |
| Who partners Mandhana best? | Pratika Rawal: 1,885 runs in 26 ODI stands |
| Compare Kohli and Rohit in chases | SR 108.6 v 105.2 (too close to call); dismissals 1.9 v 2.7 per 100 balls (Kohli leads); boundary % too close to call |
| Show India's biggest successful T20 chases | 211/4 v Sri Lanka (2009), chasing 207, then the list |
| Which Kohli–Zampa dismissals happened in death overs? | 2 of the 9, each linked to its delivery |

Screenshots (phone `m…`, desktop `d…`) and the run report are in `docs/screenshots/phase7/`. The pre-change audit screenshots are in `docs/screenshots/phase7-audit/`. I inspected them myself; issues found that way are listed below.

## Things found and fixed during the phase

- **`Filters.where` aliasing:** with a table alias, it produced `b.coalesce(chasing, false)` (a latent bug since Phase 4, hit by joined queries). Fixed to `coalesce(b.chasing, false)`.
- **Peer pools:** the fingerprint peer pool included associate T20Is, so Bumrah's economy sat at the 33rd percentile. The fan home now uses a "major" scope (opt-in; the default fingerprint is unchanged) for the player and peers alike. Against it he is "among the most economical of 306 peers".
- **Strengths-engine copy:** a sentence like "boundary rate 1.3× higher than a typical top-order batter's change" is now "After facing 30 balls, Virat Kohli's boundary rate rises, where a typical top-order batter's falls", with the four numbers. The test and thresholds are unchanged.
- **Explore internal score:** Explore showed internal ranking scores ("score 7.51"). Removed from fan copy and kept in the API.
- **Partnership numbering:** stand numbers were 0-based in new copy ("for wicket 0"); now shown 1-based.
- **"Because" in method notes:** "Not shown, because the data doesn't record it" and three similar method notes were reworded so no page uses causal words.
- **Ask "best bowlers":** read "best" as batting strike rate; it now reads "best bowlers" as economy, with a 300-ball phase minimum, and states both assumptions.
- **Record-page 500:** a record whose rows had no player ids caused a 500 in its graph neighbours. Fixed, and record rows now also link the people on the list.
- **Match header:** the competition was plain text on match pages; it now links to the edition.
- **Share card overflow (seen in screenshots):** long headlines ran off the share card and statements were cut mid-sentence. Fixed with adaptive title size and line wrapping. The story card's big number had picked the "20" in "T20"; fixed.
- **Play picks below the fold:** a Play moment opened the replay with the pick buttons out of view. The page now scrolls them in under the sticky score strip.
- **Session memory not recorded:** partnership, spell, delivery, competition and rivalry pages didn't record visits. All entity pages now do.
- **Repetition:** the crawl showed one page recommended 9 times. Visited destinations are now excluded when enough fresh ones exist, and findings are de-duplicated against the same partnership or battle.

Measured repetition (crawl, 70 pages): 392 recommendations, 304 distinct, 65 recommended more than once. The most repeated is Kohli's page (8), because most seeds are Kohli-centred and memory keeps the last 40 visits.

## Changed regression selectors (documented, not weakened)

- **Phase 4 rabbit-hop test:** it clicked fixed Explore-next labels ("Adam Zampa", "Latest dismissal", "This edition"). Explore next is now ranked per session, so the script picks hops by destination type (battle → delivery → spell → match → competition → records → player). It asserts the same chain of page types as before.
- **Phase 2/4 hero chips:** the hero now shows only known metadata chips (role, keeper). The "unknown" ones moved behind WHY, which the audit asked for.

## Not changed

Phase 2–6 statistical, provenance, licensing, spoiler-safety and regression gates are all preserved.
