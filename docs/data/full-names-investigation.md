# Full player names: what we hold, what's missing, what would fix it (Phase 8)

**Constraint:** no new or questionable source was added in Phase 8.

## What we hold

The Cricsheet people register gives each player one identifier and the scorecard names used in each match (aliases). CRICINTEL already shows the **fullest alias** the register holds (e.g. "Virat Kohli" rather than "V Kohli").

| Measure (covered players, resolved) | Count |
|---|---|
| Players | 8,469 |
| Display name is initials + surname (e.g. "S Mandhana", "KA Pollard") | 4,806 (57%) |

For these 4,806, Cricsheet provides **only** the initials form, so we keep it rather than guess. Some are also the conventional public name ("MS Dhoni", "KL Rahul").

## Consistency fixes made in Phase 8 (same source, no new data)

| Where | Before | After |
|---|---|---|
| Match header, player of the match | raw scorecard string ("V Kohli") | register display name via the match's name → person map ("Virat Kohli") |
| Play (What happens next?) batter / non-striker / bowler | raw scorecard names ("LMM Tahuhu") | register display names (`names(db)`) |
| Ask, search, player, battle, partnership | already register display names | unchanged |

Rule: **every** displayed player name goes through the register's person ID; raw scorecard strings are never shown as a name.

## What source would be needed

| Option | What it gives | Status |
|---|---|---|
| Wikidata labels (CC0) via the register's Cricinfo ID → Wikidata property P2697 | full names for most international players | needs a new field fetch and an approval of the join; **not done** |
| A licensed player-profile feed (e.g. the provider that will supply live data) | full names, dates of birth, roles | commercial; tied to the live-data decision |
| Manual curation | top few hundred names | not scalable; error-prone; not recommended |

Recommendation: decide alongside the Cricsheet licence and the live-data provider; until then, initials stay.
