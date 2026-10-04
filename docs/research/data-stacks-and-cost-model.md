# Data stacks, provider scorecard summary and cost model (Phase 6)

**Do not purchase anything yet.**

Sources:
- `data-sources-phase6.md` and `.json`: the full per-source findings and 0–5 scorecard with evidence labels. Every vendor claim there is SECONDARY, because vendor hosts were blocked from this environment.
- `capability-audit.md`: what CRICINTEL's data contains, measured.

## Scorecard summary (0–5; U = UNKNOWN, never guessed)

| Source | Coverage | Granularity | History | Live | Legal clarity | Commercial rights | Cost (5 = cheap/transparent) | Integration (5 = easy) |
|---|---|---|---|---|---|---|---|---|
| Cricsheet match data | 4 | 2 | 4 | 0 | 2 | U | 5 | 5 |
| Cricsheet People Register | 4 | 1 | — | 0 | 5 | 4 | 5 | 5 |
| Wikidata | 1 | 1 | — | 0 | 4 | 4 | 5 | 4 |
| Wikipedia / DBpedia infoboxes | 2 | 1 | — | 0 | 3 | 2 | 5 | 3 |
| Stats Perform / Opta | 5 | 5 | 4 | 5 | U | U | 1 | 2 |
| CricViz (Ellipse Data) | 4 | 5 | U | 5 | U | U | 1 | 3 |
| Sportradar Cricket v2 | 4 | 4 | U | 5 | U | U | 1 | 4 |
| Roanuz | 3 | 3 | U | 4 | U | U | 3 | 4 |
| Sportmonks / EntitySport / Goalserve / STATSCORE / CricketData.org | 2–3 | 1–2 | U | 3–5 | U | U | 1–4 | 3–5 |
| Hawk-Eye / Virtual Eye | 1–2 | 5 | U | 5 | U | U | 0 | 0 |
| Board sites / ESPNcricinfo (scraping) | 5 | 2 | 5 | 4 | 1 | 0 | U | 0 |
| Cricbuzz unofficial wrappers | 4 | 2 | 2 | 4 | 0 | 0 | 4 | 3 (excluded: legally risky) |

## Three stacks

**A. Near-zero cost: what CRICINTEL can legally build now.**
- **Sources:** Cricsheet match data, the Cricsheet People Register (ODC-By 1.0) and Wikidata (CC0) via the existing GitHub-runner fetch.
- **Unlocks:** everything in CRICINTEL today, Layers 0–1 (partial).
- **Precondition:** Cricsheet's written confirmation of match-data terms. Until then it stays internal preview only; the email is drafted and not sent.
- **Cannot unlock:** line/length, shot, edge, speed or tracking. No open source has them.

**B. Serious consumer product: materially better without broadcaster-scale infrastructure.**
- **Sources:** Stack A plus one licensed ball-by-ball feed with coded fields. The research's lead candidate is Sportradar Cricket v2: its developer documentation describes per-match coverage levels, though this is SECONDARY. Roanuz is a fallback with zone-level wagon data (SECONDARY). Plus licensed player profiles (batting hand, bowling style).
- **Unlocks (if verified in contract):**
  - live delivery events (the Phase 5 contract is ready);
  - batting-hand and bowling-style splits;
  - wagon or zone direction and possibly coded shot types (Layers L1 and L3 partially).
- **Precondition:** contract review of storage, display, consumer use, derivation, attribution, deletion on termination, and coverage by competition and gender.

**C. Maximum intelligence: the full graphical vision, regardless of price.**
- **Sources:** Stats Perform/Opta and/or CricViz (coded plus tracking-derived line, length, speed and shot), plus Sportradar's advanced and fielding coverage, plus Hawk-Eye-derived fields where boards or the ICC consent.
- **Unlocks:** Layers L2–L5 (pitch maps, line/length weakness, shot atlas, wagon wheels, field positions, trajectory), within the coverage those providers have.
- **Precondition:** board or ICC consent for tracking-derived data (UNKNOWN whether any third-party route exists), enterprise contracts, and per-competition coverage audits.

## Cost model

Vendor prices: **QUOTE REQUIRED** for every commercial option. Indicative prices for Roanuz, Sportmonks, EntitySport, Goalserve and CricketData.org appeared only in SECONDARY sources and are not used. No price is invented.

### 1. Current Cricsheet architecture (measured)

| Item | Today |
|---|---|
| Data licensing | £0 (licence position unresolved; internal only) |
| Storage | raw downloads 106 MB; canonical Parquet + derived 528 MB, including the persisted working DB of ~404 MB |
| Compute: build | full rebuild and precompute in minutes on a 4-vCPU / 15 GB container; working DB build about 36 s |
| Compute: serving | one API process; warm responses 2–12 ms; replay forward step 37–42 ms |
| API traffic | none external (Cricsheet downloads on demand via the GitHub workflow) |
| Infrastructure | one small VM-class host would serve the internal preview. Hosting price depends on provider: QUOTE REQUIRED, not invented |

### 2. Open-metadata enrichment (Wikidata, measured pilot)

| Item | Cost |
|---|---|
| Data licensing | £0 (CC0) |
| Retrieval | one GitHub Actions run of about 25 s per refresh; within free minutes for a private repo, depending on plan |
| Storage | under 1 MB of observations |
| Value | small: bowling style for 6.4% of players. Batting hand needs a licence-cleared source |

### 3. One commercial feed (stack B)

| Item | Cost |
|---|---|
| Data licensing | **QUOTE REQUIRED** (per competition, per season, consumer-display tier) |
| Infrastructure | live ingestion worker plus event log storage. About 300 deliveries per T20 and 600 per ODI at well under 1 KB per enriched event means tens of MB per season per competition |
| Compute | the Phase 5 engine applies a ball in about 21 µs and serves a forward step in about 40 ms, so one process covers several concurrent matches |
| API traffic | vendor pull or push rate limits and overage: **QUOTE REQUIRED** |

### 4. Premium tracking scenario (stack C)

| Item | Cost |
|---|---|
| Data licensing | **QUOTE REQUIRED**, plus board or ICC consent (UNKNOWN availability) |
| Storage | trajectory samples per ball are orders of magnitude larger than events. Size depends on the vendor's format: QUOTE REQUIRED |
| Compute | visual rendering is client-side; server load is dominated by ingestion and aggregation of tracking frames |
| API traffic | likely push or streaming during matches: **QUOTE REQUIRED** |
