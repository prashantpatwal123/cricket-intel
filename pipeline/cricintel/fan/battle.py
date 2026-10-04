"""Battle hero (Phase 8): every meeting of a batter and a bowler, and how the battle changed over time.

Every meeting = one row per match in which the batter faced the bowler (balls, runs, out or not, how), oldest first.
How it changed = the meetings split into earlier and later halves by balls faced (descriptive only: two numbers and their
samples, with a note when either half is under 60 balls). No winner is declared.
"""
from __future__ import annotations

from ..db import DB
from ..analytics.stats import wilson


def meetings(db: DB, bat: str, bowl: str) -> dict:
    rows = db.q("""SELECT b.match_id, any_value(b.innings_no) AS innings_no, min(b.start_date) AS date, any_value(b.competition) AS competition,
                          any_value(b.format_group) AS format, any_value(b.batting_team) AS team, any_value(b.bowling_team) AS opp,
                          count(*) FILTER (WHERE b.wides = 0) AS balls, sum(b.runs_batter) AS runs,
                          count(*) FILTER (WHERE b.is_four) AS fours, count(*) FILTER (WHERE b.is_six) AS sixes
                   FROM balls b WHERE b.batter_id = ? AND b.bowler_id = ? GROUP BY b.match_id ORDER BY date, b.match_id""", [bat, bowl])
    outs = {r["match_id"]: r for r in db.q("""SELECT match_id, kind, delivery_id, batter_runs_before FROM dis WHERE player_out_id = ? AND bowler_id = ?
                                              AND bowler_credited""", [bat, bowl])}
    for r in rows:
        o = outs.get(r["match_id"])
        r["date"] = str(r["date"])
        r["out"] = bool(o)
        r["how"] = o["kind"] if o else None
        r["out_delivery"] = o["delivery_id"] if o else None
        r["href"] = f"/innings/{r['match_id']}/{r['innings_no']}/{bat}"
    # earlier v later halves by balls
    total = sum(r["balls"] for r in rows)
    half, acc, early, late = total / 2, 0, [], []
    for r in rows:
        (early if acc < half else late).append(r)
        acc += r["balls"]

    def agg(lst):
        b = sum(x["balls"] for x in lst); ru = sum(x["runs"] for x in lst); o = sum(1 for x in lst if x["out"])
        lo, hi = wilson(o, b) if b else (None, None)
        return {"meetings": len(lst), "balls": b, "runs": ru, "outs": o, "sr": round(100 * ru / b, 1) if b else None,
                "from": lst[0]["date"][:4] if lst else None, "to": lst[-1]["date"][:4] if lst else None,
                "balls_per_out": round(b / o, 1) if o else None, "out_rate_interval_90": [round(100 * lo, 2), round(100 * hi, 2)] if lo is not None else None}
    change = {"earlier": agg(early), "later": agg(late)} if len(rows) >= 4 else None
    if change:
        small = min(change["earlier"]["balls"], change["later"]["balls"]) < 60
        change["note"] = ("Each half has under 60 balls: treat any difference as noise." if small else
                          "Two halves of the same battle, split by balls faced. A difference describes what happened; it is not a trend forecast.")
    return {"rows": rows, "change": change, "count": len(rows)}
