# Phase 7 fan audit: the product as a cricket fan on a phone

Written **before** any Phase 7 change, from a walk of the Phase 6 build (`20139f0`) at 390 × 844.

Evidence:
- Screenshots and per-page metrics: `docs/screenshots/phase7-audit/` (`metrics.json`).
- Script: `scripts/audit-phase7.mjs`.
- Pages walked: Explore, Kohli, Bumrah, Mandhana, a lesser-known player (Kartik Sharma, 11 matches), Kohli v Zampa, MCG 2022 (India v Pakistan), Kohli's 82*, Ask (empty and "Who dismisses Kohli most?"), Play, Records, Compare, Search, Live Lab.

Technical health is fine: 0 console or network errors and 0 px horizontal overflow on every page. The problems are about experience.

## Measured signals (390 px)

| Page | Screens tall | In-page links | Explore next | Methodology terms | Text < 11 px |
|---|---|---|---|---|---|
| Explore | 10.6 | 45 | no | 2 | **41** |
| Kohli | 4.6 | **8** | yes | 7 | 8 |
| Bumrah | 4.1 | **9** | yes | 7 | 4 |
| Mandhana | 4.7 | **8** | yes | 7 | 8 |
| Lesser-known player | 4.1 | **8** | yes | 9 | 5 |
| Kohli v Zampa | 5.6 | 20 | yes | 8 | 14 |
| MCG 2022 | 5.1 | 57 | yes | 5 | 12 |
| Kohli 82* | 3.6 | **8** | yes | 3 | **21** |
| Ask (answer) | 1.9 | 6 | **no** | 1 | 1 |
| Play | 1.5 | **1** | **no** | 1 | 7 |
| Records | 4.7 | 26 (25 are players) | **no** | 1 | 13 |
| Compare (empty) | 1.0 | **0** | **no** | 0 | 2 |

How the columns were measured:
- "Links" counts visible internal links in `<main>`.
- "Methodology terms" counts occurrences of words like provenance, percentile, OBSERVED/DERIVED, shrinkage and credible.

## Findings by journey

### Player home (Kohli, Mandhana, Bumrah, lesser-known)
1. **Bumrah's page leads with his batting. This is the worst finding.**
   - "What stands out" compares him with *ODI lower-order batters* and reports nothing.
   - "How Jasprit Bumrah gets out" is the next large section: 26 batting dismissals.
   - His wickets, spells and victims are hidden behind tabs, even though bowling is what a fan opens Bumrah for.
   - The page does not use the player's primary role to order sections.
2. **The hero shows absences.** "Bats: unknown" and "Bowls: unknown" pills are the second thing a fan reads. Absence belongs behind WHY, not in the hero.
3. **Raw scorecard names.** Examples: "S Mandhana" in headings, "RM Ghosh" on Explore, "V Kohli" as Player of the match on MCG 2022.
4. **The fingerprint reads as a dashboard.**
   - A 15-petal radial chart with about 8 px labels, then a definition/sample/peer table, a legend paragraph, and a "not in this fingerprint because…" paragraph, all before the first finding.
   - Methodology is shown too early.
5. **Findings are buried and repetitive.**
   - The first finding sits about 1.7 screens down.
   - Kohli's top two findings are the *same* situation ("after facing 30 balls"): one on boundary rate, one on strike rate. Mandhana's top two are both "against Australia".
   - The copy is a difference-in-differences sentence ("…changes it ×0.89, so Virat Kohli's is 1.3× higher than the typical change would predict"). It is defensible but not understandable without statistical training.
6. **Very few next actions.**
   - Only 8 links on a 4.6-screen page.
   - Explore next is a fixed list of 7 rows: top two innings, longest battle, top partner, competition, latest match, career explorer.
   - It is identical in shape for every player, and Kohli and Mandhana get the same seven kinds.
   - Missing:
     - biggest battles (more than one);
     - who dismissed them most;
     - who they dominated;
     - best spells (for bowlers);
     - records they hold;
     - similar players;
     - compare;
     - a Play moment.
7. **Tabs are cut off on mobile.** "Wher…" is cut off at 390 px, and three filter rows (format, level, role) come before content.
8. **Lesser-known player.** The page is honest (an under-threshold warning is shown) but identical in structure. Nothing tells the fan *who this player is related to* (team-mates, the matches they played in, who they faced most).

### Kohli v Zampa (battle)
- **Good:** the numbers hero, the dismissal breakdown, the uncertainty band, and an honest "Not available" panel.
- **Too much method, too early.** "Who has the edge?" uses a MODEL badge plus interval bullets; then come the Known / Derived / Not-available lists, and only then the story button.
- **Similar battles show `d 0.52`.** That is an internal distance, meaningless to a fan. Names are truncated ("Harb…"), and the explanation repeats the same phrase on every row ("batter scores about as usual, bowler dismisses them about as usual").
- **Missing continuations:**
  - Zampa's other victims;
  - Kohli's hardest matchups;
  - the match where Zampa first dismissed him;
  - a Play moment from this battle.

### MCG 2022 (match)
- **Good:** the scoreboard hero, the worm chart, the turning-points list, and many links (57).
- **Jargon block:** "Largest changes in situation difficulty — experimental" is dense, with "difficulty 3.2 → 75 (+71.8)" on raw-initial names.
- **No "Replay / Play this match" entry point,** although the match is a featured Live Lab replay.
- **No route to the people:** there is no "players of this match" route or partnership story.

### Kohli 82* (innings)
- **Good:** the ball-by-ball scrubber and the delivery-replay link.
- **Spoiler on open:** the scrubber opens at the last ball, so the ending is on screen immediately. For an archive story that is acceptable, but there is no **"You are Kohli. India need X from Y. What happened next?"** challenge, the obvious hook.
- **Tiny text:** 21 tiny-text elements (chart axis and legend).
- **Only 8 links.** The innings does not link to the bowlers he faced, his partners in the innings, or the record it belongs to.

### Explore
- **Strong concept** ("14 things worth your time", deterministic and daily), but:
  - **Internal scores are exposed:** "Why this: … (score 7.51)" and "(score 15.0)". That is a ranking debug line shown to fans on every card.
  - **Raw names in the headlines:** "S MANDHANA'S ODI STRIKE RATE…" and "RM Ghosh".
  - **10.6 screens long, with 41 tiny-text elements.** Below the feed, "Found in the data" repeats the same kind of cards with a filter-chip wall.
  - **Missing sections:** no "On this day", no "Great battles" grouping, no "You probably didn't know", and no "continue where you left off".
  - Nothing remembers what the fan has already seen.

### Ask
- **Good:** "How I interpreted your question" and visible assumptions ("'Kohli' → Virat Kohli; also matches A Kohli, Taruwar Kohli").
- **Truncated tiles:** the answer tiles cut bowler names at 390 px ("9 Adam…").
- **Dead end after the answer:** apart from the stat tiles there is no Explore-next. Kohli v Zampa, "Kohli's hardest matchups" and "Show the 9 dismissals" are not offered.
- **The empty page is a manual:** a three-sentence explanation of the query engine before any example.
- **Unsupported questions:** several Phase 7 questions are not answered yet:
  - who Kohli scored fastest against;
  - best death bowlers since 2020;
  - players similar to Rohit;
  - Bumrah's best spell;
  - compare Kohli and Rohit in chases;
  - India's biggest successful chases;
  - Kohli–Zampa dismissals in death overs.

### Play
- **One link on the whole page:** to Live Lab.
- **No route onward after a prediction:** no link to the batter, the bowler, the match or the innings.
- **Moments are random,** not tied to stories ("Kohli's 82*"), battles or matches the fan is looking at.
- **The scoreboard is self-contained and works well.**

### Records
- **A BI tool on a phone:**
  - 8 chips, then a statistic select, then **11 filter rows** (gender, format, level, phase, innings, teams, years, wickets down, for, against, min matches, min sample);
  - then a Definition/Filters/Threshold/Coverage table;
  - the first leaderboard row is about 2 screens down.
- **Titles are statistic names** ("Runs"), not "Highest strike rate after 30 balls".
- **No categories:** batting, bowling, partnerships, matchups, phases, chasing, eras.
- **Only player links:** rows link only to players, never to the innings, spell or battle that holds the record.

### Compare
- **An empty page with zero links:** no suggested pairs (Kohli v Rohit, Bumrah v Starc, Mandhana v Lanning). It is a dead end for anyone arriving without a plan.
- **No balanced verdict:** when filled in, it compares batting numbers only, with no "where A leads / where B leads / tied".

### Search and Live Lab
- **Search is a directory** (12 browse links). Fine, but there is no "recently viewed".
- **Live Lab is fine,** but it isn't reachable from the matches it replays.

## Cross-cutting problems, ranked

1. **The primary role is ignored:** bowlers are presented as batters (Bumrah).
2. **No knowledge graph at the page level.** Every page builds its own small, fixed link list. There is no shared notion of "where can the fan go from here", and nothing avoids showing the same entity on every page.
3. **Findings sit under methodology.** Definitions, peer pools, legends and "not available" lists come before the interesting sentence.
4. **Statistician copy:** difference-in-differences phrasing, `d 0.52`, `score 7.51`, "difficulty 3.2 → 75".
5. **Raw scorecard names** in headlines and match summaries.
6. **Dead ends:** Compare (empty), Play, Ask answers and Records rows.
7. **No memory:** recommendations repeat across pages; there is no recently viewed and no reset.
8. **Play is an island,** not woven into innings, matches and battles.
9. **Tiny text:** chart labels below 11 px (fingerprint petals, innings axis, Explore "why this" boxes).
10. **Absence displayed as a feature:** "unknown" pills in the hero. The truth about absence must stay, but behind WHY.

## What must not change

- Statistical safeguards:
  - minimum samples;
  - shrinkage;
  - split-half stability ("holds in both halves");
  - multiple-comparison protection;
  - coverage warnings;
  - provenance tags;
  - the honest "Not available" panels.
- Phase 5 spoiler protection.
- No line/length, shot, edge, trajectory or field position anywhere.
- No causal language. Words such as "because", "handles pressure", "clutch" or "loses concentration" stay out.

These move behind WHY controls; they are not deleted.

## Targets for the Phase 7 build

| Problem | Phase 7 response |
|---|---|
| Fixed link lists, repetition | Knowledge graph plus the session-aware Rabbit-Hole engine on every entity page |
| Bowler shown as a batter | Role-ordered player home |
| Findings buried, statistician copy | "What makes them different" (3–5 de-duplicated findings in plain words, method behind WHY), Player Stories, "You probably didn't know" |
| No matchup discovery | Biggest battles / dismissed most by / dominated / balanced / unusual, with a sample shown and no "rivalry" label below threshold |
| Compare and Records feel like BI | Compare V2 with suggested pairs and lead/lead/tied; Records V2 categories with human-readable titles |
| Play is an island | "What happened next?" inside innings, matches and battles, spoiler-safe |
| No memory | Local-only recently viewed, prediction score, de-duplication, reset |
| Raw names, `score 7.51`, `d 0.52` | Register display names; internal scores removed from fan copy and kept in the API |

---

## After Phase 7: the same walk, re-measured

Same script (`scripts/audit-phase7.mjs`), same pages, same 390 px viewport. The screenshots are in `docs/screenshots/phase7/`.

| Page | Links before → after | Explore next | Text < 11 px before → after |
|---|---|---|---|
| Explore | 45 → 72 | daily sections + rabbit hole | 41 → 0 |
| Kohli | 8 → 53 | ranked, session-aware | 8 → 2 |
| Bumrah | 9 → 51 | ranked, session-aware | 4 → 1 |
| Mandhana | 8 → 53 | ranked, session-aware | 8 → 2 |
| Lesser-known player | 8 → 18 | ranked, session-aware | 5 → 3 |
| Ask answer | 6 → 12 | none → "Keep exploring" | 1 → 1 |
| Records | 26 (all players) → 205 (evidence rows) | per-record Explore next | 13 → 0 |
| Compare (empty) | 0 → 8 suggested pairs | — | 2 → 2 |
| Kohli 82* | 8 → 11, plus a Play moment | yes | 21 → 2 |

Player pages are longer (about 11 screens). That is the brief's section order: fingerprint, findings, wickets/dismissals, battles, stories, partnerships, records, career and similar players. Each section is a destination, not a method block.

Responses to the ranked problems:

1. **Primary role:** Bumrah's home leads with "How Jasprit Bumrah takes wickets", and his peers are like-for-like (leagues + full-member internationals).
2. **Fixed link lists replaced:**
   - an explicit knowledge graph (13 node types) and the Rabbit-Hole ranker;
   - 0 dead ends across 70 crawled pages of 11 types;
   - the three required journeys pass.
3. **Findings above method:** "What makes them different" comes second, in plain words; definitions, peer pools and tests are behind WHY.
4. **Statistician copy removed:**
   - The strengths engine's comparison now reads "rises, where a typical top-order batter's falls", with the four numbers.
   - The internal `score 7.51` is gone from Explore.
   - `d 0.52` is not used on the new surfaces.
5. **Raw names:**
   - Fixed where a register display name exists.
   - Register names that are themselves initials ("S Mandhana") are what Cricsheet publishes. A fuller name would need a new data source, which Phase 7 does not add.
6. **Dead ends:**
   - Compare has suggestions.
   - Play has onward links after the reveal.
   - Ask answers end with "Keep exploring".
   - Every record row opens its evidence.
7. **No memory:** fixed. Local-only memory provides "Continue where you left off", pushes visited pages out of recommendations, and has a clear reset.
8. **Play is integrated:** spoiler-safe "What happened next?" moments appear in innings, matches, battles, player homes and Explore.
9. **Tiny text:** badges and labels have an 11 px floor, and chart axis labels are enlarged.
10. **Absence moved behind WHY:** the hero shows only known metadata. "Unknown" values and coverage detail are under "WHY? Coverage & metadata".

Still open, honestly:
- The battle and match pages keep some 10 px chart text inside scaled SVGs.
- Player homes are long on a phone.
- Initials-style register names remain.
