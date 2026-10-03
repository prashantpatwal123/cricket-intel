"""Cricket Fingerprint: how a batter plays, measured on dimensions the event data genuinely supports.

Every dimension is computed by ONE SQL aggregation used for both the player and the peer pool, so definitions
can't drift. Peers = batters of the same gender in the same format group with >= PEER_MIN balls faced in
the scope. Percentiles describe *style* ("more boundaries than 84% of peers"), not quality.
No shot, line, length or field-position dimensions exist, because the data doesn't contain them.
"""
from __future__ import annotations

from functools import lru_cache

from ..db import DB
from .stats import percentile_rank, wilson

PEER_MIN = {"T20": 500, "ODI": 800}
DIM_MIN = {"T20": 60, "ODI": 100}  # min balls inside a dimension's subset before it is shown

AGG_SQL = """
WITH b AS (
  SELECT batter_id AS pid, faced, runs_batter AS r, is_four, is_six, phase, chasing, required_rate, wickets_before,
         batter_balls_before AS bb, format_group, gender
  FROM balls WHERE format_group = ? AND gender = ? {extra}
), o AS (
  SELECT x.player_out_id AS pid, x.phase, x.chasing, x.required_rate, x.wickets_before, x.batter_balls_before AS bb,
         x.bowler_id, x.route, x.striker_out
  FROM dis x WHERE x.counts_as_dismissal AND x.format_group = ? AND x.gender = ? {extra_dis}
), bat AS (
  SELECT pid,
    count(*) FILTER (WHERE faced) AS balls, sum(r) AS runs,
    count(*) FILTER (WHERE faced AND r = 0) AS dots, count(*) FILTER (WHERE is_four) AS fours,
    count(*) FILTER (WHERE is_six) AS sixes,
    count(*) FILTER (WHERE faced AND phase = 'powerplay') AS pp_b, sum(r) FILTER (WHERE phase = 'powerplay') AS pp_r,
    count(*) FILTER (WHERE faced AND phase = 'middle') AS mid_b, sum(r) FILTER (WHERE phase = 'middle') AS mid_r,
    count(*) FILTER (WHERE faced AND phase = 'death') AS death_b, sum(r) FILTER (WHERE phase = 'death') AS death_r,
    count(*) FILTER (WHERE faced AND chasing) AS ch_b, sum(r) FILTER (WHERE chasing) AS ch_r,
    count(*) FILTER (WHERE faced AND NOT coalesce(chasing, false)) AS set_b, sum(r) FILTER (WHERE NOT coalesce(chasing, false)) AS set_r,
    count(*) FILTER (WHERE faced AND wickets_before <= 2) AS top_b, sum(r) FILTER (WHERE wickets_before <= 2) AS top_r,
    count(*) FILTER (WHERE faced AND chasing AND required_rate >= ?) AS pr_b, sum(r) FILTER (WHERE chasing AND required_rate >= ?) AS pr_r,
    count(*) FILTER (WHERE faced AND bb >= 30) AS a30_b, sum(r) FILTER (WHERE bb >= 30) AS a30_r,
    count(*) FILTER (WHERE faced AND bb < 30) AS b30_b
  FROM b GROUP BY 1
), outs AS (
  SELECT pid, count(*) AS outs,
    count(*) FILTER (WHERE chasing AND required_rate >= ?) AS pr_o,
    -- innings-stage dimensions use only dismissals while on strike (bb is the striker's balls faced)
    count(*) FILTER (WHERE bb >= 30 AND striker_out) AS a30_o, count(*) FILTER (WHERE bb < 30 AND striker_out) AS b30_o
  FROM o GROUP BY 1
), conc AS (
  SELECT pid, sum(n) FILTER (WHERE rk <= 3) AS top3_bowler_outs, sum(n) AS credited_outs FROM (
    SELECT pid, bowler_id, count(*) AS n, row_number() OVER (PARTITION BY pid ORDER BY count(*) DESC) AS rk
    FROM o WHERE route NOT IN ('RUN_OUT', 'OTHER', 'RETIRED_NOT_OUT') GROUP BY 1, 2) GROUP BY 1
), rconc AS (
  SELECT pid, max(n) AS top_route_outs, arg_max(route, n) AS top_route FROM (
    SELECT pid, route, count(*) AS n FROM o GROUP BY 1, 2) GROUP BY 1
)
SELECT bat.*, coalesce(outs.outs, 0) AS outs, coalesce(pr_o, 0) AS pr_o, coalesce(a30_o, 0) AS a30_o,
       coalesce(b30_o, 0) AS b30_o, coalesce(top3_bowler_outs, 0) AS top3_bowler_outs,
       coalesce(credited_outs, 0) AS credited_outs, coalesce(top_route_outs, 0) AS top_route_outs, top_route
FROM bat LEFT JOIN outs USING (pid) LEFT JOIN conc USING (pid) LEFT JOIN rconc USING (pid)
"""

PRESSURE_RRR = {"T20": 10.0, "ODI": 7.0}


def _sr(r, b):
    return 100.0 * (r or 0) / b if b else None


# key, label, group, value fn, sample fn, unit, description, evidence filters
DIMS = [
    ("sr", "Scoring rate", "Tempo", lambda a: _sr(a["runs"], a["balls"]), lambda a: a["balls"], "SR",
     "Runs per 100 balls faced", {}),
    ("boundary_pct", "Boundary frequency", "Tempo", lambda a: 100 * (a["fours"] + a["sixes"]) / a["balls"] if a["balls"] else None,
     lambda a: a["balls"], "% of balls", "4s and 6s per ball faced", {}),
    ("six_pct", "Six frequency", "Tempo", lambda a: 100 * a["sixes"] / a["balls"] if a["balls"] else None,
     lambda a: a["balls"], "% of balls", "Sixes per ball faced", {}),
    ("dot_pct", "Dot-ball rate", "Tempo", lambda a: 100 * a["dots"] / a["balls"] if a["balls"] else None,
     lambda a: a["balls"], "% of balls", "Balls faced with no run off the bat", {}),
    ("out_rate", "Dismissal frequency", "Survival", lambda a: 100 * a["outs"] / a["balls"] if a["balls"] else None,
     lambda a: a["balls"], "outs / 100 balls", "Dismissals per 100 balls faced (incl. run-outs)", {}),
    ("pp_sr", "Powerplay scoring", "Phase", lambda a: _sr(a["pp_r"], a["pp_b"]), lambda a: a["pp_b"], "SR",
     "Strike rate in powerplay overs", {"phase": "powerplay"}),
    ("mid_sr", "Middle-overs scoring", "Phase", lambda a: _sr(a["mid_r"], a["mid_b"]), lambda a: a["mid_b"], "SR",
     "Strike rate in middle overs", {"phase": "middle"}),
    ("death_sr", "Death-overs scoring", "Phase", lambda a: _sr(a["death_r"], a["death_b"]), lambda a: a["death_b"], "SR",
     "Strike rate in death overs", {"phase": "death"}),
    ("chase_sr", "Chasing", "Situation", lambda a: _sr(a["ch_r"], a["ch_b"]), lambda a: a["ch_b"], "SR",
     "Strike rate in second-innings chases", {"chasing": True}),
    ("set_sr", "Setting a target", "Situation", lambda a: _sr(a["set_r"], a["set_b"]), lambda a: a["set_b"], "SR",
     "Strike rate batting first", {"chasing": False}),
    ("top_sr", "0–2 wickets down", "Situation", lambda a: _sr(a["top_r"], a["top_b"]), lambda a: a["top_b"], "SR",
     "Strike rate when 0–2 wickets have fallen", {"wk_to": 2}),
    ("pressure_sr", "Under chase pressure", "Situation", lambda a: _sr(a["pr_r"], a["pr_b"]), lambda a: a["pr_b"], "SR",
     "Strike rate when the required rate is high", {"chasing": True, "rrr_from": "PRESSURE"}),
    ("after30_sr", "Once set (30+ balls)", "Innings stage", lambda a: _sr(a["a30_r"], a["a30_b"]), lambda a: a["a30_b"], "SR",
     "Strike rate after facing 30 balls in the innings", {"faced_from": 30}),
    ("after30_out", "Survival once set", "Innings stage", lambda a: 100 * a["a30_o"] / a["a30_b"] if a["a30_b"] else None,
     lambda a: a["a30_b"], "outs / 100 balls", "Dismissal rate after facing 30 balls", {"faced_from": 30}),
    ("early_out", "Early-innings vulnerability", "Innings stage", lambda a: 100 * a["b30_o"] / a["b30_b"] if a["b30_b"] else None,
     lambda a: a["b30_b"], "outs / 100 balls", "Dismissal rate in the first 30 balls of an innings", {"faced_to": 29}),
    ("bowler_conc", "Matchup concentration", "Concentration",
     lambda a: 100 * a["top3_bowler_outs"] / a["credited_outs"] if a["credited_outs"] >= 10 else None,
     lambda a: a["credited_outs"], "% of outs", "Share of bowler-credited dismissals taken by their 3 most frequent dismissers", {}),
    ("route_conc", "Dismissal concentration", "Concentration",
     lambda a: 100 * a["top_route_outs"] / a["outs"] if a["outs"] >= 10 else None,
     lambda a: a["outs"], "% of outs", "Share of dismissals that happen in their single most common way", {}),
]


@lru_cache(maxsize=32)
def _peers(db: DB, fmt: str, gender: str, team_type: str | None) -> dict:
    extra = " AND team_type = ?" if team_type else ""
    p = [fmt, gender] + ([team_type] if team_type else [])
    rr = PRESSURE_RRR.get(fmt, 10.0)
    sql = AGG_SQL.format(extra=extra, extra_dis=extra.replace("team_type", "x.team_type"))
    rows = db.q(sql, [*p, *p, rr, rr, rr])
    return {r["pid"]: r for r in rows}


def fingerprint(db: DB, pid: str, fmt: str | None = None, team_type: str | None = None) -> dict:
    prof = db.q1("SELECT genders FROM player_profile WHERE person_id = ?", [pid])
    if not prof:
        return {"available": False, "reason": "unknown player"}
    gender = prof["genders"][0]
    avail = db.q("""SELECT format_group, count(*) FILTER (WHERE faced) AS balls FROM balls WHERE batter_id = ?
                    AND format_group IN ('T20','ODI') GROUP BY 1 ORDER BY balls DESC""", [pid])
    if not avail:
        return {"available": False, "reason": "no batting in covered data"}
    fmt = fmt or avail[0]["format_group"]
    peers = _peers(db, fmt, gender, team_type)
    me = peers.get(pid)
    if not me or not me["balls"]:
        return {"available": False, "reason": f"no {fmt} batting", "formats": avail}
    pool = {k: v for k, v in peers.items() if v["balls"] >= PEER_MIN[fmt]}
    dims = []
    for key, label, group, val, samp, unit, desc, ev in DIMS:
        n = samp(me) or 0
        v = val(me)
        minimum = 10 if key in ("bowler_conc", "route_conc") else DIM_MIN[fmt]
        popvals = [x for x in (val(a) for a in pool.values() if (samp(a) or 0) >= minimum) if x is not None]
        ok = v is not None and n >= minimum
        evidence = {k2: (PRESSURE_RRR[fmt] if v2 == "PRESSURE" else v2) for k2, v2 in ev.items()}
        dim = {"key": key, "label": label, "group": group, "unit": unit, "description": desc, "value": round(v, 2) if v is not None else None,
               "n": n, "n_unit": "outs" if key in ("bowler_conc", "route_conc") else "balls", "enough_sample": ok,
               "min_sample": minimum, "percentile": percentile_rank(v, popvals) if ok else None,
               "peer_median": round(sorted(popvals)[len(popvals) // 2], 2) if popvals else None, "peer_n": len(popvals),
               "evidence": {"format": fmt, **({"team_type": team_type} if team_type else {}), **evidence}, "prov": "OBSERVED aggregate"}
        if key == "route_conc" and ok:
            dim["detail"] = me["top_route"]
        dims.append(dim)
    # one-line interval for the headline rates (shown in WHY)
    lo, hi = wilson(me["outs"], me["balls"])
    return {"available": True, "role": "batting", "format": fmt, "team_type": team_type, "gender": gender, "formats": avail,
            "balls": me["balls"], "runs": me["runs"], "outs": me["outs"], "below_peer_threshold": me["balls"] < PEER_MIN[fmt],
            "peer_pool": {"size": len(pool), "definition": f"{'women' if gender == 'female' else 'men'}'s {fmt} batters in our covered data "
                          f"with >= {PEER_MIN[fmt]} balls faced" + (f" ({team_type})" if team_type else ""),
                          "pressure_rrr": PRESSURE_RRR[fmt]},
            "out_rate_interval_90": [round(100 * lo, 2), round(100 * hi, 2)] if lo is not None else None,
            "dimensions": dims,
            "not_available": ["shot types", "line & length", "pitch map", "fielding positions", "bowler pace/spin (metadata coverage too low)"]}


# ---------------------------------------------------------------------------------------------- bowling
BOWL_PEER_MIN = {"T20": 480, "ODI": 900}
BOWL_DIM_MIN = {"T20": 60, "ODI": 120}

BOWL_SQL = """
WITH b AS (
  SELECT bowler_id AS pid, legal, runs_batter + wides + noballs AS rc, runs_batter AS r, is_four, is_six, wides, noballs, phase, chasing
  FROM balls WHERE format_group = ? AND gender = ? {extra}
), w AS (
  SELECT bowler_id AS pid, count(*) AS wkts, count(*) FILTER (WHERE kind IN ('bowled', 'lbw')) AS stumps_wkts,
         count(*) FILTER (WHERE phase = 'death') AS death_w, count(*) FILTER (WHERE phase = 'powerplay') AS pp_w
  FROM dis x WHERE bowler_credited AND format_group = ? AND gender = ? {extra_dis} GROUP BY 1
)
SELECT b.pid, count(*) FILTER (WHERE legal) AS balls, sum(rc) AS runs, count(*) FILTER (WHERE legal AND rc = 0) AS dots,
  count(*) FILTER (WHERE is_four OR is_six) AS bnd, count(*) FILTER (WHERE is_six) AS sixes,
  count(*) FILTER (WHERE wides > 0 OR noballs > 0) AS extras_balls,
  count(*) FILTER (WHERE legal AND phase = 'powerplay') AS pp_b, sum(rc) FILTER (WHERE phase = 'powerplay') AS pp_r,
  count(*) FILTER (WHERE legal AND phase = 'middle') AS mid_b, sum(rc) FILTER (WHERE phase = 'middle') AS mid_r,
  count(*) FILTER (WHERE legal AND phase = 'death') AS death_b, sum(rc) FILTER (WHERE phase = 'death') AS death_r,
  count(*) FILTER (WHERE legal AND chasing) AS def_b, sum(rc) FILTER (WHERE chasing) AS def_r,
  coalesce(any_value(w.wkts), 0) AS wkts, coalesce(any_value(w.stumps_wkts), 0) AS stumps_wkts,
  coalesce(any_value(w.death_w), 0) AS death_w, coalesce(any_value(w.pp_w), 0) AS pp_w
FROM b LEFT JOIN w USING (pid) GROUP BY b.pid
"""


def _econ(r, b):
    return 6.0 * (r or 0) / b if b else None


BOWL_DIMS = [
    ("econ", "Economy", "Control", lambda a: _econ(a["runs"], a["balls"]), lambda a: a["balls"], "runs/over",
     "Runs conceded per 6 legal balls (wides and no-balls count against the bowler)", {}),
    ("dot_pct", "Dot-ball rate", "Control", lambda a: 100 * a["dots"] / a["balls"] if a["balls"] else None, lambda a: a["balls"],
     "% of balls", "Legal balls conceding nothing", {}),
    ("bnd_pct", "Boundaries conceded", "Control", lambda a: 100 * a["bnd"] / a["balls"] if a["balls"] else None, lambda a: a["balls"],
     "% of balls", "4s and 6s conceded per legal ball", {}),
    ("extras_pct", "Wides & no-balls", "Control", lambda a: 100 * a["extras_balls"] / a["balls"] if a["balls"] else None,
     lambda a: a["balls"], "per 100 balls", "Deliveries called wide or no-ball per 100 legal balls", {}),
    ("wkt_rate", "Wicket frequency", "Threat", lambda a: 100 * a["wkts"] / a["balls"] if a["balls"] else None, lambda a: a["balls"],
     "wkts / 100 balls", "Bowler-credited wickets per 100 legal balls", {}),
    ("stumps_share", "Attacks the stumps", "Threat", lambda a: 100 * a["stumps_wkts"] / a["wkts"] if a["wkts"] >= 10 else None,
     lambda a: a["wkts"], "% of wkts", "Share of wickets that are bowled or LBW", {}),
    ("pp_econ", "Powerplay economy", "Phase", lambda a: _econ(a["pp_r"], a["pp_b"]), lambda a: a["pp_b"], "runs/over",
     "Economy in powerplay overs", {"phase": "powerplay"}),
    ("mid_econ", "Middle-overs economy", "Phase", lambda a: _econ(a["mid_r"], a["mid_b"]), lambda a: a["mid_b"], "runs/over",
     "Economy in middle overs", {"phase": "middle"}),
    ("death_econ", "Death-overs economy", "Phase", lambda a: _econ(a["death_r"], a["death_b"]), lambda a: a["death_b"], "runs/over",
     "Economy in death overs", {"phase": "death"}),
    ("def_econ", "Defending a target", "Situation", lambda a: _econ(a["def_r"], a["def_b"]), lambda a: a["def_b"], "runs/over",
     "Economy when the batting side is chasing", {"chasing": True}),
]


@lru_cache(maxsize=32)
def _bowl_peers(db: DB, fmt: str, gender: str, team_type: str | None) -> dict:
    extra = " AND team_type = ?" if team_type else ""
    p = [fmt, gender] + ([team_type] if team_type else [])
    return {r["pid"]: r for r in db.q(BOWL_SQL.format(extra=extra, extra_dis=extra), [*p, *p])}


def bowling_fingerprint(db: DB, pid: str, fmt: str | None = None, team_type: str | None = None) -> dict:
    prof = db.q1("SELECT genders FROM player_profile WHERE person_id = ?", [pid])
    gender = prof["genders"][0]
    avail = db.q("""SELECT format_group, count(*) FILTER (WHERE legal) AS balls FROM balls WHERE bowler_id = ?
                    AND format_group IN ('T20','ODI') GROUP BY 1 ORDER BY balls DESC""", [pid])
    if not avail:
        return {"available": False, "reason": "no bowling in covered data"}
    fmt = fmt or avail[0]["format_group"]
    peers = _bowl_peers(db, fmt, gender, team_type)
    me = peers.get(pid)
    if not me or not me["balls"]:
        return {"available": False, "reason": f"no {fmt} bowling", "formats": avail}
    pool = {k: v for k, v in peers.items() if v["balls"] >= BOWL_PEER_MIN[fmt]}
    dims = []
    for key, label, group, val, samp, unit, desc, ev in BOWL_DIMS:
        n = samp(me) or 0
        v = val(me)
        minimum = 10 if key == "stumps_share" else BOWL_DIM_MIN[fmt]
        popvals = [x for x in (val(a) for a in pool.values() if (samp(a) or 0) >= minimum) if x is not None]
        ok = v is not None and n >= minimum
        dims.append({"key": key, "label": label, "group": group, "unit": unit, "description": desc,
                     "value": round(v, 2) if v is not None else None, "n": n, "n_unit": "wkts" if key == "stumps_share" else "balls",
                     "enough_sample": ok, "min_sample": minimum, "percentile": percentile_rank(v, popvals) if ok else None,
                     "peer_median": round(sorted(popvals)[len(popvals) // 2], 2) if popvals else None, "peer_n": len(popvals),
                     "evidence": {"format": fmt, **({"team_type": team_type} if team_type else {}), **ev}, "prov": "OBSERVED aggregate"})
    return {"available": True, "role": "bowling", "format": fmt, "gender": gender, "formats": avail, "balls": me["balls"],
            "wickets": me["wkts"], "runs": me["runs"], "below_peer_threshold": me["balls"] < BOWL_PEER_MIN[fmt],
            "peer_pool": {"size": len(pool), "definition": f"{'women' if gender == 'female' else 'men'}'s {fmt} bowlers in our covered data "
                          f"with >= {BOWL_PEER_MIN[fmt]} legal balls"},
            "dimensions": dims, "not_available": ["line & length", "pace/speed", "bowling type (metadata coverage too low)", "field settings"]}
