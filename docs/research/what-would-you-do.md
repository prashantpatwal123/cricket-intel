# "What Would You Do?" — feasibility test

**Verdict: rejected for now.** The data cannot support fair scoring.

## The idea

Show a real match situation and ask the player to choose an approach: ATTACK, ROTATE or PROTECT THE WICKET. Then
score the choice.

## Why it fails on our data

1. **Intent is not recorded.** Cricsheet records outcomes (runs, wicket), not what the batter tried to do. A dot ball
   can be a defended ball, a missed slog or a well-bowled yorker; a single can be a deliberate push or a mistimed drive.
2. **Most outcomes are intent-ambiguous.** Measured on legal balls in our data:

   | Format | Dot (no wicket) | 1–3 runs | 4 or 6 | Wicket |
   |---|---|---|---|---|
   | T20 | 38.5% | 42.5% | 13.5% | 5.7% |
   | ODI | 52.6% | 35.9% | 8.8% | 2.8% |

   Only boundaries are reasonably attributable to attacking intent (≈9–14% of balls), and even those include edges.
   About 80–90% of balls could not be labelled without guessing.
3. **No counterfactual.** Even with intent, judging the "right" choice needs the outcome of the options *not* taken.
   Within one tightly matched situation (T20, death overs, 2–4 down, required rate 9–11: 5,495 balls) the observed
   mix is 20.9% dots, 18.1% boundaries and 7.7% wickets. That mix blends every approach batters chose, so it cannot
   tell us what ATTACK or PROTECT would have yielded.
4. **Fairness.** Scoring the player against the batter's actual result would reward luck of execution, not judgment,
   and would quietly invent an intent label for the historical batter.

## What would make it feasible

Ball-level shot classification (attacking/defensive) from a licensed provider (`delivery_shot.control`, `shot_family`)
plus a validated model of outcome given approach. Both are dormant contracts today. Until then, What Happens Next
(predicting the recorded outcome) is the honest version of this game.
