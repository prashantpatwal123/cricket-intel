# Information architecture (Phase 4)

## Five tabs, unchanged in number

| Tab | Job | Gateways it holds |
|---|---|---|
| **Explore** | "Show me something." Daily feed (deterministic, reasoned), discoveries, patterns. | Competitions, Innings & spells libraries, Play, Compare, Partnerships, Context engine |
| **Search** | "Find a thing." Grouped results across every entity type. | Browse list: Players, Competitions, Rivalries, Innings library, Spell library, Battle universe, Records, Partnerships, Data & methodology |
| **Battles** | Batter v bowler. Lands on the Battle Universe; a battle page has Similar battles. | — |
| **Ask** | "Answer a question." Deterministic parser; shows its interpretation and evidence. | — |
| **Play** | What happens next? | — |

"Players" became **Search**, because players are now one entity type among eleven (player, team, competition, edition,
match, innings, spell, battle, partnership pair, rivalry, record). Search and Ask are deliberately separate:
Search returns *entities*, while Ask returns a *computed answer*. Each page says so in a one-line note.

On desktop, a search box sits in the header on every page.

## Where each new destination lives

| Destination | Route | Reached from |
|---|---|---|
| Match | `/match/[id]` | Search, innings/spell/delivery pages, competition and rivalry match lists, Explore next |
| Competition / edition | `/competitions`, `/competition?name&gender&season` | Explore gateway, Search, match header, Explore next |
| Rivalry / team overview | `/rivalries`, `/rivalry?a&b&gender` | Search ("RCB v CSK"), match page, Explore next |
| Career explorer | `/players/[id]?tab=career&year=` | Player tabs; selecting a year rewrites the page |
| Innings library | `/innings` | Explore gateway, Search browse |
| Spell library | `/spells` | Explore gateway, Search browse |
| Battle universe | `/battle` (no params) | Battles tab |
| Records V2 | `/records` | Search browse, competition page, share cards |
| Stories | `/story/innings/…`, `/story/match/[id]`, `/story/battle` | "How it unfolded" buttons on innings, match and battle pages |
| Share cards | `/share?type=…` | "Share card" buttons; export only |
| Data & methodology | `/data` | Search browse, footer, licence banner |

## The rabbit hole

Every entity page ends with **Explore next** (`components/ExploreNext.tsx`). The links come from
`analytics/related.py`, are deterministic, de-duplicated, and each carries its reason (for example, "Dismissed them 3
times", "Next match in the same competition"). The Phase 4 journey test walks player → battle → delivery → spell →
match → edition → records → player, and checks that each of nine page types offers at least three onward links.

## Design direction

Fewer boxed cards and more typography: rule-separated sections (`.rule-section`), ranked text rows (`.trow`), large
display numerals, a scoreboard header and a story timeline. The cricket motifs are the worm and Manhattan, ball
chips and the year strip. Phase 2/3 card components remain where they carry interactive state (discoveries,
patterns).
