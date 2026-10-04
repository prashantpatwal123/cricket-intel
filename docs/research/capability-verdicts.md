# Capability gates: shot, line/length, edge/contact, computer vision (Phase 6)

Evidence base:
- The observed Cricsheet schema (`../data/cricsheet-schema-observed.json`) and the measured audit (`../data/capability-audit.md`).
- `data-sources-phase6.md`: vendor findings, all SECONDARY because vendor hosts were blocked.
- `computer-vision-phase6.md`: 1 PRIMARY and 27 SECONDARY sources.

A search snippet is not treated as licensing evidence.

## 12. Shot intelligence: **BLOCKED**

Target questions:
- How often does Kohli play the cover drive?
- How many runs does he score from it?
- How often is he dismissed playing it?
- How does that change against leg spin?
- Show every recorded cover drive.

- **Cricsheet:** no shot key in any of 10,247 files. **Wikidata/Wikipedia:** no ball-level data at all.
- **Commercial:** coded shot data is described (SECONDARY) by Stats Perform/Opta, CricViz and Sportradar's higher coverage levels. Fields, coverage, history and rights were **not verified first-hand**. Every price is QUOTE REQUIRED.
- **Computer vision:** shot-family classification is research-feasible but not factual. A 2025 re-implementation got 57.7% for a model reported at 93% (SECONDARY). There is no cross-broadcaster validation, and broadcast video rights are needed.
- **Also missing:** "against leg spin" needs bowling style, which is in licence-cleared data for 7.2% of deliveries only.

**What would unblock it:**
- A licensed ball-by-ball feed with coded shot type, signed terms covering storage, display and commercial derivation, and enough history (≥ 3 seasons for the formats shown).
- A per-source label → canonical mapping table, reviewed (`taxonomy.map_shot`).
- Coverage reporting per match.
- For "against leg spin": licence-cleared bowling style for most bowlers.

## 13. Line/length intelligence: **BLOCKED**

Target questions:
- Where should you bowl to Kohli?
- What is his SR outside off on a good length?
- Where does Bumrah take most wickets?
- Show Zampa's pitch map against Kohli.

- **Cricsheet:** no line, length, pitch coordinate or speed key.
- **Not inferred from proxies:** dismissal kind, outcome and commentary are never used to infer line or length. That rule is written into the taxonomy and enforced by the live contract (canonical codes only, with provenance).
- **Commercial:** ball-tracking-derived line/length/speed is described (SECONDARY) for Opta/CricViz and Sportradar's advanced levels. Rights to Hawk-Eye-derived fields may require board or ICC consent (UNKNOWN). QUOTE REQUIRED.
- **Computer vision:** coarse length bins (full / good / short) from the end-on camera are research-feasible. Line is not feasible now. Neither is production-grade without calibrated ground truth.

**What would unblock it:**
- A licensed feed with per-ball line/length (coded or tracked) or pitch coordinates, plus the vendor's bucket definitions so they map to `LINE`/`LENGTH`.
- Rights confirmed for tracking-derived fields.
- Batting hand for the left/right transform.

## 14. Edge/contact intelligence: **BLOCKED**

Target: outside, inside or top edge; toe, splice or middle; contact coordinates.

- **No source available to CRICINTEL records edges or contact.**
- **Not inferred from dismissal kind:** "caught by wicketkeeper" is derived and explicitly not equated with an edge.
- **Commentary is not ground truth:** commentary text ("edged and taken") could suggest edges, but it is not validated and is not used. Doing so would need a labelled validation set and per-label error rates, and still would not give contact location.
- **Vendors:** edge-detection systems (UltraEdge/Snicko-type, Hawk-Eye) are owned by broadcast and tracking providers. No third-party licensing route was found (SECONDARY).
- **Computer vision:** not feasible from broadcast audio and video. It needs stump-mic audio synchronised with high-frame-rate video.

**What would unblock it:**
- A licensed feed with validated edge flags, published accuracy and rights to display. This is a very high bar.
- For contact coordinates, sensor-bat or tracking data. No consumer-grade source is known.

## 15. Computer vision: **RESEARCH ONLY: do not build**

| Capability | Research-feasible now? | Suitable for factual consumer statistics? |
|---|---|---|
| Ball trajectory (3D) | No (broadcast, single view) | No |
| Pitch / bounce point | Coarse, end-on camera only | No (no calibrated ground truth) |
| Line / length | Length bins only | No; at best CONDITIONAL for length bins |
| Shot family | Yes, coarse | CONDITIONAL: rights-cleared multi-broadcaster training data, per-label precision and recall, abstain below a confidence threshold, coverage reporting |
| Batter pose | 2D yes, metric 3D no | No |
| Fielder positions | No from broadcast (needs a dedicated top view) | No |
| Edges | No from broadcast | No |

**Rights:** broadcast footage belongs to boards, the ICC and broadcasters. Processing it for derived statistics needs a written licence. Research-only datasets (e.g. CricShot10, PRIMARY: research use) do not transfer to a product. No footage was downloaded.

**Difference from a research prototype:** factual statistics need audited accuracy, error bars, abstention, complete coverage and the right to process the footage. None of these exists for broadcast-derived cricket CV.

**Recommendation:** no CV in production. A future internal spike would only be acceptable on consented, own-camera amateur footage, labelled as RECONSTRUCTED or MODELLED and never mixed with Cricsheet facts.
