# Richer per-delivery data: candidate sources

| | |
|---|---|
| **Status** | Research only. No sign-ups, trials, purchases, forms or scraping were done. |
| **Date** | 2026-10-04 |
| **Question** | Which legitimate sources could give CRICINTEL line/length, shot type, wagon-wheel direction, bowling type, batting hand, delivery speed, pitch coordinates, ball tracking/trajectory and fielding positions? |

## 0. How to read the evidence

The research sandbox's egress proxy **blocked direct fetches** of every vendor site tried (cricsheet.org, sportradar.com, cricketapi.com, cricketdata.org, wikidata.org, espncricinfo.com, entitysport.com, sportmonks.com, cricviz.com, hawkeyeinnovations.com, pitchvision.com, crichq.com, kaggle.com). Evidence comes from three places, labelled in the table:

- **[P-ARCH]**: primary pages archived earlier by this project (`docs/data/cricsheet-verification.md`, retrieved 2026-10-03 via GitHub Actions). These are primary-verified.
- **[IDX]**: the search engine's index/summary of the **vendor's own page** at the URL given. The page itself was **not opened**, so these items are **unverified** until someone reads the page.
- **[PRESS]**: press releases or trade-press articles, seen through the search index. These are secondary and **unverified**.

Anything not covered by one of these labels is marked "unverified" or "not public". **Prices are reported only where a vendor pricing page was indexed. Each one is unverified, dated 2026-10-04, and must be re-checked on the live page before anyone relies on it.** Nothing in this document is legal advice. Commercial-use and redistribution terms for paid providers are set in contracts that are not public.

Field abbreviations used below: **LL** line/length · **SHOT** shot type · **WW** wagon-wheel direction/zone · **BT** bowling type · **BH** batting hand · **SPD** delivery speed · **PC** pitch coordinates · **TRK** ball tracking/trajectory · **FLD** fielding positions/coordinates.

## 1. Summary table

| Source | Classification | Fields (of the nine) | Competitions | History | Live | API/export | Public pricing (2026-10-04) | Commercial use / redistribution / attribution | Evidence |
|---|---|---|---|---|---|---|---|---|---|
| **Cricsheet** | OPEN/FREE (match-data licence **unconfirmed**) | **None.** Has ball-by-ball outcome data, named fielders on wickets, and DRS reviews. Says it does not provide ball-tracking or batting/bowling types. | Internationals (men/women), IPL, WPL and many franchise and domestic leagues; Afghanistan men's matches and APL withheld | Men's ODIs from Jun 2002, T20Is from Feb 2005, IPL from 2008 | No (post-match files) | Bulk JSON/CSV downloads | Free | Register: ODC-By 1.0 (attribution required). Match data: no licence stated, footer reads "All rights reserved". Draft question to the owner is not yet sent. | [P-ARCH] `docs/data/cricsheet-verification.md` |
| **ESPNcricinfo / Statsguru** | NOT PRACTICALLY ACCESSIBLE (no public data licence) | Text commentary sometimes describes LL/SHOT/WW in words, not as structured data. Player profiles show BH/BT. | Effectively all first-class and international cricket | Scorecards for very old matches; commentary from about the 2000s (unverified) | Yes (website only) | No public API | Not public | ToU (as indexed): "only for personal use… may not use the Site for commercial purposes"; content may not be "reproduced, transmitted, distributed". **Do not scrape.** | [IDX] https://www.espncricinfo.com/ci/content/site/company/terms_use.html |
| **CricViz (part of Ellipse Data)** | PAID/LICENSED, PARTNERSHIP REQUIRED | Advanced feed: ball-by-ball and wagon wheels. Its app shows pitch maps and beehives (LL/PC). Has a deep database of SHOT/LL (unverified at feed level). | "All major international cricket and franchise competitions" | Unverified | Yes | Data feeds plus embeddable widgets (`<ellipse-data-cricket>`, needs a `customer-id`) | Not public | Contract-defined; not public | [IDX] https://cricviz.com/data-feeds/ , https://widgets.cricviz.com/docs/ , https://www.cricviz.com/about/ ; [PRESS] https://sbcnews.co.uk/sportsbook/2023/12/15/img-cricviz-west-indies/ , https://www.nzc.nz/news-items/archive/cricviz-appointed-official-performance-analysis-and-scoring-partner |
| **Stats Perform (Opta) cricket** | PAID/LICENSED, PARTNERSHIP REQUIRED | Opta ball-by-ball with shot and ball-type coding (SHOT, LL, WW, BT; unverified field list). Official data for several boards. | ICC events (official distributor 2024–2027), ECB home internationals, CA, CSA, NZC, CWI (per press) | "Over five million deliveries" collected per year (vendor claim); depth unverified | Yes | SDAPI feeds | Not public | Contract-defined. Official-data deals are often tied to betting/media rights. | [IDX] https://www.statsperform.com/team-performance/performance-solutions-for-cricket/ ; [PRESS] https://www.statsperform.com/press/stats-perform-wins-back-exclusive-rights-to-collect-and-distribute-official-icc-data-and-live-streams/ , https://www.icc-cricket.com/media-releases/stats-perform-becomes-icc-s-official-data-partner-until-2027 , https://www.prnewswire.com/news-releases/stats-perform-announces-extension-of-official-data-partnership-with-ecb-301328854.html |
| **Sportradar Cricket API (v2)** | PAID/LICENSED (self-serve trial exists; production by contract) | "Advanced" coverage: shot and ball types, wagon wheel data. Docs mention pitch and field coordinates (SHOT, BT/delivery type, WW, PC, possibly FLD). Coverage varies per match. | Broad. Docs call v2 "official for ICC, ECB and CPL", which may be stale because ICC rights moved to Stats Perform in 2024. | Unverified | Yes | REST API (OpenAPI spec) | Not public. Trial defaults: 30 days, 1,000 requests, 1 QPS. | Contract-defined; not public | [IDX] https://developer.sportradar.com/cricket/reference/cricket-overview , https://developer.sportradar.com/getting-started/docs/registration |
| **Hawk-Eye Innovations (Sony)** | NOT PRACTICALLY ACCESSIBLE (rights holders / broadcasters only) | TRK, SPD, PC, bounce, and (in ICC events) post-bat ball tracking | ICC events and major bilateral series where contracted | Unverified | Yes (broadcast/officiating) | No public API | Not public | Data is generated for ICC/boards/broadcasters; no evidence of third-party licensing | [IDX] https://www.hawkeyeinnovations.com/ ; [PRESS] https://www.svgeurope.org/blog/headlines/behind-the-icc-mens-cricket-world-cup-2023-innovations-with-vertical-video-feed-plus-ball-and-player-tracking/ |
| **Roanuz Cricket API** | PAID/LICENSED (self-serve) | Ball-by-ball with "ball type", batter, bowler, fielder, wicket. A separate "Wagon Zone" API (WW as zones). LL/SPD/PC unverified. | International and major leagues (unverified list) | Unverified | Yes | REST/GraphQL | Indexed pricing page: Essential ₹15,902/mo (annual) or ₹17,669 (monthly), 100 matches/mo; Business ₹27,999 / ₹34,999, 200 matches; Business+ ₹47,999 / ₹59,999, unlimited matches. Ball-by-ball resource ₹100/match. **Unverified.** | ToS not read; unverified | [IDX] https://www.cricketapi.com/v5/package-pricing/ , https://www.cricketapi.com/v5/resource/match-wagon-zone , https://sports.dev.roanuz.com/v5/resource/match-ball-by-ball |
| **CricketData.org (CricAPI)** | PAID/LICENSED, with a free tier | Live scores, ball-by-ball, scorecards. None of the nine fields confirmed. | ICC events, IPL, T20I, BBL, PSL and more | Unverified | Yes | REST | Per a third-party profile (not the vendor page): Free $0 (100 hits/day), S $5.99, M $12.99, L $29.99, U $64.99/mo. **Unverified.** | ToS not read; unverified | [IDX] https://cricketdata.org/ ; secondary https://github.com/api-evangelist/cricapi |
| **EntitySport** | PAID/LICENSED (self-serve) | Ball-by-ball commentary; "charts and wagon wheels" (WW). Others unverified. | International and domestic, fantasy-oriented | Unverified | Yes | REST | Indexed pricing page: Starter $150/mo, Pro $250, Elite $450. With commentary: $250 / $500 / $750. **Unverified.** | ToS not read; unverified | [IDX] https://www.entitysport.com/pricing/ , https://www.entitysport.com/cricket-api/ |
| **SportMonks Cricket API** | PAID/LICENSED (self-serve; 14-day trial advertised) | Ball objects: over, ball, score, wicket, four, six, short commentary. **None of the nine fields.** | 20+ / 60+ / 100+ leagues by plan | Unverified | Yes | REST v2 | Indexed pricing page: Major €29/mo, World €75/mo, Enterprise from €129/mo. **Unverified.** | ToS not read; unverified | [IDX] https://www.sportmonks.com/cricket-api/plans-pricing/ , https://docs.sportmonks.com/cricket/our-api/fixtures/get-fixture-by-id |
| **Cricbuzz** | NOT PRACTICALLY ACCESSIBLE | n/a | n/a | n/a | Website/app only | **No official public API found.** RapidAPI/Apify "Cricbuzz" offerings are unofficial scrapers; avoid them. | n/a | ToU at https://www.cricbuzz.com/info/termsofuse (not read) | [IDX] search results only |
| **ICC / national boards (BCCI/IPL, ECB, CA, CSA, NZC)** | PARTNERSHIP REQUIRED | Whatever their appointed collector holds (Opta / CricViz / Hawk-Eye) | Own competitions | Varies | Yes | Through the partner, not the board | Not public | Boards license data exclusively through partners. BCCI–Sportradar deal found is for **integrity**, not data distribution. | [PRESS] links in §2.4 |
| **PitchVision (miSport)** | NOT PRACTICALLY ACCESSIBLE for match data | SPD, LL, PC, TRK, deviation, shot and outcome, **from nets and academies only** | Training environments, not professional matches | n/a | Device-local | No public API found | Not public | Belongs to the player or academy that captured it | [IDX] https://pitchvision.com/about , https://www.pitchvision.com/products |
| **CricHQ / NV Play** | PARTNERSHIP REQUIRED | Scorer-entered SHOT, pitch map (LL/PC), ball arrival, WW. Integrates with Opta and Hawk-Eye. | Mainly grassroots/domestic and the board scoring products that use it | Unverified | Yes | Integrations; no public data API found | Not public | Data belongs to the competition or club; unverified | [IDX] https://www.nvplay.com/products/analysis , https://www.nvplay.com/products/cricket-partnerships-integrations |
| **Wikidata** | OPEN/FREE (CC0, a Wikidata-wide policy; not re-read this session) | **BT** via P2545 "bowling style" (as used in `pipeline/cricintel/metadata/adapters.py`). Batting hand: **no confirmed property**. | Notable players only | n/a (static metadata) | n/a | SPARQL | Free | CC0 means no attribution is legally required (still recommended). Coverage is patchy. | Project code; property pages not reachable (**unverified**) |
| **DBpedia** | OPEN/FREE, but **CC BY-SA** (share-alike) | BH (`dbo:battingSide`), BT (`dbo:bowlingSide`), extracted from Wikipedia infoboxes | Notable players | n/a | n/a | SPARQL/dumps | Free | Share-alike may "infect" a combined metadata dataset. Use only after legal review. | [IDX] https://dbpedia.org/page/Off_spin |
| **Kaggle / academic IPL datasets** | NOT PRACTICALLY ACCESSIBLE (provenance problems) | Usually Cricsheet-equivalent. Some claim LL/SHOT from scraped commentary. | Mostly IPL | Varies | No | CSV | Free | Licences declared by uploaders (often CC0 or "unknown") cannot override the source's rights. Many say they were scraped from ESPNcricinfo. | [IDX] https://www.kaggle.com/datasets/ariadaikalam/the-ultimate-ball-by-ball-cricket-dataset ; Baselight mirrors of Kaggle IPL sets |

## 2. Notes per source

### 2.1 Cricsheet
- **Primary-verified (archived 2026-10-03):** Cricsheet's contact page says *"I don't provide ball-tracking information"* and *"Batting/bowling types for players: I don't store this information for any players"*. It has no delivery timestamps. Per delivery it has batter, bowler, non-striker, runs, extras, wickets with named fielders (and a substitute flag), DRS reviews, and replacements. It has **none of the nine target fields**.
- **Licence:** the Register (`people.csv`, `names.csv`) is ODC-By 1.0. **The match data has no licence statement**; pages say "Freely-available structured data" and the footer reads "Site © 2009–2026 Cricsheet. All rights reserved." A search-engine summary claimed "CC BY-SA 4.0" for Cricsheet. That was **not** found on any primary page and looks like a confusion with the CC BY-SA 2.0 icon credit on `/about/`. **Do not rely on it.**
- **Useful as a join hub:** the Register maps people to identifiers on other sites. A search-indexed Cricsheet page lists ESPNcricinfo, Cricbuzz, CricHQ, NV Play, **Opta**, Pulse, BCCI, Big Bash and others (**unverified** list; check `people.csv` columns). The Opta and Cricinfo keys could make joining licensed data much easier.
- **Action:** the existing draft at `docs/legal/cricsheet-licence-question.md` stays the right next step.

### 2.2 ESPNcricinfo / Statsguru
- The terms of use as indexed restrict the site to personal, non-commercial use and forbid reproducing or distributing content. Commentary text often names the shot and length ("full, driven to cover"), but it is unstructured, inconsistent, and covered by those terms.
- No public data-licensing programme was found. Disney/ESPN may license on request (**unverified**). Third-party "Statsguru scrapers" exist; **CRICINTEL must not use them**, and must not use datasets derived from them (see §2.10).
- Player profile pages show batting hand and bowling style, but the same terms apply. Use them only as a **manual cross-check**, not as an ingestion source.

### 2.3 CricViz and Stats Perform / Opta
- **Ownership:** CricViz describes itself as "part of Ellipse" (Ellipse Data). No evidence was found that CricViz acquired, or was acquired by, Stats Perform. Trade coverage describes CricViz **using Opta-collected data**, and both companies operate in the same market (**unverified** current relationship). Ask both directly.
- **CricViz** publicly offers Standard feeds (fixtures, scorecards, results, standings, squads) and Advanced feeds (Manhattan, wagon wheels, full player stats, WinViz for selected games, ball-by-ball) [IDX]. It also offers embeddable widgets keyed by `customer-id`. It is the analytics partner for ICC event broadcasts and has scoring or performance deals with NZC, Zimbabwe Cricket and the SA20 [PRESS]. Pitch maps and beehives in its app show that it holds LL/PC-type data; whether that data is in a licensable feed is **unverified**.
- **Stats Perform (Opta)** describes "highly detailed ball-by-ball Opta data… for all internationals, T20 leagues and leading domestic first-class and List A competitions" and shot and ball-type data [IDX]. It is the exclusive official data collector/distributor for ICC events (2024–2027) and for ECB home internationals, and has had deals with CA, CSA, NZC and CWI [PRESS]. Many of these deals are framed around **betting** distribution; media or app licences may be a separate product.
- **Classification:** PAID/LICENSED, PARTNERSHIP REQUIRED. No public prices.

### 2.4 Sportradar
- The Cricket v2 docs [IDX] describe three per-match coverage levels: **Post-match**, **Core** and **Advanced**. Advanced "includes more datapoints such as shot and ball types, wagon wheel data". The overview also mentions "live pitch and field coordinates" and "ball tracking for shot and delivery type coding".
- Trial access exists (30 days, 1,000 requests, 1 QPS) and needs registration. **Not done, per instructions.** Production access requires a contract; no price list is published.
- The docs' "official for ICC, ECB and CPL" may be stale: Sportradar held ICC betting rights from 2021 to 2023, and they went back to Stats Perform from 2024 [PRESS: https://www.sportspro.com/news/betting/stats-perform-icc-betting-data-live-streams-distribution-deal/]. Sportradar's BCCI/IPL agreement is for **integrity monitoring** [PRESS: https://www.sportbusiness.com/news/sportradar-inks-agreement-to-scrutinise-ipl-betting/], not official IPL data.

### 2.5 Hawk-Eye (Sony)
- Hawk-Eye provides DRS ball tracking and edge detection, and at the 2023 World Cup it added bat speed, launch angle and post-bat trajectory [PRESS]. This is the only source of true **TRK/SPD/PC** at professional level, alongside other broadcast tracking vendors such as Virtual Eye (not researched).
- No evidence of a public or third-party licensing route was found. The data is owned or controlled by the event rights holder (ICC or board) and reaches the public through broadcasters and partners such as CricViz. Treat it as **NOT PRACTICALLY ACCESSIBLE** directly. Derived tracking fields could arrive indirectly through Opta, CricViz or Sportradar if their contract includes them (**unverified**).

### 2.6 Roanuz, CricketData.org, EntitySport, SportMonks (developer APIs)
- All four are self-serve, live-score and fantasy-oriented APIs. Their main value is **live scoring and ball-by-ball outcomes**, not analyst-grade coding.
  - **Roanuz:** "ball type" (likely legal/wide/no-ball rather than delivery type; unverified) and a **Wagon Zone** API for zone-level WW. Prices above come from the indexed pricing page.
  - **EntitySport:** advertises wagon wheels and ball-by-ball commentary; commentary is a price tier.
  - **SportMonks:** documented ball fields are over, ball, score, wicket, four, six and commentary, so **none of the nine fields**.
  - **CricketData.org:** none of the nine fields confirmed. Its prices come only from a third-party profile.
- **Where they get their data** (own scorers or relicensed official feeds) was not found for any of them. That matters for rights: ask each one.
- No ToS was read for any of the four (sites blocked). Commercial display and redistribution terms are **unverified**.

### 2.7 Boards and leagues (ICC, BCCI/IPL, ECB, CA)
- Boards do not sell data directly to app developers. They appoint exclusive collectors/distributors (Opta for ECB home internationals and ICC events; CricViz for NZC scoring). IPL's official data collector was **not identified** (unverified). The BCCI–Sportradar link found is integrity-only.
- Route: go through the appointed partner. A direct approach to a board is realistic only for a formal partnership.

### 2.8 PitchVision, CricHQ / NV Play
- **PitchVision** captures SPD/LL/PC/TRK in **nets and academies**. That is useful for a future "your own bowling" feature but has no professional match coverage.
- **NV Play** (CricHQ-linked; the exact corporate relationship is unverified) lets scorers code shot type, pitch map and ball arrival, and integrates with Opta and Hawk-Eye. Data belongs to the competition using it. Classification is PARTNERSHIP REQUIRED; most realistic for domestic or grassroots competitions.

### 2.9 Wikidata / DBpedia (player metadata)
- **Wikidata**: the project adapter already uses **P2545 "bowling style"** and **P413 "position played"**, joined through **P2697 ESPNcricinfo player ID**, which matches the Cricsheet Register's cricinfo key. The property IDs could not be re-checked in this session (wikidata.org blocked). No Wikidata **batting-hand** property was confirmed; P741 "playing hand" is used in other sports, but its use for cricketers is **unverified**.
- **DBpedia** has `battingSide` / `bowlingSide` from Wikipedia infoboxes, but it is CC BY-SA. Mixing it into CRICINTEL's metadata table could trigger share-alike. Get legal review before use.
- Coverage will be weakest for women's, associate-nation and domestic players. Keep showing "unknown".

### 2.10 Kaggle and academic datasets
- Most IPL ball-by-ball sets on Kaggle are repackaged Cricsheet data, which inherits Cricsheet's unconfirmed licence, or are **scraped from ESPNcricinfo**, which conflicts with the Cricinfo terms. An uploader's "CC0" label cannot grant rights the uploader did not have. Sets advertising line/length/shot almost certainly come from scraped commentary.
- **Recommendation:** do not ingest. At most, use them for offline research with no publication, and only after a provenance check.

## 3. Recommendation: realistic path to each field

| Field | Most realistic path | Notes |
|---|---|---|
| **Batting hand (BH)** | Open metadata: Wikidata first (confirm a property), then a manually curated override table with cited evidence | A licensed provider's player feed (Sportradar/Opta/Roanuz player profiles) is the fallback. DBpedia only after a share-alike review. |
| **Bowling type (BT)** | Wikidata P2545 (already wired) plus curated overrides | The same licensed player feeds are the fallback. Per-delivery "delivery type" (e.g. googly, slower ball) is licensed-only (Opta / Sportradar Advanced / CricViz). |
| **Line/length (LL)** | Licensed only: Opta, CricViz, Sportradar (Advanced) | No open source exists. Do not derive it from commentary. |
| **Shot type (SHOT)** | Licensed only: same three | Roanuz/EntitySport might offer something; unverified. |
| **Wagon-wheel direction (WW)** | Cheapest: Roanuz Wagon Zone or EntitySport (zone-level, live, self-serve). Analyst-grade: Sportradar Advanced, CricViz, Opta. | Confirm whether data is per-delivery or aggregated, and whether it is a zone or an angle/coordinate. |
| **Delivery speed (SPD)** | Licensed (Opta/CricViz/Sportradar, if they carry Hawk-Eye-derived speed) | Unverified for every provider. Ask explicitly. |
| **Pitch coordinates (PC)** | Sportradar Advanced (documented "pitch coordinates"); CricViz/Opta (unverified) | Ask for the coordinate system and units. |
| **Ball tracking / trajectory (TRK)** | Not practically accessible. Only Hawk-Eye or rights holders, through a formal partnership. | Keep the existing "schematic, labelled" reconstructions. |
| **Fielding positions (FLD)** | Sportradar "field coordinates" (verify meaning); otherwise not available | Named fielders on dismissals already come from Cricsheet. |

**Suggested sequence:**
1. Resolve the Cricsheet match-data licence (draft already prepared).
2. Ship BH/BT from Wikidata plus curated overrides.
3. Use free documentation or trial evaluations, with owner approval, to compare Sportradar (Advanced) with Roanuz/EntitySport on real sample payloads.
4. Open commercial conversations with Stats Perform and CricViz only when there is a budget for enterprise licences.

## 4. Questions to ask each provider

**Ask every paid provider:**
1. Which of these fields do you deliver **per delivery**: line, length, shot type, wagon-wheel angle or zone, delivery/bowling type, batting hand, speed, pitch (x,y), trajectory, fielder positions? Please send a sample payload.
2. For which competitions and seasons? What share of matches gets your highest coverage level? How far back does the history go, and is it in bulk?
3. Is the data **your own collection or relicensed** (from Opta, Hawk-Eye, or a board)? Are you an official data partner for any competition?
4. Licence terms: **commercial use** in a public analytics app; **displaying individual deliveries** compared with derived aggregates only; caching and storage duration; **redistribution or export** to end users; what happens on termination (must we delete historical data?).
5. **Attribution** wording and logo requirements.
6. Pricing for: (a) historical bulk, (b) live, (c) a non-betting media/app use case. Minimum term? Is there a startup or non-commercial tier?
7. Player identifiers: do you expose ESPNcricinfo or other IDs that match the Cricsheet Register?

**Provider-specific:**
- **Sportradar:** which competitions have "Advanced" coverage? What do "pitch coordinates" and "field coordinates" mean (system, units)? Is speed included? Is the ICC/ECB "official" status current?
- **Stats Perform / Opta:** is there a media/app licence separate from betting distribution? What do the line/length and shot taxonomies look like? Is Hawk-Eye-derived speed included?
- **CricViz / Ellipse:** can the Advanced feed be delivered as raw data rather than widgets? Are pitch-map and beehive coordinates included? What is the relationship to Opta data?
- **Roanuz / EntitySport:** is Wagon Zone per-delivery or aggregated? What does "ball type" mean? What is your data source?
- **SportMonks / CricketData.org:** do you carry any of the nine fields? (Current documentation suggests no.)
- **NV Play / CricHQ:** can competition owners authorise third-party access to scorer-coded shot and pitch-map data?
- **Cricsheet:** see `docs/legal/cricsheet-licence-question.md`.

## 5. Open verification items
- Re-read every [IDX] page directly from a network that can reach it, especially the pricing pages and ToS of Roanuz, EntitySport, SportMonks and CricketData.org.
- Confirm Wikidata P2545, P2697 and any batting-hand property directly on wikidata.org.
- Identify IPL's current official data collector.
- Confirm the current CricViz ↔ Stats Perform relationship.
