"""Partnership Intelligence. Partnerships are DERIVED from consecutive deliveries with the same pair at the crease
(analytics/context.py). Every result links to the actual partnerships (Innings Story) and deliveries.
"""
from __future__ import annotations

from ..db import DB
from .stats import Z90, mean_diff

PAIR_MIN_INNINGS = 8
PAIR_MIN_BALLS = 240
PARTNER_MIN_BALLS = {"T20": 120, "ODI": 200}


def _scope(gender, fmt, team_type, alias="p") -> tuple[str, list]:
    w, p = [f"{alias}.format_group IN ('T20','ODI')"], []
    for col, v in (("gender", gender), ("format_group", fmt), ("team_type", team_type)):
        if v:
            w.append(f"{alias}.{col} = ?"); p.append(v)
    return " AND ".join(w), p


def _names(db: DB, ids) -> dict:
    ids = list({i for i in ids if i})
    if not ids:
        return {}
    return {r["person_id"]: r["name"] for r in db.q(f"SELECT person_id, name FROM player_profile WHERE person_id IN ({','.join('?' * len(ids))})", ids)}


def best_pairs(db: DB, gender: str = "male", fmt: str | None = None, team_type: str | None = None, sort: str = "runs",
               min_innings: int = PAIR_MIN_INNINGS, min_balls: int = PAIR_MIN_BALLS, phase: str | None = None, limit: int = 20) -> dict:
    w, p = _scope(gender, fmt, team_type)
    order = {"runs": "runs DESC", "run_rate": "run_rate DESC", "average": "average DESC", "innings": "innings DESC, runs DESC"}[sort]
    if phase:  # partnership runs within one phase need ball-level aggregation
        rows = db.q(f"""SELECT least(batter_id, non_striker_id) AS p1, greatest(batter_id, non_striker_id) AS p2,
                count(DISTINCT match_id || ':' || innings_no) AS innings, sum(runs_total) AS runs, count(*) FILTER (WHERE legal) AS balls,
                count(*) FILTER (WHERE is_four OR is_six) AS boundaries, count(*) FILTER (WHERE legal AND runs_total = 0) AS dots,
                count(*) FILTER (WHERE legal AND runs_batter IN (1, 2, 3)) AS rotations,
                sum(runs_batter) FILTER (WHERE batter_id = least(batter_id, non_striker_id)) AS p1_runs,
                sum(runs_batter) FILTER (WHERE batter_id = greatest(batter_id, non_striker_id)) AS p2_runs,
                min(start_date) AS first_date, max(start_date) AS last_date, NULL AS best, 0 AS wickets
              FROM balls p WHERE {w} AND phase = ? GROUP BY 1, 2""", [*p, phase])
    else:
        rows = db.q(f"""SELECT p1, p2, count(*) AS innings, sum(runs) AS runs, sum(balls) AS balls, sum(boundaries) AS boundaries,
                sum(dots) AS dots, sum(rotations) AS rotations, sum(p1_runs) AS p1_runs, sum(p2_runs) AS p2_runs,
                min(start_date) AS first_date, max(start_date) AS last_date, max(runs) AS best,
                count(*) FILTER (WHERE ended = 'wicket') AS wickets
              FROM partnerships p WHERE {w} GROUP BY 1, 2""", p)
    out = []
    for r in rows:
        if r["innings"] < min_innings or r["balls"] < min_balls:
            continue
        r["run_rate"] = round(6 * r["runs"] / r["balls"], 2)
        r["average"] = round(r["runs"] / max(1, r["wickets"]), 1) if r["wickets"] else None
        r["boundary_pct"] = round(100 * r["boundaries"] / r["balls"], 1)
        r["dot_pct"] = round(100 * r["dots"] / r["balls"], 1)
        r["rotation_pct"] = round(100 * r["rotations"] / r["balls"], 1)
        tot = (r["p1_runs"] or 0) + (r["p2_runs"] or 0)
        r["p1_share"] = round(100 * (r["p1_runs"] or 0) / tot, 1) if tot else None
        r["first_date"], r["last_date"] = str(r["first_date"]), str(r["last_date"])
        out.append(r)
    out.sort(key=lambda r: -(r[{"runs": "runs", "run_rate": "run_rate", "average": "average", "innings": "innings"}[sort]] or 0))
    out = out[:limit]
    names = _names(db, [x for r in out for x in (r["p1"], r["p2"])])
    for i, r in enumerate(out, 1):
        r["rank"] = i
        r["p1_name"], r["p2_name"] = names.get(r["p1"], r["p1"]), names.get(r["p2"], r["p2"])
    return {"rows": out, "sort": sort, "filters": {"gender": gender, "format": fmt, "team_type": team_type, "phase": phase},
            "thresholds": f"at least {min_innings} partnerships together and {min_balls} legal balls",
            "definition": "A partnership is every delivery bowled while the same two batters were at the crease (runs include extras). "
                          "Run rate = runs per 6 legal balls. Average = runs per partnership ended by a wicket. Rotation = legal balls "
                          "with 1–3 runs off the bat.", "prov": "DERIVED from OBSERVED deliveries"}


def top_stands(db: DB, gender: str = "male", fmt: str | None = None, team_type: str | None = None, limit: int = 20) -> dict:
    w, p = _scope(gender, fmt, team_type)
    rows = db.q(f"""SELECT partnership_id, match_id, innings_no, part_no, p1, p2, runs, balls, wicket_no, p1_runs, p1_balls, p2_runs, p2_balls,
                           ended, start_date, competition, batting_team, bowling_team, first_over, last_over
                    FROM partnerships p WHERE {w} ORDER BY runs DESC, balls ASC LIMIT ?""", [*p, limit])
    names = _names(db, [x for r in rows for x in (r["p1"], r["p2"])])
    for r in rows:
        r["p1_name"], r["p2_name"] = names.get(r["p1"], r["p1"]), names.get(r["p2"], r["p2"])
        r["start_date"] = str(r["start_date"])
        r["wicket_label"] = f"for the {_ord(r['wicket_no'] + 1)} wicket"
    return {"rows": rows, "definition": "Highest single partnerships (runs incl. extras) in covered data. Not official records."}


def _ord(n: int) -> str:
    return f"{n}{'th' if 10 <= n % 100 <= 20 else {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')}"


def player_partners(db: DB, pid: str, fmt: str | None = None, team_type: str | None = None) -> dict:
    """With whom does this player bat, and does their own scoring change with the partner? Phase-adjusted."""
    avail = db.q("SELECT format_group, count(*) AS n FROM balls WHERE batter_id = ? AND format_group IN ('T20','ODI') GROUP BY 1 ORDER BY n DESC", [pid])
    if not avail:
        return {"available": False, "reason": "no batting in covered data"}
    fmt = fmt or avail[0]["format_group"]
    tt = " AND team_type = ?" if team_type else ""
    p = [pid, fmt] + ([team_type] if team_type else [])
    # Player's own balls, by partner and phase (sum and sum of squares for intervals)
    rows = db.q(f"""SELECT non_striker_id AS partner, phase, year, count(*) AS n, sum(runs_batter) AS s, sum(runs_batter * runs_batter) AS ss
                    FROM balls WHERE batter_id = ? AND format_group = ? AND wides = 0 {tt} GROUP BY 1, 2, 3""", p)
    by_phase: dict[str, list] = {}
    for r in rows:
        x = by_phase.setdefault(r["phase"], [0, 0, 0]); x[0] += r["n"]; x[1] += r["s"]; x[2] += r["ss"]
    phase_sr = {k: v[1] / v[0] for k, v in by_phase.items() if v[0]}
    by_py: dict[tuple, list] = {}
    for r in rows:
        x = by_py.setdefault((r["phase"], r["year"]), [0, 0]); x[0] += r["n"]; x[1] += r["s"]
    # the player's own rate in that phase and year (career stage); falls back to phase only when the cell is thin
    py_sr = {k: v[1] / v[0] for k, v in by_py.items() if v[0] >= 40}
    tot = [sum(v[i] for v in by_phase.values()) for i in range(3)]
    partners: dict[str, dict] = {}
    for r in rows:
        x = partners.setdefault(r["partner"], {"n": 0, "s": 0, "ss": 0, "exp": 0.0})
        x["n"] += r["n"]; x["s"] += r["s"]; x["ss"] += r["ss"]; x["exp"] += r["n"] * py_sr.get((r["phase"], r["year"]), phase_sr.get(r["phase"], 0))
    stands = db.q(f"""SELECT CASE WHEN p1 = ? THEN p2 ELSE p1 END AS partner, count(*) AS innings, sum(runs) AS runs, sum(balls) AS balls,
                             max(runs) AS best, count(*) FILTER (WHERE ended = 'wicket') AS wickets,
                             sum(CASE WHEN p1 = ? THEN p1_runs ELSE p2_runs END) AS my_runs,
                             arg_max(partnership_id, runs) AS best_id, arg_max(match_id, runs) AS best_match, arg_max(innings_no, runs) AS best_inn
                      FROM partnerships WHERE (p1 = ? OR p2 = ?) AND format_group = ? {tt} GROUP BY 1""",
                   [pid, pid, pid, pid, fmt] + ([team_type] if team_type else []))
    names = _names(db, [s["partner"] for s in stands])
    minb = PARTNER_MIN_BALLS[fmt]
    out = []
    for s in stands:
        me = partners.get(s["partner"], {"n": 0, "s": 0, "ss": 0, "exp": 0})
        row = {**s, "partner_name": names.get(s["partner"], s["partner"]), "run_rate": round(6 * s["runs"] / s["balls"], 2) if s["balls"] else None,
               "my_share": round(100 * (s["my_runs"] or 0) / s["runs"], 1) if s["runs"] else None, "my_balls": me["n"],
               "my_sr": round(100 * me["s"] / me["n"], 1) if me["n"] else None, "enough_sample": me["n"] >= minb}
        if me["n"] >= minb:
            # vs the player's balls with everyone else, and vs a phase-adjusted expectation
            others_n, others_s, others_ss = tot[0] - me["n"], tot[1] - me["s"], tot[2] - me["ss"]
            d = mean_diff(me["s"], me["ss"], me["n"], others_s, others_ss, others_n)
            row["sr_with_others"] = round(100 * others_s / others_n, 1) if others_n else None
            row["diff_vs_others"] = {k: (round(100 * v, 1) if isinstance(v, float) and k != "p" else v) for k, v in d.items()}
            row["phase_adjusted_expected_sr"] = round(100 * me["exp"] / me["n"], 1)
            row["vs_phase_adjusted"] = round(row["my_sr"] - row["phase_adjusted_expected_sr"], 1)
            lo, hi = row["diff_vs_others"].get("lo"), row["diff_vs_others"].get("hi")
            row["clear"] = lo is not None and (lo > 0 or hi < 0) and abs(row["vs_phase_adjusted"]) >= 8
        row["evidence"] = {"batter_id": pid, "non_striker_id": s["partner"], "format": fmt, **({"team_type": team_type} if team_type else {})}
        row["best_link"] = {"match_id": row.pop("best_match"), "innings_no": row.pop("best_inn")}
        out.append(row)
    out.sort(key=lambda r: -r["runs"])
    best = sorted([r for r in out if r.get("clear") and r["vs_phase_adjusted"] > 0], key=lambda r: -r["vs_phase_adjusted"])
    worse = sorted([r for r in out if r.get("clear") and r["vs_phase_adjusted"] < 0], key=lambda r: r["vs_phase_adjusted"])
    return {"available": True, "format": fmt, "formats": avail, "partners": out[:30], "brings_out_best": best[:5], "quieter_with": worse[:5],
            "overall_sr": round(100 * tot[1] / tot[0], 1) if tot[0] else None, "min_balls": minb,
            "method": f"The player's strike rate on balls they faced with each partner at the other end, compared with (a) their balls with all "
                      f"other partners (Welch 90% interval) and (b) an expectation adjusted for phase and year (their own strike rate in that phase and season, "
                      f"weighted by when they batted with that partner, so career stage and innings phase don't masquerade as partner effects). A partner is listed only with at least {minb} balls, an interval that excludes "
                      f"zero and a phase-adjusted difference of 8+ strike-rate points. Association, not cause: partners also differ in "
                      f"era, opposition and match situation."}
