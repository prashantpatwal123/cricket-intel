"""Provider-neutral live event contract (Phase 5).

Every source of match events, whether a genuine live feed in future or the historical Cricsheet replay today, implements
`LiveProvider` and emits `Event`s. The match-state engine consumes only these events. It never reads a completed
scorecard, so the same engine can run on a real feed.

Event kinds (payload fields in KINDS below):
  match_meta       teams, competition, format, gender, venue, date, scheduled overs, toss. Never the result.
  playing_xi       squads as announced (where the provider has them)
  innings_start    innings number, batting/bowling team, super_over flag, target (if chasing), penalty runs carried in
  target_revision  revised target/overs (rain rules). Applies from the delivery after it in the log.
  interruption     play suspended/resumed (informational; does not change state)
  pre_ball         who is about to face/bowl the next delivery: striker, non-striker, bowler. Identity only, no outcome.
  delivery         one ball (legal or not): over, index in over, batter, non-striker, bowler, runs split, boundary flag,
                   wickets on that ball
  correction       op=update|retract|insert against an earlier delivery (by event_id)
  innings_end      innings closed (all out, overs done, target reached, declared, abandoned)
  match_end        result text, winner, method. Only ever emitted after the last delivery.

Real-world feed problems and how the contract handles them (see docs/architecture/live-data-contract.md):
  duplicates            identical event_id twice → ignored; same id with different content → first kept, anomaly logged
  out-of-order/delayed  deliveries are ordered by `order` (innings, over, index[, sub…]), never by arrival
  corrected scores      correction/update replaces the delivery; state is recomputed from the last checkpoint before it
  changed attribution   same: the wicket payload of the delivery is replaced
  retractions           correction/retract removes a delivery that should not exist
  missing ball inserted correction/insert with `after_event_id`: ordered immediately after that delivery
  abandoned matches     match_end with result 'no result'/'abandoned' at any point; innings_end reason 'abandoned'
  super overs           innings_start with super_over=True; ball limit 6, 2 wickets end it
  revised targets       target_revision events
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Iterator, Protocol

KINDS = {
    "match_meta": {"teams", "competition", "format", "gender", "venue", "date", "scheduled_overs"},
    "playing_xi": {"teams"},
    "innings_start": {"innings", "batting_team", "bowling_team", "super_over"},
    "target_revision": {"innings", "target_runs", "target_overs"},
    "interruption": {"status"},
    "pre_ball": {"innings", "striker", "non_striker", "bowler"},
    "delivery": {"innings", "over", "index", "batter", "non_striker", "bowler", "runs"},
    "correction": {"op", "target_event_id"},
    "innings_end": {"innings", "reason"},
    "match_end": {"result"},
}
RUN_KEYS = ("batter", "wides", "noballs", "byes", "legbyes", "penalty")

# Dismissal kinds: which count as a team wicket, and which are credited to the bowler. Provider-neutral vocabulary.
NOT_TEAM_WICKET = {"retired hurt", "retired not out"}
BOWLER_CREDITED = {"bowled", "caught", "lbw", "stumped", "caught and bowled", "hit wicket"}

# Fields a pre_ball event may carry. Anything else would leak the outcome of the coming delivery.
PRE_BALL_FIELDS = {"innings", "striker", "non_striker", "bowler"}


@dataclass(frozen=True)
class Event:
    event_id: str
    match_id: str
    kind: str
    payload: dict = field(hash=False, compare=True)
    seq: int = 0                      # provider sequence (arrival order); NOT used for cricket ordering

    def __post_init__(self):
        if self.kind not in KINDS:
            raise ValueError(f"unknown event kind {self.kind!r}")
        missing = KINDS[self.kind] - set(self.payload)
        if missing:
            raise ValueError(f"{self.kind} event {self.event_id} missing {sorted(missing)}")
        if self.kind == "pre_ball" and set(self.payload) - PRE_BALL_FIELDS:
            raise ValueError(f"pre_ball may only carry identities, got {sorted(set(self.payload) - PRE_BALL_FIELDS)}")
        if self.kind == "delivery":
            r = self.payload["runs"]
            if set(r) - set(RUN_KEYS) or any(not isinstance(r.get(k, 0), int) or r.get(k, 0) < 0 for k in RUN_KEYS):
                raise ValueError(f"bad runs in {self.event_id}: {r}")

    def digest(self) -> str:
        return hashlib.sha256(json.dumps([self.kind, self.payload], sort_keys=True, default=str).encode()).hexdigest()[:16]


def delivery_order(p: dict) -> tuple:
    """Cricket order of a delivery: innings, over, index within the over, then any insertion sub-keys."""
    return (p["innings"], p["over"], p["index"], *p.get("sub", ()))


class LiveProvider(Protocol):
    """What any source of match events must offer. `upto` bounds what is fetched: a provider must not read beyond it."""

    match_id: str

    def events(self, upto: int | None = None) -> Iterator[Event]:
        """Events in arrival order, stopping after the `upto`-th delivery (1-based) plus the pre_ball for the next one."""
        ...
