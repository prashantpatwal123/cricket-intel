# Live-data adapter contract (Phase 5)

CRICINTEL has no licensed live feed. The Historical Live Lab replays completed Cricsheet matches through the pipeline
a live feed would use. Nothing downstream of the provider knows it is reading history. Code: `pipeline/cricintel/live/`.

```
LiveProvider ──events──▶ EventLog ──ordered deliveries──▶ Engine (fold, one ball at a time) ──state──▶ Right Now / Record Watch /
 (Cricsheet replay today;   (dedupe, ordering,              checkpoints every over, state hash        Timeline / Battle / Prediction
  a vendor feed later)       corrections)                                                              ──▶ API at cursor N ──▶ Match Centre
```

## Event kinds (`contract.py`)

| Kind | Required payload | Notes |
|---|---|---|
| `match_meta` | teams, competition, format, gender, venue, date, scheduled_overs | Never the result. Toss included (known before play). |
| `playing_xi` | teams → players | Where the provider has it. |
| `innings_start` | innings, batting_team, bowling_team, super_over | Carries target/target_overs for a chase, plus penalty runs brought in. |
| `target_revision` | innings, target_runs, target_overs, optional `after_event_id` | Rain rules. Applies from the delivery it follows. |
| `interruption` | status | Informational; does not change state. |
| `pre_ball` | innings, striker, non_striker, bowler | **Identities only.** The constructor rejects any other field, so an outcome cannot ride along. |
| `delivery` | innings, over, index, batter, non_striker, bowler, runs{batter, wides, noballs, byes, legbyes, penalty}, boundary, wickets[] | One ball, legal or not. |
| `correction` | op = update · retract · insert, target_event_id | `update` replaces fields; `retract` removes; `insert` adds a delivery immediately after the target. |
| `innings_end` | innings, reason | all out · overs complete · target reached · declared · abandoned |
| `match_end` | result | Only ever after the last delivery. |

Dismissal vocabulary is provider-neutral:
- Retired hurt and retired not out are not team wickets.
- Bowled, caught, lbw, stumped, caught and bowled, and hit wicket are credited to the bowler.

## Real-world feed problems

| Problem | Handling | Test |
|---|---|---|
| Duplicate events | Same `event_id` and same content is ignored. Same id with different content keeps the first and logs an anomaly. | `test_conflicting_duplicate_keeps_first_and_records_anomaly`, `test_out_of_order_and_duplicate_arrival_gives_identical_state` |
| Out-of-order / delayed | Deliveries are ordered by cricket position `(innings, over, index[, insert sub-keys])`, never by arrival. | `test_out_of_order_…` (5 shuffles plus 8 duplicates each give an identical hash) |
| Corrected scores | `correction/update`; state recomputed from the nearest checkpoint before the change. | `test_update_correction_matches_a_log_that_was_right_first_time` |
| Changed dismissal attribution | `correction/update` of the wickets payload. | `test_changed_dismissal_attribution` |
| Phantom ball | `correction/retract`. | `test_retract_and_insert` |
| Missed ball | `correction/insert` after an anchor. | `test_retract_and_insert` |
| Delivery before its innings_start | A placeholder innings plus a recorded anomaly; no crash. | `test_bad_events_are_rejected` |
| Super overs | `innings_start.super_over`: 6-ball limit, 2 wickets end it, excluded from statistics (Cricsheet: "super overs don't count towards statistics"). | Engine tests, plus all 73 covered super-over matches reconcile |
| Revised targets | `target_revision`; Cricsheet's final D/L target is applied from the start of the chase and labelled as such. | `test_revised_target_applies_from_its_position`, plus 100 D/L matches reconcile |
| Abandoned / no result | `innings_end(reason=abandoned)` and `match_end(result=no result)`. | Contract supports it; the Cricsheet replay emits Cricsheet's result |

## Determinism, checkpoints, hashes (`engine.py`)

- **Same ordered log, same state:** `replay(log)` is a pure fold. `state_hash` is a SHA-256 of the canonical JSON state.
- **Checkpoints after every over:** a deep copy of the state after each sixth legal ball.
- **Recompute from a checkpoint:** `recompute(log, prev)` finds the first ordered position whose delivery changed. It restores the latest checkpoint at or before that position and re-applies only from there.
  - Tested: equal to a full replay.
  - Benchmark (MCG): 24 ms and 35 deliveries re-applied, against 60 ms for a full replay. Hashes are identical.

## The historical Cricsheet provider (`cricsheet_provider.py`)

Spoiler safety is enforced where data is read, not by hiding things in the UI:
- **Bounded reads:** rows come from a match-sorted copy of the raw deliveries, `LIMIT cursor`, extended incrementally. The provider never holds a row past the highest cursor requested (tested).
- **Next ball:** read for identity only (who faces, who bowls), exactly what a live "new batter / new over" message carries.
- **Raw facts only:** the precomputed scoreboard columns (`score_before`, `required_rate` and so on) and the match result are never read for events. The engine derives everything.
- **Innings boundaries:** `innings_end` and the next `innings_start` (with its target) are emitted straight after the last ball of an innings, when a live feed would send them.
- **Super-over chases:** the target, which Cricsheet does not store, is derived from the previous super over at the break.

## Spoiler-safe API (`service.py`, `/api/live/...`)

| Endpoint | Returns |
|---|---|
| `GET /api/live/featured` | Neutral descriptions only: no results, scores or "famous finish" words. |
| `GET /api/live/{id}?cursor=N` | The state after ball N. Every number is derived from balls 1..N, and every historical comparison uses matches before this one. |
| `GET /api/live/{id}/seek?cursor=N&to=` | A cursor number only. |
| `GET /api/live/{id}/play?cursor=N&pick=X` | Exactly one more ball. |
| `GET /api/live/{id}/ask?q=&cursor=N` | Match Ask, resolved at ball N, limited to matches before this one. |

Leakage tests:
- **Engine** (`test_phase5_engine.py`): state at N is unchanged when every later delivery is mutated, and equal to a log that never contained them.
- **Service** (`test_phase5_live.py`):
  - No later delivery id, no result text and no match length appear in any response before the end.
  - A fresh replay at N equals a long-running replay truncated to N.
  - The provider never reads past the cursor.
- **Browser** (`scripts/screenshots-phase5.mjs`): every `/api/live` response the page received is scanned against the full delivery order. The result was 0 leaks.

## Migrating to a genuine live feed

Implement `LiveProvider.events()` for the vendor and map its messages to these kinds. Its own ids become `event_id`, and its corrections become `correction` events. Nothing downstream changes. What a vendor integration would still need:
- Authentication and back-pressure.
- Reconciliation against an end-of-day scorecard (the `validate.py` pattern).
- A licence.
