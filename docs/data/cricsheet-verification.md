# Cricsheet verification record

| | |
|---|---|
| **Status** | ⚠️ **PRIMARY VERIFICATION BLOCKED.** Only secondary corroboration is done. |
| **Last attempt** | 2026-10-03 |
| **Blocker** | The build environment's network egress policy denies `cricsheet.org` (HTTP CONNECT rejected by the proxy). `web.archive.org` and `wikidata.org` are also denied. |
| **Fix** | Allow `cricsheet.org` in the cloud environment's network settings, then run `python -m cricintel.sources.cricsheet verify`. That command downloads the files, records checksums, and rewrites the "Observed" sections of this document automatically. |

This document separates three levels of evidence:

- **VERIFIED-PRIMARY**: fetched from cricsheet.org by our tooling (none yet).
- **CORROBORATED-SECONDARY**: stated by at least two independent third-party sources found during research.
- **ASSUMED**: our prior knowledge of the published format, not yet checked. The ingestion adapter treats every ASSUMED item defensively (see the "Adapter behaviour" column).

We have **not** used any third-party mirror of the data. Attaching a GitHub mirror was considered and declined: an unofficial copy can't be verified as unmodified, and doing so was not permitted in this environment. Only data fetched directly from cricsheet.org will be loaded as `source_id = cricsheet`.

## 0. Access routes attempted (2026-10-03)

| # | Route | Result | Evidence |
|---|---|---|---|
| 1 | Direct official downloads `https://cricsheet.org/downloads/*` | ❌ **Blocked by the sandbox egress proxy** (HTTPS CONNECT rejected; `http://` returns proxy 403). `www.cricsheet.org` also blocked. | `curl` status 000 / proxy log `connect_rejected` |
| 2 | Official Cricsheet GitHub org [github.com/cricsheet](https://github.com/cricsheet) (links to cricsheet.org) | ⚠️ Reachable but **not usable**: 3 repos (`cricsheet-xml`, `csv-converter`, `xml-converter`), last updated Aug 2020. They hold tools plus an XML conversion of the retired v0.9 YAML data. No current JSON, no Register. | WebFetch of the org page |
| 3 | Official packages (PyPI / npm / CRAN) | ❌ No Cricsheet-published package exists. PyPI/npm only have community projects (`cricsummary`, `yorkpy`, MCP servers with "bundled" data). Not first-party, not verifiable. CRAN is blocked anyway. | PyPI JSON API, npm search API |
| 4 | Other first-party points: Stephen Rushe's Sourcehut `git.sr.ht/~srushe` (project moved there from GitHub), `deeden.co.uk` | ❌ Blocked by the egress proxy. | proxy `connect_rejected` |
| 5 | Archives / mirrors (web.archive.org, archive.org, Zenodo, Hugging Face, figshare, OSF, data.world) | ❌ All blocked by the proxy. Third-party GitHub mirrors exist (e.g. `nandyad/Cric-Data`), but **Cricsheet publishes no checksums**, so a mirror can't be independently verified. Attaching one was also refused by this environment's permission policy. | proxy log; permission denial |
| 6 | **GitHub Actions retrieval** (prepared): `.github/workflows/fetch-cricsheet.yml` downloads from cricsheet.org on a GitHub runner, records headers, SHA-256 and the run URL, and pushes the files unmodified to branch `data/cricsheet-raw`. `python -m cricintel.sources.cricsheet import --src <checkout>` re-verifies every hash locally. | ⏸ **Needs the cricket-intel GitHub repo to exist.** The integration can't create repositories (HTTP 403), and none is attached to this session. | 403 from create_repository; `list_repos` returns none |

**Unblock (either one):** (a) add `cricsheet.org` to this environment's allowed domains, or (b) create the empty `cricket-intel` repo and attach it, so the code can be pushed and the workflow run.

## 1. Licence, commercial use, attribution

| Item | Level | Finding |
|---|---|---|
| Licence | CORROBORATED-SECONDARY | **Open Data Commons Attribution License v1.0 (ODC-By 1.0)**. Corroborated by (a) the IRW dataset PR, which quotes "This dataset is made available under the Open Data Commons Attribution License" and tags the tables ODC-BY 1.0, and (b) a Cricsheet processing guide stating Cricsheet publishes under ODC-By 1.0 and that anything published from the data must credit Cricsheet and make the licence clear. |
| Conflicting claim | NOTED | One AI search summary claimed "CC BY-SA 4.0". It cited no source and two independent sources contradict it, so we treat it as an error. **The primary check must settle this.** ODC-By (attribution only) and a share-alike licence have very different implications for a commercial product: share-alike would require our derived databases to carry the same licence. **If primary verification shows share-alike, work stops for a decision.** |
| Commercial use | CORROBORATED-SECONDARY | ODC-By permits commercial use, modification and derived works, subject to attribution. |
| Attribution | CORROBORATED-SECONDARY | Credit Cricsheet and state the licence on any public use. Implemented in the product as a site-wide attribution footer, a `/about/data` page, and a `source` block in every API response. |
| Register licence | ASSUMED | Assumed to match the match data. To be verified. |

## 2. Coverage (secondary evidence)

Per the IRW dataset PR, built from `all_json.zip` with input cut at **2026-09-17**:

| Slice | Matches | Teams | Date span |
|---|---|---|---|
| International men | 7,548 | 110 | 2001–2026 |
| International women | 2,860 | 90 | 2003–2026 |
| Domestic/club men | 10,374 | 245 | 2008–2026 |
| Domestic/club women | 1,710 | 69 | 2015–2026 |
| **Total** | **≈22,492** | | |

**Material limitation (secondary):** Cricsheet *withholds every match involving the Afghanistan men's team and the Afghanistan Premier League*. Any player who played against Afghanistan will be missing those matches. This is surfaced in the product's coverage notices.

The Cricsheet Register is described by search results as covering ~17.5k people with ~27k identifiers from 12 sources (figures are likely dated).

## 3. Downloads (ASSUMED URLs, adapter configurable)

| File | Purpose | Adapter behaviour |
|---|---|---|
| `https://cricsheet.org/downloads/all_json.zip` | All matches, JSON | Primary input; checksum recorded |
| `https://cricsheet.org/downloads/{t20s,odis,tests,it20s,ipl,wpl,...}_json.zip` | Subsets | Optional; same parser |
| `https://cricsheet.org/downloads/recently_added_7_json.zip` (or similar) | Incremental | Optional |
| `https://cricsheet.org/register/people.csv`, `names.csv` | Register | Optional; ingestion works without them (falls back to the per-match `registry`) |

## 4. JSON schema (ASSUMED, format "data_version" 1.0.0 / 1.1.0)

| Path | Assumed meaning | Adapter behaviour if absent/different |
|---|---|---|
| `meta.data_version`, `meta.created`, `meta.revision` | Format version | Recorded; unknown versions logged as schema drift (not fatal) |
| `info.balls_per_over` | Usually 6 (The Hundred: 5) | Default 6 with a warning |
| `info.dates[]` | Match dates | Required; the file is quarantined if missing |
| `info.event.{name, match_number, group, stage}` | Competition | Optional |
| `info.gender` | `male` / `female` | **Required. Never defaulted.** Quarantined if missing |
| `info.match_type` | `T20`, `IT20`, `ODI`, `ODM`, `Test`, `MDM` | Unknown values are kept and mapped to `format_group = other` |
| `info.match_type_number` | Official international number | Optional |
| `info.team_type` | `international` / `club` | Optional; derived if missing |
| `info.overs` | Scheduled overs | Optional |
| `info.teams[]`, `info.players{team: [names]}` | XIs | Required |
| `info.registry.people{name: id}` | Per-match name → Register id | If missing, a deterministic fallback id is used and flagged `identity_unresolved` |
| `info.toss.{winner, decision, uncontested}` | Toss | Optional |
| `info.outcome.{winner, by.{runs,wickets,innings}, method, result, eliminator, bowl_out}` | Result | Optional; all shapes handled |
| `info.officials`, `info.player_of_match`, `info.season`, `info.venue`, `info.city`, `info.missing`, `info.supersubs`, `info.bowl_out` | Metadata | Optional; `missing` recorded as a coverage flag |
| `innings[].team` | Batting team | Required |
| `innings[].overs[].over` | 0-based over number | Required |
| `innings[].overs[].deliveries[]` | Deliveries in sequence (incl. wides/no-balls) | Required |
| `delivery.{batter, bowler, non_striker}` | Names (resolved via registry) | Required |
| `delivery.runs.{batter, extras, total, non_boundary}` | Runs | Required except `non_boundary` |
| `delivery.extras.{wides, noballs, byes, legbyes, penalty}` | Extras | Optional |
| `delivery.wickets[].{player_out, kind, fielders[].{name, substitute}}` | Dismissals (list, can be >1) | Unknown `kind` kept and mapped to route `OTHER` |
| `delivery.replacements.{match[], role[]}` | Impact/concussion subs; role replacements | Optional |
| `delivery.review.{by, umpire, batter, decision, umpires_call, type}` | DRS | Optional; any subset of keys |
| `innings[].target.{runs, overs}` | Chase target | Optional; if absent for a chase, derived from the first-innings total and flagged DERIVED |
| `innings[].powerplays[].{from, to, type}` | Powerplays | Optional |
| `innings[].{declared, forfeited, super_over, absent_hurt, penalty_runs.{pre,post}, miscounted_overs}` | Innings flags | Optional |

**Not present (by design of the source):** line, length, speed, pitch coordinates, trajectory, shot type, shot direction, fielder positions, bat contact, wicketkeeper flag, batting hand, bowling style, captain flag. Our canonical schema has nullable, provenance-tagged satellite tables for the tracking/shot/position fields (see `docs/architecture/canonical-model.md`).

## 5. Register (ASSUMED)

`people.csv` columns are assumed to be `identifier, name, unique_name` plus `key_*` columns for external sites (e.g. `key_cricinfo`, `key_cricbuzz`, `key_bcci`, `key_cricketarchive`, `key_crichq`, `key_opta`, `key_pulse`, `key_nvplay`, `key_cricheroes`, `key_cricingif`). `names.csv` holds alternative names. The adapter reads **whatever `key_*` columns exist** and stores them generically. Nothing is hardcoded.

**External identifiers do not grant data rights.** Holding a `key_cricinfo` value lets us *link* to a profile. It does not let us copy data from that site.

## 6. Observed (to be filled automatically by `verify`)

_Not yet run: network blocked._

## Sources (secondary)

- IRW dataset PR, "Cricsheet international and domestic cricket matches (ODC-BY)": https://github.com/ben-domingue/irw/pull/2633
- "How to download and process Cricsheet data": https://www.tigzig.com/agents-faq/how-to-download-and-process-cricsheet-data
- Cricsheet Register page (title only via search): https://cricsheet.org/register/
- Cricsheet article introducing the Register and the JSON format: https://cricsheet.org/article/introducing-the-cricsheet-register-and-a-new-data-format-json
