# Pressure / Situation-Difficulty Methods: Literature and Methodology Review

Status: research note, input to the design of "Situation Difficulty — Experimental" (SDx). Not a specification.
Date: 2026-10-04.

## 0. How this review was produced (read first)

Outbound page fetching was blocked by the network egress policy in the research environment. arXiv, journal sites, ESPNcricinfo, FanGraphs, SABR and Wikipedia all failed. **No primary source was opened in full.** Every statement below comes from search-engine result pages: titles, bibliographic records, abstracts and indexed snippets. Verification levels used:

- **[abstract]**: the bibliographic details and the summary claim appeared in the indexed abstract or publisher record.
- **[snippet]**: a secondary or indexed summary, consistent across results but not read in the original.
- **[unverified]**: from background knowledge or one weak snippet. Check it against the primary source before relying on it.

Before any formula in this note goes into code, someone should read the primary PDF. Formulas reported here could contain transcription errors.

---

## 1. Duckworth–Lewis–Stern (DLS) resources

**Sources.** Duckworth, F.C. & Lewis, A.J. (1998). "A fair method for resetting the target in interrupted one-day cricket matches." *Journal of the Operational Research Society* 49(3), 220–227. doi:10.1057/palgrave.jors.2600524 [abstract]. Stern, S.E. (2016). "The Duckworth-Lewis-Stern method: extending the Duckworth-Lewis methodology to deal with modern scoring rates." *JORS* 67(12), 1469–1480 [abstract].

**Method.** The original model gives the expected further runs with *u* overs remaining and *w* wickets lost as an exponential-decay form, Z(u,w) = Z0·F(w)·[1 − exp(−b·u / F(w))] [snippet; check exact parameterisation]. "Resources remaining" is Z(u,w)/Z(50,0), a percentage that falls monotonically in overs used and in wickets lost. A Professional Edition (2003) and Stern's 2016 revision change the resource curves for high-scoring modern innings, particularly T20 [abstract]. The current DLS parameters and tables are proprietary to the ICC. The published papers give the functional form but not the fitted values now in use [unverified as to exact current licensing].

**Use for "situation".** Resources remaining is the standard compact way to describe a limited-overs state from (balls left, wickets lost) alone. Pressure indices (§3) and contextual-batting work (§3, Thomson et al.) divide runs required by resources remaining. A 2026 arXiv preprint audits DLS for format-specific and gender-differential bias ("A Fairness Audit of the Duckworth-Lewis-Stern Method", arXiv:2609.04754) [title only; unverified content]. If that holds, a single resource table may not transfer cleanly between T20 and ODI, or between men's and women's cricket.

**Relevance to CRICINTEL.** We cannot use the official DLS table. We *can* fit our own DLS-style resource table from Cricsheet: the empirical mean of further runs by (balls left, wickets lost), smoothed and constrained to be monotone. This is transparent and reproducible, and we must describe it as "DLS-style", not "DLS".

## 2. Win-probability (WP) models for limited-overs cricket

**WASP.** Brooker, S. & Hogan, S., University of Canterbury. WASP (Winning and Score Predictor) is a ball-by-ball dynamic-programming model. It estimates expected first-innings score and second-innings win probability from historical transition frequencies. It was built on non-shortened ODI and T20 matches between top-eight nations from about 2006, and broadcast in New Zealand from about 2012 [snippet]. A related working paper is Brooker & Hogan (2011), "A Method for Inferring Batting Conditions in ODI Cricket from Historical Data", University of Canterbury Economics Working Paper 11/44 (https://ideas.repec.org/p/cbt/econwp/11-44.html) [abstract]. It estimates a latent "ground conditions" distribution from first-innings score and result, using Monte Carlo methods. WASP's exact transition model is not fully public [unverified]. Commentators have criticised its thin tails, i.e. overconfidence in extreme situations (noenthuda.com, 2014, "WASPs have thin tails") [title only].

**Dynamic logistic regression.** Asif, M. & McHale, I.G. (2016). "In-play forecasting of win probability in One-Day International cricket: A dynamic logistic regression model." *International Journal of Forecasting* 32(1), 34–43. doi:10.1016/j.ijforecast.2015.02.005 [abstract]. The coefficients of a logistic regression vary smoothly with match progress. According to the abstract, this cuts the parameter count sharply and "produces stable and intuitive forecast probabilities" with minimal loss of explanatory power. This is the most directly reusable academic template for us: a small number of interpretable covariates (runs required, balls left, wickets lost, plus first-innings score for innings 1) with coefficients that vary by stage.

**Other.** "In-Game Win Prediction Models for Cricket" (Springer chapter, 2024, doi 10.1007/978-3-031-67871-4_11) [title only]. Many open-source GBM and logistic T20 chase models report Brier scores of about 0.09–0.15 on held-out data, depending on league [snippet; these are GitHub READMEs, not peer reviewed, and are useful only as a sanity range].

**Leverage from WP.** In baseball, leverage is the expected *swing* in WP at a state, normalised by the average swing (§5). The cricket analogue is the probability-weighted absolute change in chase WP over the next ball's outcomes {0,1,2,3,4,6,W,extras}. No peer-reviewed cricket paper defining a "Leverage Index" this way was found [unverified absence]. An arXiv title, "The Calibration-Leverage Tradeoff in Exactly Solvable Win-Probability Models" (arXiv:2608.14696), suggests recent work on this exact tension [title only; unverified].

## 3. Published cricket pressure indices

**Shah & Shah (2014).** "Pressure Index in Cricket", *IOSR Journal of Sports and Physical Education* [unverified venue details; Semantic Scholar record exists]. As later quoted: PI = CI×100 + [wicket weight/180 × T × Br/B × Rr/T]. Later authors report that this PI *decreased* when a wicket fell and when an over went below the required rate, which they call unrealistic [snippet, via arXiv:2505.01849]. Lesson: an index that is not monotone in the obvious directions is not credible.

**Bhattacharjee & Lemmer (2016).** "Quantifying the pressure on the teams batting or bowling in the second innings of limited overs cricket matches." *International Journal of Sports Science & Coaching* 11(5), 683–692 [abstract]. Inputs: DLS resources used, wickets lost (weighted by batting position using Lemmer's wicket weights), and the ratio of current to initial required run rate [snippet]. As quoted by later authors:

  PI = (CRRR / IRRR) × ½ [ e^(RU/100) + e^(Σwᵢ/11) ]

Here IRRR = 6T/B is the initial required rate, CRRR = 6(T−R′)/(B−B′) is the current required rate, RU is the percentage of resources used, and Σwᵢ is the sum of the weights of fallen wickets [snippet; read the primary source to confirm]. PI equals about 1 at the start of the chase and is unbounded above. The authors and later users say it can relate to winning probability and to crediting batters for runs scored under pressure [snippet]. I could not confirm a formal validation such as a calibration curve or Brier score [unverified].

**Mallawa Arachchi, Manage & Scariano (2024).** "A pressure index for the team batting second in T20I cricket." *Journal of Sports Analytics*, doi:10.3233/JSA-240792 [abstract]. This is a differential-equation formulation. The rate of change of pressure depends on current pressure and on the required run rate relative to resources remaining. It is illustrated on T20Is between major nations in 2017–2019 and 2021 [abstract]. Validation details were not visible [unverified].

**Higher-order Markov + PI for T20 chases.** arXiv:2505.01849 (2025), "Applications of higher order Markov models and Pressure Index to strategize controlled run chases in Twenty20 cricket" [abstract/snippet]. It uses PI-style measures to plan chases.

**Thomson, Perera & Swartz (2021).** "Contextual batting and bowling in limited overs cricket." *South African Statistical Journal* (https://www.journals.ac.za/sasj/article/view/4951) [abstract]. Before each ball they compute the ratio of runs required to resources remaining. A batter's ball is credited by how much it lowers that ratio. They aggregate to "clutch batting" and "clutch bowling" statistics [abstract]. This is effectively a resource-based WPA, and the closest academic analogue to what we want.

**ESPNcricinfo Smart Stats / Superstats (2018–).** Explainer: https://www.espncricinfo.com/story/explainer-how-smart-stats-works-1178326 [snippet]. For each ball a pressure-index value is assigned to batter and bowler, on a 0–10 scale according to one ESPN page [snippet]. It is based on required run rate and wickets in hand, quality of the batters to come, quality of the bowlers with overs remaining, and the batter/bowler involved. Runs and wickets are multiplied by the PI value to give "Smart Runs" and "Smart Wickets". "Match Impact" or "Player Impact" aggregates these, and a separate Forecaster gives win probabilities [snippet]. The weights and model are proprietary. **No published validation was found** [unverified]. It cannot be reproduced and should be cited only as practice, not as evidence. CricViz publishes similar WP and "impact" figures. I found no public methodology document for them in this session [unverified].

**Common pattern.** Every published cricket pressure index (a) applies to chases, (b) uses required rate relative to the initial or par rate, (c) uses wickets lost, often weighted, and (d) uses resources or balls remaining. None that I could see is bounded or published with out-of-sample validation.

## 4. Required run rate, dot balls, recent wickets, and momentum

**RRR vs CRR.** RRR/IRRR (Bhattacharjee & Lemmer) and runs-required / resources-remaining (Thomson et al.) are better than raw RRR−CRR. That gap ignores wickets in hand and stage, and it is undefined in the first innings. It is the usual broadcast heuristic, but none of the academic sources treated it as sufficient [snippet].

**Dot balls.** A 2025 ResearchGate paper, "Quantifying the Impact of Dot Balls on Winning Probability in T20 Cricket", exists [title only]. Most "dot balls build pressure that leads to wickets" claims found were coaching or blog content, not controlled studies [snippet]. **There is no confirmed evidence that a dot-ball streak raises next-ball dismissal probability once batter, stage and RRR are controlled for** [unverified either way].

**Batter "set-ness" (a confounder for momentum).** Brewer, B.J. (2008), "Getting your eye in: a Bayesian analysis of early dismissals in cricket", arXiv:0801.4408 [title/snippet]: dismissal hazard is higher early in an innings. Misra, V. (2026), "The Set-Batter Paradox" (Columbia, preprint, not peer reviewed): this used about 281k IPL deliveries with within-batter fixed effects. It reports that strike rate *and* per-ball dismissal hazard both rise with balls faced. The same summary says recent strike rate does not significantly affect dismissal probability [snippet]. Treat it as a single preprint.

**Hot hand.** Ram, S.K., Nandan, S. & Sornette, D. (2022), "Significant hot hand effect in the game of cricket", *Scientific Reports* 12 (PMC9270381) [abstract]. Using self-exciting point processes on the history of international cricket, they find hot-hand predictability in *individual* performance streaks, but none in *team* performance or match outcome. In their words, cricket is "a game of skill for individuals and a game of chance for the teams" [abstract]. This is about form across innings, not within-innings momentum.

**Implication.** Within-innings "momentum" (recent dots, wickets in the last N balls) is weakly evidenced. If used at all, it should be a separate, explicitly experimental component whose effect we test, not something we assume.

## 5. Baseball Leverage Index (LI) and WPA as a template

**Definitions.** Win Probability Added (WPA) is the change in the batting team's win expectancy across a play, credited to the players involved [snippet; FanGraphs Library, Baseball-Reference "wpa.shtml"]. Leverage Index, created by Tom Tango, is the expected absolute WP swing available in a game state, divided by the mean swing over all states. LI = 1 is average; leverage in blowouts is near 0; pivotal late situations exceed 2 [snippet; MLB glossary, FanGraphs Library]. WPA/LI ("context-neutral wins") divides each play's WPA by that play's LI to remove situational weighting [snippet]. See also Tango, Lichtman & Dolphin (2007), *The Book: Playing the Percentages in Baseball* [snippet].

**Pitfalls.**
1. *Model dependence.* LI is only as good as the WP model under it. A miscalibrated WP model (e.g. WASP's alleged thin tails) produces leverage that is too high or too low exactly in the extreme states that matter.
2. *Circularity.* If the WP model includes batter/bowler quality, and "pressure" is later used to judge batter/bowler quality, the measure partly validates itself. The same applies if SDx is validated against match outcome and also built from a model fitted to match outcome on the same data.
3. *Leverage ≠ difficulty.* LI is about *importance*: a 50/50 last-over finish has high LI even when the required rate is easy. A near-hopeless chase has low LI but very high difficulty. Pressure indices (§3) measure difficulty. SDx should say which one it measures. The name implies difficulty.
4. *Units.* LI is a ratio to average, centred on 1 and unbounded. Mapping it to 0–100 needs an explicit, versioned transform.

## 6. Validation approaches in this literature

- **Proper scoring rules for WP models.** Brier score (Brier, G.W., 1950, *Monthly Weather Review* 78(1), 1–3) and log loss. Both are strictly proper (Gneiting, T. & Raftery, A.E., 2007, *JASA* 102, 359–378) [abstract]. Asif & McHale assess forecast performance against outcomes. I could not confirm their exact metrics [unverified].
- **Calibration / reliability curves.** Predicted vs observed win rate by decile. This is common in open-source T20 WP work [snippet].
- **Face validity and monotonicity.** Implicit in the critique of Shah & Shah: pressure should not fall when a wicket falls [snippet].
- **Year-to-year persistence for "clutch" skill.** Cramer, R.D. (1977), "Do Clutch Hitters Exist?", *Baseball Research Journal* (SABR) [snippet]. Bill James's critique ("Underestimating the Fog", SABR) argues that a non-persistence result has low power and cannot prove absence [snippet].
- **Holdout by time.** Not confirmed as standard in the cricket pressure papers I saw [unverified]. It is standard forecasting practice and is needed here because scoring rates drift, especially in T20, as Stern (2016) notes.

## 7. "Clutch": when the word is justified

Baseball's large literature (Cramer 1977; *The Book* 2007; SABR debate) finds that clutch *performance* in a season is easy to measure. Clutch *ability*, meaning a repeatable tendency to outperform one's baseline in high-leverage spots, is small and hard to separate from noise [snippet]. The cricket "clutch batting" statistic of Thomson et al. (2021) is a descriptive aggregate. I could not confirm that they tested persistence [unverified]. Ram et al. (2022) find individual streakiness but no team-level hot hand [abstract].

**Rule for CRICINTEL.** Use "performance in high-difficulty situations" by default. Use "clutch" only for a player whose high-SDx performance beyond baseline (a) has a confidence interval excluding zero after shrinkage, and (b) persists split-half or season-to-season with a correlation significantly above zero, on enough balls. Otherwise, do not use the word.

---

## 8. Implications for CRICINTEL

**8.1 Defensible inputs (from Cricsheet alone).**
- Balls remaining (legal deliveries, honouring reduced overs where Cricsheet records them) and wickets lost. Together these give a self-fitted DLS-style resource %.
- In chases: runs required and target, from which come RRR and RRR/IRRR. Prefer runs-required ÷ expected-runs-from-resources (the Thomson et al. form). It combines rate and wickets in one interpretable ratio.
- In innings 1: projected total vs a format- and competition-season par, e.g. the median first-innings score for that competition and season. This is weaker, because there is no target. Label it lower-confidence.
- Optional, experimental: dots and wickets in the last 6/12 balls. Evidence for momentum is weak (§4), so keep this as a separate component that can be switched off.
- **Avoid in v1:** player-quality terms such as "batters to come" or "bowlers left". These need ratings, which brings in circularity and model dependence (§5). Avoid venue, pitch and toss effects, which we cannot measure reliably. Avoid batting hand and bowling style, which we lack.

**8.2 Bounded and explainable.** Define SDx = Σ component scores. Each component is a monotone, capped transform of one input, e.g. a logistic or piecewise-linear map of (required/expected) onto 0–60, wickets lost relative to resources onto 0–30, and optional momentum onto 0–10. The total is clipped to 0–100. Publish the component breakdown for every ball. Fix the transforms by percentiles of a *frozen training window*, not the live data, so scores are reproducible. Version the transform (`sdx-t20-v0.1`, `sdx-odi-v0.1`) and store the version with each score. Build in hard monotonicity: SDx must not fall when a wicket falls or when runs required rise with balls held fixed. Unit-test this property (the Shah & Shah lesson).

**8.3 Avoiding circularity.**
- Build SDx from state only (score, balls, wickets, target). Use no player identities and no outcome-derived player ratings.
- If a WP model is used, e.g. a dynamic logistic in the Asif & McHale style for a leverage companion metric, fit it on seasons strictly earlier than the ones scored and validated.
- Do not evaluate players with SDx-weighted runs using the same matches that set the SDx transforms.
- Keep "Difficulty" (SDx) and "Leverage" (expected |ΔWP|) as separate fields. Do not combine them.

**8.4 Validation tests on Cricsheet (pre-register before looking).**
1. *Outcome relation (chases).* Chase win rate should fall monotonically across SDx deciles at fixed stage, e.g. at over 10 and over 15 in T20. Report Brier and log loss of a one-variable logistic on SDx against a balls+wickets+runs-required baseline. SDx should not be much worse, because it is a compression of the same state.
2. *Subsequent behaviour.* Measure next-6-ball dismissal rate and scoring rate by SDx band, controlling for stage. A plausible expectation is that both scoring rate and dismissal rate rise with SDx in chases (forced risk). Report this as observed, not assumed.
3. *Temporal holdout.* Fit the transforms on, e.g., seasons up to 2021 and test on later seasons. Report drift of decile boundaries per season.
4. *Format split.* Fit and report T20 and ODI separately. Do not pool.
5. *Men's vs women's.* Report calibration separately. Given the DLS bias audit (§1, unverified) and different scoring levels, expect to need separate pars or resource tables. Publish whichever applies.
6. *Competition split.* International vs franchise leagues.
7. *Reliability of player-level aggregates.* Run split-half correlation of each player's "performance above baseline in high SDx" before any player-facing claim. This is the gate for §7.

**8.5 Why T20 and ODI definitions must differ.** Resource curves differ in shape: in T20, wickets are far less binding relative to balls than in ODI, and Stern 2016 revised DLS precisely for high T20 scoring. Par scores and the spread of achievable required rates differ by roughly a factor of two per over. ODIs have three powerplay phases, T20s one. In T20 a few balls swing the state; in ODI pressure builds over many overs, so any momentum window must scale with format. A single formula would make an ODI score of 70 mean something different from a T20 score of 70. Separate fits with separate version tags avoid that.

**8.6 Honesty and labelling.** Ship SDx as "Experimental". Show the component breakdown and model version, and link to this note and a model card. State that it measures *situation difficulty from scoreboard state only*, not player skill, not "clutch", and not win probability.

---

## Source list (as accessed: search results only, no full texts)

- Duckworth & Lewis (1998), JORS 49(3) 220–227. doi:10.1057/palgrave.jors.2600524
- Stern (2016), JORS 67(12) 1469–1480. https://research.bond.edu.au/en/publications/the-duckworth-lewis-stern-method-extending-the-duckworth-lewis-me/
- Anonymous (2026) DLS fairness audit, arXiv:2609.04754 (title only)
- Brooker & Hogan (2011), UC Econ WP 11/44. https://ideas.repec.org/p/cbt/econwp/11-44.html; WASP overview https://en.wikipedia.org/wiki/WASP_(cricket_calculation_tool), https://www.nzc.nz/news-items/archive/whats-wasp-all-about/
- Asif & McHale (2016), IJF 32(1) 34–43. https://doi.org/10.1016/j.ijforecast.2015.02.005
- Bhattacharjee & Lemmer (2016), IJSSC 11(5) 683–692
- Shah & Shah (2014), "Pressure Index in Cricket". https://www.semanticscholar.org/paper/1f62f73e39086f5c5c11215e3683a79bb3dce2a2
- Mallawa Arachchi, Manage & Scariano (2024), JSA. https://doi.org/10.3233/JSA-240792
- arXiv:2505.01849 (2025), Markov + Pressure Index for T20 chases. https://arxiv.org/abs/2505.01849
- Thomson, Perera & Swartz (2021), SA Statistical Journal. https://www.journals.ac.za/sasj/article/view/4951
- ESPNcricinfo Smart Stats explainer. https://www.espncricinfo.com/story/explainer-how-smart-stats-works-1178326
- Ram, Nandan & Sornette (2022), Sci. Rep. https://www.ncbi.nlm.nih.gov/pmc/articles/PMC9270381/
- Brewer (2008), arXiv:0801.4408
- Misra (2026), "The Set-Batter Paradox" (preprint). https://www.cs.columbia.edu/~misra/set-batter-2026.pdf
- FanGraphs Library, Leverage Index. https://library.fangraphs.com/misc/li; MLB glossary https://www.mlb.com/glossary/advanced-stats/leverage-index; Baseball-Reference WPA https://www.baseball-reference.com/about/wpa.shtml
- Cramer (1977), SABR BRJ. https://sabr.org/research/cramer-do-clutch-hitters-exist; James, "Underestimating the Fog". https://sabr.org/research/article/underestimating-the-fog/
- Tango, Lichtman & Dolphin (2007), *The Book* (via secondary snippet)
- Brier (1950), Monthly Weather Review 78(1) 1–3; Gneiting & Raftery (2007), JASA 102 359–378
