"""Typed filter grammar shared by the UI, the records engine and Ask Cricket.

Match-level filters apply to innings counts and milestones; ball-level filters (phase, bowler type,
situation) only apply to ball aggregates. Unknown filter keys are rejected, not ignored.
"""
from __future__ import annotations

from dataclasses import dataclass, fields

MATCH_LEVEL = {"format", "team_type", "competition", "year_from", "year_to", "opposition", "gender", "full_members"}
FULL_MEMBERS = ("India", "Australia", "England", "South Africa", "New Zealand", "Pakistan", "Sri Lanka", "West Indies",
                "Bangladesh", "Zimbabwe", "Ireland", "Afghanistan")
BALL_LEVEL = {"phase", "bowler_family", "bowler_arm", "bowler_style", "chasing", "bowler_id", "batter_id", "over_from", "over_to",
              "wk_from", "wk_to", "faced_from", "faced_to", "rrr_from", "innings_no"}


@dataclass
class Filters:
    format: str | None = None          # T20 | ODI | Test | MDM
    team_type: str | None = None       # international | club
    competition: str | None = None
    year_from: int | None = None
    year_to: int | None = None
    opposition: str | None = None      # team the player was playing against
    gender: str | None = None
    full_members: bool | None = None   # internationals between ICC full members, plus all league matches
    phase: str | None = None           # powerplay | middle | death
    bowler_family: str | None = None   # pace | spin   (requires metadata; unknowns excluded + counted)
    bowler_arm: str | None = None      # left | right
    bowler_style: str | None = None
    chasing: bool | None = None
    bowler_id: str | None = None
    batter_id: str | None = None
    over_from: int | None = None
    over_to: int | None = None
    wk_from: int | None = None        # wickets down before the ball
    wk_to: int | None = None
    faced_from: int | None = None     # balls the striker had already faced in the innings
    faced_to: int | None = None
    rrr_from: float | None = None     # required run rate (chases only)
    innings_no: int | None = None

    @classmethod
    def parse(cls, d: dict) -> "Filters":
        known = {f.name for f in fields(cls)}
        bad = set(d) - known
        if bad:
            raise ValueError(f"unknown filter(s): {sorted(bad)}")
        kw = {}
        for k, v in d.items():
            if v in (None, "", "all"):
                continue
            if k in ("year_from", "year_to", "over_from", "over_to", "wk_from", "wk_to", "faced_from", "faced_to", "innings_no"):
                v = int(v)
            if k == "rrr_from":
                v = float(v)
            if k in ("chasing", "full_members"):
                v = v in (True, "true", "1", 1)
            kw[k] = v
        return cls(**kw)

    def active(self) -> dict:
        return {f.name: getattr(self, f.name) for f in fields(self) if getattr(self, f.name) is not None}

    def has_ball_level(self) -> bool:
        return any(k in BALL_LEVEL for k in self.active())

    def where(self, perspective: str = "batter", alias: str = "", ball_level: bool = True) -> tuple[str, list]:
        """SQL predicate over `balls`/`dis` columns. perspective decides what 'opposition' means."""
        a = f"{alias}." if alias else ""
        c, p = [], []
        if self.format:
            c.append(f"{a}format_group = ?"); p.append(self.format)
        if self.team_type:
            c.append(f"{a}team_type = ?"); p.append(self.team_type)
        if self.competition:
            c.append(f"{a}competition = ?"); p.append(self.competition)
        if self.gender:
            c.append(f"{a}gender = ?"); p.append(self.gender)
        if self.year_from:
            c.append(f"{a}year >= ?"); p.append(self.year_from)
        if self.year_to:
            c.append(f"{a}year <= ?"); p.append(self.year_to)
        if self.full_members:
            fm = ",".join("'" + t + "'" for t in FULL_MEMBERS)
            c.append(f"({a}team_type = 'club' OR ({a}batting_team IN ({fm}) AND {a}bowling_team IN ({fm})))")
        if self.opposition:
            col = "bowling_team" if perspective == "batter" else "batting_team"
            c.append(f"{a}{col} = ?"); p.append(self.opposition)
        if ball_level:
            for k, col in (("phase", "phase"), ("bowler_family", "bowler_family"), ("bowler_arm", "bowler_arm"),
                           ("bowler_style", "bowler_style"), ("bowler_id", "bowler_id"), ("batter_id", "batter_id")):
                v = getattr(self, k)
                if v is not None:
                    c.append(f"{a}{col} = ?"); p.append(v)
            if self.chasing is not None:
                c.append(f"{a}coalesce(chasing, false) = ?"); p.append(self.chasing)
            if self.over_from is not None:
                c.append(f"{a}over + 1 >= ?"); p.append(self.over_from)  # 1-based, as fans count overs
            if self.over_to is not None:
                c.append(f"{a}over + 1 <= ?"); p.append(self.over_to)
            for k, col, op in (("wk_from", "wickets_before", ">="), ("wk_to", "wickets_before", "<="),
                               ("faced_from", "batter_balls_before", ">="), ("faced_to", "batter_balls_before", "<="),
                               ("rrr_from", "required_rate", ">="), ("innings_no", "innings_no", "=")):
                v = getattr(self, k)
                if v is not None:
                    c.append(f"{a}{col} {op} ?"); p.append(v)
        return (" AND ".join(c) or "TRUE"), p
