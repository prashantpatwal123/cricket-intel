# Machine-readable provenance and the visual-fidelity contract (Phase 6)

Code: `pipeline/cricintel/enrich/provenance.py` (Python) and `web/lib/visual.ts` (`Provenance` type), with the same wire format.

## The record

| Field | Meaning |
|---|---|
| `provenance_type` | OBSERVED · DERIVED · RECONSTRUCTED · MODELLED · ILLUSTRATIVE |
| `source` | e.g. `cricsheet`, `wikidata`, `derived` |
| `source_field` | e.g. `wickets[].kind`, `P2545 bowling style` |
| `source_event_id` | the delivery id the element describes |
| `confidence` | 0–1 where meaningful (keeper inference 0.90–0.97, mapping confidence) |
| `method` | rule, mapping or model name with version |
| `model_version` | for MODELLED |
| `retrieved_at` | when the source was read |
| `licence` | the source's licence |
| `subject_ids` | real player ids the element is about |
| `why` | generated plain-text answer to "Why am I seeing this?" |

## The five types, enforced in code

| Type | Means | Required | Forbidden |
|---|---|---|---|
| OBSERVED | Directly present in the source | `source`, `source_field` | — |
| DERIVED | Deterministic rule over observed data | `method` | — |
| RECONSTRUCTED | Estimated from sufficient observed inputs | `method`, `confidence` | — |
| MODELLED | Statistical or model output | `method`, `model_version`, `confidence` | — |
| ILLUSTRATIVE | Generic illustration, not a reconstruction of anything that happened | `method` | `source_event_id`, `subject_ids` |

The constructor raises on violations (tested in `test_phase6.py`).

The live contract rejects any enrichment on a real delivery that carries ILLUSTRATIVE provenance, so an illustration cannot be attached to a real ball or player.

## Visual-fidelity contract (for every graphical component)

1. **Layer 0 suffices.** Every component renders with event data alone.
2. **Absent means absent.** If a component's layer is missing it renders an explicit "not recorded" state (`NotRecorded`): what is missing, why, and what would unlock it. It never shows placeholder dots, default trajectories, centred pitch points or "typical" positions.
3. **Every data mark is explainable.** Its provenance is reachable via "Why am I seeing this?" (`Why`), with a colour dot per type.
4. **Illustrations look different.** ILLUSTRATIVE content is drawn dashed, hatched and semi-transparent, inside a frame with a diagonal "ILLUSTRATIVE · NOT REAL DATA" watermark. It takes generic data only (no ids, no names), and its caption states that CRICINTEL has no line, length, shot or tracking data. It never looks like a known trajectory.
5. **Relationships, not geometry.** With only Layer 0, a dismissal is drawn as who → how → whom (`DismissalTheatre`). A keeper catch is labelled "wicketkeeper (derived)" with its confidence, and is never described as "caught behind" or an edge.
6. **Accessible text equivalents.** Every graphic has an `aria-label` and a visible text equivalent built only from recorded facts, e.g. "Adam Zampa to Virat Kohli, Virat Kohli out, caught by Nathan Coulter-Nile. Where the ball pitched, the shot played and any edge are not recorded."
7. **Tests enforce it.**
   - `test_delivery_layers_never_invent_geometry`: no geometry keys exist on Cricsheet deliveries.
   - The Phase 6 journey asserts there is no illustrative frame on any real-data view and no real player named in illustrative examples.
