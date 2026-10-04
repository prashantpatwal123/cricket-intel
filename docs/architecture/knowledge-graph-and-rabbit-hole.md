# Knowledge graph and Rabbit-Hole engine (Phase 7)

**Code:** `pipeline/cricintel/fan/kg.py` (graph), `fan/rabbit.py` (ranking), `fan/index.py` (in-memory indexes), `web/lib/memory.ts` (session memory) and `web/components/ExploreNext.tsx` (UI).

**API:**
- `GET /api/fan/next?type=&key=&seen=&shown=&k=` returns the ranked list.
- `GET /api/fan/graph` returns the node types, relation priors, weights and both docstrings.

## Nodes

| Type | Key | Page |
|---|---|---|
| player | person id | `/players/{id}` |
| team | name\|gender | `/rivalries?team=` |
| match | match id | `/match/{id}` |
| innings | match\|innings\|batter | `/innings/…` |
| spell | match\|innings\|bowler | `/spell/…` |
| battle | batter\|bowler | `/battle?bat=&bowl=` |
| partnership | p1\|p2 (sorted) | `/partnerships?p1=&p2=` |
| competition | name\|gender | `/competition?name=&gender=` |
| rivalry | a\|b\|gender | `/rivalry?a=&b=&gender=` |
| record | record id | `/records/{id}` |
| finding | discovery id | the finding's evidence page |
| delivery | delivery id | `/delivery/{id}` |
| moment | match\|cursor | `/live-lab/{match}?n={cursor}&game=1` |

A *view* of the same entity (its story, replay, how-out drill or compare view) gets its own id, `view:{kind}:{key}`. That way it can be recommended without the entity linking to itself.

## Edges (all from covered data)

| From | Relations (examples) |
|---|---|
| player | best innings, best spells, dismissed by (nemesis), dominated, victims, took them apart, partners, similar players, compare, records held, findings, a Play moment, how they get out, main competition, latest match |
| battle | latest dismissal, biggest meeting, the batter's other nemeses, the bowler's other victims, similar battles, both players, the dismissals drill, a Play moment |
| match | top innings, top spells, biggest stand, records containing something from the match, story, replay, a Play moment, edition, rivalry, next match |
| innings | match, Play moment, dismissing bowler (battle), the wicket ball, bowlers faced most, partnership, team-mate, records containing it, story, player |
| spell | match, victims (battles), the batter who scored most off it, the bowler's other best spell, records containing it, bowler |
| delivery | the batter's innings, the bowler's spell, the battle, the match |
| competition | finals, top run-scorer and wicket-taker, most frequent fixture, records in the competition |
| rivalry | recurring battles, latest meeting, top run-scorer |
| partnership | the match of their biggest stand, both players |
| record | its top rows (innings/spell/match/battle/player), people on the list, related records |
| finding | the players involved |

Every edge carries:
- a human reason ("Dismissed them 9 times in 385 balls (about 8.1 expected)");
- six features in [0, 1]: sample (log-scaled), strength, unusualness, recency, recognisability (log of covered matches, 300 = 1) and the relation prior.

## Ranking

    score = 0.22·strength + 0.20·unusual + 0.14·sample + 0.16·recognisability + 0.08·recency + 0.20·relation prior

Picks are made greedily (maximal marginal relevance):
- **Same relation:** subtract 0.16 for each already-picked edge with the same relation.
- **Same target type:** subtract 0.08 for each already-picked edge with the same target type.
- **Already visited this session:** multiply by 0.15 if the fan has opened the destination in this browser session.
- **Already recommended:** multiply by 0.6 if it was already recommended to them twice elsewhere.
- **One entity per list:** an entity appears at most once.

The output keeps every component under `why`. The UI shows only the human reason, and the method sits behind "WHY these?".

Nothing is random. With an empty session memory, the same entity always gives the same list.

## Session memory (local only)

`localStorage["ci-memory-v1"]` holds:
- **Visited:** pages opened (graph id, label, href; the last 80).
- **Shown:** how often each destination was recommended.
- **Play:** the running score.

**Stays in the browser:** there is no account, server copy or tracking. `ExploreNext` sends the visited and shown lists with the request (they are used for that ranking and not stored).

**Reset:** "Clear my history" on Explore and "Clear" on Search remove it. All storage access is wrapped, so a private window simply has no memory.

## Performance

- **Indexes:** player-centric neighbours read from in-memory indexes (best innings, best spells, battles by batter and bowler, partners, main competition, latest match, dismissal counts). These are built in about 2 s per data build by the API warm-up.
- **Caching:** neighbour lists are cached per entity. Ranking (the only session-dependent part) is pure Python over 8–30 edges.
- **Measurements:** see `docs/data/benchmarks-phase7.md`.

## Deterministic rabbit hole

`rabbit.chain(type, key, steps)` follows the top recommendation from each stop and never revisits one. It prefers a different kind of page from the last two stops when one scores within 60% of the best. Explore's "Player rabbit hole" is this chain from a player picked for the day.
