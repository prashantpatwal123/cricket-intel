"""Historical baselines for a replayed match, AS OF THE DAY BEFORE IT (Phase 5).

Every number here is computed only from covered matches that started strictly before the replayed match's date, in the
same format and gender, so a replay can never use the future (including the match itself) as "history".
Computed once per match in a handful of batched scans (all players in both squads at once), then cached; the per-ball
work is then pure dictionary lookups, never a scan of the 3.3M-row table.
"""
from __future__ import annotations

import threading
import time

from ..db import DB

STAGES = [("1-10", 0, 9), ("11-30", 10, 29), ("31+", 30, 10_000)]
_CACHE: dict = {}
_LOCK = threading.Lock()


def stage_of(balls_before: int) -> str:
    return next(s for s, lo, hi in STAGES if lo <= balls_before <= hi)


def _stage_sql(col: str) -> str:
    return "CASE " + " ".join(f"WHEN {col} BETWEEN {lo} AND {hi} THEN '{s}'" for s, lo, hi in STAGES) + " END"


def for_match(db: DB, mid: str) -> dict:
    key = (getattr(db, "stamp", None) or id(db), mid)
    with _LOCK:
        if key in _CACHE:
            return _CACHE[key]
    b = _build(db, mid)
    with _LOCK:
        _CACHE[key] = b
        if len(_CACHE) > 48:
            _CACHE.pop(next(iter(_CACHE)))
    return b


def _build(db: DB, mid: str) -> dict:
    t0 = time.perf_counter()
    m = db.q1("SELECT start_date, format_group, gender, competition, team_type FROM matches WHERE match_id = ?", [mid])
    d, fmt, g, comp = str(m["start_date"]), m["format_group"], m["gender"], m["competition"]
    squads: dict = {}
    for r in db.q("SELECT team, person_id FROM live_players WHERE match_id = ?", [mid]):
        squads.setdefault(r["team"], []).append(r["person_id"])
    ids = [p for v in squads.values() for p in v]
    if not ids:
        return {"asof": d, "format": fmt, "gender": g, "competition": comp, "bat": {}, "bowl": {}, "battles": {}, "pairs": {}, "comp": {}, "ref": {}}
    q = ",".join("?" * len(ids))
    W = "b.format_group = ? AND b.gender = ? AND b.start_date < ?::DATE"
    P = [fmt, g, d]

    bat: dict = {}
    for r in db.q(f"""SELECT b.batter_id AS pid, {_stage_sql('b.batter_balls_before')} AS stage, b.phase,
                             count(*) FILTER (WHERE b.faced) AS balls, sum(b.runs_batter) AS runs, count(x.delivery_id) AS outs,
                             count(*) FILTER (WHERE b.faced AND b.runs_batter = 0) AS dots, count(*) FILTER (WHERE b.is_four OR b.is_six) AS bnd
                      FROM balls b LEFT JOIN dis x ON x.delivery_id = b.delivery_id AND x.player_out_id = b.batter_id
                      WHERE b.batter_id IN ({q}) AND {W} GROUP BY ALL""", ids + P):
        e = bat.setdefault(r["pid"], {"all": _z(), "stage": {}, "phase": {}})
        for bucket in (e["all"], e["stage"].setdefault(r["stage"], _z()), e["phase"].setdefault(r["phase"], _z())):
            for k in ("balls", "runs", "outs", "dots", "bnd"):
                bucket[k] += r[k] or 0
    inns = {r["pid"]: r for r in db.q(f"""SELECT batter_id AS pid, count(*) AS innings, max(runs) AS best, count(*) FILTER (WHERE runs >= 50) AS fifties
                                          FROM bat_innings b WHERE batter_id IN ({q}) AND {W} GROUP BY 1""", ids + P)}
    for pid, e in bat.items():
        e["innings"] = inns.get(pid, {})

    bowl: dict = {}
    for r in db.q(f"""SELECT b.bowler_id AS pid, b.phase, count(*) FILTER (WHERE b.legal) AS balls, sum(b.runs_batter + b.wides + b.noballs) AS runs,
                             count(x.delivery_id) AS wkts, count(*) FILTER (WHERE b.legal AND b.runs_batter + b.wides + b.noballs = 0) AS dots,
                             count(*) FILTER (WHERE b.is_four OR b.is_six) AS bnd
                      FROM balls b LEFT JOIN dis x ON x.delivery_id = b.delivery_id AND x.bowler_credited
                      WHERE b.bowler_id IN ({q}) AND {W} GROUP BY ALL""", ids + P):
        e = bowl.setdefault(r["pid"], {"all": _z(), "phase": {}})
        for bucket in (e["all"], e["phase"].setdefault(r["phase"], _z())):
            for k, src in (("balls", "balls"), ("runs", "runs"), ("outs", "wkts"), ("dots", "dots"), ("bnd", "bnd")):
                bucket[k] += r[src] or 0
    spells = {r["pid"]: r for r in db.q(f"""SELECT bowler_id AS pid, count(*) AS innings, max(wickets) AS best_w,
                                                  arg_min(runs, -wickets * 1000 + runs) AS best_r, count(*) FILTER (WHERE wickets >= 4) AS hauls
                                           FROM bowl_innings b WHERE bowler_id IN ({q}) AND {W} GROUP BY 1""", ids + P)}
    for pid, e in bowl.items():
        e["innings"] = spells.get(pid, {})

    battles: dict = {}
    for r in db.q(f"""SELECT b.batter_id AS bat, b.bowler_id AS bowl, count(*) FILTER (WHERE b.faced) AS balls, sum(b.runs_batter) AS runs,
                             count(x.delivery_id) AS outs, count(*) FILTER (WHERE b.faced AND b.runs_batter = 0) AS dots,
                             count(*) FILTER (WHERE b.is_four) AS fours, count(*) FILTER (WHERE b.is_six) AS sixes,
                             count(DISTINCT b.match_id) AS matches, min(b.start_date) AS first, max(b.start_date) AS last
                      FROM balls b LEFT JOIN dis x ON x.delivery_id = b.delivery_id AND x.player_out_id = b.batter_id AND x.bowler_credited
                      WHERE b.batter_id IN ({q}) AND b.bowler_id IN ({q}) AND {W} GROUP BY 1, 2""", ids + ids + P):
        r["first"], r["last"] = str(r["first"]), str(r["last"])
        battles[f"{r['bat']}|{r['bowl']}"] = r

    pairs: dict = {}
    for r in db.q(f"""SELECT least(p1, p2) AS a, greatest(p1, p2) AS b, count(*) AS stands, sum(runs) AS runs, sum(balls) AS balls,
                             max(runs) AS best, count(*) FILTER (WHERE runs >= 50) AS fifties
                      FROM partnerships b WHERE p1 IN ({q}) AND p2 IN ({q}) AND {W} GROUP BY 1, 2""", ids + ids + P):
        pairs[f"{r['a']}|{r['b']}"] = r

    # Competition records within covered data (as of the day before), for Record Watch.
    cw, cp = ("b.competition = ? AND " + W, [comp] + P) if comp else (W, P)
    comp_ref: dict = {"name": comp}
    if comp:
        comp_ref["matches"] = (db.q1(f"SELECT count(*) AS n FROM team_results b WHERE {cw}", cp) or {}).get("n", 0)
        comp_ref["top_total"] = db.q1(f"SELECT max(total_runs) AS v FROM innings i JOIN team_results b USING (match_id) WHERE NOT i.super_over AND {cw}", cp)["v"]
        comp_ref["top_score"] = db.q1(f"SELECT max(runs) AS v FROM bat_innings b WHERE {cw}", cp)["v"]
        comp_ref["top_part"] = {r["w"]: r["v"] for r in db.q(f"SELECT wicket_no AS w, max(runs) AS v FROM partnerships b WHERE {cw} GROUP BY 1", cp)}
        comp_ref["top_part_any"] = max(comp_ref["top_part"].values(), default=None)
        comp_ref["best_wkts"] = db.q1(f"SELECT max(wickets) AS v FROM bowl_innings b WHERE {cw}", cp)["v"]
        comp_ref["runs_board"] = db.q(f"""SELECT batter_id AS pid, sum(runs) AS runs FROM bat_innings b WHERE {cw}
                                          GROUP BY 1 ORDER BY runs DESC LIMIT 25""", cp)
        comp_ref["squad_runs"] = {r["pid"]: r["runs"] for r in db.q(f"SELECT batter_id AS pid, sum(runs) AS runs FROM bat_innings b WHERE batter_id IN ({q}) AND {cw} GROUP BY 1", ids + cp)}
        comp_ref["wkts_board"] = db.q(f"""SELECT bowler_id AS pid, sum(wickets) AS wkts FROM bowl_innings b WHERE {cw}
                                          GROUP BY 1 ORDER BY wkts DESC LIMIT 25""", cp)
        comp_ref["squad_wkts"] = {r["pid"]: r["wkts"] for r in db.q(f"SELECT bowler_id AS pid, sum(wickets) AS wkts FROM bowl_innings b WHERE bowler_id IN ({q}) AND {cw} GROUP BY 1", ids + cp)}

    # Reference distributions for "unusual" statements (same format and gender, before this match).
    ref: dict = {}
    ref["dot_streak_p99"] = db.q1(f"""SELECT quantile_disc(ds, 0.99) AS v, count(*) AS n FROM (SELECT match_id, innings_no, max(team_dot_streak) AS ds
                                      FROM balls b WHERE {W} GROUP BY 1, 2)""", P)
    ref["over_runs_p99"] = db.q1(f"""SELECT quantile_disc(r, 0.99) AS v, count(*) AS n FROM (SELECT match_id, innings_no, over, sum(runs_total) AS r
                                     FROM balls b WHERE {W} GROUP BY 1, 2, 3)""", P)
    # score and wickets at each legal-ball mark, per innings 1/2, for "where this innings stands" comparisons
    pts: dict = {}
    for r in db.q(f"""SELECT innings_no AS i, legal_balls_before AS lb, count(*) AS n, avg(score_before) AS score
                      FROM balls b WHERE {W} AND b.legal AND innings_no <= 2 AND legal_balls_before % 6 = 0 GROUP BY 1, 2""", P):
        pts.setdefault(str(r["i"]), {})[str(r["lb"])] = {"n": r["n"], "score": round(r["score"], 1)}
    ref["score_at"] = pts
    wd: dict = {}
    for r in db.q(f"""SELECT legal_balls_before AS lb, wickets_before AS w, count(*) AS n FROM balls b
                      WHERE {W} AND b.legal AND legal_balls_before % 6 = 0 GROUP BY 1, 2""", P):
        wd.setdefault(str(r["lb"]), {})[str(r["w"])] = r["n"]
    ref["wickets_at"] = wd
    return {"asof": d, "format": fmt, "gender": g, "competition": comp, "squads": squads, "bat": bat, "bowl": bowl, "battles": battles,
            "pairs": pairs, "comp": comp_ref, "ref": ref, "build_ms": round(1000 * (time.perf_counter() - t0))}


def _z() -> dict:
    return {"balls": 0, "runs": 0, "outs": 0, "dots": 0, "bnd": 0}


def sr(x: dict | None) -> float | None:
    return round(100 * x["runs"] / x["balls"], 1) if x and x.get("balls") else None


def econ(x: dict | None) -> float | None:
    return round(6 * x["runs"] / x["balls"], 2) if x and x.get("balls") else None
