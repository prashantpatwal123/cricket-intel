"""Player intelligence queries. Every block returns sample sizes and provenance."""
from __future__ import annotations

from .graph import TEAM_CANON
from ..db import DB
from .filters import Filters

ROUTES = [
    # route, label, provenance of the route classification, explanation
    ("BOWLED", "Bowled", "OBSERVED", "Ball hit the stumps."),
    ("LBW", "LBW", "OBSERVED", "Leg before wicket."),
    ("CAUGHT_KEEPER", "Caught by wicketkeeper", "DERIVED", "Catcher identified as the fielding side's wicketkeeper by inference (stumpings / keeping record)."),
    ("CAUGHT_BOWLER", "Caught & bowled", "OBSERVED", "Caught by the bowler."),
    ("CAUGHT_FIELDER", "Caught by a fielder", "DERIVED", "Caught by a named fielder who is not the bowler or identified keeper. Fielding position is NOT recorded in the data."),
    ("CAUGHT_KEEPER_STATUS_UNKNOWN", "Caught (keeper status unknown)", "OBSERVED", "Caught by a named fielder; we could not establish whether they were keeping."),
    ("CAUGHT_UNKNOWN_FIELDER", "Caught (fielder not recorded)", "OBSERVED", "Caught; the source names no fielder."),
    ("STUMPED", "Stumped", "OBSERVED", "Stumped by the wicketkeeper."),
    ("RUN_OUT", "Run out", "OBSERVED", "Run out (striker or non-striker)."),
    ("HIT_WICKET", "Hit wicket", "OBSERVED", "Broke own wicket."),
    ("OTHER", "Other", "OBSERVED", "Retired out, obstructing the field, handled the ball, timed out, hit the ball twice."),
]
ROUTE_META = {r[0]: {"label": r[1], "prov": r[2], "explain": r[3]} for r in ROUTES}


def _rate(num, den, mult=1.0, nd=2):
    return round(mult * num / den, nd) if den else None


def _meta_field(p: dict, f: str) -> dict:
    v = p.get(f)
    if v is None:
        return {"value": None, "prov": None, "source": None, "confidence": None, "status": "UNKNOWN"}
    return {"value": v, "prov": p.get(f"{f}_prov"), "source": p.get(f"{f}_source"),
            "confidence": p.get(f"{f}_confidence"), "status": "KNOWN"}


def search(db: DB, q: str, limit: int = 12) -> list[dict]:
    return db.q("""SELECT person_id, name, register_name, matches, genders, teams, role FROM player_profile
                   WHERE person_id = ? OR list_bool_or(list_transform(aliases, a -> a ILIKE ?))
                   ORDER BY matches DESC LIMIT ?""", [q, f"%{q}%", limit])


def featured(db: DB) -> list[dict]:
    """Highest-sample players per gender, for the home screen (purely data-driven)."""
    return db.q("""WITH b AS (SELECT batter_id AS person_id, count(*) FILTER (WHERE faced) AS balls FROM balls GROUP BY 1),
        w AS (SELECT bowler_id AS person_id, count(*) FILTER (WHERE legal) AS bb FROM balls GROUP BY 1)
        SELECT pp.person_id, pp.name, pp.genders, pp.role, pp.matches, coalesce(b.balls,0) AS balls_faced, coalesce(w.bb,0) AS balls_bowled
        FROM player_profile pp LEFT JOIN b USING (person_id) LEFT JOIN w USING (person_id)
        QUALIFY row_number() OVER (PARTITION BY pp.genders[1] ORDER BY coalesce(b.balls,0) + coalesce(w.bb,0) DESC) <= 4
        ORDER BY pp.genders[1], balls_faced + balls_bowled DESC""")


def coverage_breakdown(db: DB, pid: str, f: Filters) -> list[dict]:
    """Per competition/format: what we analysed and what Cricsheet itself says about completeness."""
    wm, pm = f.where("batter", ball_level=False)
    rows = db.q(f"""SELECT CASE WHEN team_type = 'international' THEN (CASE format_group WHEN 'T20' THEN 'T20I' ELSE format_group END)
                               ELSE competition END AS label,
                    team_type, format_group, gender, any_value(batting_team) AS team, count(DISTINCT match_id) AS matches,
                    min(start_date) AS first_date, max(start_date) AS last_date
                    FROM (SELECT m.*, year(m.start_date) AS year, pim.team AS batting_team,
                          CASE WHEN pim.team = m.team1 THEN m.team2 ELSE m.team1 END AS bowling_team
                          FROM players_in_match pim JOIN matches m USING (match_id) WHERE pim.person_id = ?) x
                    WHERE {wm} GROUP BY ALL ORDER BY matches DESC""", [pid, *pm])
    has = getattr(db, "has_source_coverage", False)
    for r in rows:
        r["status"], r["note"] = "UNKNOWN", "Completeness not assessed for this dataset."
        if not has:
            continue
        if r["team_type"] == "club":
            c = db.q1("SELECT have, \"of\", pct FROM source_coverage_pct WHERE scope = 'competition' AND name = ? ORDER BY gender NULLS FIRST LIMIT 1", [r["label"]])
            if c:
                r["status"] = "COMPLETE" if c["have"] == c["of"] else "PARTIAL"
                r["note"] = (f"Cricsheet holds {c['have']} of {c['of']} {r['label']} matches ({c['pct']}%)."
                             + ("" if c["have"] == c["of"] else " Some of this player's matches may be missing."))
        elif r["format_group"] == "ODI":
            n = db.q1("""SELECT count(*) AS n FROM source_missing_matches WHERE match_type = 'Odi' AND gender = ?
                         AND ? IN (team1, team2) AND date::DATE BETWEEN ? AND ?""",
                      [r["gender"], r["team"], r["first_date"], r["last_date"]])["n"]
            r["status"] = "COMPLETE_FOR_TEAM" if n == 0 else "PARTIAL"
            r["note"] = (f"Cricsheet lists {n} {r['team']} ODI{'s' if n != 1 else ''} in this period that it could not source; "
                         "this player may have played in some." if n else
                         f"Cricsheet lists no unsourced {r['team']} ODIs in this period.")
        elif r["format_group"] == "T20":
            r["status"] = "UNKNOWN"
            r["note"] = "Cricsheet does not track missing T20 internationals, so completeness can't be established."
        if r["gender"] == "male" and r["team_type"] == "international":
            r["note"] += " Matches against Afghanistan are withheld by Cricsheet."
    return rows


def batting_innings_sql(f: Filters) -> tuple[str, list]:
    """Per-innings batting lines for one player (match-level filters only)."""
    w, p = f.where("batter", "m", ball_level=False)
    sql = f"""
    WITH me AS (SELECT ?::VARCHAR AS pid),
    mm AS (SELECT m.*, year(m.start_date) AS year, i.innings_no, i.batting_team, i.bowling_team
                FROM matches m JOIN innings i USING (match_id) WHERE NOT i.super_over),
    inn AS (
      SELECT bo.match_id, bo.innings_no, bo.batting_position, m.start_date, m.format_group, m.competition,
             m.batting_team, m.bowling_team
      FROM batting_order bo JOIN mm m ON m.match_id = bo.match_id AND m.innings_no = bo.innings_no
      WHERE bo.person_id = (SELECT pid FROM me) AND {w}
    ),
    b AS (SELECT match_id, innings_no, sum(runs_batter) AS runs, count(*) FILTER (WHERE faced) AS balls,
                 count(*) FILTER (WHERE is_four) AS fours, count(*) FILTER (WHERE is_six) AS sixes
          FROM balls WHERE batter_id = (SELECT pid FROM me) GROUP BY ALL),
    o AS (SELECT match_id, innings_no, bool_or(counts_as_dismissal) AS is_out FROM wickets WHERE player_out_id = (SELECT pid FROM me) GROUP BY ALL)
    SELECT inn.*, coalesce(b.runs,0) AS runs, coalesce(b.balls,0) AS balls, coalesce(b.fours,0) AS fours,
           coalesce(b.sixes,0) AS sixes, coalesce(o.is_out,false) AS is_out
    FROM inn LEFT JOIN b USING (match_id, innings_no) LEFT JOIN o USING (match_id, innings_no)
    """
    return sql, p  # params: [pid, *p]


def profile(db: DB, pid: str, f: Filters) -> dict | None:
    p = db.q1("SELECT * FROM player_profile WHERE person_id = ?", [pid])
    if not p:
        return None
    wm, pm = f.where("batter", ball_level=False)
    # ---- coverage
    cov = db.q1(f"""SELECT count(DISTINCT match_id) AS matches, min(start_date) AS first_date, max(start_date) AS last_date,
                   list(DISTINCT format_group) AS formats
                   FROM (SELECT DISTINCT pim.match_id, m.start_date, m.format_group, m.team_type, m.competition,
                         year(m.start_date) AS year, m.gender, pim.team AS batting_team,
                         CASE WHEN pim.team = m.team1 THEN m.team2 ELSE m.team1 END AS bowling_team
                         FROM players_in_match pim JOIN matches m USING (match_id) WHERE pim.person_id = ?) x
                   WHERE {wm}""", [pid, *pm])
    comps = db.q(f"""SELECT competition, format_group, team_type, count(DISTINCT match_id) AS matches,
                    min(start_date) AS first_date, max(start_date) AS last_date FROM
                    (SELECT m.*, year(m.start_date) AS year, pim.team AS batting_team,
                     CASE WHEN pim.team = m.team1 THEN m.team2 ELSE m.team1 END AS bowling_team
                     FROM players_in_match pim JOIN matches m USING (match_id) WHERE pim.person_id = ?) x
                    WHERE {wm} GROUP BY ALL ORDER BY matches DESC""", [pid, *pm])
    # Left-censoring: first appearance within a year of where the SOURCE's coverage for that format begins
    # (Cricsheet /coverage/ 'earliest provided'). Club competitions use Cricsheet's own completeness instead.
    censored = []
    if getattr(db, "has_source_coverage", False):
        fmt_name = {"ODI": "One-day Internationals", "T20": "T20 Internationals"}
        for c in coverage_breakdown(db, pid, f):
            if c["team_type"] != "international" or c["format_group"] not in fmt_name:
                continue
            per = db.q1("SELECT earliest_provided FROM source_coverage_periods WHERE gender = ? AND name = ?",
                        [c["gender"], fmt_name[c["format_group"]]])
            if per:
                start = db.q1("SELECT strptime(?, '%b %Y')::DATE AS d", [per["earliest_provided"]])["d"]
                if (c["first_date"] - start).days <= 365:
                    censored.append(f"{c['label']} (coverage begins {per['earliest_provided']})")
    notes = []
    if censored:
        notes.append({"kind": "possible_earlier_matches",
                      "text": "This player's first appearance in our data is close to where Cricsheet's coverage begins for "
                              + ", ".join(censored) + ". Earlier matches probably exist, so treat totals as partial."})
    if db.manifest.get("source_id") == "cricsheet" and "male" in (p.get("genders") or []):
        notes.append({"kind": "source_exclusion",
                      "text": "Cricsheet does not publish matches involving the Afghanistan men's team or the Afghanistan Premier League. Those matches are missing."})
    if not p.get("identity_resolved", True):
        notes.append({"kind": "identity", "text": "Some appearances could not be matched to a Register identifier."})

    # ---- batting
    sql, prm = batting_innings_sql(f)
    bat = db.q1(f"""WITH x AS ({sql}) SELECT count(*) AS innings, sum(runs) AS runs, sum(balls) AS balls,
        count(*) FILTER (WHERE is_out) AS outs, count(*) FILTER (WHERE NOT is_out) AS not_outs, max(runs) AS hs,
        arg_max(NOT is_out, runs) AS hs_not_out, count(*) FILTER (WHERE runs >= 50 AND runs < 100) AS fifties,
        count(*) FILTER (WHERE runs >= 100) AS hundreds, count(*) FILTER (WHERE runs = 0 AND is_out) AS ducks,
        sum(fours) AS fours, sum(sixes) AS sixes FROM x""", [pid, *prm])
    if bat and bat["innings"]:
        bat["average"] = _rate(bat["runs"], bat["outs"])
        bat["strike_rate"] = _rate(bat["runs"], bat["balls"], 100)
    # ---- bowling (ball-level, any filters)
    wb, pb = f.where("bowler")
    bowl = db.q1(f"""SELECT count(*) FILTER (WHERE legal) AS balls, sum(runs_batter + wides + noballs) AS runs,
        count(DISTINCT match_id || ':' || innings_no) AS innings,
        (SELECT count(*) FROM dis WHERE bowler_id = ? AND bowler_credited AND {wb}) AS wickets
        FROM balls WHERE bowler_id = ? AND {wb}""", [pid, *pb, pid, *pb])
    if bowl and bowl["balls"]:
        bowl["economy"] = _rate(bowl["runs"], bowl["balls"], 6)
        bowl["average"] = _rate(bowl["runs"], bowl["wickets"])
        bowl["strike_rate"] = _rate(bowl["balls"], bowl["wickets"], 1, 1)
        best = db.q1(f"""SELECT match_id, innings_no, count(*) FILTER (WHERE bowler_credited) AS w
                        FROM dis WHERE bowler_id = ? AND {wb} GROUP BY ALL ORDER BY w DESC LIMIT 1""", [pid, *pb])
        bowl["best_wickets_innings"] = best["w"] if best else 0
        bowl["four_plus"] = db.q1(f"""SELECT count(*) AS n FROM (SELECT match_id, innings_no, count(*) FILTER (WHERE bowler_credited) AS w
                        FROM dis WHERE bowler_id = ? AND {wb} GROUP BY ALL) WHERE w >= 4""", [pid, *pb])["n"]
    # ---- fielding (match-level filters; perspective: the player is fielding, opposition = batting team)
    wf, pf = f.where("bowler", "x", ball_level=False)
    field = db.q1(f"""SELECT count(*) FILTER (WHERE x.kind = 'caught' AND wf.fielder_id = ? AND NOT wf.substitute) AS catches,
        count(*) FILTER (WHERE x.kind = 'caught' AND wf.fielder_id = ? AND x.route = 'CAUGHT_KEEPER') AS catches_as_keeper,
        count(*) FILTER (WHERE x.kind = 'stumped' AND wf.fielder_id = ?) AS stumpings,
        count(*) FILTER (WHERE x.kind = 'run out' AND wf.fielder_id = ?) AS run_out_involvements
        FROM dis x JOIN wicket_fielders wf ON wf.delivery_id = x.delivery_id AND wf.wicket_idx = x.wicket_idx
        WHERE wf.fielder_id = ? AND {wf}""", [pid, pid, pid, pid, pid, *pf])
    return {
        "person_id": pid, "name": p["name"], "register_name": p.get("register_name"), "aliases": p.get("aliases"),
        "identity": {"canonical_player_id": pid, "cricsheet_register_id": pid if not pid.startswith("unres:") else None,
                     "external_ids": (db.q1("SELECT external_ids FROM persons WHERE person_id = ?", [pid]) or {}).get("external_ids")},
        "genders": p["genders"], "teams": list(dict.fromkeys(TEAM_CANON.get(t, t) for t in (p["teams"] or []))),  # renamed franchises once
        "metadata": {k: _meta_field(p, k) for k in ("role", "batting_hand", "bowling_style", "bowling_arm", "bowling_family", "wicketkeeper")},
        "coverage": {**(cov or {}), "competitions": comps, "breakdown": coverage_breakdown(db, pid, f), "notes": notes,
                     "statement": f"Analysed from {cov['matches'] if cov else 0} matches in our dataset"
                                  + (f" ({cov['first_date']} – {cov['last_date']})" if cov and cov['matches'] else "")
                                  + ". These are not official career totals."},
        "batting": bat, "bowling": bowl if bowl and bowl["balls"] else None, "fielding": field,
        "filters": f.active(), "prov": "OBSERVED aggregates of source deliveries; role/keeper DERIVED; hand/style per source",
    }


def dismissals(db: DB, pid: str, f: Filters) -> dict:
    w, p = f.where("batter")
    rows = db.q(f"""SELECT route, kind, count(*) AS n FROM dis WHERE player_out_id = ? AND {w} GROUP BY ALL""", [pid, *p])
    total = sum(r["n"] for r in rows if r["route"] != "RETIRED_NOT_OUT")
    by_route: dict[str, int] = {}
    for r in rows:
        if r["route"] != "RETIRED_NOT_OUT":
            by_route[r["route"]] = by_route.get(r["route"], 0) + r["n"]
    balls = db.q1(f"SELECT count(*) FILTER (WHERE faced) AS balls, count(DISTINCT match_id||':'||innings_no) AS inns FROM balls WHERE batter_id = ? AND {w}", [pid, *p])
    routes = []
    for code, label, prov, explain in ROUTES:
        n = by_route.get(code, 0)
        if n or code in ("BOWLED", "LBW", "CAUGHT_KEEPER", "CAUGHT_BOWLER", "CAUGHT_FIELDER", "STUMPED", "RUN_OUT", "HIT_WICKET"):
            routes.append({"route": code, "label": label, "n": n, "pct": _rate(n, total, 100, 1), "prov": prov, "explain": explain})
    conf = db.q1(f"""SELECT avg(route_confidence) AS c FROM dis WHERE player_out_id = ? AND route IN ('CAUGHT_KEEPER','CAUGHT_FIELDER') AND {w}""", [pid, *p])
    by_family = db.q(f"""SELECT coalesce(bowler_family, 'unknown') AS family, count(*) AS n FROM dis
                        WHERE player_out_id = ? AND counts_as_dismissal AND {w} GROUP BY 1 ORDER BY n DESC""", [pid, *p])
    by_phase = db.q(f"""SELECT phase, count(*) AS n FROM dis WHERE player_out_id = ? AND counts_as_dismissal AND {w} GROUP BY 1 ORDER BY n DESC""", [pid, *p])
    top_bowlers = db.q(f"""SELECT bowler_id, bowler, count(*) AS n FROM dis WHERE player_out_id = ? AND bowler_credited AND {w}
                          GROUP BY ALL ORDER BY n DESC, bowler LIMIT 5""", [pid, *p])
    top_fielders = db.q(f"""SELECT fielder_id, fielder, route, count(*) AS n FROM dis WHERE player_out_id = ? AND kind = 'caught'
                           AND fielder IS NOT NULL AND {w} GROUP BY ALL ORDER BY n DESC LIMIT 5""", [pid, *p])
    retired = sum(r["n"] for r in rows if r["route"] == "RETIRED_NOT_OUT")
    return {"total": total, "balls_faced": balls["balls"], "innings": balls["inns"],
            "balls_per_dismissal": _rate(balls["balls"], total, 1, 1), "routes": routes,
            "kinds": sorted(({"kind": r["kind"], "n": r["n"]} for r in rows), key=lambda r: -r["n"]),
            "catch_route_mean_confidence": round(conf["c"], 3) if conf and conf["c"] else None,
            "by_bowler_family": by_family, "by_phase": by_phase, "top_bowlers": top_bowlers,
            "top_catchers": top_fielders, "retired_not_out": retired, "filters": f.active(),
            "position_note": "Fielding positions (slip, gully, cover, deep…) are not in the source data and are never inferred."}


MATCHUP_COLS = """count(*) FILTER (WHERE faced) AS balls, sum(runs_batter) AS runs,
  count(*) FILTER (WHERE faced AND runs_batter = 0) AS dots, count(*) FILTER (WHERE faced AND runs_batter = 1) AS ones,
  count(*) FILTER (WHERE faced AND runs_batter = 2) AS twos, count(*) FILTER (WHERE faced AND runs_batter = 3) AS threes,
  count(*) FILTER (WHERE is_four) AS fours, count(*) FILTER (WHERE is_six) sixes"""


def _finish(r: dict) -> dict:
    r["strike_rate"] = _rate(r["runs"], r["balls"], 100, 1)
    r["runs_per_dismissal"] = _rate(r["runs"], r["dismissals"], 1, 1)
    r["dot_pct"] = _rate(r["dots"], r["balls"], 100, 1)
    r["boundary_pct"] = _rate(r["fours"] + r["sixes"], r["balls"], 100, 1)
    r["balls_per_dismissal"] = _rate(r["balls"], r["dismissals"], 1, 1)
    return r


def matchups(db: DB, pid: str, f: Filters, by: str = "bowler", q: str | None = None, limit: int = 30,
             role: str = "batter") -> dict:
    """role=batter: pid batting vs bowlers / bowler groups. role=bowler: pid bowling vs batters / batter groups."""
    me = "batter_id" if role == "batter" else "bowler_id"
    out_col = "player_out_id" if role == "batter" else "bowler_id"
    w, p = f.where(role)
    groups = {
        "bowler": ("bowler_id", "bowler", "OBSERVED"), "batter": ("batter_id", "batter", "OBSERVED"),
        "bowler_family": ("bowler_family", "bowler_family", "player metadata"),
        "bowler_style": ("bowler_style", "bowler_style", "player metadata"),
        "bowler_arm": ("bowler_arm", "bowler_arm", "player metadata"),
        "batter_hand": ("batter_hand", "batter_hand", "player metadata"),
    }
    if by not in groups:
        raise ValueError(f"unknown matchup grouping {by}")
    key, label, prov = groups[by]
    extra, ep = "", []
    if q:
        extra, ep = f" AND {label} ILIKE ?", [f"%{q}%"]
    rows = db.q(f"""
      WITH b AS (SELECT {key} k, any_value({label}) AS label, {MATCHUP_COLS} FROM balls
                 WHERE {me} = ? AND {w}{extra} GROUP BY 1),
      d AS (SELECT {key} k, count(*) FILTER (WHERE bowler_credited) AS dismissals,
                   count(*) FILTER (WHERE NOT bowler_credited AND counts_as_dismissal) AS other_dismissals
            FROM dis WHERE {out_col} = ? AND {w}{extra} GROUP BY 1)
      SELECT b.*, coalesce(d.dismissals, 0) AS dismissals, coalesce(d.other_dismissals, 0) AS other_dismissals
      FROM b LEFT JOIN d ON b.k IS NOT DISTINCT FROM d.k ORDER BY balls DESC LIMIT ?""",
                [pid, *p, *ep, pid, *p, *ep, limit])
    rows = [_finish(r) for r in rows]
    total = db.q1(f"SELECT {MATCHUP_COLS} FROM balls WHERE {me} = ? AND {w}", [pid, *p])
    total["dismissals"] = db.q1(f"SELECT count(*) AS n FROM dis WHERE {out_col} = ? AND bowler_credited AND {w}", [pid, *p])["n"]
    total["other_dismissals"] = 0
    return {"by": by, "role": role, "rows": rows, "baseline": _finish(total), "grouping_prov": prov,
            "filters": f.active(),
            "note": "Dismissals = wickets credited to the bowler. Run-outs on these balls are counted separately (other_dismissals)."}


def situations(db: DB, pid: str, f: Filters) -> dict:
    """Genuine situational analytics from event data (no pitch coordinates required)."""
    w, p = f.where("batter")
    base = f"FROM balls b WHERE b.batter_id = ? AND {w}"
    dmap = """LEFT JOIN (SELECT delivery_id, 1 AS is_out FROM wickets WHERE player_out_id = ? AND counts_as_dismissal) o USING (delivery_id)"""

    def grid(expr: str, order: str = "1") -> list[dict]:
        rows = db.q(f"""SELECT {expr} AS bucket, count(*) FILTER (WHERE faced) AS balls, sum(runs_batter) AS runs,
               count(o.is_out) AS dismissals, count(*) FILTER (WHERE faced AND runs_batter = 0) AS dots,
               count(*) FILTER (WHERE is_four OR is_six) AS boundaries
               FROM balls b {dmap} WHERE b.batter_id = ? AND {w} GROUP BY 1 ORDER BY {order}""", [pid, pid, *p])
        for r in rows:
            r["strike_rate"] = _rate(r["runs"], r["balls"], 100, 1)
            r["dismissal_rate"] = _rate(r["dismissals"], r["balls"], 100, 2)  # per 100 balls
            r["dot_pct"] = _rate(r["dots"], r["balls"], 100, 1)
            r["boundary_pct"] = _rate(r["boundaries"], r["balls"], 100, 1)
        return rows

    return {
        "by_over": grid("b.over + 1"),
        "by_wickets_down": grid("b.wickets_before"),
        "by_innings_stage": grid("""CASE WHEN b.batter_balls_before < 10 THEN '0–9' WHEN b.batter_balls_before < 20 THEN '10–19'
                                       WHEN b.batter_balls_before < 30 THEN '20–29' WHEN b.batter_balls_before < 50 THEN '30–49' ELSE '50+' END"""),
        "by_required_rate": grid("""CASE WHEN NOT coalesce(b.chasing,false) OR b.required_rate IS NULL THEN NULL
                                        WHEN b.required_rate < 6 THEN '<6' WHEN b.required_rate < 8 THEN '6–8'
                                        WHEN b.required_rate < 10 THEN '8–10' WHEN b.required_rate < 12 THEN '10–12' ELSE '12+' END"""),
        "by_chase_state": grid("CASE WHEN coalesce(b.chasing,false) THEN 'Chasing' ELSE 'Setting / no target' END"),
        "by_phase": grid("b.phase"),
        "prov": "DERIVED context (score, wickets, required rate) computed deterministically from the observed ball sequence",
        "filters": f.active(),
    }


def delivery_query(db: DB, f: Filters, *, out_id: str | None = None, route: str | None = None,
                   kind: str | None = None, batter_id: str | None = None, bowler_id: str | None = None,
                   fielder_id: str | None = None, offset: int = 0, limit: int = 25) -> dict:
    """Aggregate -> evidence: the deliveries behind a number."""
    if out_id or route or kind or fielder_id:
        w, p = f.where("batter", "x")
        conds, params = [w], list(p)
        if out_id:
            conds.append("x.player_out_id = ?"); params.append(out_id)
        if route:
            conds.append("x.route = ?"); params.append(route)
        if kind:
            conds.append("x.kind = ?"); params.append(kind)
        if bowler_id:
            conds.append("x.bowler_id = ?"); params.append(bowler_id)
        if fielder_id:
            conds.append("x.fielder_id = ?"); params.append(fielder_id)
        wh = " AND ".join(conds)
        total = db.q1(f"SELECT count(*) AS n FROM dis x WHERE {wh}", params)["n"]
        ids = [r["delivery_id"] for r in db.q(
            f"SELECT delivery_id FROM dis x WHERE {wh} ORDER BY x.start_date DESC, x.delivery_id LIMIT ? OFFSET ?",
            [*params, limit, offset])]
    else:
        w, p = f.where("batter", "b")
        conds, params = [w], list(p)
        if batter_id:
            conds.append("b.batter_id = ?"); params.append(batter_id)
        if bowler_id:
            conds.append("b.bowler_id = ?"); params.append(bowler_id)
        wh = " AND ".join(conds)
        total = db.q1(f"SELECT count(*) AS n FROM balls b WHERE {wh}", params)["n"]
        ids = [r["delivery_id"] for r in db.q(
            f"SELECT delivery_id FROM balls b WHERE {wh} ORDER BY b.start_date DESC, b.match_id, b.innings_no, b.seq LIMIT ? OFFSET ?",
            [*params, limit, offset])]
    return {"total": total, "offset": offset, "limit": limit, "deliveries": delivery_cards(db, ids)}


def delivery_cards(db: DB, ids: list[str]) -> list[dict]:
    if not ids:
        return []
    rows = db.q(f"""SELECT b.*, m.source_ref, m.match_type FROM balls b JOIN matches m USING (match_id)
                    WHERE delivery_id IN ({','.join('?' * len(ids))})""", ids)
    wk = db.q(f"""SELECT delivery_id, player_out_id, player_out, kind, route, route_prov, route_confidence, route_method,
                  fielders, keeper_id, keeper_method, striker_out, counts_as_dismissal
                  FROM dis WHERE delivery_id IN ({','.join('?' * len(ids))}) ORDER BY wicket_idx""", ids)
    rv = db.q(f"SELECT * FROM reviews WHERE delivery_id IN ({','.join('?' * len(ids))})", ids)
    wk_by, rv_by = {}, {r["delivery_id"]: r for r in rv}
    for x in wk:
        x["route_label"] = ROUTE_META.get(x["route"], {}).get("label", x["route"])
        for fd in x["fielders"] or []:
            fd["role"] = ("wicketkeeper" if fd["id"] and fd["id"] == x["keeper_id"] else
                          "bowler" if x["kind"] == "caught and bowled" else
                          "substitute" if fd["sub"] else "fielder" if x["keeper_id"] else "fielder (keeper status unknown)")
            fd["role_prov"] = "DERIVED" if fd["role"] in ("wicketkeeper", "fielder") else "OBSERVED"
            fd["position"] = None  # never inferred
        wk_by.setdefault(x["delivery_id"], []).append(x)
    order = {d: i for i, d in enumerate(ids)}
    cards = []
    for r in sorted(rows, key=lambda r: order[r["delivery_id"]]):
        after_w = r["wickets_before"] + sum(1 for x in wk_by.get(r["delivery_id"], []) if x["counts_as_dismissal"])
        cards.append({
            "delivery_id": r["delivery_id"], "match_id": r["match_id"], "date": r["start_date"],
            "competition": r["competition"], "format": r["format_group"], "gender": r["gender"],
            "teams": [r["team1"], r["team2"]], "venue": r["venue"], "innings_no": r["innings_no"],
            "batting_team": r["batting_team"], "bowling_team": r["bowling_team"],
            "over_ball": r["ball_label"], "over": r["over"], "phase": r["phase"],
            "batter": {"id": r["batter_id"], "name": r["batter"], "hand": r["batter_hand"]},
            "bowler": {"id": r["bowler_id"], "name": r["bowler"], "style": r["bowler_style"], "family": r["bowler_family"]},
            "non_striker": {"id": r["non_striker_id"], "name": r["non_striker"]},
            "score_before": f"{r['score_before']}/{r['wickets_before']}",
            "score_after": f"{r['score_before'] + r['runs_total']}/{after_w}",
            "context": {"chasing": r["chasing"], "target": r["target_runs"], "runs_required": r["runs_required"],
                        "balls_remaining": r["balls_remaining"], "required_rate": r["required_rate"] and round(r["required_rate"], 2),
                        "batter_score_before": f"{r['batter_runs_before']} ({r['batter_balls_before']})",
                        "prov": "DERIVED"},
            "runs": {"batter": r["runs_batter"], "extras": r["runs_extras"], "total": r["runs_total"],
                     "wides": r["wides"], "noballs": r["noballs"], "byes": r["byes"], "legbyes": r["legbyes"],
                     "four": r["is_four"], "six": r["is_six"]},
            "wickets": wk_by.get(r["delivery_id"], []), "review": rv_by.get(r["delivery_id"]),
            "source": {"source_id": r["source_id"], "source_ref": r["source_ref"], "match_id": r["match_id"],
                       "prov": "OBSERVED"},
        })
    return cards
