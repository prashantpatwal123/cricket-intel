# Phase 6: cricket data sources, rights and recommended stacks

| | |
|---|---|
| **Status** | Research only. Nothing was signed up for, trialled, requested, purchased or scraped, and no vendor was contacted. **Do not purchase anything yet.** |
| **Date** | 2026-10-04 |
| **Companion file** | `docs/research/data-sources-phase6.json`, which holds the machine-readable scorecard and evidence. |
| **Builds on** | `docs/data/cricsheet-verification.md` (Cricsheet pages archived first-hand on 2026-10-03), `docs/research/visual-data-sources.md` (field survey from earlier the same day), `docs/data/player-metadata-coverage-cricsheet.md` |
| **Not legal advice** | Every licensing conclusion below is either quoted from a page someone actually read or marked **UNKNOWN (contract review required)**. |

## 1. Method, evidence labels and reachable hosts

### 1.1 Labels

- **PRIMARY**: the page was opened directly, either in this session or in the project's own archived retrieval (`docs/data/cricsheet-verification.md`, a GitHub Actions `curl` run on 2026-10-03, marked **PRIMARY-ARCHIVED**).
- **SECONDARY**: known only from a search engine's summary of the URL, or from trade press or a third-party page. A SECONDARY item is a lead to check, not a fact.
- **UNKNOWN**: no evidence found. For licensing this always reads **UNKNOWN (contract review required)**.

Rules applied throughout:

- A search snippet is never accepted as evidence for a licence or commercial right.
- A price is reported only with its label. Prices seen only through search are listed as SECONDARY indications, and the planning value stays **QUOTE REQUIRED**.

### 1.2 Reachability this session (2026-10-04)

The sandbox egress proxy returned `EGRESS_BLOCKED` for every vendor, board and open-data host tried:

| Blocked (WebFetch refused) |
|---|
| cricsheet.org · developer.sportradar.com · docs.sportradar.com · www.wikidata.org · query.wikidata.org · www.sportmonks.com · docs.sportmonks.com · www.entitysport.com · www.cricketapi.com (Roanuz) · cricketdata.org · www.goalserve.com · cricviz.com · ellipsedata.com · www.statscore.com · www.statsperform.com · www.hawkeyeinnovations.com · www.kaggle.com · api.market · apify.com · support.nvplay.com · dbpedia.org, rapidapi.com, virtualeye.tv, pitchvision.com (curl timed out) |

| Reachable | What was read |
|---|---|
| **github.com** (via WebFetch) | `github.com/roanuz`, `github.com/roanuz/py-cricket`, `github.com/robjhyndman/cricketdata`, `github.com/codophobia/pycricbuzz` |
| **raw.githubusercontent.com** | `api-evangelist/cricapi` README (a third-party profile) |
| **pypi.org** (JSON API) | package metadata for `cricapi`, `pycricbuzz`, `sportmonks`, `sportradar` (all community wrappers) |

**Consequence:** no vendor's own documentation, terms or pricing page was read first-hand this session. All vendor field lists and prices below are SECONDARY. All vendor licence fields are UNKNOWN. The only PRIMARY licensing facts are the archived Cricsheet ones.

## 2. Per-source findings

Field codes:

| Code | Field | Code | Field |
|---|---|---|---|
| **BH** | batting hand | **SW** | swing/seam movement |
| **BS** | bowling style | **SHOT** | shot type |
| **LL** | line and length | **WW** | shot direction / wagon wheel |
| **PC** | pitch coordinates | **FLD** | fielder positions |
| **SPD** | speed | **EDGE** | edge/contact |
| | | **TRK** | trajectory |

The rights columns separate six levels:

- **View**: publicly viewable
- **API**: available through an API
- **Lic**: available under a licence
- **Store**: permitted to store
- **Display**: permitted to display
- **Derive**: permitted to commercially derive from

### 2.1 Open and public sources

| Source | Fields | Coverage / history | Delivery | Rights (View / API / Lic / Store / Display / Derive) | Evidence |
|---|---|---|---|---|---|
| **Cricsheet match data** (JSON/CSV/YAML) | Ball-by-ball outcomes: batter, bowler, non-striker, runs, extras, wickets with named fielders, DRS reviews, replacements. Has **none** of BH/BS/LL/PC/SPD/SW/SHOT/WW/FLD/EDGE/TRK. Cricsheet states *"I don't provide ball-tracking information"* and *"Batting/bowling types for players: I don't store this information"*. | Men's and women's internationals, IPL, WPL and many franchise and domestic leagues. Men's ODIs from 2002, T20Is from 2005, IPL from 2008. | Bulk download, post-match. No live feed. | View yes / API no (files only) / **Lic: UNRESOLVED**: no licence statement; the footer reads "Site © 2009–2026 Cricsheet. All rights reserved." / Store, Display, Derive: **UNKNOWN (written confirmation from Cricsheet required)** | PRIMARY-ARCHIVED: `docs/data/cricsheet-verification.md` |
| **Cricsheet People Register** | Person IDs plus cross-site keys (indexed list: BCCI, Big Bash, Cricbuzz, CricHeroes, CricHQ, Cricingif, CricketArchive, Cricketworld, ESPNcricinfo, NV Play, **Opta**, Pulse) | ~18k people (SECONDARY figure) | CSV download | **ODC-By 1.0** (PRIMARY-ARCHIVED): store, display and derive allowed with attribution | PRIMARY-ARCHIVED for the licence. Key list is SECONDARY: https://cricsheet.org/register/ |
| **Wikidata** | **BS** (P2545 bowling style), BH via P552 handedness (sparse), P413 position, P2697 ESPNcricinfo ID as join key | Notable players only. Project measurement (re-measured 2026-10-04, `enrich/capability.py`): bowling style on **6.4%** of Cricsheet players (7.2% of deliveries), batting hand **0%**. Phase 6 pilot: all 31,699 Wikidata cricketer items have P2545 on 1,157 and P552 on 29 (generic handedness). | SPARQL / dumps | CC0 per the CRICINTEL brief and Wikidata's site-wide policy. **Not re-read first-hand this session (host blocked)**: re-verify before public launch. | PRIMARY (project data: `docs/data/player-metadata-coverage-cricsheet.md`). Property pages were blocked, so UNKNOWN this session. |
| **DBpedia / Wikipedia infoboxes** | BH (`dbo:battingSide`), BS (`dbo:bowlingSide`/infobox "bowling") | Notable players; better batting-hand coverage than Wikidata likely (unmeasured) | SPARQL / dumps | CC BY-SA (share-alike) per the brief. **Not read first-hand.** Share-alike may attach to a combined player table, so derive rights are **UNKNOWN (legal review)**. | SECONDARY: https://dbpedia.org/page/Sachin_Tendulkar , https://dief.tools.dbpedia.org/server/mappings/en/pages/Mapping_en%3AInfobox_recent_cricketer |
| **Board sites** (BCCI, ECB, CA, ICC) | Profiles show BH/BS; scorecards; some board match centres show wagon wheels or pitch maps supplied by partners | Own competitions | Website only. No public data API found. | BCCI ToU (search summary) prohibits reproduction and "systematic retrieval of data… to create… a database" without written consent. ECB, CA and ICC terms not found. All rights: **UNKNOWN (contract review required)**. Treat as no reuse. | SECONDARY: https://www.bcci.tv/news/article/copyright |
| **ESPNcricinfo / Statsguru** | Profiles show BH/BS. Commentary describes LL/SHOT/WW in prose. | Effectively all top-level cricket | Website only | Terms not readable this session. An earlier indexed summary said "personal use… not commercial". **UNKNOWN; do not scrape.** | SECONDARY: https://www.espncricinfo.com/ci/content/site/company/terms_use.html |
| **Kaggle / Baselight mirrors** | Mostly flattened Cricsheet (IPL). Some mix in ESPNcricinfo-scraped fields. | Mostly IPL 2008–2026 | CSV | Uploader licences cannot grant rights the uploader lacks. Treat as **UNKNOWN**, and use Cricsheet directly instead. | SECONDARY: https://baselight.app/u/kaggle/dataset/lyc0riz_ipl_ball_by_ball_dataset_2008_2026 |
| **`cricketdata` R package** (Hyndman) | Wraps Cricsheet and ESPNcricinfo (including `player_meta` from Cricinfo) | As upstream | R package | Code is GPL-3. The README tells users to respect the ESPNcricinfo and Cricsheet terms, so **data rights are not granted by the package**. | PRIMARY: https://github.com/robjhyndman/cricketdata |

### 2.2 Commercial and licensed feeds

| Source | Fields (SECONDARY unless stated) | Coverage | Live | Delivery / docs | Licence (Store / Display / Derive) | Evidence |
|---|---|---|---|---|---|---|
| **Stats Perform (Opta)** | Ball-by-ball with shot type, ball type and line/length (pitch maps "based on line, length and bowling type"), spray charts (WW), "field position" and "batting feet" in the MA3 Match Events feed. Research paper mentions "a bowler's delivery trajectory". So: **LL, PC (likely), BS, SHOT, WW, FLD (some)**. SPD/TRK unconfirmed. | "Every Test, ODI and T20I" plus 14 domestic/franchise competitions. Claims >5M deliveries per year. Official ICC data partner to 2027 (press). | Yes | SDAPI REST feeds (MA1–MA3…). Docs not public. | **UNKNOWN (contract review required)**. Official-data deals are often betting-oriented. | SECONDARY: https://www.statsperform.com/team-performance/performance-solutions-for-cricket/provision-cricket/ , https://support.flowics.com/en_US/sports/working-with-data-connectors-stats-perform-sdapi-cricket , https://www.businesswire.com/news/home/20200302005814/en/Stats-Perform%E2%80%99s-AI-Cricket-Prediction-Research-Paper |
| **CricViz (Ellipse Data)** | Standard feeds (fixtures, scorecards, squads) and Advanced feeds (ball-by-ball, wagon wheels, Manhattan, WinViz). The app shows beehives and pitch maps (LL/PC exist internally). xR/xW metrics. | "All major international and franchise" (vendor claim). Partners include SA20, Star (IPL/T20 WC coverage) and NZC (press). | Yes | Feeds plus embeddable widgets keyed by `customer-id` | **UNKNOWN (contract review required)** | SECONDARY: https://cricviz.com/data-feeds/ , https://www.sportcal.com/news/star-brings-in-cricviz-as-partner-for-ipl-and-t20-world-cup-coverage , https://www.broadcastnow.co.uk/tech-innovation/cricviz-partners-with-sa20/5189308.article |
| **Sportradar Cricket v2** | Per-match coverage levels: **Post-match / Core / Advanced** ("shot and ball types, wagon wheel data") / **Fielding** (fielding position coordinates; ICC majors and CPL only). Overview mentions "live pitch and field coordinates" and "ball tracking for shot and delivery type coding". So **SHOT, BS/ball type, WW, PC, FLD (some matches)**. SPD/TRK unconfirmed. | Broad. Docs say "official for ICC, ECB and CPL", which may be stale because ICC rights moved to Stats Perform for 2024–27. | Yes | REST, public developer portal with OpenAPI. Trial requires registration (not done). | **UNKNOWN (contract review required)** | SECONDARY: https://developer.sportradar.com/cricket/reference/cricket-overview , https://developer.sportradar.com/cricket/reference/cricket-faq , https://sportradar.com/content-hub/news/sportradar-launches-new-comprehensive-live-fielding-data-capture-solution-at-cricket-world-cup/ |
| **Roanuz Cricket API** | Match, **Ball-by-Ball**, Over summary, Player stats, Fantasy, Coverage, Board schedule endpoints (PRIMARY via SDK README). **Wagon Zone** API (zone-level WW, IPL; SECONDARY). Per-ball field schema not seen. | International and major leagues (unverified) | Yes (also a websocket client repo) | REST SDKs in Python/Node/PHP (Apache-2.0 code). Docs host blocked. | **UNKNOWN (contract review required)**; ToS not read | PRIMARY: https://github.com/roanuz/py-cricket , https://github.com/roanuz . SECONDARY: https://www.cricketapi.com/v5/resource/match-wagon-zone |
| **Sportmonks Cricket** | Ball objects: over, ball, score, wicket, four, six, short commentary. **None** of the target fields. | 3 leagues (free), 20 (Major), "all major" (World), 140+ (Enterprise) | Yes | REST v2 | **UNKNOWN (contract review required)** | SECONDARY: https://www.sportmonks.com/cricket-api , https://www.sportmonks.com/blogs/introducing-our-new-pricing-setup/ |
| **EntitySport** | Ball-by-ball live scoring, scorecards, fantasy points, commentary tiers. "Wagon wheels" claimed in earlier indexed page. | International and domestic, fantasy-oriented | Yes | REST, token auth | **UNKNOWN (contract review required)** | SECONDARY: https://apis.io/plans/entitysport/entitysport-plans-pricing/ , https://www.entitysport.com/pricing/ |
| **Goalserve** | Live score, scorecards, **ball by ball**, lineups, standings, odds. No advanced fields seen. | IPL, Tests/ODI/T20I, World Cup, BBL, County Championship, BPL, women's series | Yes | XML/JSON feed | **UNKNOWN (contract review required)** | SECONDARY: https://www.goalserve.com/en/sport-data-feeds/cricket-api/prices |
| **STATSCORE (ScoutsFeed / LivematchPro)** | "Ball-by-ball fast data", scores, wickets, bet-stop/start. Collected by **scouts from low-latency TV**. No advanced fields. | IPL, CPL, MLC, LPL, ICC qualifiers and events (press) | Yes, low latency | Feed (betting-oriented) | **UNKNOWN (contract review required)**. Collected-from-TV raises its own rights questions. | SECONDARY: https://www.gamblinginsider.com/news/22328/statscore-expands-cricket-coverage-with-2023-asia-cup-data |
| **CricketData.org (CricAPI)** | Live scores, ball-by-ball, scorecards, player info. No advanced fields confirmed. | ICC events, IPL, T20I, BBL, PSL… | Yes | REST, hit-count quotas | **UNKNOWN (contract review required)** | PRIMARY (third-party profile only): https://raw.githubusercontent.com/api-evangelist/cricapi/main/README.md . SECONDARY: https://cricketdata.org/ |
| **NV Play / CricHQ** | Scorer-entered SHOT, pitch map (LL/PC), WW. Integrates with Opta and Hawk-Eye (earlier indexed pages). | Mainly domestic and grassroots board scoring | Yes | Integrations; no public data API seen | **UNKNOWN (contract review required)** | SECONDARY: https://www.nvplay.com/products/analysis |
| **Cricbuzz "APIs"** (RapidAPI, Apify actors, `pycricbuzz`) | Scores, scorecards, commentary | As Cricbuzz | Yes | **Unofficial scrapers.** Search results state Cricbuzz "has no official public API". | **LEGALLY RISKY: do not use.** Cricbuzz ToU not read. | SECONDARY: https://apify.com/solidcode/cricbuzz-scraper.md . PRIMARY (repo exists, data method not stated): https://github.com/codophobia/pycricbuzz |

### 2.3 Tracking and vision

| Source | Fields | Third-party availability | Licence | Evidence |
|---|---|---|---|---|
| **Hawk-Eye (Sony)** | TRK, SPD, PC (bounce), impact, EDGE (UltraEdge/Snicko-type), post-bat trajectory and bat speed at ICC events (press) | No public or third-party licensing route found. Data is generated for the ICC, boards and broadcasters. The ICC's 2024–27 data rights tender went to an exclusive partner. Derived fields may reach the market only through Opta, CricViz or Sportradar contracts (**unconfirmed**). | **UNKNOWN (contract review required)** | SECONDARY: https://www.sportcal.com/news/icc-issues-data-rights-tender-through-2027/ , https://www.wipo.int/web-publications/spark-sports-technology/en/game-changing-technologies.html |
| **Virtual Eye (ARL, NZ)** | TRK, SPD, PC (DRS-grade) | Broadcast and DRS supplier. No data product for third parties found. | **UNKNOWN** | SECONDARY: https://virtualeye.tv/the-sports/virtual-eye-cricket |
| **PitchVision** | SPD, LL, PC, deviation (SW), height, TRK, shot. **Nets and academies only.** | Device-local, owned by the user or academy. API/export claims came from a third-party page. | **UNKNOWN**; not match data | SECONDARY: https://www.pitchvision.com/products , https://www.pitchvision.com/about-pitchvision |
| **Broadcaster graphics** | Everything above, as pictures | Broadcast rights only. Extracting the data from video would infringe broadcast rights. | Not available | n/a |

**Bottom line on fields:**

| Field(s) | Realistic source |
|---|---|
| BH, BS | Free, from open metadata (Wikidata, legally clean but sparse), or from any commercial feed's player profiles |
| SHOT, WW, ball/delivery type, LL and pitch-map coordinates, some FLD | Only the **official-data tier**: Opta/Stats Perform, Sportradar Advanced/Fielding, CricViz |
| SPD, SW, TRK, EDGE at professional level | Exist only inside Hawk-Eye / Virtual Eye. No legitimate third-party channel was confirmed. |

## 3. Provider scorecard

Scale is 0–5. Higher is better on every axis:

- **Cost**: 5 = cheapest or most transparent pricing
- **Integration**: 5 = easiest to integrate

Where evidence is missing the score is **UNKNOWN**. Legal clarity and commercial rights are UNKNOWN for every vendor whose terms were not read first-hand. The same table, with evidence URLs, is in the JSON.

| Source | Cov | Gran | Hist | Live | Rel | Docs | Legal | Comm | Cost | Integ |
|---|---|---|---|---|---|---|---|---|---|---|
| Cricsheet match data | 4 | 2 | 4 | 0 | 4 | 4 | 2 | UNK | 5 | 5 |
| Cricsheet Register | 4 | 1 | n/a | 0 | 4 | 3 | 5 | 4 | 5 | 5 |
| Wikidata | 1 | 1 | n/a | 0 | 3 | 4 | 4 | 4 | 5 | 4 |
| DBpedia | 2 | 1 | n/a | 0 | 2 | 3 | 3 | 2 | 5 | 3 |
| Board sites / ESPNcricinfo | 5 | 2 | 5 | 4 | 4 | 0 | 1 | 0 | UNK | 0 |
| Kaggle mirrors | 2 | 2 | 3 | 0 | 2 | 2 | 1 | UNK | 5 | 4 |
| Stats Perform / Opta | 5 | 5 | 4 | 5 | 5 | UNK | UNK | UNK | 1 | 2 |
| CricViz | 4 | 5 | UNK | 5 | 4 | UNK | UNK | UNK | 1 | 3 |
| Sportradar Cricket v2 | 4 | 4 | UNK | 5 | 4 | 4 | UNK | UNK | 1 | 4 |
| Roanuz | 3 | 3 | UNK | 4 | UNK | 3 | UNK | UNK | 3 | 4 |
| Sportmonks | 3 | 1 | UNK | 4 | UNK | 3 | UNK | UNK | 3 | 4 |
| EntitySport | 3 | 2 | UNK | 4 | UNK | UNK | UNK | UNK | 3 | 4 |
| Goalserve | 3 | 1 | UNK | 4 | UNK | UNK | UNK | UNK | 3 | 3 |
| STATSCORE | 2 | 1 | UNK | 5 | UNK | UNK | UNK | UNK | 1 | 3 |
| CricketData.org | 3 | 1 | UNK | 3 | UNK | 2 | UNK | UNK | 4 | 5 |
| Hawk-Eye | 2 | 5 | UNK | 5 | 5 | 0 | UNK | UNK | 0 | 0 |
| Virtual Eye | 1 | 5 | UNK | 5 | 4 | 0 | UNK | UNK | 0 | 0 |
| PitchVision | 0 | 4 | 0 | 2 | UNK | 1 | UNK | UNK | UNK | 1 |
| Cricbuzz unofficial wrappers | 4 | 2 | 2 | 4 | 1 | 1 | 0 | 0 | 4 | 3 |

**One-line justifications** (C = coverage, G = granularity, H = history, L = live latency, R = reliability, D = documentation, Lg = legal clarity, Cm = commercial rights, $ = cost, I = integration):

- **Cricsheet match data.**
  - C4: broad men's and women's coverage, but not everything, and Afghanistan men withheld.
  - G2: outcomes only, no tracking or shot fields.
  - H4: back to 2002/2005/2008.
  - L0: post-match only.
  - R4: checksum-verified locally.
  - D4: format docs read first-hand.
  - Lg2: the licence is explicitly missing ("All rights reserved").
  - Cm UNK: needs written confirmation.
  - $5: free.
  - I5: already integrated.
- **Cricsheet Register.**
  - C4/G1: IDs only.
  - Lg5/Cm4: ODC-By read first-hand; attribution is the only condition.
  - I5: already used.
- **Wikidata.**
  - C1: 6.4% bowling style (7.2% of deliveries) and 0% batting hand on Cricsheet players (re-measured).
  - Lg4/Cm4: CC0, but not re-read this session.
  - I4: SPARQL is easy when reachable.
- **DBpedia.**
  - C2: likely more batting hands than Wikidata (unmeasured).
  - Lg3/Cm2: share-alike obligations unclear for a merged table.
- **Board sites / ESPNcricinfo.**
  - C5/H5: the most complete record.
  - D0/Lg1/Cm0/I0: no API, and the indexed terms prohibit database compilation, so unusable.
- **Kaggle mirrors.**
  - Lg1: provenance laundering risk.
  - G2: no better than Cricsheet.
- **Stats Perform / Opta.**
  - C5/G5/L5/R5: official ICC partner, shot, line/length and field positions (SECONDARY).
  - $1: enterprise-only.
  - I2: enterprise onboarding, and docs not public.
- **CricViz.**
  - G5: holds pitch-map, beehive and wagon data.
  - H UNK.
  - I3: widgets lower the effort, but raw feed terms are unknown.
- **Sportradar.**
  - G4: Advanced and Fielding levels vary by match.
  - D4: a public OpenAPI developer portal (SECONDARY).
  - I4: standard REST.
  - $1: no public price.
- **Roanuz.**
  - G3: ball-by-ball plus wagon zones.
  - D3: SDKs read first-hand.
  - $3: a pricing page exists (SECONDARY).
- **Sportmonks.**
  - G1: no target fields.
  - $3: low entry tiers (SECONDARY).
- **EntitySport.**
  - G2: fantasy-oriented, with possible wagon wheels.
  - $3: tiered prices (SECONDARY).
- **Goalserve.**
  - G1: basic ball-by-ball.
  - $3: listed prices (SECONDARY).
- **STATSCORE.**
  - L5: scouted from TV.
  - G1: basic events.
  - $1: betting B2B, no prices.
- **CricketData.org.**
  - $4: cheapest tiers (third-party page).
  - G1: outcomes only.
  - I5: simple REST.
- **Hawk-Eye / Virtual Eye.**
  - G5: real tracking.
  - $0/I0/D0: no third-party channel found.
- **PitchVision.**
  - C0: no professional-match data.
  - G4: tracks nets sessions.
- **Cricbuzz wrappers.**
  - Lg0/Cm0: unofficial scraping, so excluded however cheap.

## 4. Recommended stacks

**No stack below should be purchased yet.** Each one has preconditions that must be cleared first.

### A. Near-zero cost: what can legally be built now

| | |
|---|---|
| **Sources** | Cricsheet match data (internal preview only) · Cricsheet Register (ODC-By, with attribution) · Wikidata (CC0) for bowling style and batting hand where present · CRICINTEL's own derived features (role-from-usage, keeper inference, phase/pressure models) |
| **Unlocks** | Everything outcome-based: matchups, phase splits, pressure indices, win-probability baselines, similar-battle search, partnership analysis. Bowler-family split on about 8% of deliveries (current Wikidata reach). |
| **Does not unlock** | LL, PC, SPD, SW, SHOT, WW, FLD, EDGE, TRK, or reliable batting hand |
| **Legal preconditions** | (1) **Written match-data licence confirmation from Cricsheet** before any public or commercial release; the draft is already at `docs/legal/cricsheet-licence-question.md`. (2) Re-read Wikidata's CC0 statement first-hand. (3) Keep Cricsheet attribution site-wide. (4) No DBpedia or Wikipedia infobox data in the shipped dataset until share-alike scope is reviewed. (5) No Kaggle mirrors and no scraping. |
| **Open questions** | Does Cricsheet grant commercial use of match data, and on what terms? Is DBpedia batting-hand coverage worth the share-alike review? Can a manually curated, CRICINTEL-owned batting-hand table (entered from personal knowledge, not copied from ToU-restricted sites) close the batting-hand gap? That needs legal sign-off on the method. |

### B. Serious consumer product: materially better without broadcaster-scale infrastructure

| | |
|---|---|
| **Sources** | Stack A **plus one developer-tier commercial API for live ball-by-ball and player profiles**. Leading candidate: **Sportradar Cricket v2**, because its public developer portal documents Advanced (shot, ball type, wagon wheel) and Fielding coverage levels per match. Fallback: **Roanuz** (ball-by-ball plus Wagon Zone, SDKs read first-hand). Entry-level options for live scores only: CricketData.org, Sportmonks, EntitySport, Goalserve. |
| **Unlocks** | Live in-match intelligence (live win probability, live pressure). BH/BS from the vendor's profiles. With Sportradar Advanced: SHOT, ball type, WW and pitch coordinates on covered matches, enough for wagon-wheel and shot-selection views. |
| **Does not unlock** | Hawk-Eye-grade SPD/SW/TRK/EDGE. Consistent depth across every match, because coverage level varies. |
| **Legal preconditions** | Before anything else, read the vendor's terms and contract: storage duration, caching, display in a consumer app, derived-metric ownership, attribution, redistribution limits, and termination clauses (what must be deleted). Check whether the vendor's data is **official** (licensed from the board) or scouted. Confirm whether mixing it with Cricsheet is allowed. |
| **Open questions** | Which matches get Advanced coverage, and how far back? Is historical Advanced data included or priced separately? Are consumer-app display rights included, or only B2B or betting uses? What does the price look like (QUOTE REQUIRED)? Does Sportradar still hold any ICC or ECB official status after 2024? Where does Roanuz's data come from, and what fields does its per-ball schema contain? |

### C. Maximum intelligence: full graphical vision regardless of price

| | |
|---|---|
| **Sources** | **Stats Perform / Opta** (official ICC data partner to 2027; ball-by-ball with shot, line/length, field position) and/or **CricViz** (pitch maps, beehives, wagon wheels, xR/xW). Add **Sportradar Fielding** for ICC majors and CPL. Ask each whether **Hawk-Eye-derived** speed, trajectory and bounce coordinates are included or can be sublicensed through them or via the ICC or a board. Direct Hawk-Eye/Sony or Virtual Eye data would require a rights-holder (ICC/board) agreement. |
| **Unlocks** | Full visual suite: pitch maps and beehives (LL/PC), wagon wheels (WW), shot-type matchups, field-placement analysis (FLD). With tracking: speed, swing/seam, trajectory and edge-based models, so "what the bowler is doing" rather than only "what happened". |
| **Legal preconditions** | Enterprise contracts with explicit consumer-display and derived-analytics rights. Data-rights holder consent (ICC/boards) where tracking is involved. Exclusivity checks, because official-data deals are often tied to betting distribution. A competition-by-competition rights matrix. |
| **Open questions** | Does any vendor actually sell Hawk-Eye-derived fields to a non-broadcaster? What is the current Opta/CricViz relationship, given CricViz is owned by Ellipse Data and no Stats Perform acquisition was found? How deep is the history? Are there IPL rights (BCCI's data partner was not identified)? What is the price (QUOTE REQUIRED for all)? |

## 5. Cost-model inputs

"Planning value" is what a cost model may use today. No price below came from a vendor page read first-hand, so all planning values are **QUOTE REQUIRED**. SECONDARY figures are indications only and must be re-read on the live vendor page.

| Option | Publicly priced? | Indication (label, URL) | Planning value |
|---|---|---|---|
| Stats Perform / Opta | No public price found | n/a | **QUOTE REQUIRED** |
| CricViz | No public price found | n/a | **QUOTE REQUIRED** |
| Sportradar Cricket v2 | No public price. A trial needs registration (not done). | SECONDARY: https://developer.sportradar.com/cricket/reference/cricket-faq | **QUOTE REQUIRED** |
| Roanuz | Pricing page exists | SECONDARY (indexed in earlier project research `visual-data-sources.md`): Essential about ₹15,902/mo annual (100 matches/mo), Business about ₹27,999, Business+ about ₹47,999 (unlimited); ball-by-ball about ₹100/match. https://www.cricketapi.com/v5/package-pricing/ | **QUOTE REQUIRED** |
| Sportmonks Cricket | Pricing page exists | SECONDARY: Free (3 leagues), Major €29/mo, World €75/mo, Enterprise (140+ leagues) custom. https://www.sportmonks.com/cricket-api , https://www.sportmonks.com/blogs/introducing-our-new-pricing-setup/ | **QUOTE REQUIRED** (Enterprise is quote-only even per the secondary source) |
| EntitySport | Pricing page exists | SECONDARY: Starter $150/mo, Pro $250, Elite $450; commentary tiers $250 / $500 / … https://apis.io/plans/entitysport/entitysport-plans-pricing/ (third party), https://www.entitysport.com/pricing/ | **QUOTE REQUIRED** |
| Goalserve | Pricing page exists | SECONDARY: Cricket $125 for 1 month, $550 for 6 months, $1,000 for 12 months. https://www.goalserve.com/en/sport-data-feeds/cricket-api/prices | **QUOTE REQUIRED** |
| STATSCORE | No public price found | n/a | **QUOTE REQUIRED** |
| CricketData.org | Pricing page exists (not read) | Third-party page read first-hand (still not vendor-primary): Free $0 (100 hits/day), S $5.99, M $12.99, L $29.99, U $64.99 per month. https://raw.githubusercontent.com/api-evangelist/cricapi/main/README.md | **QUOTE REQUIRED** |
| NV Play / CricHQ | No public data price found | n/a | **QUOTE REQUIRED** |
| Hawk-Eye / Virtual Eye | No third-party product | n/a | **Not purchasable as found**; rights-holder route only |
| Cricsheet / Wikidata | Free | PRIMARY-ARCHIVED (Cricsheet) | $0 data cost. Licence clarification cost is legal time only. |

Hidden cost drivers to capture in any quote:

- per-competition add-ons
- historical archive fees
- request quotas and QPS
- consumer-display versus B2B licences
- per-match pricing for advanced coverage
- minimum contract terms
- attribution and branding obligations
- deletion-on-termination obligations (these affect derived models)

## 6. Licensing questions that remain UNKNOWN

1. **Cricsheet match data**: no licence stated. Commercial use, redistribution and derived-product rights need written confirmation.
2. **Wikidata CC0 / DBpedia CC BY-SA**: not re-read first-hand this session. DBpedia's share-alike scope for a merged player table needs review.
3. **Every commercial vendor** (Opta, CricViz, Sportradar, Roanuz, Sportmonks, EntitySport, Goalserve, STATSCORE, CricketData.org, NV Play): storage, display, consumer-app use, commercial derivation, caching limits and post-termination deletion are **UNKNOWN (contract review required)**.
4. **Tracking data** (Hawk-Eye, Virtual Eye): whether any third-party sublicence exists, and who must consent (ICC, boards, broadcaster).
5. **Data provenance of mid-tier APIs**: official licensed data versus scouted-from-TV. This affects whether their own rights to resell are sound.
6. **Board sites, ESPNcricinfo, Cricbuzz**: treated as no-reuse. Unofficial wrappers are excluded.

## 7. Sources

**PRIMARY (opened this session or archived first-hand by the project)**

- `docs/data/cricsheet-verification.md` (archive of cricsheet.org pages, 2026-10-03)
- `docs/data/player-metadata-coverage-cricsheet.md` (Wikidata coverage measured by the project)
- https://github.com/roanuz
- https://github.com/roanuz/py-cricket
- https://github.com/robjhyndman/cricketdata
- https://github.com/codophobia/pycricbuzz
- https://raw.githubusercontent.com/api-evangelist/cricapi/main/README.md (third-party profile)
- https://pypi.org/pypi/cricapi/json , https://pypi.org/pypi/pycricbuzz/json , https://pypi.org/pypi/sportmonks/json , https://pypi.org/pypi/sportradar/json

**SECONDARY (search-result summaries; pages not opened)**

- Cricsheet register: https://cricsheet.org/register/
- Sportradar:
  - https://developer.sportradar.com/cricket/reference/cricket-overview
  - https://developer.sportradar.com/cricket/reference/cricket-faq
  - https://sportradar.com/content-hub/news/sportradar-launches-new-comprehensive-live-fielding-data-capture-solution-at-cricket-world-cup/
- Stats Perform / Opta:
  - https://www.statsperform.com/team-performance/performance-solutions-for-cricket/provision-cricket/
  - https://support.flowics.com/en_US/sports/working-with-data-connectors-stats-perform-sdapi-cricket
  - https://www.businesswire.com/news/home/20200302005814/en/Stats-Perform%E2%80%99s-AI-Cricket-Prediction-Research-Paper
  - https://igamingbusiness.com/stats-performs-opta-named-exclusive-data-partner-of-nz-cricket/
- CricViz:
  - https://cricviz.com/data-feeds/
  - https://www.sportcal.com/news/star-brings-in-cricviz-as-partner-for-ipl-and-t20-world-cup-coverage
  - https://www.broadcastnow.co.uk/tech-innovation/cricviz-partners-with-sa20/5189308.article
  - https://apps.apple.com/gb/app/cricviz/id1044644979
- Roanuz:
  - https://www.cricketapi.com/v5/package-pricing/
  - https://www.cricketapi.com/v5/resource/match-wagon-zone
- Sportmonks:
  - https://www.sportmonks.com/cricket-api
  - https://www.sportmonks.com/blogs/introducing-our-new-pricing-setup/
- EntitySport:
  - https://www.entitysport.com/pricing/
  - https://apis.io/plans/entitysport/entitysport-plans-pricing/
- Goalserve: https://www.goalserve.com/en/sport-data-feeds/cricket-api/prices
- STATSCORE:
  - https://www.gamblinginsider.com/news/22328/statscore-expands-cricket-coverage-with-2023-asia-cup-data
  - https://www.statscore.com/news-center/sport/cricket/unlock-the-power-of-cricket-data-for-icc-champions-trophy-2025/
- CricketData.org: https://cricketdata.org/
- NV Play: https://www.nvplay.com/products/analysis
- Hawk-Eye and ICC data rights:
  - https://www.sportcal.com/news/icc-issues-data-rights-tender-through-2027/
  - https://www.wipo.int/web-publications/spark-sports-technology/en/game-changing-technologies.html
- Virtual Eye: https://virtualeye.tv/the-sports/virtual-eye-cricket
- PitchVision:
  - https://www.pitchvision.com/products
  - https://www.pitchvision.com/about-pitchvision
- BCCI: https://www.bcci.tv/news/article/copyright
- ESPNcricinfo: https://www.espncricinfo.com/ci/content/site/company/terms_use.html
- DBpedia:
  - https://dbpedia.org/page/Sachin_Tendulkar
  - https://dief.tools.dbpedia.org/server/mappings/en/pages/Mapping_en%3AInfobox_recent_cricketer
- Kaggle mirror: https://baselight.app/u/kaggle/dataset/lyc0riz_ipl_ball_by_ball_dataset_2008_2026
- Cricbuzz scraper: https://apify.com/solidcode/cricbuzz-scraper.md
