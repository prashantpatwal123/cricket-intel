# Visual Cricket Engine V2 (Phase 6)

Backend: `pipeline/cricintel/analytics/visual.py`. Components: `web/components/visual/index.tsx`. Contracts: `web/lib/visual.ts`.

## Layers: progressive fidelity

| Layer | Content | Today (Cricsheet + CC0) |
|---|---|---|
| L0 Event | batter, bowler, non-striker, runs and extras, boundary flag, dismissal kind, fielder names | ✓ every delivery |
| L1 Player metadata | batting hand, bowling arm and style (career-level), keeper status (derived) | △ bowling style for 7.2% of deliveries, batting hand 0%, keeper for 76.9% of team-matches |
| L2 Delivery geometry | line, length, pitch point, speed | ✕ |
| L3 Shot | shot type, direction | ✕ |
| L4 Contact | edge, contact location | ✕ |
| L5 Tracking | trajectory, movement, positions | ✕ |

`delivery_layers(delivery_id)` returns every layer with `available` and its provenance. Absent layers carry `why_missing` (with evidence) and `unlock` (what source would be needed). `fidelity` is the highest layer present: 0 or 1 today.

## Component contracts (all accept partial data)

| Component | Needs | With today's data |
|---|---|---|
| `LayerLadder` | layers | Shows L0 ✓, L1 △/✕, L2–L5 ✕ with reasons |
| `PitchMap` | `pitch_x`/`pitch_y` (canonical metres: x across, + = off side for the batter; y from the batting crease to the bowler's stumps); hand for the left/right transform (`toBatterFrame`) | "Pitch points: not recorded" |
| `LineLengthMap` | canonical `line` + `length` codes; counts, SR, wickets, boundaries per cell | "Line and length: not recorded" |
| `WagonMap` | real `direction_deg` only | "Shot direction: not recorded" |
| `ShotAtlas` | canonical `shot` codes; balls, runs, SR, boundaries, dismissals | "Shot type: not recorded" |
| `EdgeMap` | validated contact data | Architecture only: "Edges and bat contact: not recorded" |
| `DismissalTheatre` | L0 dismissal (+ derived keeper) | Who → how → whom; no positions; keeper "derived" with confidence |
| `BowlerMap`, `MatchupMap` | compose `LineLengthMap` + `PitchMap` (SR per cell for matchups) | "not recorded" states |

Every component takes an `illustrative` flag. In that mode it draws dashed and hatched marks inside a watermarked frame from generic data only (`/visual-lab`).

## Delivery Replay V2

The delivery page now has a "Progressive replay · layer N of 5" section:
- the layer ladder;
- the dismissal relationship (if any);
- one explicit empty slot for pitch point, shot, edge and ball path;
- an accessible text equivalent.

The Phase 3 schematic scene above it is unchanged: it was already honest ("Schematic · no ball path recorded").

When a future feed supplies L2–L5 on the delivery event (below), the same components render real marks. Nothing else changes.

## Dismissal DNA V2: "How does X get out?" (`/how-out/[id]`, Ask, player page)

The drill path is how out → by bowler → format → phase → every dismissal. Each step is a URL parameter, so any view is linkable.

Virat Kohli in covered data:
- **567 dismissals:**
  - caught by a fielder 239;
  - bowled 89;
  - caught with keeper status unknown 75;
  - caught by wicketkeeper (derived) 74;
  - lbw 37;
  - run out 27;
  - caught & bowled 14;
  - stumped 11;
  - hit wicket 1.
- **Keeper catches (74):** led by Rampaul, Morkel and Southee with 3 each.

How the page handles what isn't recorded:
- **Bowling family split:** offered only when known for ≥ 50% of the selection. For Kohli it is known for 54 of 567, so the page explains why the split is withheld.
- **Unavailable filters:** line/length, shot and edge are listed as unavailable, each with its reason.
- **Keeper catches:** never equated with "caught behind" or an edge.

## Kohli v Zampa: "What do we actually know?" (battle page)

| Known (OBSERVED) | Derived | Not available |
|---|---|---|
| 385 balls, 425 runs across 30 matches; 9 dismissals by kind | SR and dismissal rate v each player's usual; keeper status of catches; phase and situation splits | line and length, shots, edges, pace/turn/drift/bounce |

Metadata status: Kohli's batting hand and Zampa's bowling style are **not in a licence-cleared source**. Wikipedia lists both, but under CC BY-SA, pending review, so they are not used.

The page says plainly what it cannot say:

> We cannot say why this matchup behaves as it does in terms of line, length, shot or spin: none of that is recorded.

No statement such as "struggles against leg-spin outside off" is produced. The journey test asserts this.

## Future live-feed compatibility

The Phase 5 delivery event gains an **optional** `enrichment` block (`live/contract.py: ENRICHMENT_BLOCKS`):
- `L1` `batter_hand`, `bowling_style`;
- `L2` `line`, `length`, `pitch_x`, `pitch_y`, `speed_kph`;
- `L3` `shot`, `shot_family`, `direction_deg`, `attacking`;
- `L4` `contact`, `edge`;
- `L5` `trajectory`, `release`, `fielder_positions`.

Rules:
- Each block must carry a valid Provenance record.
- Line, length and shot must be canonical taxonomy codes.
- ILLUSTRATIVE provenance is rejected on a real delivery.

The engine carries enrichment through (`last.enrichment`, per-ball `layers`, a `capabilities` count per layer) and **never uses it for scoring**.

Tested (`test_phase6.py`):
- An enriched log produces identical scores, batters and partnerships to the same log without enrichment.
- Capabilities are counted.
- Five kinds of bad enrichment are rejected.

The Match Centre architecture does not change: a basic feed sends none, and a licensed one adds what it has.

## Source versioning

See `../data/metadata-pilot.md`. Observations are append-only. `resolve()` reports:
- the value used, its source, version and retrieval time;
- whether the source changed;
- whether sources disagree.
