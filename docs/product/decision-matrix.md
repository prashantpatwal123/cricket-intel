# Product decision matrix: where the frontier is (Phase 6)

Legend: **Yes** (built, or buildable now) · **Partial** · **No**.

Column meanings:
- **Now:** in CRICINTEL today with Cricsheet plus CC0 metadata.
- **Open data:** possible with open, licence-clear data.
- **Commercial feed:** plausibly available from a licensed coded feed. SECONDARY evidence; contract verification needed.
- **Tracking:** needs ball or player tracking.

| Capability | Now | Open data possible | Commercial feed | Tracking required |
|---|---|---|---|---|
| Dismissal DNA (how out, by whom, format, phase) | **Yes** (keeper catches derived; 78.6% of catches have known keeper status) | Yes | Yes | No |
| Batter v bowler matchup | **Yes** | Yes | Yes | No |
| Bowling-style splits | **Partial** (7.2% of deliveries; withheld below 50% coverage) | Partial (CC0 sparse; Wikipedia blocked by licence) | Yes (player profiles) | No |
| Handedness splits | **No** (0%) | Blocked by licence (Wikipedia CC BY-SA) | Yes (player profiles) | No |
| Line/length weakness | **No** | No | Yes (coded or tracking-derived) | Often (tracking-derived) |
| Shot atlas | **No** | No | Partial–Yes (coded shot labels) | No |
| Cover-drive analysis | **No** | No | Partial (if shot labels are that granular) | No |
| Edge map | **No** | No | Unclear (validated edge flags rare) | Yes (contact detection) |
| Wagon wheel | **No** | No | Yes (direction or zones) | No |
| Pitch map | **No** | No | Partial (tracking-derived via vendor) | Yes |
| Delivery speed | **No** | No | Partial (tracking-derived) | Yes |
| Swing / seam | **No** | No | Rare | Yes |
| Ball trajectory | **No** | No | No (beyond tracking vendors) | Yes |
| Batter stance | **No** | No | No | Yes (pose tracking) |
| Bat path | **No** | No | No | Yes (sensor or tracking) |
| Fielder positions | **No** (fielder names only, on dismissals) | No | Partial (fielding coverage levels) | Yes |
| Graphical dismissal reconstruction | **Partial**: relationship only (who → how → whom, keeper derived); no spatial claim | Same | Partial (with line/length and direction) | Yes for true spatial reconstruction |
| Delivery replay | **Yes**: Layer 0 event chain, schematic | Same | Layers 1–3 | Layers 4–5 |
| Live match centre | **Yes** (historical replay; Phase 5 contract) | — | Yes (live events into the same contract) | No |

## Where the frontier is

1. **Today (Cricsheet + CC0):** CRICINTEL can describe *what happened, to whom, by whom, when and in what match state*, with full evidence trails. That covers dismissals, matchups, partnerships, records, discovery, replays and stories.
2. **Licensed player profiles:** cross the next boundary, batting-hand and bowling-style splits. Licensed profiles, or a legal opinion on Wikipedia infoboxes, unlock them without touching ball-level data.
3. **A licensed coded feed:** crosses the boundary into *how the ball was played and where it went*: shot types, wagon wheels, some line/length.
4. **Tracking-grade data under board or ICC consent:** needed for *what the ball did* (speed, swing, seam, trajectory, edges, pitch maps) and for positions.

The visual engine is already built to receive each layer when it arrives (`../architecture/visual-engine-v2.md`). Until then, it shows a sparse, truthful state.
