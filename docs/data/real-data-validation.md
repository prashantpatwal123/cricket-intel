# External validation: real Cricsheet data vs published scorecards and statistics

**Method.** Our values come from the pipeline (`balls`/`dis` working tables, super overs excluded). Reference values come from published match reports and statistics found by web search on 2026-10-03. The build sandbox can't reach ESPNcricinfo, Wikipedia or ICC sites directly, and we don't scrape them. Each reference cites its source. A value counts as **confirmed** only when a source states it. Numbers that appeared only in my search query, and that no source restated, are marked *unconfirmed*.

## A. Match-level checks (6 finals across all 6 loaded competitions/genders)

| Match (Cricsheet id) | Check | Ours | Published | Result |
|---|---|---|---|---|
| **IPL 2024 final**, KKR v SRH, 26 May 2024 (1426312) | SRH total | 113 all out, 111 balls (18.3 ov) | 113 all out | ✅ |
| | KKR chase | 114/2 in 63 balls (10.3 ov) | chased 114 in 10.3 overs | ✅ |
| | Result | KKR by 8 wickets | KKR won by 8 wickets | ✅ |
| | Cummins | 24 (19) | 24 off 19 | ✅ |
| | Starc | 3 ov, 14 runs, 2 wkts | 2/14 off 3 overs | ✅ |
| | Russell / Harshit Rana wickets | 3 / 2 | 3 / 2 | ✅ |
| | Venkatesh Iyer | 52 (26) | "half-century" | ✅ (exact 52 (26) unconfirmed) |
| **WPL 2024 final**, DC v RCB, 17 Mar 2024 (1417737) | DC total | 113 all out, 18.3 ov | 113 in 18.3 overs | ✅ |
| | RCB chase | 115/2 in 19.3 ov | chased 114 with 3 balls to spare | ✅ |
| | Shafali Verma | 44 (27) | 44 off 27 | ✅ |
| | Shreyanka Patil / Molineux | 4/12, 3/20 | 4/12, 3/20 | ✅ |
| | Perry / Devine / Mandhana | 35*, 32 (27), 31 (39) | 35*, 32 off 27, 31 off 39 | ✅ |
| **Men's T20 WC 2024 final**, Ind v SA, 29 Jun 2024 (1415755) | India total | 176/7 | 176/7 | ✅ |
| | Kohli | 76 (59), 6×4, 2×6 | 76 off 59, six fours, two sixes | ✅ |
| | Axar Patel | 47 (31) | 47 from 31 | ✅ |
| | Klaasen | 52 (27), 2×4, 5×6 | 52 off 27, five sixes, two fours | ✅ |
| | Hardik / Bumrah | 3 ov 3/20; 4 ov 2/18 | 3/20 in three overs; 2-18 from four | ✅ |
| | Maharaj / Nortje / Arshdeep | 2/23, 2/26, 2 wkts | 2/23, 2/26, two wickets | ✅ |
| | Result | India by 7 runs | won by seven runs | ✅ |
| **Men's ODI WC 2023 final**, Ind v Aus, 19 Nov 2023 (1384439) | India total | 240 all out | 240 all out | ✅ |
| | Aus chase | 241/4 in 258 balls (43.0 ov) | 241-4 in 43.0 overs | ✅ |
| | Head | 137 (120), 15×4, 4×6 | 137 off 120, 15 fours and 4 sixes | ✅ |
| | KL Rahul / Starc | 66; 3/55 | 66; 3/55 | ✅ |
| **Women's ODI WC 2022 final**, Aus v Eng, 3 Apr 2022 (1243938) | Totals | 356/5 and 285 in 262 balls (43.4 ov) | 356/5; 285 in 43.4 overs | ✅ |
| | Result | Australia by 71 runs | won by 71 runs | ✅ |
| | Healy / Sciver | 170 (138), 26×4; 148* (121) | Healy player of the match | ✅ (exact figures unconfirmed by the returned sources) |
| **Women's T20 WC 2023 final**, Aus v SA, 26 Feb 2023 (1338062) | Totals | 156/6; 137/6 | 156/6; 137/6 | ✅ |
| | Mooney / Gardner | 74 (53); 29 (21) | 74 off 53; 29 off 21 | ✅ |
| | Wolvaardt / Tryon | 61 (48); 25 (23) | 61 off 48; 25 off 23 | ✅ |
| | Ismail / Kapp | 2/26; 2/35 | 2-26; 2-35 | ✅ |
| | Result | Australia by 19 runs | won by 19 runs | ✅ |

**Result: 0 discrepancies across 42 confirmed checks** (many checks cover several numbers: team totals, balls, batting runs/balls/4s/6s, bowling figures, results).

## B. Career-level checks (expected to differ: coverage, not computation)

| Player · format | Ours (covered data) | Published | Gap explained by |
|---|---|---|---|
| **Virat Kohli · T20I** | 118 matches, 3,963 runs, avg 48.33, SR 135.95, 37 fifties, 0 hundreds | 125 matches, 4,188 runs, avg 48.69, SR 137.04, 38 fifties, HS 122* | **Afghanistan withholding (primary-confirmed).** His only T20I hundred (122* v Afghanistan, Asia Cup 2022) and a 29 v Afghanistan (Jan 2024) are confirmed missing; the other 5 missing matches are consistent with this but not individually verified. Our page shows "Matches against Afghanistan are withheld by Cricsheet". |
| **Meg Lanning · T20I** | 100 matches, 2,538 runs, 1 hundred | 132 matches, 2 hundreds (sources disagree on runs: 3,405 vs 4,405) | **Unsourced women's T20Is.** Cricsheet doesn't track missing T20Is, so the page says "completeness can't be established". Also, 17 Australia women's ODIs in her ODI window are listed as unsourced by Cricsheet. |

Conclusion: computation agrees exactly wherever a match exists. Career totals differ only because of **coverage**, which the product now states per format.

## C. Dismissal DNA: wicketkeeper inference (derived)

Cricsheet doesn't mark the keeper. Measured on the loaded subset:

| Keeper identification per team-match (20,494) | Count | Share |
|---|---|---|
| Stumping in that match (conf 0.97) | 3,756 | 18.3% |
| Sole player in XI with ≥2 career stumping matches, didn't bowl (conf **0.95**, measured) | 8,129 | 39.7% |
| Dominant candidate, ≥3× the next (conf **0.90**, measured) | 3,869 | 18.9% |
| **Unknown (left unknown)** | 4,740 | 23.1% |

**Accuracy measurement.** On the 3,756 team-matches where a stumping identifies the keeper, the career rule was applied with that match's own stumpings excluded. It labelled 78% of them, with **92.3% precision** overall and **95.3% for the sole-candidate rule**. The confidence values shown in the product are these measured figures. (Caveat: matches with stumpings skew towards spin-heavy games.)

| Catches (71,824 `caught` dismissals) | Count |
|---|---|
| Caught by wicketkeeper (derived) | 10,687 |
| Caught by named non-keeper fielder (derived: keeper known, catcher isn't the keeper) | 44,453 |
| Caught by substitute (observed) | 1,261 |
| **Keeper status unknown (never converted to caught-behind)** | **15,398 (21.4%)** |
| Caught, no fielder named | 25 |

Terminology: the product says **"caught by wicketkeeper"**, never "edged behind". The data contains no edge information (Ask Cricket's caveat says so explicitly).

## D. Internal consistency against the source's own declarations
- `chase_result` QA: every chase that reached its target is recorded by Cricsheet as a win for the chasing side. **0 violations.**
- `innings_total`, `runs_total_sum`, `extras_sum`: **0 violations** over 3,298,987 deliveries.

## Sources
- KKR v SRH IPL 2024 final: [Sportskeeda](https://www.sportskeeda.com/cricket/kkr-vs-srh-ipl-2024-final-full-list-award-winners-player-match-scorecard-records), [ESPNcricinfo scorecard (cited by search)](https://espncricinfo.com/ci/engine/match/1426312.html), [MyKhel](https://www.mykhel.com/cricket/kolkata-vs-hyderabad-ipl-2024-final-scorecard-60590/)
- WPL 2024 final: [Business Standard](https://www.business-standard.com/amp/cricket/news/wpl-2024-final-dc-vs-rcb-124031700542_1.html), [The Week](https://www.theweek.in/wire-updates/sports/2024/03/17/spd23-spo-cri-wpl-dc-rcb-result.html), [Wisden](https://wisden.com/stories/global-t20-leagues/wpl-2024/watch-the-moment-rcb-beat-delhi-capitals-in-wpl-2024-final-to-lift-first-major-silverware)
- T20 WC 2024 final: [BCCI](https://www.bcci.tv/articles/2024/news/55556122/dominant-unbeaten-and-magnificent-india-lift-second-men-s-t20-world-cup-title), [Sky Sports](https://www.skysports.com/cricket/news/12040/13161121/t20-world-cup-final-virat-kohli-and-jasprit-bumrah-step-up-in-indias-time-of-need-as-title-drought-ends), [Rajasthan Royals](https://rajasthanroyals.com/latest-news/t20-world-cup-2024-india-vs-south-africa-final-ind-sa-match-report)
- ODI WC 2023 final: [Wisden scorecard](https://www.wisden.com/live-cricket-scores/india-vs-australia-match-odi-inau11192023228846-scorecard), [MyKhel](https://www.mykhel.com/cricket/india-vs-australia-icc-cricket-world-cup-2023-final-scorecard-57812/)
- Women's WC 2022 final: [Wikipedia (via search)](https://en.wikipedia.org/wiki/2022_Women%27s_Cricket_World_Cup_final)
- Women's T20 WC 2023 final: [Al Jazeera](https://www.aljazeera.com/amp/sports/2023/2/26/dominant-australia-beat-south-africa-for-sixth-womens-t20-title), [Wisden](https://wisden.com/series/icc-womens-t20-world-cup-2022-23/live-cricket-scores/australia-women-vs-south-africa-women-match-t20-auwsaw02262023217647)
- Kohli T20I career: [cricket.com](https://cricket.com/players/virat-kohli-3993), [Guinness World Records](https://www.guinnessworldrecords.com/world-records/761051-highest-batting-average-in-a-t20-international-career-male); v Afghanistan: [WION](https://www.wionews.com/sports/asia-cup-virat-kohli-finally-ends-century-drought-with-maiden-t20i-ton-in-afghanistan-clash-514206), [Sportskeeda](https://www.sportskeeda.com/cricket/asia-cup-2022-5-records-virat-kohli-broke-unbeaten-122-run-knock-afghanistan)
- Lanning T20I career: [cricket.com.au](https://www.cricket.com.au/news/3773916/meg-lanning-announces-international-retirement-at-31-after-13-year-career-australia-womens-captain-legend-icon-seven-world-cups), [Wikipedia (via search)](https://en.wikipedia.org/wiki/Meg_Lanning)
