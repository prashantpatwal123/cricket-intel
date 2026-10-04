# Similar Players (Phase 7)

**Code and data:**
- Code: `pipeline/cricintel/fan/similar.py`.
- Index: `derived/fan_similar.json`, built by `python -m cricintel.precompute` in about 15 s.
- API: `GET /api/fan/player/{id}/similar`.

**What it is:** nearest neighbours on the Cricket Fingerprint dimensions, separately for batting and bowling, and per format and gender.

**What it is not:** a quality ranking. Two players can share a profile and differ greatly in output. The page says so next to the list.

## Method

1. **Pool:** each pool (role × format × gender) uses the same SQL as the fingerprint, limited to leagues and internationals between ICC full members. Players need the fingerprint's peer minimum (T20: 500 balls faced or 480 bowled; ODI: 800 faced or 900 bowled).
2. **Shrinkage:** each rate is shrunk toward the pool mean with a pseudo-sample equal to the dimension's minimum, so small samples move less. It is then z-scored within the pool.
3. **Excluded:** concentration dimensions ("matchup concentration", "dismissal concentration") are too noisy for distance and are left out.
4. **Distance:** root-mean-square z difference over the dimensions both players have, with at least 8 shared.
5. **"Alike":** the dimensions where both players are distinctive (|z| ≥ 0.5, same side) and closest. **"Differ most":** the largest gap. Both are shown as within-pool percentiles.

## Validation (holdout)

Vectors are rebuilt from two disjoint halves of each player's matches (split by match id hash), using players with at least half the pool minimum in both halves.

- **Self-match:** start from a player's half-A vector and find where their own half-B vector ranks among all half-B vectors.
- **Neighbour stability:** the overlap of the top-5 neighbours computed on half A versus half B.

**Bar:** self-match in the top 5 at least 5× chance, and neighbour overlap at least 3× chance. A pool that fails is not shown, and the page says why.

| Pool | Players in pool | Tested | Self-match top-1 (chance) | Self-match top-5 (chance) | Top-5 lift | Top-5 neighbour overlap (chance) | Verdict |
|---|---|---|---|---|---|---|---|
| Men's T20 batting | 255 | 227 | 11.5% (0.4%) | 25.6% (2.2%) | 11.6× | 8.1% (2.2%) | **shown** |
| Women's T20 batting | 93 | 75 | 17.3% (1.3%) | 48.0% (6.7%) | 7.2× | 20.0% (6.7%) | not shown (overlap at the bar, not above it) |
| Men's ODI batting | 307 | 264 | 11.0% (0.4%) | 32.2% (1.9%) | 17.0× | 11.4% (1.9%) | **shown** |
| Women's ODI batting | 98 | 84 | 10.7% (1.2%) | 47.6% (6.0%) | 8.0× | 21.4% (6.0%) | **shown** |
| Men's T20 bowling | 306 | 267 | 8.6% (0.4%) | 22.5% (1.9%) | 12.0× | 7.7% (1.9%) | **shown** |
| Women's T20 bowling | 110 | 101 | 8.9% (1.0%) | 25.7% (5.0%) | 5.2× | 14.7% (5.0%) | not shown |
| Men's ODI bowling | 320 | 283 | 8.5% (0.4%) | 23.7% (1.8%) | 13.4× | 8.1% (1.8%) | **shown** |
| Women's ODI bowling | 102 | 84 | 6.0% (1.2%) | 32.1% (6.0%) | 5.4× | 14.3% (6.0%) | not shown |

**How to read it:** profiles are stable enough to find the same player again far above chance, but most of the time not at rank 1. That is why the page shows several similar players with their reasons rather than a single "twin". The neighbour lists themselves move between halves (8–21% overlap), so they are suggestions to explore, not facts.

## Examples (real data)

- **Bumrah** (men's T20 bowling): Senanayake, Malinga, Steyn, Mendis.
- **Zampa** (men's ODI bowling): Vandersay, Kuldeep Yadav, Chahal, Sodhi. These are all spinners. Bowling style is *not* an input (it is known for only 6% of players), so this grouping emerges from economy, wicket and phase patterns alone.
- **Rohit Sharma** (men's ODI batting): Fakhar Zaman, Dawid Malan, Evin Lewis, David Warner.
- **Mandhana** (women's ODI batting): Litchfield, Lanning, Sciver-Brunt, Devine.
