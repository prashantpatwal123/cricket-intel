# Live replay validation: engine v Cricsheet's recorded totals

The event-driven engine never reads Cricsheet's innings totals. Here every covered match is replayed event by event
through `HistoricalCricsheetProvider` → `EventLog` → `Engine`. The derived runs (plus any post-innings penalty runs), wickets
and legal balls per innings are then compared with the `innings` table.

Reproduce: `python -m cricintel.live.validate --dataset cricsheet` (full) and `--edge` (rare cases). Raw output:
`live-replay-validation.json`.

## Full run

| Matches | Innings | Deliveries | Mismatches | Time |
|---|---|---|---|---|
| 10,247 | 20,475 | 3,298,987 | **0** | 28 min (1,964 deliveries/s, one provider and replay per match) |

## Rare cases

Real matches containing each case, capped at 25 per case except where noted:

| Case | Matches | Innings | Deliveries | Mismatches |
|---|---|---|---|---|
| retired hurt | 25 | 49 | 10,173 | 0 |
| retired out | 25 | 50 | 5,920 | 0 |
| retired not out | 11 | 22 | 3,965 | 0 |
| obstructing the field | 20 | 42 | 7,297 | 0 |
| timed out | 2 | 4 | 812 | 0 |
| hit the ball twice | 1 | 2 | 243 | 0 |
| stumped | 25 | 50 | 12,561 | 0 |
| run out | 25 | 50 | 10,862 | 0 |
| hit wicket | 25 | 50 | 8,634 | 0 |
| super overs (all covered) | 73 | 298 | 22,360 | 0 |
| D/L revised targets | 100 | 200 | 36,456 | 0 |

Retired hurt and retired not out are not team wickets, and a retired batter can return; the rest are wickets. Run outs and obstructing
the field are not credited to the bowler. Super-over chases use a target derived at the break from the previous super over.
D/L chases use Cricsheet's recorded final target, applied from the start of the chase and labelled in the UI.
