# QA report — dataset `synthetic`

> ⚠️ SYNTHETIC FIXTURE (fictional matches). This report validates the pipeline, not real data.

**32 checks · 0 failing ERROR · 3 WARN · 0 matches quarantined at ingest · ran in 0.3s**

| Table | Rows |
|---|---|
| matches | 1,534 |
| innings | 3,068 |
| deliveries | 415,676 |
| wickets | 21,408 |
| wicket_fielders | 13,728 |
| players_in_match | 33,748 |
| persons | 674 |

| Status | Area | Check | Violations | Example |
|---|---|---|---|---|
| ✅ PASS | duplicate matches | match_id appears more than once (`dup_match_id`) | 0 |  |
| 🟡 WARN | duplicate matches | same teams + start date + venue under different ids (possible duplicate upload) (`dup_match_fingerprint`) | 1 | `Dunmere · Estrova · 2016-09-07 · Estrova Arena · ['9000986', '9001221'] · 2` |
| ✅ PASS | duplicate deliveries | delivery_id not unique (`dup_delivery_id`) | 0 |  |
| ✅ PASS | duplicate deliveries | two deliveries share (match, innings, seq) (`dup_delivery_seq`) | 0 |  |
| ✅ PASS | innings totals | runs.total != runs.batter + runs.extras (`runs_total_sum`) | 0 |  |
| ✅ PASS | innings totals | innings total != Σ delivery totals + penalty runs (`innings_total`) | 0 |  |
| ✅ PASS | extras | runs.extras != wides + noballs + byes + legbyes + penalty (`extras_sum`) | 0 |  |
| ✅ PASS | extras | wide and no-ball on the same delivery (`extras_combo`) | 0 |  |
| ✅ PASS | extras | 4 or 6 flagged non_boundary (all-run) (`boundary_four_six`) | 0 |  |
| ✅ PASS | wicket totals | more than 10 dismissals in an innings (`wickets_per_innings`) | 0 |  |
| ✅ PASS | wicket totals | dismissals >= batting XI size (`wickets_vs_xi`) | 0 |  |
| ✅ PASS | legal deliveries | over has more legal balls than balls_per_over (umpire miscount?) (`legal_per_over`) | 0 |  |
| ✅ PASS | legal deliveries | non-final over with fewer legal balls than balls_per_over (`short_over_mid_innings`) | 0 |  |
| 🟡 WARN | player identity | player name without a Register id (fallback id used) (`identity_unresolved`) | 17 | `9000060 · Stonebridge Wolves · T Dunson` |
| ✅ PASS | player identity | one person_id appears under several names (`identity_multi_name`) | 0 |  |
| ✅ PASS | player identity | batter/non-striker not in batting XI (check replacements) (`batter_not_in_xi`) | 0 |  |
| ✅ PASS | team identity | bowler not in bowling XI (and not a listed replacement) (`bowler_not_in_xi`) | 0 |  |
| ✅ PASS | team identity | innings batting team not one of the match teams (`innings_team`) | 0 |  |
| ✅ PASS | match identity | winner is not one of the teams (`winner_team`) | 0 |  |
| ✅ PASS | match identity | match missing gender/format/date/teams (`match_required`) | 0 |  |
| ✅ PASS | dismissal consistency | player out is neither batter nor non-striker (`player_out_on_ball`) | 0 |  |
| ✅ PASS | dismissal consistency | bowler-credited dismissal of the non-striker (`bowler_kind_non_striker`) | 0 |  |
| ✅ PASS | dismissal consistency | same batter dismissed twice in one innings (`dismissed_twice`) | 0 |  |
| ✅ PASS | dismissal consistency | bowled/lbw/caught on a wide (impossible) (`wicket_on_wide_kind`) | 0 |  |
| ✅ PASS | dismissal consistency | bowled/lbw/caught/stumped on a no-ball (impossible) (`wicket_on_noball_kind`) | 0 |  |
| ✅ PASS | fielder references | caught/stumped without a named fielder (`fielder_required`) | 0 |  |
| ✅ PASS | fielder references | non-substitute fielder not in fielding XI (`fielder_not_in_xi`) | 0 |  |
| 🟡 WARN | fielder references | catches whose wicketkeeper status could not be inferred (`keeper_unresolved`) | 468 | `9000674:1:26 · L Wexson` |
| ✅ PASS | target/chase | observed target != first-innings total + 1 without a DLS-type method (`target_mismatch`) | 0 |  |
| ✅ PASS | target/chase | chasing side reached target but is not recorded as winner (`chase_result`) | 0 |  |
| ✅ PASS | target/chase | chase continued after the target was reached (`chase_overshoot`) | 0 |  |
| ✅ PASS | target/chase | required rate inconsistent with runs required / balls remaining (`context_required_rate`) | 0 |  |
