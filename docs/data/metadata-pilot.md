# Player-metadata pilot (Phase 6)

**Verdict: PARTIAL.**
- **Identity joins:** reliable for all 8 players.
- **Licence-cleared values:** none. No source we may use holds batting hand or bowling style for any pilot player.
- **Nothing questionable was populated.**

Reproduce:
- Fetch: GitHub workflow `fetch-wikidata` on branch `phase6/metadata-pilot` (run 37187863520, 2026-10-04 08:06 UTC), which wrote raw results to branch `data/wikidata-pilot`.
- Ingest: `python -m cricintel.enrich.pilot --pilot-dir … --snapshot-dir …`.
- Report: `metadata-pilot.json`.

This sandbox cannot reach Wikidata or Wikipedia, so the fetch ran on a GitHub-hosted runner, as the Phase 2 Cricsheet and Wikidata fetches did.

## Players and joins (never by name)

The join path is Cricsheet Register id → the Register's ESPNcricinfo identifier → Wikidata item carrying P2697 (ESPNcricinfo player ID) with that value.

| Player | Register id | ESPNcricinfo id | Wikidata item | Join |
|---|---|---|---|---|
| Virat Kohli | ba607b88 | 253802 | Q213854 | unique ✓ |
| Rohit Sharma | 740742ef | 34102 | Q3520045 | unique ✓ |
| Jasprit Bumrah | 462411b3 | 625383 | Q16227998 | unique ✓ |
| MS Dhoni | 4a8a2e3b | 28081 | Q470774 | unique ✓ |
| Smriti Mandhana | 5d2eda89 | 597806 | Q16224802 | unique ✓ |
| Meg Lanning | 27e003ce | 329336 | Q6807995 | unique ✓ |
| Sophie Ecclestone | cdb82f1c | 878039 | Q25339050 | unique ✓ |
| Adam Zampa | 14f96089 | 379504 | Q16225921 | unique ✓ |

Why ids matter:
- The Register holds **three different "Rohit Sharma" records** (740742ef, 94ed3e4b, a1cbdeeb).
- Mandhana and Ecclestone appear only under initials ("S Mandhana", "S Ecclestone").

A name join would have mis-attributed or missed them.

## What each source said

| Field | Wikidata (CC0), 8 players | Wikipedia infobox (CC BY-SA 4.0), 8 players |
|---|---|---|
| Batting hand | **0/8** (no P552; and P552 is generic handedness, not batting hand) | 8/8 present: **withheld** |
| Bowling style | **0/8** (no P2545) | 8/8 present: **withheld** |
| Role / position | 1/8 (Kohli: P413 "batter") | 8/8 present: not ingested |

Wikidata coverage across **all 31,699** items with an ESPNcricinfo ID:
- P2545 (bowling style): 1,157 items.
- P413 (position): 420 items.
- P552 (handedness): 29 items, generic handedness rather than batting hand.

Across Cricsheet players, CC0 bowling style covers 6.4% of players and 7.2% of deliveries (`capability-audit.md`).

Wikipedia values are **withheld** from the committed report and the product. They are CC BY-SA 4.0, and whether extracted infobox facts may be stored, shown and commercially derived from needs legal review. Raw retrieval output stays on the data branch only. The infobox cleaner (`taxonomy.clean_label`) mapped all 8 bowling strings to canonical codes at confidence 0.9–0.95 in the pilot. Mapping is therefore not the bottleneck; licence and coverage are.

Source disagreement is preserved: Bumrah's infobox records "fast" with a footnote that "some sources list him as fast-medium". The normaliser keeps that footnote as a `source note` instead of discarding it.

## Source versioning (`enrich/versioning.py`)

Every value is stored as an **immutable observation**:
- entity, field, source;
- source reference (item or page) and source version (retrieval run or page revision id);
- retrieval time;
- the original text and the normalised code, with mapping confidence;
- licence, whether that licence permits product use, the join method, and a content hash.

Observations are appended, never overwritten. Absence is recorded too ("P2545 absent on item at 2026-10-04"), so a later appearance is visible as a change.

`resolve(entity, field)` answers:
- **What value did CRICINTEL use?** The first *usable* source by policy: manual override > Wikidata > derived.
- **From which source, which version, retrieved when?**
- **Has the source changed?** Per source, whether its content hash ever changed.
- **Do sources disagree?** Across all sources, usable or not.

The pilot store holds 50 observations, including two Wikidata snapshots (3 Oct and 4 Oct) as separate versions.

## Scalable enrichment design (not executed beyond the pilot)

1. **Fetch** on a GitHub runner on a schedule (CC0 Wikidata only), output to a dated data branch with SHA-256 sums. The pipeline is already proven.
2. **Join only by ids:** Register → ESPNcricinfo → P2697. Zero or multiple items means no join, and is reported.
3. **Normalise** with `taxonomy.normalize_bowling` / `normalize_batting_hand`. Unmapped labels stay unknown; coarse labels map only as far as they say.
4. **Append** observations to the versioned store; resolve per policy. Only `usable` (licence-cleared, confidence ≥ 0.8) values reach `player_metadata`.
5. **Report** coverage by field and by delivery weight on `/data`; changed or disagreeing values go to a review list. Nothing is overwritten silently.
6. **Unblock** batting hand and full bowling-style coverage with one of:
   - a legal opinion that Wikipedia infobox facts may be used under CC BY-SA (with attribution and share-alike obligations understood);
   - a licensed player-profile feed (see `../research/data-sources-phase6.md`);
   - manual curation with cited, licence-compatible evidence.
