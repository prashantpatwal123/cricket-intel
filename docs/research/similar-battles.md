# Similar battles — method and validation

`analytics/libraries.py: similar_battles, _sim_space, validate_similarity`. Status: **DERIVED**, validated below.

## Definition

A battle (batter v bowler, ≥ 60 legal balls for similarity) is described by what happened *relative to both players'
usual numbers*, plus where it was played. Raw totals are not used, so famous pairs do not just match other famous pairs.

| Feature | Meaning |
|---|---|
| log SR ratio v batter usual | Shrunk toward 1 (K = 60 balls) |
| log SR ratio v bowler conceded | Shrunk, same K |
| out-rate ratio | Dismissals per ball ÷ batter's usual rate, shrunk |
| log balls | Size of the evidence |
| powerplay share, death share | Phase mix of the balls |
| T20 share | Format mix |

Features are standardised within gender and compared by weighted Euclidean distance. Results are restricted to the
same gender. Each result states its closest-matching features ("both scored ~20% below the batter's usual rate…").

## Validation: split-half self-retrieval

Each battle with ≥ 160 balls is split into two halves by alternating meetings in date order (both halves ≥ 40 balls). Half A's features are used to rank
every half-B battle by distance. If the features capture something stable about the matchup, the battle's own other
half should rank near the top. Chance is a median rank of 50%.

| Pool | Battles | Median rank of own half (all features) | Outcome-only features | Own half in top 10% |
|---|---|---|---|---|
| Men | 317 | **13.3%** | 29.4% | 43.8% |
| Women | 108 | **17.8%** | 35.5% | 36.1% |

The full feature set is far better than chance and better than the three outcome features alone (unweighted), so context (phase and format
mix, sample size) carries real signal. It is not a claim that similar battles *will* play out the same way.

## Limits

- Below 60 balls the page says "Similar battles need at least 60 balls in this battle" instead of guessing.
- No pace/spin or style feature: bowling-style metadata is too incomplete (see `docs/data/known-limitations.md`).
- Covered data only.

Reproduce: `validate_similarity(db, 'male' | 'female')` (deterministic; numbers above recomputed on the current build).
