# Live cricket second-screen experiences: competitive review

| | |
|---|---|
| **Status** | Research only. No UI copied. No sign-ups, app installs or scraping. |
| **Date** | 2026-10-04 |
| **Question** | How do major score, statistics and broadcast products structure the live "second screen", and where can the CRICINTEL Phase 5 replay Match Centre be different in structure, given Cricsheet-only data and the evidence/provenance model? |

## 0. How to read the evidence

**No PRIMARY evidence was obtainable.** The research sandbox's egress proxy blocked direct fetches of every product page tried: espncricinfo.com, espn.co.uk, africa.espn.com, cricbuzz.com (the fetch tool refused it), bbc.co.uk (refused), iplt20.com, icc-cricket.com, cricviz.com, apps.apple.com, applevis.com, cricsheet.org, en.wikipedia.org, plus the secondary hosts punekarnews.in, marcellus.in and acr.iitm.ac.in. A `curl` check also failed for skysports.com, foxsports.com.au, cricket.com.au, thehundred.com and play.google.com. All evidence below came through the web-search index, which means a search engine's summary of the page at the cited URL. **We did not open the page itself.**

Labels:

- **[S-VENDOR]**: SECONDARY. The index summary of the product owner's own page, store listing or press release. It is the closest thing to primary we have, but the wording has not been checked against the live page.
- **[S-3P]**: SECONDARY. A third party (trade press, partner agency, university, accessibility directory) describing the product.
- **unverified**: we found no evidence either way. Common knowledge about these products is **not** stated as fact here.

Because nothing was seen first-hand, **topic 1 (mobile above-the-fold hierarchy) is mostly unverified for every product.** Section 4 gives a short manual audit checklist that someone with normal network access can use to fill the gaps.

## 1. Per-product findings

### 1.1 ESPNcricinfo (site and app)

| Topic | Finding | Evidence |
|---|---|---|
| 1. Above the fold | The relaunched app has a "live score carousel" across concurrent matches. The order of batters, bowler and recent balls inside a match page is **unverified**. | [S-3P] exchange4media 109729 |
| 2. Live score | "Fast live scores and ball-by-ball commentary" plus a "new live cricket score card interface" (app listing). | [S-VENDOR] apps.apple.com/app/417408017 (index); [S-3P] exchange4media |
| 3. Commentary | Ball-by-ball text commentary pages exist per match (URL pattern `/series/<id>/commentary/<id>/…`). Editorial voice versus data inserts is **unverified**. | [S-VENDOR] africa.espn.com commentary URL (index only) |
| 4. Matchups | No evidence found of a live batter v bowler module. **Unverified.** | search returned nothing specific |
| 5. Win probability | **Forecaster** (2019, with IIT Madras and Gyan Data) predicts the innings' final score and each team's win probability "using statistical and machine learning models". Inputs: run rate, overs and wickets left, "quality and form of the players", batting quality of remaining batters, bowlers' remaining overs. It is described as dynamic and shown during live matches. **We found no public calibration disclosure** (no reliability plot or Brier score). | [S-3P] acr.iitm.ac.in (index); [S-3P] punekarnews.in (index); [S-3P] caribbeancricket.com/news/2019/06/07/7903 (index) |
| 5b. Context metrics | **Smart Stats / Superstats**: Smart Runs, Smart Strike Rate, Smart Economy, Smart Wickets, Player Quality Index, Match Impact, a **Luck Index**, and a **Pressure Index** that scores "pressure on a batsman… at each ball faced" from 0 to 10 and weights runs by it. | [S-VENDOR] espn.co.uk story 26312448; espn.com story 30017173 (index) |
| 6. Records/milestones | **Unverified** for the live page. Statsguru records are a separate product. | — |
| 7. Visualisation | A third-party summary says the Match Centre shows "wagon wheels, pitch maps, and session summaries". The data source (scorer-coded or tracking) is **unverified**. | [S-3P] low-quality aggregator (not cited as reliable) |
| 8. Games | **Unverified.** | — |
| 9. Notifications | The app listing mentions "notification updates for live cricket matches". Granularity is **unverified**. | [S-VENDOR] apps.apple.com/app/417408017 (index) |

### 1.2 Cricbuzz

| Topic | Finding | Evidence |
|---|---|---|
| 1. Above the fold | "The Match Center screen adapts to the state of the match: Upcoming, Live or Complete." Element order is **unverified**. | [S-VENDOR] App Store listing via applevis.com and apps.apple.com/us/app/-/id360466413 (index) |
| 2–3. Score, commentary | "Fast scores and immersive ball-by-ball commentary", detailed scorecards, player stats, editorials and expert analysis. | same |
| 4–5. Matchups, win probability | **Unverified.** | — |
| 9. Notifications | Customisable alerts for wickets, milestones (50s and 100s) and end of innings. | same (index summary) |

### 1.3 CricViz / WinViz (Ellipse Data)

| Topic | Finding | Evidence |
|---|---|---|
| 5. Win probability | **WinViz**: an algorithm by Nathan Leamon that "takes account of the players, the venue and the state of the match to run a series of simulations" and gives each team a win percentage. It is shown on **Sky Sports, BBC** and the **Hundred app Match Centre**, and has been used by the ICC and Fox Sports. The Test version adds conditional "what if" queries ("How would WinViz change with two wickets?" / "if the batting side declared?"). The Hundred version is "modelled on the last 100 balls of a T20 innings" and **does not take account of team strength**, so that it shows the balance of the game state. No calibration disclosure found. | [S-VENDOR] ellipsedata.com/?p=642 (index); [S-VENDOR] CricViz app listing apps.apple.com/app/id1044644979 (index) |
| 7. Visualisation | The CricViz app offers "WinViz Over Time", Expected Runs, Expected Wickets and Expected Dismissals. The CricViz database combines Opta event coding (fielding positions, shots) with **Hawk-Eye / Virtual Eye ball-tracking** going back about 20 years. | [S-VENDOR] app listing (index); [S-3P] marcellus.in (index) |

### 1.4 Opta / Stats Perform (Opta Analyst)

| Topic | Finding | Evidence |
|---|---|---|
| 5. Win probability | **Live Win Probability** (win, loss and draw) simulates every remaining delivery. Each simulated ball comes from a **Next Ball Predictor**, a feed-forward neural network trained per format on home team, score, required rate, wickets, player and venue. There is also **Score Prediction**. The vendor publishes an explainer on what win probability is. The search index surfaced no calibration statistics. | [S-VENDOR] theanalyst.com/articles/introducing-cricket-simulation-models ; theanalyst.com/articles/opta-next-ball-predictor ; statsperform.com/news/explained-what-is-win-probability-and-how-does-it-work (index) |

### 1.5 Official apps: ICC, IPL, The Hundred, Cricket Australia

| Product | Finding | Evidence |
|---|---|---|
| **ICC apps** | Personalised notifications, a dedicated match centre and multilingual content (T20 WC 2021 app). Recent events added **"360-degree visualisations of the biggest sixes"** and a **live tracker of field positions**, both built on tracking data, plus AI-generated vertical highlights. **FanScore** predictor game with global, national and private leagues, and Player-of-the-Match voting. | [S-VENDOR] icc-cricket.com news "the-icc-mens-t20-world-cup-2021-app…", media release "icc-unveils-world-first-digital-experiences…"; [S-3P] incrowdsports.com/?p=3835 (index) |
| **IPL official app** | Live scores and ball-by-ball commentary, Fantasy League, video, live photostream, "IPL Selfie", no adverts. No dedicated predictor tool found. | [S-VENDOR] apps.apple.com/app/id509837419 ; play.google.com …id=ipl.n3 (index) |
| **The Hundred app** (InCrowd for ECB) | Content "intentionally designed to focus on the most relevant information only". It shows **WinViz** in the Match Centre. The **"Who's Winning?"** feature asks fans to vote who is winning at any moment and compares the vote with an AI model that "recalibrates… after every ball". Season and career player stats were added in 2025. | [S-3P] incrowdsports.com/our-work/the-hundred (index); [S-VENDOR] thehundred.com/news/4064343 (index) |
| **Cricket Australia Live** | Live scores, streaming, wicket video replays in the match centre. In 2025 it added **"AI Insights"**: agentic AI surfaces "player milestones, records, and key moments in real time". Users can ask **follow-up questions answered by GPT-5** on Azure. Scorecards go back to **1886**. | [S-VENDOR] apps.apple.com/us/app/-/id720516760 (index); au.insight.com press release 2025; news.microsoft.com feature; [S-3P] mediaweek.com.au, itbrief.com.au |

### 1.6 Broadcasters: BBC Sport, Sky Sports, Fox Cricket

| Product | Finding | Evidence |
|---|---|---|
| **BBC Sport** | Live text commentary with video clips of big moments, audio streams (Test Match Special ball-by-ball radio) and "audience interaction". It shows WinViz. | [S-3P] advanced-television.com/?p=157273 (index); ellipsedata.com/?p=642 (index) |
| **Sky Sports Scores app** | A multi-sport match centre with commentary, line-ups and stats. In-match notifications are **opt-in per team**, through Preferences or a bell icon in the Match Centre. Cricket-specific depth is **unverified**. It shows WinViz on broadcast. | [S-VENDOR] apps.apple.com/gb/app/sky-sports-scores/id325185696 (index); applevis comments (index) |
| **Fox Cricket** | Uses WinViz (per CricViz). App features are **unverified** because the site was blocked and nothing was indexed. | [S-VENDOR] ellipsedata.com (index) |

### 1.7 Visualisation data dependencies (cross-product)

Hawk-Eye uses six or more high-speed cameras to rebuild a 3D ball path. Broadcasters have used it since 2001 to drive pitch maps, LBW projections and post-bat trajectory wagon wheels [S-3P] topendsports.com/sport/cricket/equipment-hawkeye.htm (index). Wagon wheels on score sites may instead come from manual scorer zone coding. Which source each product uses is **unverified**. **Cricsheet supplies neither.** It has batter, bowler, non-striker, runs, extras, wicket kind, player out and named fielders, but no line, length, shot direction, speed or field positions (project archive `docs/research/visual-data-sources.md`, [P-ARCH] there). Worms, Manhattans, run-rate charts and partnership bars use only per-ball runs and wickets, so Cricsheet **can** support them.

## 2. Cross-cutting patterns observed

1. **The state-adaptive match centre** (upcoming, live, complete) is standard (Cricbuzz).
2. **Win probability has become a commodity**: Forecaster, WinViz and Opta all describe "simulate the remaining balls". **None of the evidence found includes a public calibration disclosure** (reliability diagram, Brier or log-loss, sample size). The closest thing to methodological candour is WinViz's Hundred variant openly leaving out team strength.
3. **Context indices with unvalidated constructs** are shipped as headline numbers: the ESPNcricinfo Pressure Index (0–10) and Luck Index.
4. **Generative "insights" are moving into the live feed**: CA Live's agentic AI on milestones and records, with GPT-5 follow-up Q&A. Public material says nothing about how the claims are grounded or checked.
5. **Spatial visuals depend on tracking data** (Hawk-Eye/Virtual Eye, Opta coding, ICC field-position tracker).
6. **Engagement games** are common in official apps: FanScore, Fantasy League, the Hundred's "Who's Winning?" vote.
7. **Notifications** run from event-typed and customisable (Cricbuzz: wickets, milestones, innings end) to opt-in per team (Sky). Default volume is **unverified** for all products.
8. **Matchups during a live match**: no product had a publicly documented live batter v bowler module in the evidence we could reach. Treat this as an evidence gap, not proof that none exists.

## 3. Where CRICINTEL can be structurally different

These points come from CRICINTEL's model: drill-down to deliveries, a provenance tag on every number, covered-data wording, and refusing unvalidated constructs. They also stay inside what Cricsheet can support.

1. **Every insight is a link, not a sentence.** CA Live's AI Insights and Smart Stats both put a claim on screen without a visible way back to the balls behind it. In CRICINTEL, each card (for example "Bowler X has dismissed Batter Y 3 times in 41 balls") opens the exact delivery list that produces the number. A claim that cannot list its deliveries is not shown.
2. **Each number carries its provenance tag and sample size.** OBSERVED (a ball happened), DERIVED (arithmetic on observed balls), RECONSTRUCTED (for example, the state at ball *n* in replay), MODELLED (any probability), ILLUSTRATIVE (examples only). No competitor in the evidence labels model outputs apart from counts. Show "n = balls" next to every rate. Below a minimum *n*, show the count without the rate, or nothing.
3. **Records are worded as covered data.** CA Live claims official scorecards from 1886. CRICINTEL's coverage is Cricsheet's (for example, men's ODIs from 2002 and IPL from 2008), so milestone and record cards should say "highest within covered matches (n matches, from YYYY)" and never "record". Coverage boundaries should be one tap away.
4. **Relevance gating, with silence as the default.** Show a matchup or partnership insight only when it applies to the **current** striker, bowler or phase, and only when it **changed** since the last ball (for example, a new bowler, a threshold crossed, or a new partnership). If nothing changed, show nothing. This is the structural opposite of a stat dump. It also fills the matchup gap noted in §2.8 using only delivery data.
5. **Win probability only if calibrated, and calibrated in public.** If CRICINTEL shows a MODELLED probability, publish the reliability curve and the Brier/log-loss on held-out covered matches, and link the existing model card (`docs/model-card-baseline.md`). Show uncertainty and the model's inputs, and state what it ignores, much as WinViz-Hundred states that it excludes team strength. Until calibration passes, show a DERIVED alternative instead: required rate, balls left and wickets in hand, together with OBSERVED historical outcomes from similar covered states and the sample size.
6. **Spoiler-safe replay as a first-class mode.** This is a replay product, so the state must be strictly time-bounded. No final result, end-of-match records, later milestones or "this was the turning point" until the replay cursor reaches that ball. Mainstream cricket score apps show no evidence of a hide-scores mode. Other sports have one (NBA, Tennis TV, beIN: [S-VENDOR] support.watch.nba.com/hc/en-us/articles/115000587174 , support.tennistv.com …21873584842652 (index)).
7. **No fake spatial visuals.** No wagon wheel, pitch map, beehive or field graphic built from guesses. Use what the balls support honestly: worm, Manhattan, run-rate and required-rate lines, partnership bars, dismissal-type breakdown, and over-by-over strips. Each element should open its deliveries.
8. **No unvalidated constructs.** No pressure, momentum, clutch, luck or "turning point" label. Where a competitor would say "pressure", CRICINTEL can show the observable inputs (required rate, dot-ball run length, wickets in last *k* overs) as OBSERVED/DERIVED values without combining them into an index.
9. **Grounded Q&A, if any.** If a conversational feature is added later (CA Live shows this is coming), every answer should be built from queries whose results are delivery sets, with tags and citations. "Not in covered data" should be an allowed answer.

## 4. Patterns we should NOT copy

- **Single-number pressure, luck or impact indices** shown as fact (Smart Stats Pressure Index and Luck Index) without published validation. This conflicts directly with CRICINTEL's refusal policy.
- **Win probability without a calibration disclosure**: every model in the evidence. A percentage without a reliability statement teaches fans false precision.
- **Fan-vote versus model framing** ("Who's Winning?") that presents a model as the arbiter when its accuracy is undisclosed.
- **Generic stat dumps and generative insight streams** whose grounding is not visible. Volume is not insight.
- **Buzz-on-every-ball notifications.** If CRICINTEL ever notifies, use event types only (wicket, milestone, innings end, as Cricbuzz offers), opt-in, with a quiet default. For replay, do not send notifications at all.
- **Tracking-dependent visuals** (pitch maps, 3D six trajectories, live field trackers). They need Hawk-Eye/Opta data that CRICINTEL does not have and should not imitate.

## 5. Things worth learning from

- **State-adaptive layout** (Cricbuzz): the screen changes with match state. In replay, the "state" is the cursor position.
- **"Only the most relevant information"** as an explicit design goal (Hundred app, per InCrowd), together with compact score strips and carousels (ESPNcricinfo relaunch).
- **Methodological candour in one line**: WinViz-Hundred's "does not account for team strength". CRICINTEL should do the same for every MODELLED number.
- **Conditional "what if" queries** (WinViz Test). These could become a later, clearly MODELLED feature, but only after calibration.
- **Event-typed, user-configurable notifications** (Cricbuzz, Sky) rather than all-or-nothing.
- **Above-the-fold priority, to be confirmed by audit**: score and situation (target, required rate, balls left) first, then the current batters and bowler, then recent balls, then everything else.

**Manual audit checklist (for someone with normal network access):** on one live T20 match each in the ESPNcricinfo, Cricbuzz, IPL and CA Live apps, capture (a) the element order in the first mobile viewport, (b) whether a batter v bowler head-to-head appears during play, (c) how win probability is labelled and whether any methodology link exists, (d) the default notification volume, and (e) whether records are worded as "record" or qualified. Record each item as PRIMARY with the date.

## 6. Sources

All were accessed 2026-10-04 through the search index only. None were fetched directly.

- [S-3P] https://www.exchange4media.com/industry-briefing-news/espncricinfo-unveils-all-new-app-to-offer-more-dynamic-experience-to-cricket-fans-109729.html
- [S-VENDOR] https://apps.apple.com/app/417408017 (ESPNcricinfo app listing)
- [S-VENDOR] https://africa.espn.com/cricket/series/18745/commentary/1150082/india-b-vs-australia-a-final-india-a-team-quadrangular-series-2018
- [S-VENDOR] https://www.espn.co.uk/cricket/story/_/id/26312448/hd-version-conventional-cricket-stats
- [S-VENDOR] https://www.espn.com/cricket/story/_/id/30017173/introducing-smart-stats-where-context-trumps-raw-numbers
- [S-3P] https://acr.iitm.ac.in/iitm_news_repository/iit-espn-ai-driven-ipl-superstats
- [S-3P] https://www.punekarnews.in/espncricinfo-launches-superstats-new-metrics-that-uses-data-science-to-analyze-the-game-of-cricket/
- [S-3P] https://caribbeancricket.com/news/2019/06/07/7903
- [S-VENDOR] https://apps.apple.com/us/app/-/id360466413 (Cricbuzz) and [S-3P] https://applevis.com/apps/ios/sports-activities/cricbuzz-cricket-scores-news
- [S-VENDOR] https://ellipsedata.com/?p=642 (CricViz / WinViz)
- [S-VENDOR] https://apps.apple.com/app/id1044644979 (CricViz app)
- [S-3P] https://marcellus.in/story/cricket-is-having-its-moneyball-moment/
- [S-VENDOR] https://theanalyst.com/articles/introducing-cricket-simulation-models
- [S-VENDOR] https://theanalyst.com/articles/opta-next-ball-predictor
- [S-VENDOR] https://www.statsperform.com/news/explained-what-is-win-probability-and-how-does-it-work
- [S-VENDOR] https://www.icc-cricket.com/news/the-icc-mens-t20-world-cup-2021-app-all-you-need-to-know
- [S-VENDOR] https://www.icc-cricket.com/media-releases/icc-unveils-world-first-digital-experiences-that-take-fans-closer-to-the-game
- [S-3P] https://www.incrowdsports.com/?p=3835 (ICC FanScore)
- [S-VENDOR] https://apps.apple.com/app/id509837419 ; https://play.google.com/store/apps/details?id=ipl.n3 (IPL)
- [S-3P] https://www.incrowdsports.com/our-work/the-hundred
- [S-VENDOR] https://thehundred.com/news/4064343 ("Who's Winning?")
- [S-VENDOR] https://apps.apple.com/us/app/-/id720516760 (Cricket Australia Live)
- [S-VENDOR] https://au.insight.com/en_AU/about/newsroom/press-releases/2025/cricket-australia-live-app-sets-new-standard-with-real-time-ai-insights-and-historic-scorecards.html
- [S-VENDOR] https://news.microsoft.com/source/asia/features/cricket-australia-uses-ai-insights-to-bring-fans-closer-to-the-action
- [S-3P] https://www.mediaweek.com.au/cricket-australia-live-app-adds-real-time-ai-insights-and-historic-scorecards ; https://itbrief.com.au/story/cricket-australia-app-adds-ai-insights-history/
- [S-3P] https://advanced-television.com/?p=157273 (BBC live text)
- [S-VENDOR] https://apps.apple.com/gb/app/sky-sports-scores/id325185696
- [S-3P] https://www.topendsports.com/sport/cricket/equipment-hawkeye.htm
- [S-VENDOR] https://support.watch.nba.com/hc/en-us/articles/115000587174 ; https://support.tennistv.com/hc/en-us/articles/21873584842652-What-is-Spoiler-Mode-on-Tennis-TV
- Internal: `docs/research/visual-data-sources.md` (Cricsheet field coverage, [P-ARCH] there), `docs/model-card-baseline.md`
