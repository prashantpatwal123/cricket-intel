# Known data limitations (Milestone 1)

| # | Limitation | Effect in product | Mitigation |
|---|---|---|---|
| 1 | **Real Cricsheet data not yet loaded.** The build environment blocks cricsheet.org. | Everything runs on a labelled SYNTHETIC fixture. | Allow `cricsheet.org` → `python -m cricintel.sources.cricsheet verify` → `python -m cricintel.build --source cricsheet` |
| 2 | Cricsheet licence/schema/coverage verified only from **secondary** sources. | Possible schema drift. | Adapter records unknown keys as drift and quarantines on missing required fields. `verify` writes the primary record. Work stops if the licence turns out share-alike. |
| 3 | No line, length, speed, pitch coordinates, trajectory, shot, direction, fielder positions or bat contact in the source. | No pitch maps, wagon wheels or shot lab. Reconstructions are schematic and labelled. | Enrichment satellite tables exist (nullable, provenance-tagged) for licensed data later. |
| 4 | **Wicketkeeper not marked** in Cricsheet. | "Caught by wicketkeeper" is DERIVED (stumping in the match → 0.97; sole/dominant career keeper in the XI → 0.85/0.75). Ambiguous cases become "keeper status unknown", never guessed. | Better keeper sources later; manual overrides with evidence. |
| 5 | Batting hand / bowling style are **not in Cricsheet**. | Bowler-type matchups depend on an external metadata source. Unknowns are shown as "unknown" and excluded from type splits, with counts. | Wikidata adapter (CC0, joined via the Register's cricinfo key): written, but its property IDs are unverified and the network is blocked. Role and keeper are derived automatically from events. |
| 6 | Coverage starts mid-2000s for most internationals; some matches are missing. | Careers are partial. | Every player shows "Analysed from N matches… not official career totals" plus an automatic left-censoring warning. |
| 7 | (Secondary source) Cricsheet withholds **Afghanistan men** and the Afghanistan Premier League. | Head-to-heads with Afghanistan are missing. | Notice shown on men's player pages when the dataset is Cricsheet. |
| 8 | No timestamps. | No Test day/session context. Limited-overs phases are by over number. | — |
| 9 | Run-out end is not recorded. | Run-out scenes show both ends as "?". | — |
| 10 | Batting position is derived from order of first appearance. | Usually right; can be odd with retirements or super overs. | Super overs are excluded from innings stats. |
| 11 | The baseline model's player effects add ~no skill on held-out data (synthetic). | Probabilities are mostly situation-driven. Labelled MODELLED with version + training window. | Re-evaluate on real data. A better model comes later. |
| 12 | Synthetic fixture players have ~10× real-world per-player volume in the 15k benchmark. | Benchmarks are pessimistic for per-player queries. | Re-benchmark on real data. |
