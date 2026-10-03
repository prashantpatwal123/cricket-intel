# Phase 2 checkpoint: the cricket intelligence experience

Status: **internal preview only.** Real Cricsheet data; match-data licence not yet confirmed (draft question in `docs/legal/cricsheet-licence-question.md`, not sent).

Screenshots and an interaction log are in `docs/screenshots/phase2/` (`m*` = 390 px phone, `d*` = 1280 px desktop). They are produced by `scripts/screenshots-phase2.mjs` against the real dataset. The last run had **0 console errors, 0 HTTP errors and 0 px horizontal overflow at every step** (`report.json`).

## What was built

| # | Item | Where | Demonstrated interaction (real data) |
|---|------|-------|--------------------------------------|
| 1 | Cricket Fingerprint | Player → Overview | Tap petal → value, percentile, peer median, definition, sample → "See the deliveries" opens the 20 matching balls (m04, m05). Role toggle; bowler version (d03). Unsupported dimensions listed, not drawn. |
| 2 | Strength & weakness engine | Player → Strengths; Explore | Each card: sample, baseline, difference, interval, p and FDR, stability, shrinkage, thresholds, all under WHY → Deliveries (m02, m06). "In our covered … data" statements. |
| 3 | Player × Player battle | `/battle` | Pickers (m12), stat strip, dismissal-route nodes → those dismissals; WHO HAS THE EDGE? number line with 90% interval vs batter's usual and bowler's usual, observed v expected dismissals, no winner label (m10, m10b). Breakdown by phase / setting-chasing / year / format → deliveries (m11). |
| 4 | Dismissal Story | Player → Dismissals | Route → frequency + interval, format, phase, batter score, by-over, chronology, bowlers (→ battle), fielders, "Every dismissal" (m07, d04). Always "Caught by wicketkeeper"; the note says the data doesn't say whether the ball was edged. |
| 5 | Career timeline | Player → Timeline | Five metrics; one line per format and level; lines break at gaps; hatched years with no covered data; ⚠ marks team ODIs Cricsheet couldn't source; point → that year's balls (m09, d05). |
| 6 | Compare 2–4 | `/compare` | Engine warnings (gender, competitions, partial coverage) shown first; per-player coverage status; out-rate 90% intervals so overlapping samples aren't presented as different (m13, d07). |
| 7 | Records Explorer | `/records` | 8 presets, 20 metrics, gender / format / level / phase / innings / teams / years / min-sample; definition, filters, threshold, coverage on every board; row → player or battle (m14, d08). |
| 8 | Ask Cricket v1 | `/ask` | "How I interpreted your question" chips; removing a chip re-runs the validated intent via POST (economy board: full members → all teams). Pipeline view: question → intent → validated query → result → response. Ambiguous names offer candidates ("Sharma" → Rohit Sharma) (m15–m18). |
| 9 | What Happens Next v1 | `/play` | Pre-ball context, 7 options with points; reveal shows actual, model distribution, rarity, points, the model's pick; keyboard 0-6/W + Enter; next moment prefetched (NEXT BALL in 12 ms); stats kept in localStorage, no accounts (m19, m20, d09). |
| 10 | Model vs You | `/play` | Running score, accuracy and correct count for you and the model, plus beat-the-model count and streak/best. The copy says the favourite is not a certainty. |
| 11 | Graphics system v1 | `components/cricket/primitives.tsx` | Field, pitch, crease, stumps (broken state), figures, ball, event connector (draws in once; dashed = fade), unknown zone, count node, provenance strokes. Used by How-out and Battle. No ball trajectories. |
| 12 | Navigation | Shell | Explore · Players · Battles · Ask · Play; bottom tab bar on phones. |
| 13 | Mobile first | all | Matchups become cards with an SR bar on phones; battle breakdown and records are card rows, not wide tables. |
| 14 | Performance | — | Architecture unchanged. Warm timings: explore 7 ms (cached by build), fingerprint 50 ms, insights 90–350 ms, battle 160 ms, compare 145 ms, records 90–490 ms, Ask 95–170 ms. |
| 15 | Licence draft | `docs/legal/cricsheet-licence-question.md` | Draft only, **not sent**. |

## Fixes found by inspecting the screenshots
- Mobile tab bar was trapped at the top: the topbar's `backdrop-filter` made it the containing block for the fixed nav.
- `.wrap` mobile padding collided with `.chip.wrap`, turning chips into large ovals.
- The Dismissal Story overflowed at 390 px; grid children now have `min-width: 0`.
- Fingerprint labels were clipped at phone width; now a padded viewBox and two-line labels.
- Battle route labels and edge number-line labels overlapped; now HTML route nodes and separate label rows.
- Timeline chart text was too small on phones.
- Ask: "Bumrah v Warner" treated Bumrah as the batter. Orientation now comes from the data, with a visible "assumed" note.
- Ask: rate leaderboards were topped by tiny associate samples. They now default to full members plus leagues, as a visible, removable chip.

## Known limitations
- Franchise renames (Kings XI Punjab / Punjab Kings, Delhi Daredevils / Delhi Capitals) are separate teams in opposition splits.
- Batting hand is unknown for all players, and bowling style covers 2.2% of players, so no pace/spin, left/right or style breakdowns appear in Battles, Fingerprint or Insights.
- The Strengths engine is batting-only. The bowling fingerprint exists, but bowling strengths cards do not yet.
- Insights pick the player's main format when none is selected; switch format with the filter.
- Cold-start insights take 0.1–1.3 s on first request per scope (then cached).
