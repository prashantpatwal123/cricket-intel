# Phase 6 checkpoint: Data Enrichment + Visual Cricket Intelligence

**Status: internal preview only.**
- Nothing is deployed and nothing was purchased or subscribed to. No vendor was contacted.
- The Cricsheet licence email has not been sent.
- Baseline: `5908177` (Phase 5).

**Rule kept throughout:** a sparse truthful visual beats a beautiful fictional one. No real-data view in CRICINTEL draws a pitch point, line, length, shot, edge, trajectory or field position. None of those is recorded in any source we can use.

## Gate result

| Check | Result |
|---|---|
| `pytest` | **110 passed** (89 existing + 21 new in `test_phase6.py`) |
| Phase 6 phone and desktop journeys (`scripts/screenshots-phase6.mjs`) | 0 errors, 0 failed assertions, 0 px horizontal overflow. Asserts no illustrative frame on real-data views, no real player named in illustrations, no manufactured matchup explanation, and unavailable filters explained |
| Phase 2 / 3 / 4 / 5 regression journeys | 0 errors each; Phase 4 and Phase 5 0 failed assertions; Phase 5 0 spoiler leaks |
| `tsc`, `next build` | pass |

## The 23 gate items

1. **Field-level capability audit:** `docs/data/capability-audit.md` / `.json`, generated from `enrich/capability.py`, the same code that feeds `/data`.
   - 36 fields: 4 available, 6 partial, 26 unavailable.
   - Coverage is measured, e.g. keeper identified in 76.9% of team-matches, fielder named on 98.0% of fielded dismissals, bowling style on 7.2% of deliveries, batting hand 0%.
   - The evidence that geometry is absent is the observed schema of all 10,247 Cricsheet files.
2. **Sources and licensing research:** `docs/research/data-sources-phase6.md` / `.json`.
   - Only GitHub and PyPI were reachable, so every vendor claim is SECONDARY.
   - Licensing is UNKNOWN wherever terms were not read first-hand. Search snippets are not treated as licensing evidence.
3. **Provider scorecard:** about 20 sources scored 0–5 on 10 dimensions, with UNKNOWN where there is no evidence. Summary in `docs/research/data-stacks-and-cost-model.md`.
4. **Three data stacks:**
   - A: Cricsheet + Register + Wikidata.
   - B: plus one licensed coded feed (Sportradar Cricket v2 as lead candidate, Roanuz fallback; SECONDARY) and licensed player profiles.
   - C: Opta/CricViz plus advanced/fielding coverage plus tracking with board/ICC consent.
   - Do not purchase anything yet.
5. **Player-metadata pilot (PARTIAL):**
   - All 8 players joined by stable ids (Register → ESPNcricinfo → Wikidata P2697). Three different "Rohit Sharma" records show why names cannot be used.
   - Wikidata (CC0): batting hand 0/8, bowling style 0/8.
   - Wikipedia infoboxes: 8/8, but CC BY-SA, so **withheld** pending licence review. Nothing questionable was populated.
   - Details: `docs/data/metadata-pilot.md`. Fetched via a GitHub runner (run 37187863520) on research branch `phase6/metadata-pilot`, output on `data/wikidata-pilot`. The existing Wikidata snapshot was not overwritten.
6. **Canonical taxonomies:** `docs/architecture/taxonomy.md`.
   - Bowling: 12 full codes plus 5 partial codes, so coarse labels are not over-read; original wording and source footnotes are kept.
   - Line: 6 batter-relative buckets. Length: 7 buckets. Shots: 9 families and 24 shots plus modifiers.
   - Line and length are never inferred from outcomes.
7. **Machine-readable provenance:** `enrich/provenance.py` / `web/lib/visual.ts`.
   - Five types with enforced requirements; ILLUSTRATIVE cannot reference a real delivery or player.
   - `why` answers "Why am I seeing this?"
8. **Visual Cricket Engine V2:** layers L0–L5 (`analytics/visual.py`). Absent layers carry why and what would unlock them. Fidelity today is L0, or L1 where CC0 bowling style exists.
9. **Progressive Delivery Replay:** the delivery page gains a layer ladder, dismissal relationship, an explicit empty geometry slot and a text equivalent. The Phase 3 schematic stays.
10. **Graphical component contracts:**
    - PitchMap (canonical metres, left/right transform), LineLengthMap, WagonMap, ShotAtlas, EdgeMap (architecture only), DismissalTheatre V2, BowlerMap, MatchupMap.
    - All accept partial data and render "not recorded" states. Illustrative mode is watermarked.
11. **Dismissal DNA V2:** `/how-out/[id]`, drilling how out → bowler → format → phase → every dismissal.
    - The bowling-family split is offered only at ≥ 50% coverage; Kohli is at 54/567, so it is withheld with the reason shown.
    - Line/length, shot and edge filters are listed as unavailable, with why.
12. **Shot intelligence: BLOCKED.** 13. **Line/length: BLOCKED.** 14. **Edge/contact: BLOCKED.** What would unblock each is in `docs/research/capability-verdicts.md`.
15. **Computer vision: research only, do not build.** `docs/research/computer-vision-phase6.md` (1 PRIMARY, 27 SECONDARY sources). No footage was downloaded. The verdict table is in `capability-verdicts.md`.
16. **Visual Lab** (`/visual-lab`):
    - 4 real deliveries showing available data next to the visual result, staying sparse.
    - The metadata-pilot table, with Wikipedia values withheld.
    - 5 watermarked ILLUSTRATIVE components built from generic, unnamed data. The journey test asserts no real player is named in them.
17. **Kohli "how does he get out?" UX:**
    - Ask answers factually: 567 dismissals; caught by a fielder 239, bowled 89, keeper status unknown 75, caught by keeper 74 (derived). It states that pitch, shot and edge are not recorded.
    - The flow continues: "show his wicketkeeper catches" (74) → "who caused them" (by bowler) → "show every dismissal" (each opens its delivery).
18. **Kohli v Zampa enriched UX:** the battle page has a known / derived / not-available panel.
    - Zampa's bowling style is **not** safely enriched: it exists only in a CC BY-SA source.
    - The page says what it cannot explain. No manufactured "struggles against leg-spin" statement is made; a test asserts this.
19. **Data Quality Centre V2:** `/data` has a field-by-field ✓ △ ✕ matrix with coverage, source, licence, "usable now", and what would unlock each missing field.
20. **Source versioning:** `enrich/versioning.py`.
    - Append-only observations with source version, retrieval time, original value, normalised value, licence, usability and content hash.
    - `resolve()` answers which value, which source, when retrieved, whether the source changed, and whether sources disagree. Tested.
21. **Future live-feed compatibility:** the Phase 5 delivery event takes optional `enrichment` blocks L1–L5, provenance-checked, with canonical codes only.
    - Tests: an enriched log scores identically to a plain one, capabilities are counted, and 5 kinds of bad enrichment are rejected.
22. **Cost model:** measured infrastructure for the current stack and the open-metadata pilot. Every vendor licence, traffic and tracking cost is **QUOTE REQUIRED**; nothing is invented.
23. **Product Decision Matrix:** `docs/product/decision-matrix.md`, with 19 capabilities across Now / Open data / Commercial feed / Tracking, and the frontier stated.

## Bugs and corrections found during the phase

- The Visual Lab first displayed Wikipedia's (CC BY-SA) values ("Wikipedia says RM"), which contradicted the "not used" rule. These values are now withheld from the UI, the API response and the committed report.
- `known-limitations.md` was stale: it gave keeper confidences of 0.85/0.75 (measured 0.95/0.90) and called the Wikidata adapter unverified. Corrected.
- The data-sources research quoted an old 2.2% coverage figure. Re-measured: 6.4% of players, 7.2% of deliveries.
- Dismissal drill-downs showed scorecard initials ("JO Holder"). They now show register display names.
- The delivery page repeated each missing layer twice. It now shows the ladder plus one empty geometry slot.

## Not changed

Phase 2–5 statistical, provenance, licensing, spoiler-safety and regression gates are all preserved, and no test was weakened.
