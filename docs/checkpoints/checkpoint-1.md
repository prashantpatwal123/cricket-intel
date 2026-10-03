# Checkpoint 1: first functioning player experience

**Status:** the vertical slice works end to end. **The data is a SYNTHETIC fixture.** Real Cricsheet data is blocked by the build environment's network policy (see "Blockers").

## 1. Screenshots (`docs/screenshots/checkpoint-1/`)
| File | What it shows |
|---|---|
| 01-home-mobile.png | Search + highest-data players (men's and women's) |
| 02-player-hero-mobile.png | Hero: identity, metadata chips with provenance, headline numbers, **data coverage** statement + partial-history warning |
| 03-howout-mobile.png | **How they get out**: routes placed only where the Laws put them; caught-in-field is a hatched ring ("position not recorded") |
| 04-evidence-caught-keeper-mobile.png | Tap a route → every qualifying delivery (aggregate → evidence) |
| 05-delivery-scene-mobile.png | Delivery card + **Reconstruction v0** with "RECONSTRUCTED FROM EVENT DATA" banner and explicit unknowns |
| 06-matchups-mobile.png | Matchup Lab v1 (by bowler / pace-spin / style / arm) |
| 07-situations-mobile.png | Situation maps (over, balls faced, wickets down, RRR, chase state, phase) |
| 10-*-desktop.png, 11-*-delivery.png | Full pages + a delivery for each of the 5 test players |

## 2. Dataset loaded
- `synthetic_fixture`: **1,534 fictional matches** (T20 + ODI, international + league, men's + women's), ~416k deliveries, 683 player identities (674 registered + 9 deliberately unresolved). Generated in Cricsheet JSON format and ingested by the **same adapter** real data will use.
- A 15,340-match / 4.16M-delivery synthetic build was used for benchmarking only.
- **Real Cricsheet data: not loaded** (network blocked). No third-party mirror was used.

## 3. Test players (fixture analogues of the required profiles)
| Profile | Player (fictional) | Checked |
|---|---|---|
| Elite men's batter | O Valestoke | stats, filters (T20 + death), graphic, coverage note, drill-down, scene |
| Elite women's batter | I Amberholt | same; bowling style **unknown** → shown as unknown |
| Lower-sample player, missing metadata | C Wexcombe (12 matches) | hand + style unknown, low-n flags |
| Bowler | B Wexford | bowling numbers, how-out as batter |
| Incomplete historical coverage | L Inchwick | "already appears in first season of our data… totals partial" note |

Automated run: 0 console errors, 0 failed requests across all 5 players (`report.json`).

## 4. QA results
`docs/data/qa-report-synthetic.md`: 32 checks, 0 ERROR, 3 WARN (expected: 17 unresolved identities, 1 duplicate fingerprint, 468 catches with unresolvable keeper status). Unit tests prove the checks **catch** injected corruption (runs total, extras, bowler not in XI, player-out not on ball, duplicate match).

## 5. Performance (`docs/data/benchmarks-*.md`)
At 15k matches / 4.16M deliveries on 4 vCPU: profile 103 ms, dismissals 38 ms, situations 150 ms, matchup 42 ms, drill-downs 145–155 ms, records-style aggregate 51 ms (medians); cold start 3.8 s. No need for anything beyond DuckDB.

## 6. Known data limitations
See the final checkpoint message; key items: no line/length/shot/position data in the source; keeper status inferred; Afghanistan men excluded by Cricsheet (secondary source); left-censored careers; batting hand / bowling style require an external source (Wikidata adapter written, blocked by network).

## 7. Repository
Local repo `/home/user/cricket-intel` (branch `main`). GitHub repo creation was refused by the integration (403); push pending a repo being created.
