# Phase 8 dead-weight removal report

Principle: delete, combine or hide what slows a first-time fan down. **Nothing useful was deleted**; it moved out of the primary path, one tap from where it belongs.

## Removed from primary navigation / first screens

| Item | Was | Now | Why |
|---|---|---|---|
| Explore as the home page (today's mix feed, discovery grid, patterns, gateway cards, Ask chips) | first screen, about 11 phone screens | `/discover` ("Everything we found"), linked from Home | a feed isn't a promise; the home is now a launcher into five heroes |
| Duplicate Ask form + chips on Explore | two Ask entry points | one (the Ask tab) | duplication |
| Gateway cards (Live Lab, Visual Lab, Data, Context) | home | Live Lab = Match replay; Data / Visual Lab / Context = internal links | internal tools aren't fan destinations |
| Story pages (`/story/...`) as destinations | edges in the knowledge graph, links on match/battle/Ask | demoted: no graph edges, no match/battle links (route kept) | the match story now lives on the match page, factually |
| Fingerprint on the player overview | screen 3–4 of the overview | Style tab, with every finding and similar players | style detail is for the curious, not the first look |
| Player overview length | 10.9 phone screens (Kohli) | 4.7 phone screens (3,985 px at 390 px wide) | compression target 3–5 |
| Duplicate hero chips | metadata chips repeated | one row | duplication |
| Battle OutcomeMap section and story link | between edge and breakdown | removed (the breakdown table and the dismissal scene carry the same facts) | repetition |
| Battle "every meeting" list | 30 rows (Kohli v Zampa) | latest 8, "Show all 30" | length |
| Match scorecard first | scorecard top | "Scorecard & details" below the story | story first |
| Match experimental difficulty list | always open | collapsed `<details>`, still labelled EXPERIMENTAL | experimental ≠ first screen |
| Play header, explainer, points on every pick | before the first pick | after the first pick | under-5-second entry |
| Ask's 27 example chips | wall of chips | 13 questions in 6 groups + "More questions" | scanability |
| Ask's 4 example chips after every answer | generic | 1–2 deterministic follow-ups from the answer itself | relevance |
| ExploreNext on hero pages | 6 items | kept at 6 (trialled 4; the Phase 7 rabbit-hole journeys lost their match and innings hops, so depth wins) | — |

## Measured page length (390 px phone, fresh visitor; Phase 7 = commit 48acece built and measured side by side)

| Page | Phase 7 | Phase 8 | Change |
|---|---|---|---|
| Home (was Explore) | 13.7 screens (11,596 px) | 2.7 (2,260 px) | −80% |
| Player: Kohli | 10.9 (9,198 px) | 4.7 (3,985 px) | −57% |
| Player: Bumrah | 10.8 (9,080 px) | 4.9 (4,142 px) | −54% |
| Player: Mandhana | 10.8 (9,136 px) | 4.8 (4,017 px) | −56% |
| Battle: Kohli v Zampa | 5.9 (4,986 px) | 6.2 (5,274 px) | +6%: **not compressed** (see below) |
| Match: MCG 2022 | 5.5 (4,632 px) | 6.4 (5,375 px) | +16%: **not compressed** (see below) |
| Ask (empty / answered) | 1.8 / 2.3 | 1.9 / 2.5 | ≈ |
| Play | 1.7 (1,433 px) | 1.1 (930 px) | −35% |

Battle and Match were **reordered, not shortened**:
- Battle gained the battle hero, the earlier/later halves, the meetings ledger (8 of 30 shown) and similar battles.
- Match gained the story beats and the replay entry above the scorecard.

Their first viewports now answer the question, but the pages are slightly longer than in Phase 7. Shortening them (for example collapsing the breakdown table and the scorecards by default) is in the post-Phase-8 backlog. It is not claimed here.

Everything that left a first screen is still reachable: the player tabs (Style, Matchups including Matchup discovery, Innings, Bowling, Partners, Career…), "N more stories", "Show all 30 meetings", the collapsed experimental box, Discover, and the footer links.

## Kept but internal (not linked from fan paths)

`/data` (Data & methods, licence detail) and `/visual-lab` are linked from the footer (and Visual Lab from Search); `/context` and `/lab` from Discover and method pages. The licence pill stays on every page.

## Not removed (deliberately)

Provenance tags, WHY boxes, intervals, the licence pill and "Historical replay, not live" stay. They're trust, not weight.
