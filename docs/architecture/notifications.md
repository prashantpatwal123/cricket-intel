# Notification architecture: design only (Phase 5)

Nothing is sent. There is no push service, no email and no external integration. `pipeline/cricintel/live/notify.py`
implements the rules as a planner, so volume and behaviour can be measured and tested before any channel exists.

## Event types

| Type | Trigger | Default |
|---|---|---|
| wicket | a team wicket | on |
| milestone | batter 50/100/150/200; bowler 5 wickets | on |
| record_approach | a covered-data record comes within reach (Record Watch "record" items). Wording says "covered data, not an official record". | off |
| unusual_event | dot run or big over at/above the 99th percentile; wicket burst (Phase 4 collapse rule) | off |
| battle_begins | a striker–bowler pairing begins whose covered history passes the Right Now bar | off |

## Rules

1. **Dedupe:** each (type, key) at most once per match.
2. **Priority:** wicket > milestone > record_approach > unusual_event > battle_begins.
3. **Coalesce:** several candidates on one ball give one notification (the highest priority, with the others inside it).
4. **Per-over cap:** at most one per over, except wickets.
5. **Innings budget:** at most 8 non-wicket notifications per innings. Wickets always send and never use the budget.
6. **Quiet window:** after a non-wicket notification, record, unusual and battle items wait 12 legal balls.
7. **No ball-by-ball buzz:** a delivery with no qualifying candidate produces nothing.
8. **Spoiler-safe by construction:** candidates come from the same causal state as the Match Centre.

## Measured volume (planner run over whole real matches)

| Match | Balls | Default opt-in | All types | Breakdown, all types |
|---|---|---|---|---|
| Pakistan v India, MCG 2022 | 251 | 17 | 20 | 14 wickets, 3 milestones, 2 records, 1 battle |
| IPL 2023 final | 216 | 10 | 15 | 8 wickets, 2 milestones, 5 battles |
| WPL 2026 final | 246 | 10 | 22 | 7 wickets, 3 milestones, 3 records, 3 unusual, 6 battles |
| Women's World Cup 2025 final | 591 | 19 | 32 | 16 wickets, 1 milestone, 1 unusual, 14 battles |
| Men's World Cup 2023 final | 569 | 18 | 29 | 13 wickets, 4 milestones, 12 battles |
| MI v Kings XI Punjab 2020 | 269 | 15 | 23 | 13 wickets, 2 milestones, 1 unusual, 7 battles |
| Women's T20 World Cup 2026 final | 235 | 9 | 16 | 7 wickets, 2 milestones, 1 record, 6 battles |

A bug found while measuring: the innings budget originally counted wickets. In wicket-heavy innings it then blocked
milestones (Shan Masood's 50 at the MCG was suppressed). Wickets are now excluded from the budget, and all three MCG
fifties come through.

Tests (`test_phase5_live.py`): no duplicate keys, the budget is respected, fewer notifications than balls ÷ 5, and the plan is deterministic.

## Before any real delivery

- A licence for live data, and the Cricsheet licence question resolved.
- User consent and per-type opt-in UI, with quiet hours.
- A delivery service with idempotency keys (`type|key|match`).
- Correction handling: a notified wicket that a correction later retracts needs a follow-up "correction" message. The planner currently runs on the final ordered log.
