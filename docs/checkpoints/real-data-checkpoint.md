# Real Data Checkpoint

| # | Item | Result |
|---|---|---|
| 1 | Source | **Cricsheet official downloads**, retrieved directly from cricsheet.org by GitHub Actions run 37140804774 (2026-10-03T17:31:39Z). Published unchanged to `data/cricsheet-raw` and re-verified locally against two independent hash records. |
| 2 | Licence | **Register: ODC-By 1.0 (primary-verified).** **Match data: no licence stated on cricsheet.org** ("freely-available"; footer "All rights reserved"). Internal preview only until Cricsheet confirms terms. See `docs/data/cricsheet-verification.md` §2. |
| 3 | Size | 6 zips, 49.8 MB compressed / 1.16 GB JSON; Register 18,554 people + 7,549 aliases |
| 4 | Competitions | IPL (1,243), WPL (88), men's T20I (3,558), women's T20I (2,171), men's ODI (2,576), women's ODI (611) |
| 5 | Matches | 10,247 (0 quarantined, 0 schema drift) |
| 6 | Deliveries | 3,298,987 (3,298,136 in the stats working set; super overs excluded per Cricsheet) |
| 7 | Canonical players | 8,469 appearing players, every one resolved to a Register id (0 unresolved) |
| 8 | Metadata coverage | role 82.1% (derived + Wikidata) · wicketkeeper status 7.2% of players · bowling style 2.2% / bowling family 2.4% of players (7.8% of deliveries) · **batting hand 0%** (no legitimate automated source has it) |
| 9 | QA | 32 checks: **0 ERROR**, 7 WARN, all explained (`docs/data/qa-report-cricsheet.md`) |
| 10 | External validation | **0 discrepancies** across 42 confirmed checks on 6 finals. Career gaps explained by coverage (`docs/data/real-data-validation.md`) |
| 11–15 | Screenshots | `docs/screenshots/real-checkpoint/` (player pages ×8 profiles, dismissal drill-down, delivery reconstruction, Ask, What Happens Next) |
| 16 | Performance | `docs/data/benchmarks-real-cricsheet-subset.md` |
| 17 | Repository | `prashantpatwal123/cricket-intel`, branch `main`, plus data branches |
