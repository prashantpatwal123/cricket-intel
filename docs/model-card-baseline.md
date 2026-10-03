# Model card: baseline-cohort/0.1 (MODELLED)

- **Task:** next-delivery outcome ∈ {DOT, 1, 2, 3, 4, 6, WICKET}. Runs include extras; 5 counts as 4, 7+ as 6.
- **Method:** context cohorts (format → phase → wickets-down band → chase-pressure band) with empirical-Bayes backoff (K=50), times shrunk batter/bowler multipliers measured against each player's own context expectation (K=3000 pseudo-balls, min 30 balls).
- **Training window:** matches before 2024-01-01 (point-in-time). **Held out:** matches on/after 2024-01-01.
- **Held-out results (SYNTHETIC fixture, 70,553 deliveries):** log-loss 1.4846 (global rate) → 1.4702 (context) → 1.4700 (context+players). Top-1 accuracy 35.9% → 38.5%. Wicket probability is well calibrated by decile.
- **Honest reading:** situation carries almost all the signal. Player effects add almost nothing at this shrinkage (smaller K made held-out loss worse). This is a pipeline baseline, not a predictive claim.
- **Artifacts:** `data/models/baseline-cohort-0.1.json` (all cohort tables, multipliers, constants, metrics). Every prediction shown in the app carries the version and training window.

## Real data (Cricsheet subset), trained before 2025-01-01, evaluated on 2025-01-01 onwards
- Training: 2,690,951 deliveries (2002-06-27 → 2024-12-31). Held out: 607,185 deliveries.
- Log-loss: global rate 1.4035 → context 1.3723 → **context + players 1.3645**. Top-1 accuracy 39.5% → 45.1% → **45.2%**. Brier 0.6933 → 0.6778 → 0.6755.
- Unlike the synthetic fixture, **player effects add measurable skill on real data**.
- Artifact: `data/models/baseline-cohort-0.1-cricsheet.json`. What Happens Next uses only moments on/after the cutoff.
