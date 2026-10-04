# Pre-ball win probability: research gate

Status: **research only. Nothing ships.** No win probability may appear in the product, the API or the web app until the owner explicitly approves it, and approval also depends on the follow-up work listed in section 7.

- Script: `pipeline/cricintel/research/winprob.py`, run with `python -m cricintel.research.winprob --dataset cricsheet`. The run is deterministic: seed 20261004, 200 match-level bootstrap resamples. Pure Python plus DuckDB SQL, with no numpy, scipy or sklearn.
- Metrics: `docs/models/win-probability-research.json`. The script writes this file, and every number below is copied from it.
- Runtime: about 5.3 minutes on 4 CPUs (`timing_s.total_s` = 319.6 s in the JSON). Two runs produced identical metrics.

**Short answer.** For **T20 men and T20 women**, a transparent pre-ball model passes every pre-registered calibration rule on 2024–2026 out-of-time data. Both cohorts are **ACCEPT-FOR-RESEARCH**. However, the pass is driven by international matches, and several problems outside the rules would still block display (sections 6.6 and 7). **ODI men and ODI women are REJECTED**. Both are clearly over-confident on the test set (calibration slope 0.75 and 0.84), have too few test matches to estimate calibration tightly, and fail the per-year stability rule.

---

## 1. Question and target

The question is whether the dataset supports a defensible estimate of P(batting team wins | state *before* this delivery) in T20 and ODI cricket, for men and women, in both innings.

The label is 1 if the batting team won the match and 0 if it lost. **Ties count as 0.5.** That includes ties later settled by a super over, because the super over is not part of the regulation state and is ignored. The JSON's `population.ties_labelled_half` shows 26 ties in the test set (25 decided by super over, 1 plain).

## 2. Population (`population` in the JSON)

There are 10,247 T20 and ODI matches. Each match gets exactly one status, applied in the order below.

| Status | Matches |
|---|---|
| eligible | **9,019** |
| D/L (`method = 'D/L'`), excluded from training **and** evaluation | **480** |
| no result | 243 |
| non-standard or unequal innings limit (reduced-overs matches without D/L; any innings ≠ 120 / 300 balls) | 264 |
| inconsistent 2nd innings (e.g. chase "lost" while not all out and inside the limit, typically retired or absent batters) | 125 |
| more legal balls than the limit (scoring anomalies) | 59 |
| incomplete 1st innings | 50 |
| other method ("Awarded") | 4 |
| target ≠ 1st-innings total + 1 | 3 |

`limit_uncertain` matches would be excluded too. In practice every one of them was already caught by an earlier rule.

D/L exclusions in the test set: 52 T20 men, 28 T20 women, 27 ODI men, 18 ODI women.

**Eligible matches by chronological split.** Train is start date before 2023-01-01, validation is 2023, test is from 2024-01-01.

| Cohort | Train | Validation (2023) | Test (2024–26) |
|---|---|---|---|
| T20 men | 2,354 | 391 | 1,632 |
| T20 women | 690 | 243 | 1,087 |
| ODI men | 1,739 | 165 | 213 |
| ODI women | 304 | **37** | 164 |

**Legal deliveries:**
- 1,794,035 in train. All of them feed the tables; 599,611 feed the logistic fits, which use every 3rd ball (`legal_balls_before % 3 == 0`).
- 243,240 in validation.
- **795,587 in test.** Every legal ball of every test match is scored.

Both innings are used. Super-over deliveries are not in `balls`.

## 3. Leakage control

**Features** are pre-ball state only:
- score before the ball, wickets before, legal balls before
- balls left (limit − legal balls before)
- target and runs required (innings 2)
- format, gender and innings, used as the stratification for a separate model per format × gender × innings

There is **no team, player, venue, toss, competition or era feature**, and nothing that is only known later.

**Training-only lookup tables** (`training_tables`):
- A par score by ball.
- A remaining-runs "resource" table: mean and SD of runs still to come by (balls left, wickets lost), estimated from completed 1st innings, smoothed with an adaptive window and made monotone in both wickets and balls.
- The mean and SD of 1st-innings totals. Training values: T20 men 156.4 ± 35.1; T20 women 119.6 ± 41.2; ODI men 249.1 ± 66.2; ODI women 217.7 ± 64.3.

**Use of each split:**
- Validation (2023) is used only to choose the smoothing strength (Candidate A), the L2 penalty (Candidate B), the Platt recalibration, and which variant is selected.
- Test (2024 onward) is touched once.

Caveat: excluding D/L, reduced-overs and "inconsistent" matches is partly outcome-conditioned, because rain and retirements are only known later. A live product could not apply these filters in advance (see section 7, item 3).

## 4. Models

| Id | Description |
|---|---|
| B0 | Constant: training share of wins for the batting side, per format × gender × innings, weighted per match. |
| B1 | Innings 2 only. Logistic regression on required run rate (capped at 36) and wickets lost (own Newton/IRLS). |
| A | Empirical state table with empirical-Bayes shrinkage. Innings 2 cells are balls-left × wickets × runs required; innings 1 cells are balls-left × wickets × (runs − par). Cells shrink through four coarser parents to the cohort root using `p = (Σy + k·p_parent)/(n + k)`. k is chosen on validation (picked 300 for innings 1 and 100 for innings 2 everywhere). |
| B | Own L2 IRLS logistic regression. Innings 1 features: z = (score + E[remaining runs] − mean total)/√(SD_rem² + SD_total²), z × fraction bowled, fraction bowled, wickets/10. Innings 2 features: z = (E[remaining] − runs required)/SD_rem, z × fraction, log((R+1)/(E+1)), fraction, wickets/10. |
| +Platt | Logistic recalibration of logit(p), fitted on the 2023 validation year only. |
| **WP** | The **selected** model: the lowest validation log loss among A, A+Platt, B and B+Platt per format × gender × innings. The Platt variants are scored by 2-fold match-split cross-fitting inside 2023. B won in 7 of 8 groups. B+Platt won ODI women innings 2, a choice made on only 37 validation matches. |

## 5. Pre-registered acceptance criteria

These rules are fixed in `ACCEPTANCE` in the script and were written before any test metric was computed. They apply to the selected model WP, per format × gender cohort, with both innings pooled unless stated otherwise.

1. At least **150 test matches**.
2. **Calibration slope** (logistic recalibration of logit p) in **[0.9, 1.1]**.
3. **|Calibration-in-the-large|**, meaning |mean(y) − mean(p)|, **≤ 0.02**.
4. **ECE ≤ 0.03** (10 equal-width bins).
5. **ECE ≤ 0.04 in each innings separately.**
6. For every probability band (0–10, 10–30, 30–70, 70–90, 90–100 %) with ≥ 30 test matches, at least one of these holds: |obs − pred| ≤ 0.05, or the 95% match-bootstrap CI of (obs − pred) contains 0.
7. **Brier skill vs B1 on innings-2 balls > 0.**
8. **ECE ≤ 0.04 in every test year** that has ≥ 50 matches in the cohort.

A cohort that fails any rule, or lacks data, is **REJECTED** for display.

## 6. Results (test, 2024-01-01 onward)

All CIs are 95% percentile intervals from 200 bootstrap resamples **of matches**. Consecutive balls in a match are strongly correlated, so the effective sample size is the number of matches, not the number of deliveries.

### 6.1 Headline, selected model (WP)

| Cohort | Matches | Deliveries | Brier [CI] | Log loss | Skill vs B0 | Skill vs B1 (inn 2) [CI] | Slope [CI] | CITL | ECE [CI] |
|---|---|---|---|---|---|---|---|---|---|
| T20 men | 1,632 | 359,899 | 0.1627 [0.1560, 0.1684] | 0.4874 | 0.345 | 0.110 [0.084, 0.139] | 0.992 [0.933, 1.084] | +0.002 | 0.013 [0.009, 0.021] |
| T20 women | 1,087 | 236,941 | 0.1605 [0.1510, 0.1677] | 0.4799 | 0.353 | 0.120 [0.091, 0.151] | 0.996 [0.914, 1.113] | +0.001 | 0.013 [0.010, 0.025] |
| ODI men | 213 | 113,045 | 0.1855 [0.1644, 0.2095] | 0.5524 | 0.242 | 0.191 [0.132, 0.257] | **0.749** [0.579, 0.978] | +0.000 | **0.044** [0.019, 0.084] |
| ODI women | 164 | 85,702 | 0.1702 [0.1466, 0.1922] | 0.5038 | 0.331 | 0.102 [0.017, 0.187] | **0.842** [0.682, 1.127] | **+0.022** | **0.033** [0.026, 0.067] |
| All | 3,096 | 795,587 | 0.1661 | 0.4962 | 0.331 | 0.127 | 0.934 | +0.004 | 0.011 |

By innings, all cohorts pooled:
- **Innings 1:** WP Brier 0.2077 vs B0 0.2481, skill 0.163; slope 0.860; ECE 0.020.
- **Innings 2:** WP Brier 0.1179 vs B1 0.1351 vs B0 0.2487; slope 0.994; ECE 0.010.

Innings 1 is inherently close to a coin flip early on, so most of the skill comes from the chase.

### 6.2 All models (Brier / calibration slope / ECE)

| Cohort | B0 | B1 (inn 2 only) | A | A+Platt | B | B+Platt |
|---|---|---|---|---|---|---|
| T20 men | 0.2484 / – / 0.035 | 0.1282 / 1.104 / 0.035 | 0.1654 / 1.037 / 0.012 | 0.1656 / 1.046 / 0.013 | **0.1627** / 0.992 / 0.013 | 0.1629 / 1.037 / 0.012 |
| T20 women | 0.2479 / – / 0.050 | 0.1267 / 0.843 / 0.040 | 0.1637 / 0.940 / 0.019 | 0.1656 / 1.104 / 0.024 | **0.1605** / 0.996 / 0.013 | 0.1624 / 1.039 / 0.020 |
| ODI men | 0.2446 / – / 0.009 | 0.1738 / 0.751 / 0.041 | 0.1893 / 0.698 / 0.037 | 0.1898 / 0.721 / 0.037 | **0.1855** / 0.749 / 0.044 | 0.1859 / 0.775 / 0.043 |
| ODI women | 0.2545 / – / 0.069 | 0.1357 / 0.937 / 0.040 | 0.1804 / 0.763 / 0.042 | 0.1853 / 0.748 / 0.051 | **0.1685** / 0.944 / 0.026 | 0.1734 / 0.772 / 0.049 |

Reading the table:
- B0's slope is meaningless for a constant predictor, so it is shown as –.
- The B1 Brier covers innings 2 only. Compare it with the "skill vs B1" column in 6.1, which compares like with like.
- **Candidate B beats Candidate A everywhere.**
- **Platt recalibration on 2023 never improved test Brier.** One year of validation, about 37–391 matches, is too small and too year-specific to recalibrate reliably.
- In ODI women, raw B would have been better than the selected B+Platt (slope 0.944, ECE 0.026). Even so, raw B would still fail the per-year rule: ECE 0.052 in 2024 (55 matches) and 0.064 in 2025 (73 matches), from `test_by_year`. Its per-innings slopes also diverge (innings 1: 0.78, innings 2: 1.14), and B's innings-2 L2 penalty was chosen on 37 validation matches. Switching to raw B after seeing test results would also be post-hoc selection, which the pre-registration forbids.

### 6.3 Probability bands (WP; obs − pred with match-bootstrap 95% CI)

| Cohort | 0–10% | 10–30% | 30–70% | 70–90% | 90–100% |
|---|---|---|---|---|---|
| T20 men | 0.032→0.022 (−0.009 [−0.016, −0.001]) | 0.202→0.211 (+0.009) | 0.494→0.506 (+0.012) | 0.794→0.773 (−0.021) | 0.966→0.962 (−0.004) |
| T20 women | 0.029→0.021 (−0.008) | 0.200→0.219 (+0.020) | 0.506→0.505 (−0.001) | 0.799→0.791 (−0.008) | 0.951→0.960 (+0.009) |
| ODI men | 0.041→0.090 (+0.048 [0.002, 0.094]) | 0.204→0.247 (+0.044) | 0.497→0.499 (+0.002) | 0.796→0.737 (−0.059 [−0.133, 0.008]) | 0.966→0.931 (−0.035) |
| ODI women | 0.030→0.069 (+0.038) | 0.202→0.301 (**+0.099 [0.019, 0.183]**) | 0.498→0.493 (−0.005) | 0.801→0.825 (+0.024) | 0.959→0.957 (−0.001) |

Each cell reads "mean predicted → observed (gap)". Every band has at least 112 matches. The ODI pattern is classic over-confidence: underdogs win more often than predicted and favourites less often. The full 10-bin reliability tables, with deliveries, matches and the observed-rate CI, are in `test.<cohort>.WP_detail.reliability`.

### 6.4 Temporal stability (WP ECE per test year; matches in brackets)

| Cohort | 2024 | 2025 | 2026 (to 17 Sep) |
|---|---|---|---|
| T20 men | 0.023 (624) | 0.007 (532) | 0.017 (476) |
| T20 women | 0.020 (342) | 0.024 (391) | 0.023 (354) |
| ODI men | 0.038 (68) | **0.042** (92) | **0.065** (53) |
| ODI women | **0.050** (55) | **0.074** (73) | 0.048 (36, not gated) |

T20 slope by year: men 0.94 / 1.02 / 1.04, women 1.19 / 0.94 / 0.92. Skill vs B1 on innings 2 stays positive in every cohort-year.

### 6.5 Fan-visible moments (WP; one row per match, so rows are independent)

| Cohort, moment | Matches | Mean pred → observed | Brier (B0) | Band check (Wilson 95%) |
|---|---|---|---|---|
| T20 men, 2nd-innings start | 1,632 | 0.523 → 0.517 | 0.178 (0.247) | <30%: 0.166 → 0.212 [0.177, 0.252]; >70%: 0.871 → 0.836 [0.802, 0.865] |
| T20 men, after 10 overs of chase | 1,509 | 0.490 → 0.481 | 0.105 (0.249) | <30%: 0.097 → 0.087; >70%: 0.913 → 0.917 |
| T20 men, last 5 overs of chase | 1,288 | 0.421 → 0.422 | 0.079 (0.251) | <30%: 0.057 → 0.059; >70%: 0.925 → 0.922 |
| T20 women, 2nd-innings start | 1,087 | 0.490 → 0.481 | 0.173 (0.248) | <30%: 0.183 → 0.144 [0.108, 0.189]; >70%: 0.813 → 0.895 [0.851, 0.927] |
| T20 women, after 10 overs of chase | 987 | 0.442 → 0.434 | 0.105 (0.248) | <30%: 0.084 → 0.073; >70%: 0.882 → 0.896 |
| T20 women, last 5 overs of chase | 794 | 0.349 → 0.355 | 0.078 (0.247) | <30%: 0.042 → 0.046; >70%: 0.890 → 0.903 |
| ODI men, 2nd-innings start | 213 | 0.556 → 0.556 | 0.198 (0.244) | <30% (49): 0.184 → 0.286 |
| ODI women, 2nd-innings start | 164 | 0.431 → 0.512 | 0.175 (0.252) | >70% (29): 0.847 → 1.000 |

**The weakest point for T20 is the start of the chase**, where the only information is the target. T20 men are slightly too extreme there: underdogs win 21% against 17% predicted. T20 women are not extreme enough: favourites win 90% against 81% predicted. Within the chase the model is well calibrated. "Last 2 overs" and the 1st-innings moments are in `moments` in the JSON.

### 6.6 Checks outside the rules (reported, not gated)

- **International vs club** (`test.<cohort>|club`):
  - T20 men club: 210 matches, ECE **0.070**, slope **0.65**.
  - T20 women club: 66 matches, ECE **0.145**, slope **0.41**.
  - International T20: ECE 0.016 for both men and women.
  - The T20 accept is therefore really an international-T20 result. Club cricket (franchise leagues) is badly calibrated.
- **Per-innings slope inside the T20 women cohort:** innings 1 is 0.82, innings 2 is 1.22. Both pass the per-innings ECE rule (0.031 and 0.027), but the pooled slope of 0.996 hides two offsetting errors. The innings-2 L2 penalty chosen on validation was 1000, which shrinks the coefficients.
- **Monotonicity grid** (innings 2, WP):
  - More runs required never raises p (0 violations).
  - **More wickets lost does raise p in some states:** T20 men 105 of 13,400 grid states, T20 women 670 of 13,400, ODI men 1,835 of 58,500, ODI women 5,471 of 58,500.
  - A product number must never go up when a wicket falls, so this blocks display on its own.

## 7. Verdict

| Cohort | Verdict | Failed pre-registered rules |
|---|---|---|
| **T20 men** | **ACCEPT-FOR-RESEARCH** | none |
| **T20 women** | **ACCEPT-FOR-RESEARCH** | none |
| **ODI men** | **REJECT** | slope 0.749 (outside [0.9, 1.1]); ECE 0.044 > 0.03; innings-1 ECE 0.048 > 0.04; year ECE 2025 = 0.042 and 2026 = 0.065 > 0.04 |
| **ODI women** | **REJECT** | slope 0.842; CITL +0.022 > 0.02; ECE 0.033 > 0.03; innings-2 ECE 0.066 > 0.04; 10–30% band off by +0.099 (CI excludes 0); year ECE 2024 = 0.050 and 2025 = 0.074 |

Why the ODI cohorts fail:
- **Too little data.** Only 213 and 164 test matches, so the slope CIs are as wide as [0.58, 0.98] and [0.68, 1.13]. ODI women have only 304 training and 37 validation matches.
- **Possible era drift.** ODI scoring rates rose after 2023, and the training-era resource table does not know about it.

ODI should not be revisited until more seasons accumulate, and with an explicit era adjustment.

**Overall recommendation: show nothing in the product.** The T20 result shows the dataset *can* support a calibrated chase-state model for international T20 cricket. "ACCEPT-FOR-RESEARCH" is not "ship". Before any number is shown to users, the owner must approve it **and** the following must be done:

1. **Fix monotonicity.** Constrain the model (for example, a sign-constrained or isotonic structure in wickets and runs required) so that a wicket or a dot ball can never increase the batting side's probability. Then re-run this gate.
2. **Restrict scope.** Limit to international T20, or calibrate club/franchise T20 separately and prove it. Club T20 fails badly today.
3. **D/L and rain.** These matches are excluded, but a live match cannot be known in advance to be rain-free. A live product needs either a revised-target model or a rule that hides the number when overs are lost. 480 D/L matches were excluded here.
4. **Reduced-overs and super overs.** Reduced-overs matches without D/L (264 excluded) are unsupported. Ties are labelled 0.5, and super overs are not modelled.
5. **Start-of-chase calibration** (6.5) and the T20 women per-innings slope offset need a fix and a re-test.
6. **Out-of-sample monitoring.** Re-run this gate on every new season, with an automatic hide if per-year ECE exceeds 0.04 or the slope leaves [0.9, 1.1]. Platt recalibration on one year did not help, so recalibration needs more than one season.
7. **Uncertainty display.** Show bands or a range rather than a precise percentage. At the 2nd-innings start the band-level error is up to about 5–8 percentage points.

## 8. Limits and why team strength is not added

The model treats **every team as an average team**. There is no team strength, no player quality (who is still to bat, who has overs left), no venue, pitch or dew, no toss, and no competition level. A probability of 35% means "a typical side in this state wins about 35% of the time". It does not mean "India chasing against Ireland wins 35% of the time".

This is why mismatched fixtures, which are common in women's and associate cricket, drive much of the calibration error at the extremes and at the start of the chase.

Adding team strength is **not** a quick fix. It carries risks of leakage and circularity:

- **Leakage.** Ratings must be computed strictly from matches *before* each match date, including the current one's absence. A rating fitted on the full history, or on a season that includes the test match, leaks the outcome.
- **Circularity.** If ratings are derived from results that the win-probability model also explains, the model partly predicts winners from "teams that win", which inflates apparent skill without adding knowledge. Ratings must be frozen, out-of-sample inputs with their own validation.
- **Sparsity and drift.** Many teams play few matches per year, so ratings are noisy. Squads change between series, so team identity is a poor proxy for the eleven on the field. Each added feature splits already-small cohorts, which matters most for ODI and women's cricket.
- **Product and fairness risk.** A team-aware number makes a public statement about a specific team's chances, which needs a higher bar of validation and explanation.

Other limits:
- Ball-level metrics are dominated by long, one-sided innings. That is why match counts and match-bootstrap CIs are the reported effective n.
- ECE estimated on about 50–90 matches per year is noisy and biased upward. The per-year ODI failures are consistent with real drift but cannot prove it.
- The exclusions (D/L, reduced overs, inconsistent innings) depend on information that is only known after the match.
