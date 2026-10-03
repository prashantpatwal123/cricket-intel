"""Player x Player battle, Dismissal Story, Career Timeline and Compare: all from covered data only."""
from __future__ import annotations

from ..db import DB
from .filters import Filters
from .player import ROUTE_META, _rate, coverage_breakdown
from .stats import poisson_interval, rate_ratio, wilson

BATTLE_COLS = """count(*) FILTER (WHERE faced) AS balls, coalesce(sum(runs_batter), 0) AS runs,
  count(*) FILTER (WHERE faced AND runs_batter = 0) AS dots, count(*) FILTER (WHERE faced AND runs_batter = 1) AS singles,
  count(*) FILTER (WHERE faced AND runs_batter IN (2, 3)) AS twos_threes, count(*) FILTER (WHERE is_four) AS fours,
  count(*) FILTER (WHERE is_six) AS sixes, count(DISTINCT match_id) AS matches, min(start_date) AS first_date, max(start_date) AS last_date"""


def _finish(r: dict) -> dict:
    r["boundaries"] = (r.get("fours") or 0) + (r.get("sixes") or 0)
    r["strike_rate"] = _rate(r["runs"], r["balls"], 100, 1)
    r["runs_per_dismissal"] = _rate(r["runs"], r.get("dismissals"), 1, 1)
    r["dot_pct"] = _rate(r["dots"], r["balls"], 100, 1)
    r["boundary_pct"] = _rate(r["boundaries"], r["balls"], 100, 1)
    return r


def battle(db: DB, bat: str, bowl: str, f: Filters) -> dict:
    w, p = f.where("batter")
    names = {r["person_id"]: r for r in db.q("SELECT person_id, name, genders FROM player_profile WHERE person_id IN (?, ?)", [bat, bowl])}
    tot = db.q1(f"SELECT {BATTLE_COLS} FROM balls WHERE batter_id = ? AND bowler_id = ? AND {w}", [bat, bowl, *p])
    dis = db.q(f"""SELECT kind, route, count(*) AS n FROM dis WHERE player_out_id = ? AND bowler_id = ? AND bowler_credited AND {w}
                   GROUP BY ALL ORDER BY n DESC""", [bat, bowl, *p])
    tot["dismissals"] = sum(d["n"] for d in dis)
    _finish(tot)
    if not tot["balls"]:
        return {"batter": names.get(bat), "bowler": names.get(bowl), "total": tot, "met": False}
    fmts = [r["format_group"] for r in db.q(f"SELECT DISTINCT format_group FROM balls WHERE batter_id = ? AND bowler_id = ? AND {w}", [bat, bowl, *p])]

    def breakdown(expr: str, label: str, order: str = "1"):
        rows = db.q(f"""SELECT {expr} AS bucket, {BATTLE_COLS},
            (SELECT count(*) FROM dis x WHERE x.player_out_id = ? AND x.bowler_id = ? AND x.bowler_credited AND {w.replace('?', '?')}
               AND {expr.replace('format_group', 'x.format_group').replace('phase', 'x.phase').replace('innings_no', 'x.innings_no').replace('year', 'x.year')} = b.bucket_) AS dismissals
            FROM (SELECT *, {expr} AS bucket_ FROM balls WHERE batter_id = ? AND bowler_id = ? AND {w}) b GROUP BY 1, bucket_ ORDER BY {order}""",
                    [bat, bowl, *p, bat, bowl, *p])
        return {"label": label, "rows": [_finish(r) for r in rows]}

    by = {
        "phase": breakdown("phase", "Match phase"),
        "innings": breakdown("innings_no", "Innings (1 = setting, 2 = chasing)"),
        "year": breakdown("year", "Year"),
        "format": breakdown("format_group", "Format"),
    }
    # ---- WHO HAS THE EDGE?  Evidence, not a verdict.
    fmt_list = ",".join("'" + x + "'" for x in fmts)
    base_bat = db.q1(f"""SELECT count(*) FILTER (WHERE faced) AS balls, sum(runs_batter) AS runs FROM balls
                         WHERE batter_id = ? AND format_group IN ({fmt_list}) AND {w}""", [bat, *p])
    base_bat_outs = db.q1(f"""SELECT count(*) AS n FROM dis WHERE player_out_id = ? AND bowler_credited AND format_group IN ({fmt_list}) AND {w}""",
                          [bat, *p])["n"]
    base_bowl = db.q1(f"""SELECT count(*) FILTER (WHERE faced) AS balls, sum(runs_batter) AS runs FROM balls
                          WHERE bowler_id = ? AND format_group IN ({fmt_list}) AND {w}""", [bowl, *p])
    base_bowl_wk = db.q1(f"""SELECT count(*) AS n FROM dis WHERE bowler_id = ? AND bowler_credited AND format_group IN ({fmt_list}) AND {w}""",
                         [bowl, *p])["n"]
    n = tot["balls"]
    exp_outs_bat = n * base_bat_outs / base_bat["balls"] if base_bat["balls"] else None
    exp_outs_bowl = n * base_bowl_wk / base_bowl["balls"] if base_bowl["balls"] else None
    lo, hi = poisson_interval(tot["dismissals"])
    sr_bat = 100 * base_bat["runs"] / base_bat["balls"] if base_bat["balls"] else None
    sr_bowl = 100 * base_bowl["runs"] / base_bowl["balls"] if base_bowl["balls"] else None
    import math
    # SR interval for the matchup: normal approx on runs per ball using the batter's per-ball variance proxy
    var = db.q1(f"SELECT var_samp(runs_batter) AS v FROM balls WHERE batter_id = ? AND bowler_id = ? AND faced AND {w}", [bat, bowl, *p])["v"] or 0
    se_sr = 100 * math.sqrt(var / n) if n > 1 else None
    edge = {
        "sample_note": ("Small sample: fewer than 60 balls. Treat everything here as anecdotal." if n < 60 else
                        "Moderate sample." if n < 150 else "Reasonable sample for this matchup."),
        "strike_rate": {"matchup": tot["strike_rate"], "matchup_interval_90": [round(tot["strike_rate"] - 1.645 * se_sr, 1), round(tot["strike_rate"] + 1.645 * se_sr, 1)] if se_sr else None,
                        "batter_usual": round(sr_bat, 1) if sr_bat else None, "bowler_usual_conceded": round(sr_bowl, 1) if sr_bowl else None},
        "dismissals": {"observed": tot["dismissals"], "observed_interval_90": [round(lo, 1), round(hi, 1)],
                       "expected_from_batter_usual_rate": round(exp_outs_bat, 1) if exp_outs_bat is not None else None,
                       "expected_from_bowler_usual_rate": round(exp_outs_bowl, 1) if exp_outs_bowl is not None else None},
        "explain": ("'Usual' = the batter's rate against all bowlers, and the bowler's rate against all batters, in the same formats and filters. "
                    "Expected dismissals = balls in this matchup × the usual dismissal rate. If the expected value sits inside the observed "
                    "interval, the matchup is consistent with normal variation. We don't declare a winner."),
        "baseline_scope": {"formats": fmts, "filters": f.active()},
    }
    return {"batter": names.get(bat), "bowler": names.get(bowl), "met": True, "total": tot, "dismissals_by_kind": [
        {**d, "label": ROUTE_META.get(d["route"], {}).get("label", d["route"])} for d in dis], "by": by, "edge": edge,
            "evidence_query": {"batter_id": bat, "bowler_id": bowl, **f.active()},
            "not_available": ["pace/spin split (metadata)", "line & length", "shot types"]}


def notable_battles(db: DB, gender: str | None = None, limit: int = 12) -> list[dict]:
    g = "AND gender = ?" if gender else ""
    return db.q(f"""SELECT b.batter_id, any_value(pb.name) AS batter, b.bowler_id, any_value(pw.name) AS bowler, count(*) FILTER (WHERE faced) AS balls,
                    sum(runs_batter) AS runs, any_value(b.gender) AS gender,
                    (SELECT count(*) FROM dis x WHERE x.player_out_id = b.batter_id AND x.bowler_id = b.bowler_id AND x.bowler_credited) AS dismissals
                    FROM balls b JOIN player_profile pb ON pb.person_id = b.batter_id JOIN player_profile pw ON pw.person_id = b.bowler_id
                    WHERE TRUE {g} GROUP BY b.batter_id, b.bowler_id ORDER BY balls DESC LIMIT ?""", ([gender] if gender else []) + [limit])


# ---------------------------------------------------------------------------------------------- Dismissal Story
def dismissal_story(db: DB, pid: str, route: str, f: Filters) -> dict:
    w, p = f.where("batter")
    base = f"FROM dis WHERE player_out_id = ? AND route = ? AND {w}"
    args = [pid, route, *p]
    n = db.q1(f"SELECT count(*) AS n {base}", args)["n"]
    total = db.q1(f"SELECT count(*) AS n FROM dis WHERE player_out_id = ? AND counts_as_dismissal AND {w}", [pid, *p])["n"]
    balls = db.q1(f"SELECT count(*) FILTER (WHERE faced) AS b FROM balls WHERE batter_id = ? AND {w}", [pid, *p])["b"]

    def grp(expr, order="n DESC"):
        return db.q(f"SELECT {expr} AS k, count(*) AS n {base} GROUP BY 1 ORDER BY {order}", args)
    by_year = grp("year", "k")
    # chronological context: share of all dismissals each year that came this way
    yr_all = {r["k"]: r["n"] for r in db.q(f"SELECT year AS k, count(*) AS n FROM dis WHERE player_out_id = ? AND counts_as_dismissal AND {w} GROUP BY 1",
                                           [pid, *p])}
    lo, hi = wilson(n, total)
    return {
        "route": route, "label": ROUTE_META.get(route, {}).get("label", route), "prov": ROUTE_META.get(route, {}).get("prov"),
        "explain": ROUTE_META.get(route, {}).get("explain"), "n": n, "of_total": total,
        "share": round(100 * n / total, 1) if total else None, "share_interval_90": [round(100 * lo, 1), round(100 * hi, 1)] if lo is not None else None,
        "balls_per": round(balls / n, 1) if n else None,
        "by_format": grp("format_group"), "by_phase": grp("phase"), "by_over": grp("over + 1", "k"),
        "by_bowler": db.q(f"SELECT bowler_id, any_value(bowler) AS bowler, count(*) AS n {base} GROUP BY 1 ORDER BY n DESC LIMIT 8", args),
        "by_fielder": db.q(f"SELECT fielder_id, any_value(fielder) AS fielder, count(*) AS n {base} AND fielder IS NOT NULL GROUP BY 1 ORDER BY n DESC LIMIT 6", args)
        if route.startswith("CAUGHT") or route in ("STUMPED", "RUN_OUT") else [],
        "by_year": [{"year": r["k"], "n": r["n"], "all_dismissals": yr_all.get(r["k"], 0)} for r in by_year],
        "by_batter_score": grp("""CASE WHEN batter_runs_before < 10 THEN '0–9' WHEN batter_runs_before < 30 THEN '10–29'
                                       WHEN batter_runs_before < 50 THEN '30–49' ELSE '50+' END""", "k"),
        "terminology": "Caught by wicketkeeper means the catch was taken by the fielding side's keeper. The data doesn't say whether the ball was edged."
        if route == "CAUGHT_KEEPER" else None,
        "evidence_query": {"out_id": pid, "route": route, **f.active()},
    }


# ---------------------------------------------------------------------------------------------- Career Timeline
def timeline(db: DB, pid: str, f: Filters, by: str = "year") -> dict:
    w, p = f.where("batter")
    bucket = "year" if by == "year" else "season"
    rows = db.q(f"""SELECT {bucket} AS period, format_group, CASE WHEN team_type = 'club' THEN competition ELSE 'International' END AS level,
        count(DISTINCT match_id || ':' || innings_no) AS innings, count(*) FILTER (WHERE faced) AS balls, sum(runs_batter) AS runs,
        count(*) FILTER (WHERE faced AND runs_batter = 0) AS dots, count(*) FILTER (WHERE is_four OR is_six) AS boundaries
        FROM balls WHERE batter_id = ? AND {w} GROUP BY ALL ORDER BY 1""", [pid, *p])
    outs = {(r["period"], r["format_group"], r["level"]): r["n"] for r in db.q(
        f"""SELECT {bucket} AS period, format_group, CASE WHEN team_type = 'club' THEN competition ELSE 'International' END AS level, count(*) AS n
            FROM dis WHERE player_out_id = ? AND counts_as_dismissal AND {w} GROUP BY ALL""", [pid, *p])}
    for r in rows:
        o = outs.get((r["period"], r["format_group"], r["level"]), 0)
        r.update(outs=o, strike_rate=_rate(r["runs"], r["balls"], 100, 1), average=_rate(r["runs"], o, 1, 1),
                 out_rate=_rate(o, r["balls"], 100, 2), boundary_pct=_rate(r["boundaries"], r["balls"], 100, 1),
                 dot_pct=_rate(r["dots"], r["balls"], 100, 1), small_sample=r["balls"] < 60)
    # coverage gaps: years inside the active span with no covered balls, plus Cricsheet's own known-missing ODIs
    gaps = []
    if rows and by == "year":
        series = {}
        for r in rows:
            series.setdefault((r["format_group"], r["level"]), set()).add(r["period"])
        for (fmt, lvl), yrs in series.items():
            for y in range(min(yrs), max(yrs) + 1):
                if y not in yrs:
                    gaps.append({"format": fmt, "level": lvl, "year": y, "reason": "no covered balls this year (player didn't play, or matches not in our data)"})
    missing = []
    if getattr(db, "has_source_coverage", False):
        for c in coverage_breakdown(db, pid, f):
            if c["format_group"] == "ODI" and c["team_type"] == "international":
                missing += db.q("""SELECT year(date::DATE) AS year, count(*) AS n FROM source_missing_matches WHERE match_type = 'Odi'
                                   AND gender = ? AND ? IN (team1, team2) AND date::DATE BETWEEN ? AND ? GROUP BY 1 ORDER BY 1""",
                                [c["gender"], c["team"], c["first_date"], c["last_date"]])
    return {"by": by, "rows": rows, "gaps": gaps, "team_missing_odis_by_year": missing,
            "note": "Lines are broken where we have no covered data. We don't interpolate across gaps."}


# ---------------------------------------------------------------------------------------------- Compare
def compare(db: DB, pids: list[str], f: Filters) -> dict:
    w, p = f.where("batter")
    out = []
    for pid in pids[:4]:
        prof = db.q1("SELECT person_id, name, genders, teams FROM player_profile WHERE person_id = ?", [pid])
        if not prof:
            continue
        b = db.q1(f"""SELECT count(*) FILTER (WHERE faced) AS balls, coalesce(sum(runs_batter), 0) AS runs,
            count(*) FILTER (WHERE faced AND runs_batter = 0) AS dots, count(*) FILTER (WHERE is_four) AS fours,
            count(*) FILTER (WHERE is_six) AS sixes, count(DISTINCT match_id) AS matches, min(start_date) AS first_date,
            max(start_date) AS last_date, list(DISTINCT format_group) AS formats, list(DISTINCT CASE WHEN team_type='club' THEN competition ELSE 'International' END) AS levels
            FROM balls WHERE batter_id = ? AND {w}""", [pid, *p])
        o = db.q1(f"SELECT count(*) AS n FROM dis WHERE player_out_id = ? AND counts_as_dismissal AND {w}", [pid, *p])["n"]
        lo, hi = wilson(o, b["balls"]) if b["balls"] else (None, None)
        b.update(outs=o, strike_rate=_rate(b["runs"], b["balls"], 100, 1), average=_rate(b["runs"], o, 1, 1),
                 balls_per_dismissal=_rate(b["balls"], o, 1, 1), boundary_pct=_rate(b["fours"] + b["sixes"], b["balls"], 100, 1),
                 dot_pct=_rate(b["dots"], b["balls"], 100, 1),
                 out_rate_interval_90=[round(100 * lo, 2), round(100 * hi, 2)] if lo is not None else None)
        out.append({"player": prof, "stats": b, "coverage": coverage_breakdown(db, pid, f)})
    warnings = []
    if len({tuple(sorted(x["player"]["genders"])) for x in out}) > 1:
        warnings.append("Players from men's and women's cricket: different peer contexts, so compare with care.")
    spans = [(x["stats"]["first_date"], x["stats"]["last_date"]) for x in out if x["stats"]["balls"]]
    if spans:
        overlap = max(s[0] for s in spans) <= min(s[1] for s in spans)
        if not overlap:
            warnings.append("The covered periods don't overlap: these players are from different eras of our data.")
    bals = [x["stats"]["balls"] for x in out if x["stats"]["balls"]]
    if bals and max(bals) > 4 * min(bals):
        warnings.append("Sample sizes differ by more than 4×; the smaller sample's rates are much less certain (see intervals).")
    lv = [set(x["stats"]["levels"] or []) for x in out]
    if lv and len({frozenset(s) for s in lv}) > 1:
        warnings.append("Players' covered data comes from different competitions. Use the format/level filters to compare like with like.")
    for x in out:
        if any(c["status"] in ("PARTIAL", "UNKNOWN") for c in x["coverage"]):
            warnings.append(f"{x['player']['name']}: some coverage is partial or unknown (see coverage).")
    return {"players": out, "warnings": warnings, "filters": f.active()}
