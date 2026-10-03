# Game scoring: analysis and decision

**Decision (v0): "capped rarity" for single-pick play, plus a separate proper-scoring "confidence mode" for Cricket IQ.**

```
correct pick:  points = round(10 × min(4, √(p_mode / p_pick)))      wrong pick: 0
```
- The pre-ball model's most likely outcome is worth **10**. Rarer outcomes earn more, *sub-linearly*, capped at **40**.
- The points available for each option are **shown before the user picks**, so there is no hidden maths.
- Probabilities come from the MODELLED baseline (`baseline-cohort/0.1`), trained only on matches before the moment's match.
- Confidence mode (later, for Cricket IQ): the user spreads 100% across outcomes and is scored with a proper rule (Brier, 0–100). This is the right tool for measuring *calibration*. Single picks can't measure calibration.

## Why not the others

| Criterion | Inverse 10/p | Log 10·log₂(1/p) | Flat (one-hot Brier) | **Capped rarity** |
|---|---|---|---|---|
| Rewards genuine insight (informed fan vs best naive strategy) | +90%, but drowned by luck | +45% | +24% | **+40%** |
| Resists jackpot guessing (EV of "always pick the rarest") | ❌ ties with skill (≈10) | ✅ 0.4 | ✅ 0.05 | ✅ 0.21 |
| Bounded single-pick swing | ❌ max 18,096 | ⚠️ max ~108 | ✅ 10 | ✅ 40 |
| Luck in a 20-pick session (CV, informed fan) | ❌ 0.76 | ✅ 0.27 | ✅ 0.24 | ✅ 0.27 |
| Rarity reward | ✅ extreme | ✅ strong | ❌ none | ✅ moderate (×4 max) |
| Understandable on a phone | ⚠️ odds-like (sportsbook feel) | ❌ logarithms | ✅ | ✅ "10 · 14 · 20 · 40" |

Key finding: with a calibrated model, **inverse probability gives every naive strategy the same expected score (~10)**, so leaderboards would be decided by who landed a 1-in-1,800 jackpot. It also looks like betting odds, which we explicitly avoid. Log scoring is excellent statistically but hard to explain. Capped rarity keeps most of log scoring's skill separation, stays explainable, and bounds variance.

Caveats: the "informed fan" is a crude stand-in for skill (knows the outcome 15% of the time, else picks the favourite). The analysis runs on synthetic data and must be re-run on real Cricsheet data before launch (`python -m cricintel.game.whn --report`). Leaderboards should rank over a **fixed number of moments** (e.g. the daily 5) so volume can't substitute for skill.

## Full simulation output

_Simulated on 70,553 held-out deliveries (SYNTHETIC dataset), model baseline-cohort/0.1._

### inverse 10/p

| Strategy | Mean pts/pick | Hit rate | Max single pick | Share of pts from top 5% picks | 20-pick session CV |
|---|---|---|---|---|---|
| model favourite (argmax) | 10.02 | 38.5% | 30.4 | 14% | 0.29 |
| jackpot hunter (rarest) | 9.99 | 0.5% | 18096.4 | 100% | 3.5 |
| always WICKET | 9.95 | 5.3% | 628.3 | 98% | 1.02 |
| always SIX | 10.02 | 3.9% | 2004.1 | 100% | 1.37 |
| random ~ model | 9.98 | 28.2% | 962.3 | 37% | 0.49 |
| uniform random | 10.32 | 14.3% | 2747.7 | 75% | 1.44 |
| informed fan (knows 15% of outcomes) | 19.03 | 47.6% | 2747.7 | 41% | 0.76 |

### log 10·log2(1/p)

| Strategy | Mean pts/pick | Hit rate | Max single pick | Share of pts from top 5% picks | 20-pick session CV |
|---|---|---|---|---|---|
| model favourite (argmax) | 5.28 | 38.5% | 16.0 | 14% | 0.29 |
| jackpot hunter (rarest) | 0.4 | 0.5% | 108.2 | 100% | 3.11 |
| always WICKET | 2.18 | 5.3% | 59.7 | 96% | 0.99 |
| always SIX | 1.76 | 3.9% | 76.5 | 100% | 1.16 |
| random ~ model | 4.55 | 28.0% | 76.8 | 28% | 0.39 |
| uniform random | 3.07 | 14.5% | 79.9 | 55% | 0.63 |
| informed fan (knows 15% of outcomes) | 7.66 | 47.7% | 87.9 | 22% | 0.27 |

### flat (one-hot Brier)

| Strategy | Mean pts/pick | Hit rate | Max single pick | Share of pts from top 5% picks | 20-pick session CV |
|---|---|---|---|---|---|
| model favourite (argmax) | 3.85 | 38.5% | 10.0 | 13% | 0.3 |
| jackpot hunter (rarest) | 0.05 | 0.5% | 10.0 | 100% | 3.11 |
| always WICKET | 0.53 | 5.3% | 10.0 | 95% | 1.02 |
| always SIX | 0.39 | 3.9% | 10.0 | 100% | 1.18 |
| random ~ model | 2.84 | 28.4% | 10.0 | 18% | 0.36 |
| uniform random | 1.43 | 14.3% | 10.0 | 35% | 0.56 |
| informed fan (knows 15% of outcomes) | 4.79 | 47.9% | 10.0 | 10% | 0.24 |

### capped rarity √, ×4 cap

| Strategy | Mean pts/pick | Hit rate | Max single pick | Share of pts from top 5% picks | 20-pick session CV |
|---|---|---|---|---|---|
| model favourite (argmax) | 3.85 | 38.5% | 10 | 13% | 0.3 |
| jackpot hunter (rarest) | 0.21 | 0.5% | 40 | 100% | 3.11 |
| always WICKET | 1.38 | 5.3% | 40 | 97% | 0.98 |
| always SIX | 1.11 | 3.9% | 40 | 100% | 1.16 |
| random ~ model | 3.12 | 28.0% | 40 | 26% | 0.39 |
| uniform random | 1.93 | 14.1% | 40 | 52% | 0.62 |
| informed fan (knows 15% of outcomes) | 5.39 | 47.9% | 40 | 20% | 0.27 |

