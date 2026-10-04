"""Play moments inside stories: a pre-ball state from a real innings, match or battle, opened in the Live Lab replay at
that cursor with the prediction game on ("You are Kohli. India need 31 from 12. What happened next?").

Spoiler safety: a moment is described ONLY with information known before the ball (score, target, balls left, the
batter's runs and balls so far). The link carries a replay cursor; the Phase 5 replay engine never reads past it, so the
next ball is revealed only after the fan's call. Selection is deterministic (the most tense pre-ball state by rule).
"""
from __future__ import annotations

from functools import lru_cache

from ..db import DB
from ..analytics.entities import names


def _nm(db, pid, fb=None):
    return names(db).get(pid, fb or pid)


def cursor(db: DB, mid: str, did: str) -> int | None:
    r = db.q1("""WITH o AS (SELECT delivery_id, row_number() OVER (ORDER BY innings_no, seq) - 1 AS k FROM live_deliveries WHERE match_id = ?)
                 SELECT k FROM o WHERE delivery_id = ?""", [mid, did])
    return r["k"] if r else None


def _tension(b: dict) -> float:
    """Rule for an interesting pre-ball state (pre-ball fields only)."""
    s = 0.0
    if b["chasing"] and b["balls_remaining"] and b["runs_required"] and b["runs_required"] > 0:
        rpb = b["runs_required"] / b["balls_remaining"]
        if b["balls_remaining"] <= 24:
            s += 3 + max(0, 2 - abs(rpb - 1.4) * 2)          # close finish: about 1–2 runs a ball needed
    rb = b["batter_runs_before"] or 0
    if 44 <= rb <= 49 or 94 <= rb <= 99:
        s += 2.5                                                # milestone in sight
    if b["phase"] == "death":
        s += 1
    return s


def _describe(db: DB, b: dict, as_bowler: bool = False) -> str:
    who = _nm(db, b["bowler_id"], b["bowler"]) if as_bowler else _nm(db, b["batter_id"], b["batter"])
    ov = f"{b['legal_balls_before'] // 6}.{b['legal_balls_before'] % 6}"
    if as_bowler:
        lead = f"You are {who}, bowling to {_nm(db, b['batter_id'], b['batter'])} ({b['batter_runs_before']} off {b['batter_balls_before']})."
    else:
        lead = f"You are {who}, on {b['batter_runs_before']} off {b['batter_balls_before']}."
    if b["chasing"] and b["runs_required"] and b["balls_remaining"]:
        ctx = f" {b['batting_team']} need {b['runs_required']} from {b['balls_remaining']}."
    else:
        ctx = f" {b['batting_team']} {b['score_before']}/{b['wickets_before']} after {ov} overs."
    return lead + ctx + " What happened next?"


def _pack(db: DB, b: dict, as_bowler: bool = False) -> dict | None:
    k = cursor(db, b["match_id"], b["delivery_id"])
    if k is None:
        return None
    return {"key": f"{b['match_id']}|{k}", "match_id": b["match_id"], "cursor": k, "title": _describe(db, b, as_bowler),
            "href": f"/live-lab/{b['match_id']}?n={k}&game=1", "date": str(b["start_date"]), "competition": b["competition"],
            "pre_ball": {"score": f"{b['score_before']}/{b['wickets_before']}", "overs": f"{b['legal_balls_before'] // 6}.{b['legal_balls_before'] % 6}",
                         "batter_runs": b["batter_runs_before"], "batter_balls": b["batter_balls_before"],
                         "runs_required": b["runs_required"] if b["chasing"] else None, "balls_remaining": b["balls_remaining"] if b["chasing"] else None},
            "spoiler_safe": True, "prov": "OBSERVED pre-ball state; outcome revealed only after the call"}


COLS = """delivery_id, match_id, innings_no, seq, batter_id, bowler_id, batter, bowler, batting_team, score_before, wickets_before, legal_balls_before,
          batter_runs_before, batter_balls_before, phase, chasing, runs_required, balls_remaining, start_date, competition"""


# per-match reads use the match-sorted live tables (zone maps skip to one match) instead of scanning all deliveries
LIVE = """SELECT l.delivery_id, l.match_id, l.innings_no, l.seq, l.batter_id, l.bowler_id, l.batter, l.bowler, i.batting_team, l.score_before,
          l.wickets_before, l.legal_balls_before, l.batter_runs_before, l.batter_balls_before, l.phase, l.chasing, l.runs_required,
          l.balls_remaining, m.start_date, m.competition
          FROM live_deliveries l JOIN matches m ON m.match_id = l.match_id JOIN innings i ON i.match_id = l.match_id AND i.innings_no = l.innings_no
          WHERE l.match_id = ? AND l.legal"""


@lru_cache(maxsize=4096)
def for_innings(db: DB, mid: str, inn: int, pid: str) -> dict | None:
    rows = db.q(LIVE + " AND l.innings_no = ? AND l.batter_id = ? ORDER BY l.seq", [mid, inn, pid])
    if len(rows) < 8:
        return None
    cands = rows[5:]                                 # never the first few balls: there is no story yet
    best = max(cands, key=lambda b: (_tension(b), -b["seq"]))
    if _tension(best) == 0:
        best = cands[len(cands) * 2 // 3]           # otherwise two-thirds of the way through the innings
    return _pack(db, best)


@lru_cache(maxsize=4096)
def for_match(db: DB, mid: str) -> dict | None:
    rows = db.q(LIVE + " AND l.innings_no = 2 AND l.balls_remaining <= 30 ORDER BY l.seq", [mid])
    if not rows:
        return None
    best = max(rows, key=lambda b: (_tension(b), -b["seq"]))
    return _pack(db, best)


@lru_cache(maxsize=4096)
def for_battle(db: DB, bat: str, bowl: str) -> dict | None:
    rows = db.q(f"""SELECT {COLS} FROM balls WHERE batter_id = ? AND bowler_id = ? AND legal AND batter_balls_before >= 8
                    ORDER BY start_date DESC, seq LIMIT 60""", [bat, bowl])
    if not rows:
        return None
    best = max(rows, key=lambda b: (_tension(b), b["start_date"], -b["seq"]))
    return _pack(db, best, as_bowler=True)


@lru_cache(maxsize=4096)
def for_player(db: DB, pid: str) -> dict | None:
    from . import index
    from .kg import role
    ix = index.get(db)
    b = ix["best_innings15"].get(pid)
    s = (ix["best_spells"].get(pid) or [None])[0]
    if s and (role(db, pid)["primary"] == "bowler" or not b):
        rows = db.q(LIVE + " AND l.innings_no = ? AND l.bowler_id = ? ORDER BY l.seq", [s["match_id"], s["innings_no"], pid])
        if rows:
            best = max(rows[3:] or rows, key=lambda r: (_tension(r), -r["seq"]))
            return _pack(db, best, as_bowler=True)
    if b:
        return for_innings(db, b["match_id"], b["innings_no"], pid)
    return None
