# Field-level data capability audit (Phase 6)

Generated from `pipeline/cricintel/enrich/capability.py` (`python -m cricintel.enrich.capability`), which is also what `/data` shows.
UNKNOWN means unknown: nothing is marked available on assumption.

**4 available · 6 partial · 26 unavailable** of 36 fields.

Evidence: docs/data/cricsheet-schema-observed.json (every key in all 10,247 files); coverage measured from the working DB.

**Licence note for every Cricsheet-derived field:** the match-data licence is unresolved (no licence statement found; site footer "All rights reserved"). The People Register is ODC-By 1.0. CRICINTEL therefore stays internal preview only, and every "usable now" below means usable *inside the internal preview*.

## Summary

| | Field | Coverage (measured) | Source | Usable now |
|---|---|---|---|---|
| ✕ | batting handedness | 0.0% of deliveries. Wikidata P552 is generic handedness on 29 of 31,699 cricketer items, not batting hand. | Wikidata (CC0), joined via the Cricsheet Register's ESPNcricinfo id (P2697); Wikipedia infobox (CC BY-SA, comparison only) | no |
| △ | bowling handedness | 7.2% of deliveries; 6.4% of players | Wikidata (CC0), joined via the Cricsheet Register's ESPNcricinfo id (P2697) | yes |
| △ | bowling style | 7.2% of deliveries; 6.4% of players (family known on 7.8% of deliveries) | Wikidata (CC0), joined via the Cricsheet Register's ESPNcricinfo id (P2697) | yes |
| △ | wicketkeeper identity | keeper identified in 76.9% of team-matches; keeper status known for 78.6% of catches | Cricsheet ball-by-ball (match data) (derived) | yes |
| △ | player role | 82.3% of players | Cricsheet ball-by-ball (match data) (derived) + Wikidata (CC0), joined via the Cricsheet Register's ESPNcricinfo id (P2697) | yes |
| ✓ | batting position | 100.0% of deliveries | Cricsheet ball-by-ball (match data) | yes |
| ✓ | bowling spell | 100% of deliveries | Cricsheet ball-by-ball (match data) (derived) | yes |
| ✕ | delivery speed | 0% | No source available to CRICINTEL | no |
| ✕ | release speed | 0% | No source available to CRICINTEL | no |
| ✕ | line | 0% | No source available to CRICINTEL | no |
| ✕ | length | 0% | No source available to CRICINTEL | no |
| ✕ | pitch coordinates | 0% | No source available to CRICINTEL | no |
| ✕ | bounce | 0% | No source available to CRICINTEL | no |
| ✕ | swing | 0% | No source available to CRICINTEL | no |
| ✕ | seam movement | 0% | No source available to CRICINTEL | no |
| ✕ | spin | 0% | No source available to CRICINTEL | no |
| ✕ | delivery variation | 0% | No source available to CRICINTEL | no |
| ✕ | ball trajectory | 0% | No source available to CRICINTEL | no |
| ✕ | landing point | 0% | No source available to CRICINTEL | no |
| ✕ | shot type | 0% | No source available to CRICINTEL | no |
| ✕ | shot direction | 0% | No source available to CRICINTEL | no |
| ✕ | attacking defensive shot | 0% | No source available to CRICINTEL | no |
| ✕ | control false shot | 0% | No source available to CRICINTEL | no |
| ✕ | boundary destination | 0% | No source available to CRICINTEL | no |
| ✕ | edge | 0% | No source available to CRICINTEL | no |
| ✕ | bat contact location | 0% | No source available to CRICINTEL | no |
| ✕ | foot movement | 0% | No source available to CRICINTEL | no |
| ✕ | batter position at contact | 0% | No source available to CRICINTEL | no |
| ✕ | fielder position | 0% | No source available to CRICINTEL | no |
| ✕ | field configuration | 0% | No source available to CRICINTEL | no |
| ✕ | catch position | 0% | No source available to CRICINTEL | no |
| ✕ | run out location | 0% | No source available to CRICINTEL | no |
| △ | fielder identity | named on 98.0% of caught / run-out / stumped dismissals; never for non-dismissal balls | Cricsheet ball-by-ball (match data) | yes |
| ✓ | dismissal kind | 100% of dismissals | Cricsheet ball-by-ball (match data) | yes |
| ✓ | ball outcome | 100% of 3,298,136 deliveries | Cricsheet ball-by-ball (match data) | yes |
| △ | drs review | 6,566 reviews recorded (where Cricsheet records them) | Cricsheet ball-by-ball (match data) | yes |

## Full matrix

### ✕ batting handedness

- **status**: unavailable
- **source**: Wikidata (CC0), joined via the Cricsheet Register's ESPNcricinfo id (P2697); Wikipedia infobox (CC BY-SA, comparison only)
- **source authority**: community-edited encyclopaedic
- **licence**: CC0 (Wikidata); CC BY-SA 4.0 (Wikipedia)
- **commercial use**: CC0: yes. CC BY-SA: attribution + share-alike; legal review required
- **coverage**: 0.0% of deliveries. Wikidata P552 is generic handedness on 29 of 31,699 cricketer items, not batting hand.
- **historical depth**: career-level
- **live availability**: n/a (static)
- **granularity**: player
- **confidence**: Wikidata: none usable; Wikipedia: high for pilot players, licence blocks use
- **cost**: free
- **access**: SPARQL / MediaWiki API via GitHub runner
- **redistribution**: Wikipedia: share-alike
- **usable now**: False
- **notes**: Pilot: 8/8 players have batting hand in Wikipedia infoboxes, 0/8 in Wikidata.
- **what would unlock it**: Licence review of Wikipedia-derived facts, or a licensed player feed

### △ bowling handedness

- **status**: partial
- **source**: Wikidata (CC0), joined via the Cricsheet Register's ESPNcricinfo id (P2697)
- **source authority**: community-edited
- **licence**: CC0
- **commercial use**: yes
- **coverage**: 7.2% of deliveries; 6.4% of players
- **historical depth**: career
- **live availability**: n/a
- **granularity**: player
- **confidence**: medium: Wikidata labels are coarse ('fast bowling' carries no arm)
- **cost**: free
- **access**: SPARQL via GitHub runner
- **redistribution**: none (CC0)
- **usable now**: True
- **notes**: Only where the Wikidata label states the arm (e.g. 'left-arm orthodox spin').

### △ bowling style

- **status**: partial
- **source**: Wikidata (CC0), joined via the Cricsheet Register's ESPNcricinfo id (P2697)
- **source authority**: community-edited
- **licence**: CC0
- **commercial use**: yes
- **coverage**: 7.2% of deliveries; 6.4% of players (family known on 7.8% of deliveries)
- **historical depth**: career
- **live availability**: n/a
- **granularity**: player (career style, not per delivery)
- **confidence**: medium; mapping confidence recorded per value
- **cost**: free
- **access**: SPARQL via GitHub runner
- **redistribution**: none (CC0)
- **usable now**: True
- **notes**: Pilot: 0/8 pilot players have P2545 in Wikidata; Wikipedia has 8/8 (licence review pending).
- **what would unlock it**: More CC0 values, licence-cleared Wikipedia extraction, or a licensed player feed

### △ wicketkeeper identity

- **status**: partial
- **source**: Cricsheet ball-by-ball (match data) (derived)
- **source authority**: derived from observed stumpings and career usage
- **licence**: UNRESOLVED: no licence statement found for match data; site footer 'All rights reserved'. Internal preview only.
- **commercial use**: UNKNOWN (match-data licence unresolved)
- **coverage**: keeper identified in 76.9% of team-matches; keeper status known for 78.6% of catches
- **historical depth**: all covered matches
- **live availability**: derivable from events in a replay
- **granularity**: team-match
- **confidence**: 0.90–0.97 per inference method (measured)
- **cost**: free
- **access**: download
- **redistribution**: as match data
- **usable now**: True
- **notes**: Cricsheet does not mark the keeper. DERIVED, never assumed; ambiguous cases stay 'unknown'.

### △ player role

- **status**: partial
- **source**: Cricsheet ball-by-ball (match data) (derived) + Wikidata (CC0), joined via the Cricsheet Register's ESPNcricinfo id (P2697)
- **source authority**: derived from usage
- **licence**: UNRESOLVED: no licence statement found for match data; site footer 'All rights reserved'. Internal preview only.; CC0
- **commercial use**: UNKNOWN for derived values
- **coverage**: 82.3% of players
- **historical depth**: career
- **live availability**: n/a
- **granularity**: player
- **confidence**: 0.95 (derived rule)
- **cost**: free
- **access**: download
- **redistribution**: as match data
- **usable now**: True

### ✓ batting position

- **status**: available
- **source**: Cricsheet ball-by-ball (match data)
- **source authority**: official scorers' order as published by Cricsheet
- **licence**: UNRESOLVED: no licence statement found for match data; site footer 'All rights reserved'. Internal preview only.
- **commercial use**: UNKNOWN
- **coverage**: 100.0% of deliveries
- **historical depth**: all covered matches
- **live availability**: yes (order of arrival)
- **granularity**: innings
- **confidence**: high (observed order)
- **cost**: free
- **access**: download
- **redistribution**: as match data
- **usable now**: True
- **notes**: DERIVED from the order batters appear.

### ✓ bowling spell

- **status**: available
- **source**: Cricsheet ball-by-ball (match data) (derived)
- **source authority**: derived
- **licence**: UNRESOLVED: no licence statement found for match data; site footer 'All rights reserved'. Internal preview only.
- **commercial use**: UNKNOWN
- **coverage**: 100% of deliveries
- **historical depth**: all covered matches
- **live availability**: yes
- **granularity**: over
- **confidence**: rule-based (overs with at most one over between them)
- **cost**: free
- **access**: download
- **redistribution**: as match data
- **usable now**: True
- **notes**: Ends are not recorded.

### ✕ delivery speed

- **status**: unavailable
- **source**: No source available to CRICINTEL
- **source authority**: —
- **licence**: —
- **commercial use**: —
- **coverage**: 0%
- **historical depth**: —
- **live availability**: —
- **granularity**: —
- **confidence**: —
- **cost**: QUOTE REQUIRED (commercial)
- **access**: —
- **redistribution**: —
- **usable now**: False
- **notes**: Not a key in any of the 10,247 Cricsheet files (observed schema).
- **what would unlock it**: Licensed ball-tracking-derived feed

### ✕ release speed

- **status**: unavailable
- **source**: No source available to CRICINTEL
- **source authority**: —
- **licence**: —
- **commercial use**: —
- **coverage**: 0%
- **historical depth**: —
- **live availability**: —
- **granularity**: —
- **confidence**: —
- **cost**: QUOTE REQUIRED (commercial)
- **access**: —
- **redistribution**: —
- **usable now**: False
- **notes**: Not a key in any of the 10,247 Cricsheet files (observed schema).
- **what would unlock it**: Licensed ball-tracking feed

### ✕ line

- **status**: unavailable
- **source**: No source available to CRICINTEL
- **source authority**: —
- **licence**: —
- **commercial use**: —
- **coverage**: 0%
- **historical depth**: —
- **live availability**: —
- **granularity**: —
- **confidence**: —
- **cost**: QUOTE REQUIRED (commercial)
- **access**: —
- **redistribution**: —
- **usable now**: False
- **notes**: Not a key in any of the 10,247 Cricsheet files (observed schema).
- **what would unlock it**: Licensed feed with coded or tracked line

### ✕ length

- **status**: unavailable
- **source**: No source available to CRICINTEL
- **source authority**: —
- **licence**: —
- **commercial use**: —
- **coverage**: 0%
- **historical depth**: —
- **live availability**: —
- **granularity**: —
- **confidence**: —
- **cost**: QUOTE REQUIRED (commercial)
- **access**: —
- **redistribution**: —
- **usable now**: False
- **notes**: Not a key in any of the 10,247 Cricsheet files (observed schema).
- **what would unlock it**: Licensed feed with coded or tracked length

### ✕ pitch coordinates

- **status**: unavailable
- **source**: No source available to CRICINTEL
- **source authority**: —
- **licence**: —
- **commercial use**: —
- **coverage**: 0%
- **historical depth**: —
- **live availability**: —
- **granularity**: —
- **confidence**: —
- **cost**: QUOTE REQUIRED (commercial)
- **access**: —
- **redistribution**: —
- **usable now**: False
- **notes**: Not a key in any of the 10,247 Cricsheet files (observed schema).
- **what would unlock it**: Tracking-derived feed

### ✕ bounce

- **status**: unavailable
- **source**: No source available to CRICINTEL
- **source authority**: —
- **licence**: —
- **commercial use**: —
- **coverage**: 0%
- **historical depth**: —
- **live availability**: —
- **granularity**: —
- **confidence**: —
- **cost**: QUOTE REQUIRED (commercial)
- **access**: —
- **redistribution**: —
- **usable now**: False
- **notes**: Not a key in any of the 10,247 Cricsheet files (observed schema).
- **what would unlock it**: Tracking

### ✕ swing

- **status**: unavailable
- **source**: No source available to CRICINTEL
- **source authority**: —
- **licence**: —
- **commercial use**: —
- **coverage**: 0%
- **historical depth**: —
- **live availability**: —
- **granularity**: —
- **confidence**: —
- **cost**: QUOTE REQUIRED (commercial)
- **access**: —
- **redistribution**: —
- **usable now**: False
- **notes**: Not a key in any of the 10,247 Cricsheet files (observed schema).
- **what would unlock it**: Tracking

### ✕ seam movement

- **status**: unavailable
- **source**: No source available to CRICINTEL
- **source authority**: —
- **licence**: —
- **commercial use**: —
- **coverage**: 0%
- **historical depth**: —
- **live availability**: —
- **granularity**: —
- **confidence**: —
- **cost**: QUOTE REQUIRED (commercial)
- **access**: —
- **redistribution**: —
- **usable now**: False
- **notes**: Not a key in any of the 10,247 Cricsheet files (observed schema).
- **what would unlock it**: Tracking

### ✕ spin

- **status**: unavailable
- **source**: No source available to CRICINTEL
- **source authority**: —
- **licence**: —
- **commercial use**: —
- **coverage**: 0%
- **historical depth**: —
- **live availability**: —
- **granularity**: —
- **confidence**: —
- **cost**: QUOTE REQUIRED (commercial)
- **access**: —
- **redistribution**: —
- **usable now**: False
- **notes**: Not a key in any of the 10,247 Cricsheet files (observed schema).
- **what would unlock it**: Tracking (revolutions/deviation)

### ✕ delivery variation

- **status**: unavailable
- **source**: No source available to CRICINTEL
- **source authority**: —
- **licence**: —
- **commercial use**: —
- **coverage**: 0%
- **historical depth**: —
- **live availability**: —
- **granularity**: —
- **confidence**: —
- **cost**: QUOTE REQUIRED (commercial)
- **access**: —
- **redistribution**: —
- **usable now**: False
- **notes**: Not a key in any of the 10,247 Cricsheet files (observed schema).
- **what would unlock it**: Coded feed or tracking

### ✕ ball trajectory

- **status**: unavailable
- **source**: No source available to CRICINTEL
- **source authority**: —
- **licence**: —
- **commercial use**: —
- **coverage**: 0%
- **historical depth**: —
- **live availability**: —
- **granularity**: —
- **confidence**: —
- **cost**: QUOTE REQUIRED (commercial)
- **access**: —
- **redistribution**: —
- **usable now**: False
- **notes**: Not a key in any of the 10,247 Cricsheet files (observed schema).
- **what would unlock it**: Multi-camera tracking (e.g. Hawk-Eye-class)

### ✕ landing point

- **status**: unavailable
- **source**: No source available to CRICINTEL
- **source authority**: —
- **licence**: —
- **commercial use**: —
- **coverage**: 0%
- **historical depth**: —
- **live availability**: —
- **granularity**: —
- **confidence**: —
- **cost**: QUOTE REQUIRED (commercial)
- **access**: —
- **redistribution**: —
- **usable now**: False
- **notes**: Not a key in any of the 10,247 Cricsheet files (observed schema).
- **what would unlock it**: Tracking

### ✕ shot type

- **status**: unavailable
- **source**: No source available to CRICINTEL
- **source authority**: —
- **licence**: —
- **commercial use**: —
- **coverage**: 0%
- **historical depth**: —
- **live availability**: —
- **granularity**: —
- **confidence**: —
- **cost**: QUOTE REQUIRED (commercial)
- **access**: —
- **redistribution**: —
- **usable now**: False
- **notes**: Not a key in any of the 10,247 Cricsheet files (observed schema).
- **what would unlock it**: Licensed coded feed (shot labels)

### ✕ shot direction

- **status**: unavailable
- **source**: No source available to CRICINTEL
- **source authority**: —
- **licence**: —
- **commercial use**: —
- **coverage**: 0%
- **historical depth**: —
- **live availability**: —
- **granularity**: —
- **confidence**: —
- **cost**: QUOTE REQUIRED (commercial)
- **access**: —
- **redistribution**: —
- **usable now**: False
- **notes**: Not a key in any of the 10,247 Cricsheet files (observed schema).
- **what would unlock it**: Licensed coded feed (wagon-wheel angle)

### ✕ attacking defensive shot

- **status**: unavailable
- **source**: No source available to CRICINTEL
- **source authority**: —
- **licence**: —
- **commercial use**: —
- **coverage**: 0%
- **historical depth**: —
- **live availability**: —
- **granularity**: —
- **confidence**: —
- **cost**: QUOTE REQUIRED (commercial)
- **access**: —
- **redistribution**: —
- **usable now**: False
- **notes**: Not a key in any of the 10,247 Cricsheet files (observed schema).
- **what would unlock it**: Licensed coded feed

### ✕ control false shot

- **status**: unavailable
- **source**: No source available to CRICINTEL
- **source authority**: —
- **licence**: —
- **commercial use**: —
- **coverage**: 0%
- **historical depth**: —
- **live availability**: —
- **granularity**: —
- **confidence**: —
- **cost**: QUOTE REQUIRED (commercial)
- **access**: —
- **redistribution**: —
- **usable now**: False
- **notes**: Not a key in any of the 10,247 Cricsheet files (observed schema).
- **what would unlock it**: Licensed coded feed

### ✕ boundary destination

- **status**: unavailable
- **source**: No source available to CRICINTEL
- **source authority**: —
- **licence**: —
- **commercial use**: —
- **coverage**: 0%
- **historical depth**: —
- **live availability**: —
- **granularity**: —
- **confidence**: —
- **cost**: QUOTE REQUIRED (commercial)
- **access**: —
- **redistribution**: —
- **usable now**: False
- **notes**: Not a key in any of the 10,247 Cricsheet files (observed schema).
- **what would unlock it**: Coded feed with landing zone

### ✕ edge

- **status**: unavailable
- **source**: No source available to CRICINTEL
- **source authority**: —
- **licence**: —
- **commercial use**: —
- **coverage**: 0%
- **historical depth**: —
- **live availability**: —
- **granularity**: —
- **confidence**: —
- **cost**: QUOTE REQUIRED (commercial)
- **access**: —
- **redistribution**: —
- **usable now**: False
- **notes**: Not a key in any of the 10,247 Cricsheet files (observed schema).
- **what would unlock it**: Licensed feed with edge flags (validated); commentary text is not ground truth

### ✕ bat contact location

- **status**: unavailable
- **source**: No source available to CRICINTEL
- **source authority**: —
- **licence**: —
- **commercial use**: —
- **coverage**: 0%
- **historical depth**: —
- **live availability**: —
- **granularity**: —
- **confidence**: —
- **cost**: QUOTE REQUIRED (commercial)
- **access**: —
- **redistribution**: —
- **usable now**: False
- **notes**: Not a key in any of the 10,247 Cricsheet files (observed schema).
- **what would unlock it**: Tracking or sensor bat data

### ✕ foot movement

- **status**: unavailable
- **source**: No source available to CRICINTEL
- **source authority**: —
- **licence**: —
- **commercial use**: —
- **coverage**: 0%
- **historical depth**: —
- **live availability**: —
- **granularity**: —
- **confidence**: —
- **cost**: QUOTE REQUIRED (commercial)
- **access**: —
- **redistribution**: —
- **usable now**: False
- **notes**: Not a key in any of the 10,247 Cricsheet files (observed schema).
- **what would unlock it**: Tracking or coded video

### ✕ batter position at contact

- **status**: unavailable
- **source**: No source available to CRICINTEL
- **source authority**: —
- **licence**: —
- **commercial use**: —
- **coverage**: 0%
- **historical depth**: —
- **live availability**: —
- **granularity**: —
- **confidence**: —
- **cost**: QUOTE REQUIRED (commercial)
- **access**: —
- **redistribution**: —
- **usable now**: False
- **notes**: Not a key in any of the 10,247 Cricsheet files (observed schema).
- **what would unlock it**: Tracking

### ✕ fielder position

- **status**: unavailable
- **source**: No source available to CRICINTEL
- **source authority**: —
- **licence**: —
- **commercial use**: —
- **coverage**: 0%
- **historical depth**: —
- **live availability**: —
- **granularity**: —
- **confidence**: —
- **cost**: QUOTE REQUIRED (commercial)
- **access**: —
- **redistribution**: —
- **usable now**: False
- **notes**: Not a key in any of the 10,247 Cricsheet files (observed schema).
- **what would unlock it**: Coded feed or tracking

### ✕ field configuration

- **status**: unavailable
- **source**: No source available to CRICINTEL
- **source authority**: —
- **licence**: —
- **commercial use**: —
- **coverage**: 0%
- **historical depth**: —
- **live availability**: —
- **granularity**: —
- **confidence**: —
- **cost**: QUOTE REQUIRED (commercial)
- **access**: —
- **redistribution**: —
- **usable now**: False
- **notes**: Not a key in any of the 10,247 Cricsheet files (observed schema).
- **what would unlock it**: Coded feed (field settings)

### ✕ catch position

- **status**: unavailable
- **source**: No source available to CRICINTEL
- **source authority**: —
- **licence**: —
- **commercial use**: —
- **coverage**: 0%
- **historical depth**: —
- **live availability**: —
- **granularity**: —
- **confidence**: —
- **cost**: QUOTE REQUIRED (commercial)
- **access**: —
- **redistribution**: —
- **usable now**: False
- **notes**: Not a key in any of the 10,247 Cricsheet files (observed schema).
- **what would unlock it**: Coded feed or tracking

### ✕ run out location

- **status**: unavailable
- **source**: No source available to CRICINTEL
- **source authority**: —
- **licence**: —
- **commercial use**: —
- **coverage**: 0%
- **historical depth**: —
- **live availability**: —
- **granularity**: —
- **confidence**: —
- **cost**: QUOTE REQUIRED (commercial)
- **access**: —
- **redistribution**: —
- **usable now**: False
- **notes**: Not a key in any of the 10,247 Cricsheet files (observed schema).
- **what would unlock it**: Coded feed (end) or tracking

### △ fielder identity

- **status**: partial
- **source**: Cricsheet ball-by-ball (match data)
- **source authority**: official scorecards via Cricsheet
- **licence**: UNRESOLVED: no licence statement found for match data; site footer 'All rights reserved'. Internal preview only.
- **commercial use**: UNKNOWN
- **coverage**: named on 98.0% of caught / run-out / stumped dismissals; never for non-dismissal balls
- **historical depth**: all covered matches
- **live availability**: yes (with the wicket)
- **granularity**: dismissal
- **confidence**: high (observed); substitutes flagged
- **cost**: free
- **access**: download
- **redistribution**: as match data
- **usable now**: True
- **notes**: Who caught it, never where.

### ✓ dismissal kind

- **status**: available
- **source**: Cricsheet ball-by-ball (match data)
- **source authority**: official scorers
- **licence**: UNRESOLVED: no licence statement found for match data; site footer 'All rights reserved'. Internal preview only.
- **commercial use**: UNKNOWN
- **coverage**: 100% of dismissals
- **historical depth**: all covered matches
- **live availability**: yes
- **granularity**: dismissal
- **confidence**: high
- **cost**: free
- **access**: download
- **redistribution**: as match data
- **usable now**: True

### ✓ ball outcome

- **status**: available
- **source**: Cricsheet ball-by-ball (match data)
- **source authority**: official scorers
- **licence**: UNRESOLVED: no licence statement found for match data; site footer 'All rights reserved'. Internal preview only.
- **commercial use**: UNKNOWN
- **coverage**: 100% of 3,298,136 deliveries
- **historical depth**: all covered matches
- **live availability**: yes
- **granularity**: delivery
- **confidence**: high
- **cost**: free
- **access**: download
- **redistribution**: as match data
- **usable now**: True
- **notes**: Runs, extras by type, boundary flag (four/six), wickets.

### △ drs review

- **status**: partial
- **source**: Cricsheet ball-by-ball (match data)
- **source authority**: official
- **licence**: UNRESOLVED: no licence statement found for match data; site footer 'All rights reserved'. Internal preview only.
- **commercial use**: UNKNOWN
- **coverage**: 6,566 reviews recorded (where Cricsheet records them)
- **historical depth**: recent internationals mainly
- **live availability**: yes
- **granularity**: delivery
- **confidence**: high where present
- **cost**: free
- **access**: download
- **redistribution**: as match data
- **usable now**: True
- **notes**: Who reviewed and the decision; not ball-tracking output.

## Measured values

```json
{
 "deliveries": 3298136,
 "fam": 7.8,
 "sty": 7.2,
 "arm": 7.2,
 "hand": 0.0,
 "players_bowling_style": 6.4,
 "players_bowling_arm": 6.4,
 "players_batting_hand": 0.0,
 "players_role": 82.3,
 "players_wicketkeeper": 7.2,
 "players": 8469,
 "keeper_team_matches": 76.9,
 "caught_keeper_status_known": 78.6,
 "fielder_named": 98.0,
 "batting_position": 100.0,
 "reviews": 6566
}
```
