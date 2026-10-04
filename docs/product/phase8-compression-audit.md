# Phase 8 product-compression audit

**Baseline:** `48acece` (Phase 7).

**Method:** I inventoried every route and every module on the main surfaces, using the Phase 7 phone measurements (`docs/screenshots/phase7/report.json` and the re-measured fan audit) as context. Each was classified **before** any Phase 8 change.

**The question for each item:** would a first-time fan miss it if it were not in their first minute?

## Legend

- **HERO:** a core reason to use CRICINTEL.
- **SUPPORTING:** valuable once exploring.
- **ADVANCED:** for serious analysts; reachable, never dominant.
- **EXPERIMENTAL:** not validated for normal presentation.
- **REDUNDANT:** duplicates another experience.
- **INTERNAL:** methodology, debug or data quality.

## Routes

| Route | What it is | Class | Decision |
|---|---|---|---|
| `/` Explore | 13.7 phone screens: daily discovery (7 sections), Today's mix feed (13 rows), Found in the data grid, Patterns cards, 8 gateway cards | Entry point | **Compress** into a home: search, five real examples, one finding, one battle, one Play challenge, then a short "keep exploring" block |
| `/players/[id]` Overview | ~11 phone screens, 10 tabs | **HERO (Player)** | Compress to 3–5 screens; role-adaptive; fingerprint, similar players and long lists move to purposeful tabs |
| `/players/[id]` tabs: Strengths | full strengths engine | SUPPORTING | Kept as tab |
| tabs: When they change | state analysis | ADVANCED | Kept as tab, later in the order |
| tabs: Dismissals | duplicates `/how-out` | REDUNDANT | Kept as a tab (regressions use it); fan links go to `/how-out` |
| tabs: Matchups (lab table) | analyst table | ADVANCED | Kept; the fan home uses matchup discovery |
| tabs: Partners / Innings / Bowling / Career | lists | SUPPORTING | Kept as tabs |
| tabs: Numbers | stat grid | ADVANCED | Kept, last |
| `/battle?bat&bowl` | battle page | **HERO (Battle)** | Rebuilt around "what actually happens when these two meet" |
| `/battle` (no players) | Battle universe | SUPPORTING | Kept as the Battles tab landing |
| `/match/[id]` | scorecard-first match page | **HERO (Match)** | Rebuilt story-first: what made the match interesting; scorecard secondary |
| `/live-lab/[id]` | Match Centre replay | **HERO (part of Match)** | Entered from the match story ("Replay it") and from Play |
| `/live-lab` | list of featured replays | SUPPORTING | Kept; linked from Play |
| `/ask` | Ask Cricket | **HERO (Ask)** | Real categorised questions; deterministic follow-ups |
| `/play` | What happens next? | **HERO (Play)** | Remove the explanation wall: situation, question, choices first |
| `/innings/…`, `/spell/…` | innings and spell stories | SUPPORTING | Kept; evidence for Player and Match |
| `/delivery/[id]` | one ball | SUPPORTING (evidence) | Kept |
| `/how-out/[id]` | dismissal drill | SUPPORTING (evidence) | Kept; the "how they get out" link target |
| `/story/match`, `/story/innings`, `/story/battle` | narrative versions of match, innings and battle | **REDUNDANT** with the redesigned Match/Battle and the innings page | Demoted: no longer linked from hero pages or Explore next; routes kept |
| `/compare` | Compare V2 + raw table | SUPPORTING | Kept; reached from Player and Battle |
| `/records`, `/records/[id]` | record book | SUPPORTING | Kept; builder is ADVANCED behind a link |
| `/on-this-day` | calendar | SUPPORTING | Kept; one item on the home |
| `/partnerships` | pairs and stands | SUPPORTING | Kept |
| `/competitions`, `/competition`, `/rivalries`, `/rivalry` | competition and rivalry hubs | SUPPORTING | Kept; reached via Search and Match |
| `/innings` (library), `/spells` (library) | curated lists | SUPPORTING, partly REDUNDANT with Records V2 | Kept in Search → Browse |
| `/search` | search + browse | SUPPORTING (gateway) | Kept; the home search box leads here |
| `/share` | share-card generator | SUPPORTING | Kept |
| `/data` | data, licence, capability, methodology | INTERNAL | Kept, linked only from the footer, Search → Browse and WHY panels |
| `/context` | Context Engine features | INTERNAL | Search → Browse only |
| `/visual-lab` | what graphics can and can't show | INTERNAL | Search → Browse only |
| `/lab` | Situation Difficulty (SDX) | EXPERIMENTAL | Behind the experimental flag only |

## Modules on the main surfaces

| Module | Where | Class | Decision |
|---|---|---|---|
| Daily discovery: worth knowing / battles / on this day / record / rabbit hole / beat the model | Explore | HERO content, too many at once | Home shows **one** finding, **one** battle, **one** Play challenge; the rest go under "Keep exploring" (one line each) |
| Today's mix feed (13 rows, "why this" lines) | Explore | REDUNDANT with daily discovery | Moved to `/discover` |
| Found in the data (40 cards + 8 filter chips) | Explore | SUPPORTING, too heavy for a home | Moved to `/discover` |
| Patterns (strengths and weaknesses cards) | Explore | REDUNDANT with player homes | Moved to `/discover` |
| 8 gateway cards (Live Lab, Competitions, Libraries, …) | Explore | REDUNDANT with Search → Browse | Removed from home; the Live Lab gateway stays as a single link (regression) |
| Fingerprint radial | Player overview | SUPPORTING | Moved to the **Style** tab with similar players; the home shows its strongest trait in words |
| "What makes them different" (5 cards) | Player | HERO | Top 3, then "show more" |
| Dismissal DNA oval / wicket DNA bars | Player | HERO | One compact summary line with the top routes, plus a link to the step-by-step drill |
| Matchup discovery (8 tabs) | Player | HERO | Top 3 biggest battles + nemesis + one "all battles" link |
| Player stories (6 cards) + Play card | Player | HERO | Top 3 + Play card |
| Partnerships list, records list, career bars, similar players | Player | SUPPORTING | Moved to tabs; the home keeps one "Explore more" row of links |
| Explore next (6 rows) | all entity pages | HERO navigation | Kept, at most 4 rows on hero pages |
| Battle: dismissal scene, outcome map, edge panel, knowledge panel, phase table, similar, universe | Battle | mixed | Reordered: VS strip → v normal → how it changes → every meeting → similar; knowledge panel behind WHY |
| Match: scoreboard, worm, events, SDX table, scorecards, battles, partnerships | Match | mixed | Story first; scorecard and SDX behind tabs or WHY |
| Play: rules paragraph, session stats button, situation card | Play | friction | Pick buttons in the first viewport; scoring explained after the first pick |

## What a first-time fan should encounter

**In the first viewport:**
- the name and promise;
- one search box ("Search a player, match or battle");
- five real, tappable examples, one per hero:
  - Understand Kohli;
  - Kohli v Zampa;
  - Replay the MCG 2022 chase;
  - Can you predict the next ball?;
  - Ask: Who dismisses Kohli most?;
- an optional 60-second tour.

**Directly below:**
- one remarkable finding;
- one great battle;
- one Play challenge.

**Out of the first minute:**
- methodology, licensing detail, capability matrices, filters and leaderboard builders. The licence status stays as a compact pill at the top of every page.

## Hero experiences: tested, not assumed

Each candidate was scored against five questions:

1. Is it unique to ball-by-ball data?
2. Can a fan state it in one sentence?
3. Does it work for any player or match we cover?
4. Does it lead somewhere?
5. Is it trustworthy without caveat overload?

| Candidate | Unique | One sentence | Universal | Leads on | Trustworthy | Verdict |
|---|---|---|---|---|---|---|
| Player | partly (profiles exist elsewhere; dismissal DNA, battles and stories don't) | yes | yes | yes | yes | **Hero** |
| Battle | **yes**: the clearest differentiator | yes | any pair that met | yes | yes, with intervals | **Hero, the signature** |
| Match | the story layer is; the scorecard isn't | yes, if story-first | yes | yes (replay, Play) | yes, deterministic facts only | **Hero (story + replay)** |
| Ask | yes | yes | grammar-limited | yes (follow-ups) | yes, interpretation shown | **Hero** |
| Play | yes | yes | yes (moments) | weaker alone; strong inside stories | yes | **Hero** |
| Explore / discovery | the content is, the page isn't | no ("a feed of things") | — | yes | yes | Not a hero: the **home** is a launcher into the five heroes |
| Records | no (record books exist) | yes | — | yes | yes | Supporting |
| Compare | partly | yes | yes | yes | yes | Supporting (from Player and Battle) |
| Live Lab | yes | "replay a match" | yes | yes | yes | Folded into Match (replay) and Play |

**Result:** the proposed five stand. Two changes follow from the evidence:

- **Match** means *story + replay*: the Live Lab is Match's second half, not a separate destination.
- **Explore** stops being a peer destination and becomes the **Home**: a launcher into the five heroes.

**Navigation becomes:** Home · Players · Battles · Ask · Play. Players replaces Search in the tab bar because the player is the most common entry. Search stays as the home search box, a header search on every page, and `/search`. Matches are reached from the home ("Replay the MCG 2022 chase"), from Search and from every player, innings and battle page.
