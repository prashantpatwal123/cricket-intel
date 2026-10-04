# Visual data contracts (dormant)

Status: **declared, not active.** No current feature reads, renders or implies any of these fields. They exist so that
a licensed source (see `docs/research/visual-data-sources.md`) can be added without redesigning the visual engine.

## Principle

The visual engine (`web/lib/viz/model.ts`) draws `VizElement`s, each carrying a provenance state. A ball path, pitch
point, shot direction or fielder position may be drawn **only** when a row exists in one of the tables below with
`prov = OBSERVED` (or `RECONSTRUCTED` with a named method and confidence). Without such a row the element is either
absent or an `UNKNOWN` zone. The engine never substitutes a generic trajectory, swing, edge, pitch location or field.

## Tables (pipeline/cricintel/schema.py)

Already declared (Phase 1), empty: `delivery_tracking`, `delivery_shot`, `delivery_fielding`, `delivery_contact`.
Added in Phase 3 (`FUTURE_TABLES`, never created or loaded):

| Table | Grain | Fields | Feeds |
|---|---|---|---|
| `delivery_tracking` | delivery | release x/y/z, speed at release and pitch, pitch x/y, line/length buckets, bounce, swing°, seam°, spin rpm, arrival x/z, trajectory ref | pitch maps, line & length, speed |
| `delivery_trajectory_points` | delivery × idx | t, x, y, z, phase (release/flight/bounce/post_bounce/post_contact) | true ball path |
| `delivery_shot` | delivery | shot type/family, foot, direction°, distance, control, edge type | shot atlas, wagon wheel |
| `delivery_contact` | delivery | contact zone, contact x/y on the bat | edge/contact maps |
| `delivery_batter_state` | delivery | handedness, stance, guard, start/contact position, movement ref | batter movement, stance |
| `delivery_fielding` | delivery × fielder | fielder, position label, x/y, action | catch/run-out location |
| `field_configuration` | delivery × fielder | position label, x/y, inside circle | field placement |
| `tracking_provider` | source | provider, licence, coverage, units, coordinate frame, accuracy note, reconstruction method, retrieved at | provenance & attribution |

Every table carries `PROV_COLS`: `prov`, `prov_source_id`, `prov_method`, `prov_method_version`, `prov_confidence`.

## Coordinate frame

Metres. Origin at the middle stump of the striker's wicket. `y` along the pitch towards the bowler (bowler's stumps at
20.12). `x` lateral, positive to the off side of a right-hander (mirrored only when handedness is OBSERVED). `z` height
above ground. Field coordinates use the same origin.

## Activation checklist (per source)

1. Licence permits our use (including redistribution of derived visuals) — recorded in `tracking_provider`.
2. Adapter maps the provider's frame to ours; a test round-trips known deliveries.
3. External validation against a published sample (e.g. broadcast graphics) before any render.
4. The visual engine's element gets `prov` from the row, never from a default.
5. Coverage UI states exactly which matches have the data; elsewhere the element stays UNKNOWN.
