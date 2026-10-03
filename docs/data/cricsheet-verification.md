# Cricsheet verification record (PRIMARY)

| | |
|---|---|
| **Status** | ✅ Files retrieved from cricsheet.org and checksum-verified. ✅ Schema verified against all 10,247 real files. ⚠️ **Match-data licence NOT stated on cricsheet.org** (see §2). |
| **Retrieval route** | GitHub Actions run [37140804774](https://github.com/prashantpatwal123/cricket-intel/actions/runs/37140804774) on a GitHub-hosted runner, `curl` direct from `https://cricsheet.org`. The sandbox network can't reach cricsheet.org. |
| **Retrieved** | 2026-10-03T17:31:39Z (pages archive: run on branch `data/cricsheet-pages`) |
| **Published unchanged to** | branch `data/cricsheet-raw` (commit `bcb0934`) and `data/cricsheet-pages` (commit `f0c9439`) |
| **Integrity** | Every file re-hashed locally and matched **both** the branch's `SHA256SUMS` **and** the hashes printed in the Actions log (independent channel). `unzip -t` passed on every archive. A tampered file is rejected (test `test_import_rejects_tampered`). |

## 1. Files

| File | Source URL | Bytes | SHA-256 | Server `Last-Modified` | Contents |
|---|---|---|---|---|---|
| ipl_json.zip | https://cricsheet.org/downloads/ipl_json.zip | 5,180,977 | `841b98290a08bdf2a063a9f4d6342fb2363ff246491ed3db4c571bddb6ea2a79` | Wed, 10 Jun 2026 23:06:44 GMT | 1,243 matches + README |
| wpl_json.zip | …/wpl_json.zip | 364,746 | `47a05e39a61b123ef687515475406e37b5a9235382ff15a68e6094da7ca2abf5` | Wed, 10 Jun 2026 23:07:27 GMT | 88 matches |
| t20s_male_json.zip | …/t20s_male_json.zip | 14,214,702 | `e098ad15622ac9e31da60e5e2ecd793c3d33352eb25b2a286b3cf08ffe98fa9e` | Thu, 17 Sep 2026 21:52:39 GMT | 3,558 matches |
| t20s_female_json.zip | …/t20s_female_json.zip | 8,536,330 | `4f66501702589db71917ef3f8386fa6ff99850d695f397dfd262cbc1d7eaf764` | Thu, 17 Sep 2026 21:52:38 GMT | 2,171 matches |
| odis_male_json.zip | …/odis_male_json.zip | 17,456,180 | `b6a1d6b683f19110ada34191183db55c03e09acb386d0f4b9bf0be2fb75bbac0` | Thu, 17 Sep 2026 21:52:31 GMT | 2,576 matches |
| odis_female_json.zip | …/odis_female_json.zip | 4,039,766 | `355f1f5a93d8861942a6d285196362595119ff68c754095b590e23434ecbceb3` | Wed, 09 Sep 2026 19:11:39 GMT | 611 matches |
| register/people.csv | https://cricsheet.org/register/people.csv | 1,178,979 | `71d2bf507f8bde92ca4fe8bcaac4b1bce85e74d432633e8b1667a0594f66405b` | Thu, 17 Sep 2026 21:49:09 GMT | 18,554 people |
| register/names.csv | https://cricsheet.org/register/names.csv | 162,433 | `864bb683c219249194a7dabf4be4086ce97c7f2e351bcee31c026ed46d308601` | Wed, 09 Sep 2026 19:09:54 GMT | 7,549 alternative names |

Hashes above are copied programmatically from the verified manifest (`data/raw/cricsheet/manifest.json`).
Each zip's `README.txt` states: *"The JSON data files contained in this zip file are version 1.2.0 files."*

## 2. Licence, commercial use, attribution (PRIMARY: what cricsheet.org actually says)

| Item | Finding (quoted from archived pages) |
|---|---|
| **Register** (`/register/`) | ✅ *"This dataset is made available under the Open Data Commons Attribution License: http://opendatacommons.org/licenses/by/1.0/"*, plus a summary: free to share, create and adapt, provided you *"attribute any public use of the dataset, or works produced from the dataset"* and *"make clear to others the license of the dataset"*. |
| **Match data** (`/`, `/about/`, `/matches/`, `/downloads/`, `/format/`, `/format/json/`, `/coverage/`, `/missing/`, `/contact/`, `/article/`, zip READMEs) | ⚠️ **No licence statement found.** Pages describe the data as *"Freely-available structured data"*. The site footer reads *"Site © 2009–2026 Cricsheet. All rights reserved."* The zip READMEs contain no licence text. |
| CC BY-SA 2.0 on `/about/` | Applies only to the **site icons** (*"Cricket Ball Seam by Liji Jinaraj… CC BY-SA 2.0"*), not to data. |
| Earlier secondary claims | The third-party sources I cited earlier quote the Register sentence word for word, so they probably **conflated the Register's licence with the match data**. |

**Consequence:** the ODC-By assumption is primary-verified **only for the Register**. For match data, a "freely available" intent is clear, but an explicit licence is not. **Before any public or commercial release we need written confirmation from Cricsheet** (contact given on `/contact/`: stephen (at) cricsheet (dot) org). Until then the app runs as an *internal preview*, labelled as such in the REAL DATA banner. Attribution is shown site-wide regardless.

## 3. Coverage (PRIMARY)

- `/matches/`: *"ball-by-ball information for 22,983 matches"*; *"377 matches are currently being withheld… These matches either involve Afghanistan, or took place in the Afghanistan Premier League."*
- `/article/explanation-for-withholding-of-afghanistani-matches` (14 Nov 2024): the removal of all Afghanistan men's matches and APL matches is **confirmed**.
- `/coverage/` periods ("earliest provided"): men's ODIs **Jun 2002**, men's T20Is **Feb 2005**; women's ODIs **Jan 2007**, women's T20Is **Jun 2009**; IPL **Apr 2008**; WPL **Mar 2023**.
- `/coverage/` completeness: **IPL 1,243 of 1,243 (100%)**, **WPL 88 of 88 (100%)**, plus per club team.
- `/missing/`: 2,930 known-but-unsourced matches (Tests, ODIs, club competitions). **T20 internationals are not tracked** (*"some match types are too extensive to keep track of easily"*), so **T20I completeness cannot be established from Cricsheet.**
- `/contact/` (primary statements we rely on):
  - *"Super Overs don't count towards statistics"*: super-over deliveries are therefore excluded from all player statistics.
  - *"I don't provide ball-tracking information"*.
  - *"Batting/bowling types for players: I don't store this information for any players"*.
  - *"I don't provide timestamps for individual deliveries"*.

**Loaded subset:** 10,247 matches (IPL 1,243 · WPL 88 · men's T20I 3,558 · women's T20I 2,171 · men's ODI 2,576 · women's ODI 611), 3,298,987 deliveries, 134,143 wickets, 0 quarantined, 0 schema drift.

## 4. JSON schema, observed in all 10,247 files

Full machine-readable scan: `docs/data/cricsheet-schema-observed.json` (field → occurrences, % of files, enum values, presence per zip).

| Field | Status | Observed |
|---|---|---|
| `meta.data_version` / `created` / `revision` | present (100%) | data_version **1.2.0** in every file |
| `info.balls_per_over` | present | always 6 in this subset |
| `info.dates`, `teams`, `players`, `registry.people`, `gender`, `match_type`, `team_type`, `toss.{winner,decision}`, `venue`, `season`, `overs`, `outcome` | present (100%) | gender ∈ {male, female}; match_type ∈ {T20, ODI} (**T20Is are `T20` with `team_type=international`; no `IT20` in these files**); team_type ∈ {club, international} |
| `info.registry.people` | present (100%) | 270,804 name→id entries; **every player in every file resolves to a Register id (0 unresolved)** |
| `info.event.{name, match_number, group, stage, sub_name}` | optional | name 99.2%, match_number 91.3%, group 14.0%, stage 7.1%, `sub_name` 0.8% (**not in my assumed schema; now recorded**) |
| `info.city` | optional | 94.8% |
| `info.officials.*` | optional | umpires 95.8%; tv_umpires 59.3% |
| `info.player_of_match` | optional | 92.7% |
| `info.match_type_number` | optional | 87.0% |
| `info.outcome.{winner, by.runs, by.wickets, method, result, eliminator, bowl_out}` | competition-dependent | method ∈ {D/L, Awarded}; result ∈ {tie, no result} |
| `info.missing` | optional | 10.6% (mainly missing powerplay info) |
| `info.supersubs`, `info.bowl_out`, `info.toss.uncontested` | rare | 0.5%, 0.02%, 0.01% |
| `innings[].team`, `overs[].over`, `deliveries[]` | present | |
| **`deliveries[].actual_delivery`** | **present (100%) — NEW in 1.2.0** | The source's own over.ball label (a wide and the following legal ball are both "0.1"). **Now used as the OBSERVED ball label** (was derived) |
| `deliveries[].batter / bowler / non_striker / runs.{batter,extras,total}` | present (100%) | |
| `runs.non_boundary` | optional | 309 deliveries |
| `extras.{wides, noballs, byes, legbyes, penalty}` | optional | penalty on 43 deliveries |
| `wickets[].{player_out, kind}` | present when a wicket falls | kinds: bowled, caught, caught and bowled, lbw, run out, stumped, hit wicket, retired hurt, retired not out, retired out, obstructing the field, hit the ball twice, timed out |
| `wickets[].fielders[].{name, substitute}` | optional | named fielders on 99.7% of wickets that need one; substitute flag present 1,458 times |
| `review.{by, umpire, batter, decision, umpires_call, type}` | competition-dependent | decision ∈ {struck down, upheld, technical failure}; 6,566 reviews; `type` only on 2,843; `umpires_call` on 818 |
| `replacements.match[].{in,out,reason,team}` | competition-dependent | reason ∈ {impact_player, concussion_substitute, supersub, unknown} |
| `replacements.role[].{in,out,reason,role}` | competition-dependent | reason ∈ {injury, too many overs, excluded - high full pitched balls, unknown} |
| `innings[].target.{runs, overs}` | present for chases (98%) | revised DLS targets use **cricket notation** (e.g. `31.2` = 31 overs 2 balls). The adapter now converts correctly (bug found and fixed) |
| `innings[].powerplays[].{from,to,type}` | optional (97.6%) | type ∈ {mandatory, batting, fielding} |
| `innings[].{super_over, absent_hurt, penalty_runs.{pre,post}, miscounted_overs}` | rare | super_over 152 innings; miscounted_overs 252 innings |

**Not available in the source (confirmed by Cricsheet):** line, length, speed, pitch coordinates, trajectory, shot type, shot direction, fielder positions, bat contact, wicketkeeper flag, batting hand, bowling style, captain, delivery timestamps.
