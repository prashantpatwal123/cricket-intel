"""Compare V2: two players side by side. Never one arbitrary score.

For each dimension (scoring, survival, boundaries, dot-ball avoidance, match states …) both values, both samples, the
difference and a verdict: "A leads", "B leads" or "too close to call". A lead needs the difference to clear a two-sided
test at 0.05 divided by the number of dimensions compared (Bonferroni), so a dozen comparisons don't manufacture leads.
Rates use per-ball variance (strike rate, economy) or binomial variance (dismissals, boundaries, dots, wickets).
Also: career timeline by year, records each holds and peer percentiles (each player against their own peer pool).
The fan judges; CRICINTEL does not crown anyone.
"""
from __future__ import annotations

import math

from ..db import DB
from ..analytics import fingerprint as FP
from ..analytics.entities import names
from . import kg, records2

BAT_SQL = """
SELECT count(*) FILTER (WHERE faced) AS n, sum(runs_batter) FILTER (WHERE faced) AS r, sum(runs_batter * runs_batter) FILTER (WHERE faced) AS r2,
       count(*) FILTER (WHERE faced AND (is_four OR is_six)) AS bnd, count(*) FILTER (WHERE faced AND runs_batter = 0) AS dots,
       {splits}
FROM balls WHERE batter_id = ? AND format_group = ?
"""
BOWL_SQL = """
SELECT count(*) FILTER (WHERE legal) AS n, sum(runs_batter + wides + noballs) AS r, sum((runs_batter + wides + noballs) * (runs_batter + wides + noballs)) AS r2,
       count(*) FILTER (WHERE legal AND runs_total = 0) AS dots, count(*) FILTER (WHERE is_four OR is_six) AS bnd,
       {splits}
FROM balls WHERE bowler_id = ? AND format_group = ?
"""
SPLITS = [("powerplay", "phase = 'powerplay'", "Powerplay"), ("middle", "phase = 'middle'", "Middle overs"), ("death", "phase = 'death'", "Death overs"),
          ("chasing", "coalesce(chasing, false)", "Chasing"), ("setting", "NOT coalesce(chasing, false)", "Batting first" ),
          ("set", "batter_balls_before >= 30", "After 30 balls")]


def _splits(bat: bool) -> str:
    cnt = "faced" if bat else "legal"
    val = "runs_batter" if bat else "(runs_batter + wides + noballs)"
    parts = []
    for k, cond, _ in SPLITS:
        if not bat and k == "set":
            cond = "batter_stage = 'set'"
        parts.append(f"count(*) FILTER (WHERE {cnt} AND {cond}) AS {k}_n, sum({val}) FILTER (WHERE {cond}) AS {k}_r, "
                     f"sum({val} * {val}) FILTER (WHERE {cond}) AS {k}_r2")
    return ",\n       ".join(parts)


def _mean(r, r2, n, scale):
    if not n:
        return None, None
    m = r / n
    var = max(1e-9, r2 / n - m * m)
    return scale * m, scale * math.sqrt(var / n)


def _prop(k, n, scale=100.0):
    if not n:
        return None, None
    p = k / n
    return scale * p, scale * math.sqrt(max(1e-9, p * (1 - p)) / n)


def _verdict(a, sa, b, sb, higher_better, alpha):
    if a is None or b is None:
        return "not comparable", None
    se = math.sqrt(sa * sa + sb * sb)
    z = (a - b) / se if se else 0
    p = math.erfc(abs(z) / math.sqrt(2))
    if p >= alpha:
        return "too close to call", round(p, 4)
    a_lead = (a > b) == higher_better
    return ("A leads" if a_lead else "B leads"), round(p, 4)


def _outs(db, pid, fmt, bowler):
    if bowler:
        return db.q1("SELECT count(*) AS k FROM dis WHERE bowler_id = ? AND bowler_credited AND format_group = ?", [pid, fmt])["k"]
    return db.q1("SELECT count(*) AS k FROM dis WHERE player_out_id = ? AND counts_as_dismissal AND format_group = ?", [pid, fmt])["k"]


def compare(db: DB, a: str, b: str, fmt: str | None = None, role: str | None = None) -> dict:
    nm = names(db)
    ra, rb = kg.role(db, a), kg.role(db, b)
    role = role or ("bowling" if ra["primary"] == "bowler" and rb["primary"] == "bowler" else "batting")
    bowler = role == "bowling"
    col = "bowler_id" if bowler else "batter_id"
    cnt = "legal" if bowler else "faced"
    avail = {}
    for p in (a, b):
        for r in db.q(f"SELECT format_group AS f, count(*) FILTER (WHERE {cnt}) AS n FROM balls WHERE {col} = ? AND format_group IN ('T20','ODI') GROUP BY 1", [p]):
            avail.setdefault(r["f"], {})[p] = r["n"]
    if not fmt:
        fmt = max(avail, key=lambda f: min(avail[f].get(a, 0), avail[f].get(b, 0)), default=None)
    if not fmt or not avail.get(fmt, {}).get(a) or not avail.get(fmt, {}).get(b):
        return {"available": False, "reason": f"both players need {role} in the same format to compare", "formats": avail}
    sql = (BOWL_SQL if bowler else BAT_SQL).format(splits=_splits(not bowler))
    A, B = db.q1(sql, [a, fmt]), db.q1(sql, [b, fmt])
    ga = db.q1("SELECT genders FROM player_profile WHERE person_id = ?", [a])["genders"][0]
    gb = db.q1("SELECT genders FROM player_profile WHERE person_id = ?", [b])["genders"][0]
    oa, ob = _outs(db, a, fmt, bowler), _outs(db, b, fmt, bowler)
    dims = []

    def add(key, group, label, va, vb, higher_better, unit, na, nb, nunit, note=""):
        dims.append(dict(key=key, group=group, label=label, a=va, b=vb, higher_better=higher_better, unit=unit, a_n=na, b_n=nb, n_unit=nunit, note=note))

    if not bowler:
        add("sr", "Scoring", "Strike rate", _mean(A["r"], A["r2"], A["n"], 100), _mean(B["r"], B["r2"], B["n"], 100), True, "runs / 100 balls", A["n"], B["n"], "balls")
        add("survival", "Survival", "Dismissals per 100 balls", _prop(oa, A["n"]), _prop(ob, B["n"]), False, "per 100 balls", A["n"], B["n"], "balls",
            f"balls per dismissal: {A['n'] / oa:.0f} v {B['n'] / ob:.0f}" if oa and ob else "")
        add("bnd", "Boundaries", "Boundary %", _prop(A["bnd"], A["n"]), _prop(B["bnd"], B["n"]), True, "% of balls", A["n"], B["n"], "balls")
        add("dots", "Dot-ball avoidance", "Dot-ball %", _prop(A["dots"], A["n"]), _prop(B["dots"], B["n"]), False, "% of balls", A["n"], B["n"], "balls")
        for k, _c, lab in SPLITS:
            if A[f"{k}_n"] >= 60 and B[f"{k}_n"] >= 60:
                add(k, "Match states", f"Strike rate: {lab.lower()}", _mean(A[f"{k}_r"], A[f"{k}_r2"], A[f"{k}_n"], 100),
                    _mean(B[f"{k}_r"], B[f"{k}_r2"], B[f"{k}_n"], 100), True, "runs / 100 balls", A[f"{k}_n"], B[f"{k}_n"], "balls")
    else:
        add("econ", "Scoring conceded", "Economy", _mean(A["r"], A["r2"], A["n"], 6), _mean(B["r"], B["r2"], B["n"], 6), False, "runs / over", A["n"], B["n"], "legal balls")
        add("wkts", "Wickets", "Wickets per 100 balls", _prop(oa, A["n"]), _prop(ob, B["n"]), True, "per 100 balls", A["n"], B["n"], "legal balls",
            f"balls per wicket: {A['n'] / oa:.1f} v {B['n'] / ob:.1f}" if oa and ob else "")
        add("dots", "Dot balls", "Dot-ball %", _prop(A["dots"], A["n"]), _prop(B["dots"], B["n"]), True, "% of balls", A["n"], B["n"], "legal balls")
        add("bnd", "Boundaries conceded", "Boundary % conceded", _prop(A["bnd"], A["n"]), _prop(B["bnd"], B["n"]), False, "% of balls", A["n"], B["n"], "legal balls")
        for k, _c, lab in SPLITS:
            if A[f"{k}_n"] >= 60 and B[f"{k}_n"] >= 60:
                add(k, "Match states", f"Economy: {lab.lower() if k != 'set' else 'v set batters'}", _mean(A[f"{k}_r"], A[f"{k}_r2"], A[f"{k}_n"], 6),
                    _mean(B[f"{k}_r"], B[f"{k}_r2"], B[f"{k}_n"], 6), False, "runs / over", A[f"{k}_n"], B[f"{k}_n"], "legal balls")
    alpha = 0.05 / max(1, len(dims))
    leads = {"A": [], "B": [], "tied": []}
    for d in dims:
        (va, sa), (vb, sb) = d["a"], d["b"]
        v, p = _verdict(va, sa, vb, sb, d["higher_better"], alpha)
        d.update(a=round(va, 2) if va is not None else None, a_se=round(sa, 3) if sa else None, b=round(vb, 2) if vb is not None else None,
                 b_se=round(sb, 3) if sb else None, verdict=v, p=p)
        leads["A" if v == "A leads" else "B" if v == "B leads" else "tied"].append(d["label"])
    # timeline
    tbl, idc = ("bowl_innings", "bowler_id") if bowler else ("bat_innings", "batter_id")
    tl = {}
    for p in (a, b):
        if bowler:
            rows = db.q(f"SELECT year, sum(wickets) AS v, sum(balls) AS balls, sum(runs) AS runs FROM {tbl} WHERE {idc} = ? AND format_group = ? GROUP BY 1 ORDER BY 1", [p, fmt])
            tl[p] = [{"year": r["year"], "value": r["v"], "rate": round(6 * r["runs"] / r["balls"], 2) if r["balls"] else None, "balls": r["balls"]} for r in rows]
        else:
            rows = db.q(f"SELECT year, sum(runs) AS v, sum(balls) AS balls FROM {tbl} WHERE {idc} = ? AND format_group = ? GROUP BY 1 ORDER BY 1", [p, fmt])
            tl[p] = [{"year": r["year"], "value": r["v"], "rate": round(100 * r["v"] / r["balls"], 1) if r["balls"] else None, "balls": r["balls"]} for r in rows]
    # peer percentiles: each against their own peer pool
    pct = {}
    for p in (a, b):
        fp = FP.bowling_fingerprint(db, p, fmt) if bowler else FP.fingerprint(db, p, fmt)
        pct[p] = {d["key"]: d["percentile"] for d in fp.get("dimensions", []) if d["enough_sample"]} if fp.get("available") else {}
        pct[p]["_pool"] = fp.get("peer_pool", {}).get("definition")
    pdims = [d for d in (FP.BOWL_DIMS if bowler else FP.DIMS) if d[0] not in ("bowler_conc", "route_conc")]
    return {"available": True, "role": role, "format": fmt, "formats": avail,
            "players": [{"pid": a, "name": nm.get(a, a), "gender": ga, "outs": oa, "balls": A["n"]}, {"pid": b, "name": nm.get(b, b), "gender": gb, "outs": ob, "balls": B["n"]}],
            "dimensions": dims, "leads": leads, "alpha": round(alpha, 4),
            "timeline": {"metric": "wickets" if bowler else "runs", "rate": "economy" if bowler else "strike rate", "a": tl[a], "b": tl[b]},
            "records": {a: records2.held_by(db, a)[:5], b: records2.held_by(db, b)[:5]},
            "percentiles": {"dims": [{"key": d[0], "label": d[1]} for d in pdims], "a": pct[a], "b": pct[b]},
            "gender_note": None if ga == gb else "These players play in different competitions (men's and women's cricket). Raw numbers are shown; "
                                                 "percentiles are each against their own peer pool.",
            "method": __doc__.strip()}
