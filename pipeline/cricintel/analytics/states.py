"""Innings-state analysis: WHEN DOES A PLAYER CHANGE?

For each state dimension (balls already faced, wickets down, setting/chasing, chase state, phase; and for bowlers:
batter stage, defending, spell over, wickets down, phase) we report the player's numbers in each bucket next to
  * the player's own baseline (all their balls in the same format), and
  * peers in the same bucket (same gender and format; batters also in the same batting-position band),
plus the "relative change": (player bucket − player baseline) − (peer bucket − peer baseline). That separates a
genuine personal pattern from something every player does (everyone scores faster at the death).
All numbers are OBSERVED aggregates; intervals are 90%. Buckets under MIN_N balls are flagged, not hidden.
"""
from __future__ import annotations

import math
from functools import lru_cache

from ..db import DB
from .stats import Z90, wilson

MIN_N = {"T20": 60, "ODI": 100}

BAT_DIMS = [
    ("balls_faced", "Balls already faced", ["1–10", "11–20", "21–30", "31–50", "51+"],
     "CASE WHEN batter_balls_before < 10 THEN '1–10' WHEN batter_balls_before < 20 THEN '11–20' WHEN batter_balls_before < 30 THEN '21–30' "
     "WHEN batter_balls_before < 50 THEN '31–50' ELSE '51+' END",
     {"1–10": {"faced_to": 9}, "11–20": {"faced_from": 10, "faced_to": 19}, "21–30": {"faced_from": 20, "faced_to": 29},
      "31–50": {"faced_from": 30, "faced_to": 49}, "51+": {"faced_from": 50}}),
    ("wickets", "Wickets down when batting", ["0–2", "3–5", "6+"],
     "CASE WHEN wickets_before <= 2 THEN '0–2' WHEN wickets_before <= 5 THEN '3–5' ELSE '6+' END",
     {"0–2": {"wk_to": 2}, "3–5": {"wk_from": 3, "wk_to": 5}, "6+": {"wk_from": 6}}),
    ("innings", "Setting a target or chasing", ["setting", "chasing"],
     "CASE WHEN coalesce(chasing, false) THEN 'chasing' ELSE 'setting' END",
     {"setting": {"chasing": False}, "chasing": {"chasing": True}}),
    ("chase_state", "Chasing: against the required rate", ["ahead", "around", "behind"], "chase_state",
     {"ahead": {"chase_state": "ahead"}, "around": {"chase_state": "around"}, "behind": {"chase_state": "behind"}}),
    ("phase", "Phase of the innings", ["powerplay", "middle", "death"], "phase",
     {"powerplay": {"phase": "powerplay"}, "middle": {"phase": "middle"}, "death": {"phase": "death"}}),
]

BOWL_DIMS = [
    ("batter_stage", "Batter at the crease", ["new", "settling", "set"], "batter_stage",
     {"new": {"batter_stage": "new"}, "settling": {"batter_stage": "settling"}, "set": {"batter_stage": "set"}}),
    ("defending", "Bowling first or defending", ["bowling first", "defending"],
     "CASE WHEN coalesce(chasing, false) THEN 'defending' ELSE 'bowling first' END",
     {"bowling first": {"chasing": False}, "defending": {"chasing": True}}),
    ("chase_state", "Defending: batting side against the required rate", ["ahead", "around", "behind"], "chase_state",
     {"ahead": {"chase_state": "ahead"}, "around": {"chase_state": "around"}, "behind": {"chase_state": "behind"}}),
    ("spell_over", "Over of the spell", ["1st", "2nd", "3rd", "4th+"],
     "CASE WHEN so.k = 1 THEN '1st' WHEN so.k = 2 THEN '2nd' WHEN so.k = 3 THEN '3rd' ELSE '4th+' END", {}),
    ("wickets", "Wickets down", ["0–2", "3–5", "6+"],
     "CASE WHEN wickets_before <= 2 THEN '0–2' WHEN wickets_before <= 5 THEN '3–5' ELSE '6+' END",
     {"0–2": {"wk_to": 2}, "3–5": {"wk_from": 3, "wk_to": 5}, "6+": {"wk_from": 6}}),
    ("phase", "Phase of the innings", ["powerplay", "middle", "death"], "phase",
     {"powerplay": {"phase": "powerplay"}, "middle": {"phase": "middle"}, "death": {"phase": "death"}}),
]

BANDS = {"top": (1, 3), "middle": (4, 7), "lower": (8, 11)}


def phrase(key: str, bucket: str, role: str = "batting") -> str:
    """Plain-English state description, e.g. 'in the middle overs', 'on balls 21–30 of their innings'."""
    return {"balls_faced": f"on balls {bucket} of their innings", "wickets": f"with {bucket} wickets down",
            "innings": "when setting a target" if bucket == "setting" else ("when chasing" if bucket == "chasing" else
                       ("when defending a target" if bucket == "defending" else "when bowling first")),
            "defending": "when defending a target" if bucket == "defending" else "when bowling first",
            "chase_state": f"when the chase is {bucket} of the required rate", "phase": f"in the {bucket} overs",
            "batter_stage": f"to {bucket} batters" if bucket != "set" else "to set batters", "spell_over": f"in the {bucket} over of a spell"}.get(key, bucket)


def _band(pos: int | None) -> str:
    if pos is None:
        return "top"
    return "top" if pos <= 3 else "middle" if pos <= 7 else "lower"


def _bat_sql(dims, where: str) -> str:
    sets = ", ".join(f"({k})" for k, *_ in dims)
    cols = ", ".join(f"{expr} AS {k}" for k, _, _, expr, _ in dims)
    return f"""
      WITH b AS (SELECT {cols}, runs_batter AS r, wides, is_four, is_six,
                        (x.delivery_id IS NOT NULL) AS out
                 FROM balls LEFT JOIN (SELECT delivery_id, player_out_id FROM dis WHERE counts_as_dismissal) x
                   ON x.delivery_id = balls.delivery_id AND x.player_out_id = balls.batter_id
                 WHERE {where} AND wides = 0)
      SELECT {", ".join(k for k, *_ in dims)}, {", ".join(f"grouping({k}) AS g_{k}" for k, *_ in dims)}, count(*) AS n, sum(r) AS s, sum(r * r) AS ss, count(*) FILTER (WHERE out) AS outs,
             count(*) FILTER (WHERE is_four OR is_six) AS bnd, count(*) FILTER (WHERE r = 0) AS dots
      FROM b GROUP BY GROUPING SETS ({sets}, ())"""


def _bowl_sql(dims, where: str) -> str:
    sets = ", ".join(f"({k})" for k, *_ in dims)
    cols = ", ".join(f"{expr} AS {k}" for k, _, _, expr, _ in dims)
    return f"""
      WITH so AS (SELECT match_id, innings_no, bowler_id, over,
                         row_number() OVER (PARTITION BY match_id, innings_no, bowler_id, spell_no ORDER BY over) AS k FROM spells),
      b AS (SELECT {cols}, runs_batter + wides + noballs AS r, legal, runs_total, is_four, is_six,
                   coalesce(w.n, 0) AS wk
            FROM balls JOIN so USING (match_id, innings_no, bowler_id, over)
            LEFT JOIN (SELECT delivery_id, count(*) AS n FROM wickets WHERE bowler_credited GROUP BY 1) w USING (delivery_id)
            WHERE {where})
      SELECT {", ".join(k for k, *_ in dims)}, {", ".join(f"grouping({k}) AS g_{k}" for k, *_ in dims)}, count(*) FILTER (WHERE legal) AS n, sum(r) AS s, sum(r * r) AS ss, sum(wk) AS outs,
             count(*) FILTER (WHERE is_four OR is_six) AS bnd, count(*) FILTER (WHERE legal AND r = 0) AS dots
      FROM b GROUP BY GROUPING SETS ({sets}, ())"""


def _agg(rows, dims) -> dict:
    out = {}
    for r in rows:
        grouped = [k for k, *_ in dims if r[f"g_{k}"] == 0]
        if not grouped:
            out[("all", "all")] = r
        elif r[grouped[0]] is not None:
            out[(grouped[0], r[grouped[0]])] = r
    return out


@lru_cache(maxsize=64)
def _peer(db: DB, role: str, fmt: str, gender: str, team_type: str | None, band: str | None) -> dict:
    where = "format_group = ? AND gender = ?" + (" AND team_type = ?" if team_type else "")
    p = [fmt, gender] + ([team_type] if team_type else [])
    if role == "batting":
        lo, hi = BANDS[band]
        where += f" AND batter_position BETWEEN {lo} AND {hi}"
        rows = db.q(_bat_sql(BAT_DIMS, where), p)
        return _agg(rows, BAT_DIMS)
    return _agg(db.q(_bowl_sql(BOWL_DIMS, where), p), BOWL_DIMS)


def _metrics(r: dict | None, role: str) -> dict | None:
    if not r or not r["n"]:
        return None
    n = r["n"]
    m = r["s"] / n
    var = max(1e-9, (r["ss"] - n * m * m) / (n - 1)) if n > 1 else None
    se = math.sqrt(var / n) if var else None
    lo, hi = wilson(r["outs"], n)
    if role == "batting":
        return {"balls": n, "runs": r["s"], "strike_rate": round(100 * m, 1),
                "sr_interval": [round(100 * (m - Z90 * se), 1), round(100 * (m + Z90 * se), 1)] if se else None,
                "outs": r["outs"], "outs_per_100": round(100 * r["outs"] / n, 2), "outs_interval": [round(100 * lo, 2), round(100 * hi, 2)],
                "boundary_pct": round(100 * r["bnd"] / n, 1), "dot_pct": round(100 * r["dots"] / n, 1)}
    return {"balls": n, "runs": r["s"], "economy": round(6 * m, 2),
            "econ_interval": [round(6 * (m - Z90 * se), 2), round(6 * (m + Z90 * se), 2)] if se else None,
            "wickets": r["outs"], "wkts_per_100": round(100 * r["outs"] / n, 2), "wkts_interval": [round(100 * lo, 2), round(100 * hi, 2)],
            "boundary_pct": round(100 * r["bnd"] / n, 1), "dot_pct": round(100 * r["dots"] / n, 1)}


def states(db: DB, pid: str, role: str = "batting", fmt: str | None = None, team_type: str | None = None) -> dict:
    col = "batter_id" if role == "batting" else "bowler_id"
    unit = "legal balls" if role == "bowling" else "balls faced"
    avail = db.q(f"""SELECT format_group, count(*) AS n FROM balls WHERE {col} = ? AND format_group IN ('T20','ODI')
                     GROUP BY 1 ORDER BY n DESC""", [pid])
    if not avail:
        return {"available": False, "reason": f"no {role} in covered data"}
    fmt = fmt or avail[0]["format_group"]
    gender = db.q1("SELECT genders FROM player_profile WHERE person_id = ?", [pid])["genders"][0]
    where = f"{col} = ? AND format_group = ?" + (" AND team_type = ?" if team_type else "")
    p = [pid, fmt] + ([team_type] if team_type else [])
    dims = BAT_DIMS if role == "batting" else BOWL_DIMS
    band = None
    if role == "batting":
        pos = db.q1(f"SELECT mode(batter_position) AS p FROM balls WHERE {where}", p)
        band = _band(pos["p"] if pos else None)
        me = _agg(db.q(_bat_sql(dims, where), p), dims)
    else:
        me = _agg(db.q(_bowl_sql(dims, where), p), dims)
    peer = _peer(db, role, fmt, gender, team_type, band)
    main = "strike_rate" if role == "batting" else "economy"
    risk = "outs_per_100" if role == "batting" else "wkts_per_100"
    base, pbase = _metrics(me.get(("all", "all")), role), _metrics(peer.get(("all", "all")), role)
    groups = []
    for key, label, order, _expr, ev in dims:
        rows = []
        for b in order:
            m, pm = _metrics(me.get((key, b)), role), _metrics(peer.get((key, b)), role)
            if not m:
                rows.append({"bucket": b, "player": None, "peer": pm})
                continue
            rel, clear, expected = None, False, None
            if pm and base and pbase:
                rel = {main: round((m[main] - base[main]) - (pm[main] - pbase[main]), 2),
                       risk: round((m[risk] - base[risk]) - (pm[risk] - pbase[risk]), 2)}
                # what we'd expect if the player changed exactly as peers do; "clear" if their interval excludes it
                expected = round(base[main] + (pm[main] - pbase[main]), 2)
                iv = m["sr_interval" if role == "batting" else "econ_interval"]
                if iv:  # ~20 buckets are tested per player, so "clear" uses a 99% interval, not the displayed 90%
                    mid, half = (iv[0] + iv[1]) / 2, (iv[1] - iv[0]) / 2 * (2.576 / Z90)
                    clear = (expected < mid - half or expected > mid + half) and m["balls"] >= 2 * MIN_N[fmt]
            rows.append({"bucket": b, "player": m, "peer": pm, "vs_own": round(m[main] - base[main], 2) if base else None,
                         "vs_peer": round(m[main] - pm[main], 2) if pm else None, "relative_change": rel,
                         "expected_if_typical": expected, "clear": clear,
                         "small_sample": m["balls"] < MIN_N[fmt],
                         "evidence": ({col: pid, "format": fmt, **({"team_type": team_type} if team_type else {}), **ev[b]}) if b in ev else None})
        groups.append({"key": key, "label": label, "rows": rows, "ordered": key in ("balls_faced", "wickets", "phase", "spell_over", "batter_stage")})
    # Biggest personal changes (relative to peers), only between buckets with enough sample
    moves = []
    for g in groups:
        ok = [r for r in g["rows"] if r.get("player") and not r["small_sample"] and r.get("relative_change") and r.get("clear")]
        for r in ok:
            moves.append({"group": g["label"], "key": g["key"], "bucket": r["bucket"], "phrase": phrase(g["key"], r["bucket"], role),
                          "relative": r["relative_change"][main], "balls": r["player"]["balls"]})
    moves.sort(key=lambda x: -abs(x["relative"]))
    return {"available": True, "role": role, "format": fmt, "formats": avail, "gender": gender, "band": band, "baseline": base,
            "peer_baseline": pbase, "groups": groups, "biggest_changes": moves[:4], "main_metric": main, "risk_metric": risk, "unit": unit,
            "min_sample": MIN_N[fmt],
            "peer_definition": (f"{'women' if gender == 'female' else 'men'}'s {fmt} batters batting {band}-order "
                                f"({BANDS[band][0]}–{BANDS[band][1]})" if role == "batting" else
                                f"all {'women' if gender == 'female' else 'men'}'s {fmt} bowlers") + (f", {team_type} only" if team_type else "") +
                               " in our covered data",
            "method": "Relative change = (player in state − player overall) − (peers in state − peers overall). Positive strike-rate change "
                      "means the player gains more than typical in that state. 'Clear' = the player's 99% interval in that state (stricter because ~20 states are tested) excludes "
                      "the value expected if they changed exactly as peers do. Buckets under the minimum sample are flagged; only clear changes "
                      "with at least twice the minimum sample are listed as the biggest changes."}
