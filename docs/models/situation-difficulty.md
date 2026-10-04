# Situation Difficulty — Experimental (SDX v0.1): design

Status: **EXPERIMENTAL, behind `CRICINTEL_EXPERIMENTAL=1`. Not launched, not called "Pressure".**
Validation results: `situation-difficulty-validation.md` (generated). Literature: `docs/research/pressure-methods-review.md`.

## Research summary (what we took, what we rejected)

- **Taken:** a DLS-style resource table (balls left × wickets lost; Duckworth & Lewis 1998, Stern 2016) as the core
  input; "demand = runs required ÷ expected runs from resources" (as in Thomson, Perera & Swartz 2021); keeping
  *difficulty* and *leverage* separate (Tango's Leverage Index); holdout-by-season validation with log loss, Brier
  score and calibration (Asif & McHale 2016; Brier 1950).
- **Rejected for v0.1:** player-quality terms, venue and toss (they need outcome-fitted ratings, which makes the index
  partly validate itself); momentum/recent-dot inputs (evidence for within-innings momentum is weak, e.g. Ram et al.
  2022 found no team-level hot hand); a first-innings definition (no target, so no objective anchor).
- **Caveat:** the research agent could not open primary papers (network policy). Claims are tagged by evidence level
  in the review and should be checked before any public use.

## Definition

1. Resources Z(u, w) = Z0(w) · (1 − e^(−u / c(w))), u = overs left, fitted per format × gender on first innings before
   2025-01-01 (no rain method, full overs). Monotone in u by construction; forced non-increasing in wickets lost.
2. Demand D = runs required ÷ Z(balls left, wickets lost) (interpolated to ball level).
3. SDX = 100 × P(chase fails | D), an isotonic (monotone) fit on training chases.
4. Swing = SDX after a wicket − SDX after a four, on this ball (bounded 0–100). Separate from difficulty.

Properties: bounded 0–100; reproducible from the stored artifact `derived/sdx-0.1-<dataset>.json`; versioned;
unit-tested monotone (wickets, runs required, balls passing never make it easier).

## Validation result (summary)

Holdout chases from 2025: SDX beats a required-run-rate-only model and the base rate in all four format × gender
models (log loss 0.345 v 0.377 v 0.692 in men's T20; 0.426 v 0.552 v 0.693 in men's ODIs). 0 monotonicity violations
in 200,000 states. Weaknesses: men's T20 mid-range states are ~5 points too pessimistic in 2025+ (scoring inflation;
recency-window refits did not fix it), women's ODI calibration is poor in the 60–90 band (small sample), and women's
models shift materially between eras.

## Before it could be called "Pressure"

1. Fix calibration drift (era term or rolling recalibration) and re-validate.
2. Decide and validate a first-innings definition, or keep the measure chase-only and say so.
3. External sense-check against published win-probability graphics for a sample of matches.
4. Product review of wording. Until then the label stays "Situation Difficulty — Experimental".

## Difficult-chase performance ("clutch")

Tested and **not supported**: across 200 men's T20 batters, beating expectation in hard chases (SDX ≥ 70) has an
even/odd-year split-half correlation of 0.02 (90% interval −0.09 to 0.14). Results are similar for men's ODIs, women's
T20s and ODIs, and bowlers. After a Benjamini–Hochberg correction no player passes. We therefore do not use "clutch";
the lab shows descriptive differences only, labelled as variation.
