# Private-beta readiness checklist (Phase 8): prepared, NOT executed

Nothing on this list has been actioned outside the repository. **No deployment, no purchase, no licensing email.**

## Hard blockers

| # | Item | Status | Owner |
|---|---|---|---|
| B1 | **Cricsheet licence for showing match data to people outside the team.** Ball-by-ball data and the register are under ODC-BY with attribution; the match-data terms for this use need written confirmation. | ❌ **Open: HARD GATE.** The email is drafted in `docs/legal/` and has **not been sent**. | Product owner |
| B2 | Attribution visible on every page (footer + licence pill) | ✅ in place | — |
| B3 | Internal-preview banner stays until B1 closes | ✅ in place | — |

## Product

| # | Item | Status |
|---|---|---|
| P1 | Five heroes reachable in one tap from the Home and the tab bar | ✅ |
| P2 | First-60-seconds Home with real examples | ✅ |
| P3 | Optional tour; never locks the user in; remembered locally | ✅ |
| P4 | Play: first prediction under 5 s | ✅ controls usable at 336 ms |
| P5 | Ask follow-ups deterministic; no LLM-written numbers | ✅ |
| P6 | Spoiler safety (Play, replays) | ✅ regression-tested |
| P7 | Provenance tags + WHY on every derived/modelled number | ✅ |
| P8 | Full names (57% initials-only) | ⚠️ known limitation; decision tied to B1 (see `docs/data/full-names-investigation.md`) |
| P9 | Coverage gaps stated (Afghanistan men withheld by Cricsheet; T20I completeness unknown) | ✅ in WHY / caveats |

## Quality

| # | Item | Status |
|---|---|---|
| Q1 | 10 golden journeys pass | ✅ 10/10 |
| Q2 | Phase 2–7 regressions pass | ✅ 0 errors, 0 failed assertions, 0 spoiler leaks |
| Q3 | Visual-regression baseline captured | ✅ `docs/screenshots/phase8-baseline/` |
| Q4 | Accessibility: no text < 11 px, contrast ≥ 4.5:1, names on controls, skip link, reduced motion | ✅ `scripts/a11y-phase8.mjs` |
| Q5 | Zero sideways overflow at 390 px | ✅ |
| Q6 | Zero unexpected console / network errors | ✅ |
| Q7 | Performance budget met | ✅ all < 500 ms cold; 27/28 < 50 ms warm (Play next-moment 58.7 ms: justified exception) |

## Operations (to do before inviting anyone)

| # | Item | Status |
|---|---|---|
| O1 | Hosting decision (private, access-controlled; not public) | not started |
| O2 | Access control (invite list / basic auth) | not started |
| O3 | Analytics sink + privacy notice + consent (see `beta-analytics-and-feedback.md`) | designed only |
| O4 | Feedback inbox (currently browser-local only) | designed only |
| O5 | Data refresh cadence (Cricsheet pulls) + `data_version` shown in feedback | `data_version` ✅; cadence not set |
| O6 | Incident contact + "something's wrong with a stat" triage process | not started |
| O7 | Beta cohort (10–30 fans; mix of casual and stats-literate; phone-first) | not started |
| O8 | Success criteria = metrics in `beta-analytics-and-feedback.md` | defined |

## Explicitly out of scope (Phase 8 brief, item 24)

New data providers, accounts, social, comments, fantasy, betting, payments, subscriptions, push notifications, native apps, AI commentary, 3D, computer vision, line/length or shot inference.
