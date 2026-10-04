"""Canonical entity pages built on the knowledge graph: Match, Competition, Rivalry, Career.

Everything is computed from covered data and labelled with its provenance. "Turning points" are NOT produced:
no turning-point algorithm has been validated. Match pages list *factual events* (collapses, big overs, milestones)
with their definitions; the experimental Situation Difficulty swings appear only when that flag is on, labelled as such.
"""
from __future__ import annotations

from functools import lru_cache

from ..db import DB
from .graph import TEAM_CANON
from .replay import _result_line

COLLAPSE_WKTS, COLLAPSE_BALLS, COLLAPSE_RUNS = 3, 18, 20


@lru_cache(maxsize=4)
def names(db: DB) -> dict:
    return {r["person_id"]: r["name"] for r in db.q("SELECT person_id, name FROM player_profile")}


def _nm(db, pid, fallback=None):
    return names(db).get(pid, fallback or pid)


def canon(t: str | None) -> str | None:
    return TEAM_CANON.get(t, t) if t else t


def coverage_note(db: DB, competition: str | None, gender: str | None) -> dict:
    if not competition:
        return {"status": "UNKNOWN", "text": "Bilateral series and one-off matches: completeness depends on team coverage (see each player's coverage)."}
    r = db.q1("SELECT have, of, pct FROM source_coverage_pct WHERE scope = 'competition' AND name = ? AND (gender = ? OR gender IS NULL) ORDER BY gender NULLS LAST LIMIT 1",
              [competition, gender]) if getattr(db, "has_source_coverage", False) else None
    n = db.q1("SELECT count(*) AS n FROM team_results WHERE competition = ? AND gender = ?", [competition, gender])["n"]
    if r:
        return {"status": "COMPLETE" if r["pct"] >= 100 else "PARTIAL", "have": r["have"], "of": r["of"], "ours": n,
                "text": f"Cricsheet holds {r['have']} of the {r['of']} {competition} matches it knows of ({r['pct']}%). CRICINTEL covers {n} of them."}
    return {"status": "UNKNOWN", "ours": n, "text": f"CRICINTEL covers {n} {competition} matches. Cricsheet does not publish a completeness figure for this "
                                                     f"competition, so totals here are covered-data totals, not official tournament history."}


# ------------------------------------------------------------------ Match
def match_page(db: DB, match_id: str, sdx=None) -> dict | None:
    m = db.q1("SELECT * FROM team_results WHERE match_id = ?", [match_id])
    if not m:
        return None
    meta = db.q1("SELECT * FROM matches WHERE match_id = ?", [match_id])
    m["result_line"] = _result_line(meta)
    m["start_date"] = str(m["start_date"])
    m["player_of_match_names"] = [_nm(db, p) for p in (meta.get("player_of_match") or [])] if isinstance(meta.get("player_of_match"), list) else []
    inns = db.q("""SELECT innings_no, batting_team, bowling_team, total_runs, total_wickets, legal_balls, target_runs FROM innings
                   WHERE match_id = ? AND NOT super_over ORDER BY innings_no""", [match_id])
    out_inns = []
    for i in inns:
        n = i["innings_no"]
        bat = db.q("""SELECT batter_id, runs, balls, fours, sixes, not_out, out_kind, out_bowler, position, out_delivery_id FROM bat_innings
                      WHERE match_id = ? AND innings_no = ? ORDER BY first_seq""", [match_id, n])
        for b in bat:
            b["name"] = _nm(db, b["batter_id"])
        bowl = db.q("""SELECT bowler_id, balls, runs, wickets, dots, boundaries, overs_bowled FROM bowl_innings WHERE match_id = ? AND innings_no = ?
                       ORDER BY wickets DESC, runs""", [match_id, n])
        for b in bowl:
            b["name"] = _nm(db, b["bowler_id"])
        overs = db.q("""SELECT over, sum(runs_total) AS runs, sum(n_wickets) AS wkts, any_value(phase) AS phase FROM balls
                        WHERE match_id = ? AND innings_no = ? GROUP BY 1 ORDER BY 1""", [match_id, n])
        fow = db.q("""SELECT b.ball_label, b.score_before + b.runs_total AS score, b.wickets_before + 1 AS wkt, d.player_out, d.player_out_id, d.kind, b.delivery_id
                      FROM dis d JOIN balls b USING (delivery_id) WHERE d.match_id = ? AND d.innings_no = ? AND d.counts_as_dismissal ORDER BY b.seq""",
                   [match_id, n])
        for f in fow:
            f["player_out"] = _nm(db, f["player_out_id"], f["player_out"])
        phases = db.q("""SELECT phase, sum(runs_total) AS runs, sum(n_wickets) AS wkts, count(*) FILTER (WHERE legal) AS balls FROM balls
                         WHERE match_id = ? AND innings_no = ? GROUP BY 1""", [match_id, n])
        extras = db.q1("SELECT sum(runs_extras) AS e FROM balls WHERE match_id = ? AND innings_no = ?", [match_id, n])["e"]
        out_inns.append({**i, "overs": f"{i['legal_balls'] // 6}.{i['legal_balls'] % 6}", "run_rate": round(6 * i["total_runs"] / i["legal_balls"], 2) if i["legal_balls"] else None,
                         "extras": extras, "batting": bat, "bowling": bowl, "overs_list": overs, "fall_of_wickets": fow,
                         "phases": {p["phase"]: p for p in phases}})
    parts = db.q("""SELECT partnership_id, innings_no, p1, p2, runs, balls, wicket_no, p1_runs, p2_runs FROM partnerships WHERE match_id = ?
                    ORDER BY runs DESC LIMIT 5""", [match_id])
    for p in parts:
        p["p1_name"], p["p2_name"] = _nm(db, p["p1"]), _nm(db, p["p2"])
    events = match_events(db, match_id, out_inns)
    # Battles within the match, with the career meeting totals for context
    battles = db.q("""SELECT b.batter_id, b.bowler_id, count(*) FILTER (WHERE b.wides = 0) AS balls, sum(b.runs_batter) AS runs,
                             count(*) FILTER (WHERE d.delivery_id IS NOT NULL) AS outs, any_value(bt.balls) AS career_balls,
                             any_value(bt.runs) AS career_runs, any_value(bt.outs) AS career_outs
                      FROM balls b LEFT JOIN dis d ON d.delivery_id = b.delivery_id AND d.player_out_id = b.batter_id AND d.bowler_credited
                      LEFT JOIN battles bt ON bt.batter_id = b.batter_id AND bt.bowler_id = b.bowler_id AND bt.gender = b.gender
                      WHERE b.match_id = ? GROUP BY 1, 2 HAVING count(*) FILTER (WHERE b.wides = 0) >= 6
                      ORDER BY outs DESC, balls DESC LIMIT 10""", [match_id])
    for b in battles:
        b["batter"], b["bowler"] = _nm(db, b["batter_id"]), _nm(db, b["bowler_id"])
    records = match_records(db, m, out_inns)
    exp = None
    if sdx and len(out_inns) > 1:
        rows = db.q("""SELECT b.delivery_id, b.ball_label, b.batter, b.bowler, b.runs_total, b.n_wickets, s.sdx FROM balls b JOIN situation s USING (delivery_id)
                       WHERE b.match_id = ? AND b.innings_no = 2 ORDER BY b.seq""", [match_id])
        swings = []
        for a, b in zip(rows, rows[1:]):
            swings.append({"delivery_id": a["delivery_id"], "ball_label": a["ball_label"], "batter": a["batter"], "bowler": a["bowler"],
                           "event": "W" if a["n_wickets"] else str(a["runs_total"]), "from": a["sdx"], "to": b["sdx"], "change": round(b["sdx"] - a["sdx"], 1)})
        swings.sort(key=lambda x: -abs(x["change"]))
        exp = {"label": "Largest changes in Situation Difficulty — Experimental", "rows": swings[:5], "series": [r["sdx"] for r in rows],
               "note": "MODELLED (SDX v0.1). Not a validated turning-point measure."}
    return {"match": m, "innings": out_inns, "partnerships": parts, "events": events, "battles": battles, "records": records,
            "coverage": coverage_note(db, m["competition"], m["gender"]), "experimental": exp,
            "turning_points": "Not shown: CRICINTEL has no validated turning-point algorithm. Key events below are factual and defined."}


def match_events(db: DB, match_id: str, inns: list[dict]) -> list[dict]:
    ev = []
    allb = db.q("""SELECT innings_no, seq, ball_label, legal, n_wickets, runs_total, runs_batter, score_before, wickets_before, delivery_id,
                          batter_id, batter_runs_before, batter_balls_before, wides FROM balls WHERE match_id = ? ORDER BY innings_no, seq""", [match_id])
    for i in inns:
        n, team = i["innings_no"], i["batting_team"]
        ov = sorted(i["overs_list"], key=lambda o: -o["runs"])
        if ov:
            o = ov[0]
            ev.append({"innings_no": n, "kind": "biggest_over", "label": f"{team}'s biggest over: {o['runs']} runs in over {o['over'] + 1}",
                       "definition": "Over with the most runs (incl. extras) in the innings.", "over": o["over"], "pos": o["over"] * 6 + 6})
        balls = [b for b in allb if b["innings_no"] == n]
        wk_idx = [k for k, b in enumerate(balls) if b["n_wickets"]]
        legal_idx, c = {}, 0
        for k, b in enumerate(balls):
            c += 1 if b["legal"] else 0
            legal_idx[k] = c
        used = set()
        for j in range(len(wk_idx) - COLLAPSE_WKTS + 1):
            a, z = wk_idx[j], wk_idx[j + COLLAPSE_WKTS - 1]
            if a in used:
                continue
            span = legal_idx[z] - legal_idx[a] + 1
            runs = balls[z]["score_before"] + balls[z]["runs_total"] - balls[a]["score_before"]
            if span <= COLLAPSE_BALLS and runs <= COLLAPSE_RUNS:
                ev.append({"innings_no": n, "kind": "collapse", "delivery_id": balls[a]["delivery_id"], "pos": legal_idx[a],
                           "label": f"{team} lost {COLLAPSE_WKTS} wickets for {runs} runs in {span} balls ({balls[a]['ball_label']}–{balls[z]['ball_label']})",
                           "definition": f"A cluster of {COLLAPSE_WKTS}+ wickets within {COLLAPSE_BALLS} legal balls for ≤ {COLLAPSE_RUNS} runs."})
                used.update(wk_idx[j:j + COLLAPSE_WKTS])
        nm = {b["batter_id"]: b["name"] for b in i["batting"]}
        for k, b in enumerate(balls):  # milestones, read straight from the ball sequence
            for mark in (50, 100):
                if b["batter_runs_before"] < mark <= b["batter_runs_before"] + b["runs_batter"]:
                    ev.append({"innings_no": n, "kind": "milestone", "delivery_id": b["delivery_id"], "pos": legal_idx[k],
                               "label": f"{nm.get(b['batter_id'], b['batter_id'])} reached {mark} off {b['batter_balls_before'] + (0 if b['wides'] else 1)} balls ({b['ball_label']})",
                               "definition": "Batting milestone."})
        for b in i["bowling"]:
            if b["wickets"] >= 4:
                ev.append({"innings_no": n, "kind": "haul", "label": f"{b['name']} took {b['wickets']}/{b['runs']}", "definition": "Four or more wickets in the innings.", "pos": 10 ** 6})
    return sorted(ev, key=lambda e: (e["innings_no"], e["pos"]))  # chronological


def match_records(db: DB, m: dict, inns: list[dict]) -> list[dict]:
    """Where this match's numbers rank within covered data (DERIVED; covered data only, not official records)."""
    out = []
    if not m["competition"]:
        return out
    totals = db.q("""SELECT ii.total_runs AS r FROM innings ii JOIN team_results t USING (match_id)
                     WHERE t.competition = ? AND t.gender = ? AND NOT ii.super_over""", [m["competition"], m["gender"]])
    allt = sorted((x["r"] for x in totals if x["r"] is not None), reverse=True)
    for i in inns:
        rank = sum(1 for x in allt if x > i["total_runs"]) + 1
        if rank <= 10:
            out.append({"label": f"{i['batting_team']}'s {i['total_runs']} is the #{rank} highest innings total in covered {m['competition']} data", "prov": "DERIVED"})
    top = db.q("SELECT runs FROM bat_innings WHERE competition = ? AND gender = ? ORDER BY runs DESC LIMIT 11", [m["competition"], m["gender"]])
    tops = [x["runs"] for x in top]
    for i in inns:
        for b in i["batting"]:
            rank = sum(1 for x in tops if x > b["runs"]) + 1
            if b["runs"] >= 50 and rank <= 10:
                out.append({"label": f"{b['name']}'s {b['runs']}{'*' if b['not_out'] else ''} is the #{rank} highest score in covered {m['competition']} data",
                            "prov": "DERIVED"})
    return out


# ------------------------------------------------------------------ Competition
def competitions_index(db: DB) -> list[dict]:
    rows = db.q("""SELECT competition, gender, any_value(format_group) AS format, any_value(team_type) AS team_type, count(*) AS matches,
                          count(DISTINCT season) AS editions, min(start_date) AS first, max(start_date) AS last FROM team_results
                   WHERE competition IS NOT NULL GROUP BY 1, 2 HAVING count(*) >= 6 ORDER BY matches DESC""")
    for r in rows:
        r["first"], r["last"] = str(r["first"]), str(r["last"])
    return rows


def competition_page(db: DB, name: str, gender: str, season: str | None = None) -> dict | None:
    w, p = "competition = ? AND gender = ?", [name, gender]
    base = db.q1(f"SELECT count(*) AS n, any_value(format_group) AS fmt, min(start_date) AS d0, max(start_date) AS d1 FROM team_results WHERE {w}", p)
    if not base["n"]:
        return None
    editions = db.q(f"""SELECT season, count(*) AS matches, min(start_date) AS d0, max(start_date) AS d1,
                             arg_max(winner_c, CASE WHEN event_stage = 'Final' THEN 1 ELSE 0 END) AS final_winner, bool_or(event_stage = 'Final') AS has_final
                        FROM team_results WHERE {w} GROUP BY 1 ORDER BY d0""", p)
    for e in editions:
        e["d0"], e["d1"] = str(e["d0"]), str(e["d1"])
        if not e["has_final"]:
            e["final_winner"] = None
    if season:
        w += " AND season = ?"; p.append(season)
    fmt = base["fmt"]
    minb = 120 if fmt == "T20" else 300
    teams = db.q(f"""SELECT team, count(*) AS played, count(*) FILTER (WHERE winner_c = team) AS won,
                            count(*) FILTER (WHERE winner_c IS NOT NULL AND winner_c <> team) AS lost
                     FROM (SELECT match_id, ta AS team, winner_c FROM team_results WHERE {w} UNION ALL SELECT match_id, tb, winner_c FROM team_results WHERE {w})
                     GROUP BY 1 ORDER BY won DESC, played DESC""", p + p)
    bw = w.replace("competition", "b.competition").replace("gender", "b.gender").replace("season", "b.season")
    runs = db.q(f"""SELECT batter_id AS pid, sum(runs) AS runs, sum(balls) AS balls, count(*) AS inns, count(*) FILTER (WHERE NOT not_out) AS outs,
                           max(runs) AS hs FROM bat_innings b WHERE {bw} GROUP BY 1 ORDER BY runs DESC LIMIT 10""", p)
    wk = db.q(f"""SELECT bowler_id AS pid, sum(wickets) AS wickets, sum(balls) AS balls, sum(runs) AS runs FROM bowl_innings b WHERE {bw}
                  GROUP BY 1 ORDER BY wickets DESC, runs LIMIT 10""", p)
    sr = db.q(f"""SELECT batter_id AS pid, sum(runs) AS runs, sum(balls) AS balls, round(100.0 * sum(runs) / sum(balls), 1) AS sr FROM bat_innings b
                  WHERE {bw} GROUP BY 1 HAVING sum(balls) >= ? ORDER BY sr DESC LIMIT 10""", p + [minb])
    econ = db.q(f"""SELECT bowler_id AS pid, sum(balls) AS balls, sum(runs) AS runs, round(6.0 * sum(runs) / sum(balls), 2) AS econ FROM bowl_innings b
                    WHERE {bw} GROUP BY 1 HAVING sum(balls) >= ? ORDER BY econ LIMIT 10""", p + [minb])
    hs = db.q(f"""SELECT match_id, innings_no, batter_id AS pid, runs, balls, not_out, opponent, start_date FROM bat_innings b WHERE {bw}
                  ORDER BY runs DESC, balls LIMIT 8""", p)
    bf = db.q(f"""SELECT match_id, innings_no, bowler_id AS pid, wickets, runs, balls, opponent, start_date FROM bowl_innings b WHERE {bw}
                  ORDER BY wickets DESC, runs LIMIT 8""", p)
    pw = w.replace("competition", "p.competition").replace("gender", "p.gender").replace("season", "s.season")
    parts = db.q(f"""SELECT p.partnership_id, p.match_id, p.innings_no, p.p1, p.p2, p.runs, p.balls, p.start_date FROM partnerships p
                     JOIN team_results s USING (match_id) WHERE {pw} ORDER BY p.runs DESC LIMIT 8""", p)
    battles = db.q(f"""SELECT b.batter_id, b.bowler_id, count(*) FILTER (WHERE b.wides = 0) AS balls, sum(b.runs_batter) AS runs,
                              count(*) FILTER (WHERE d.delivery_id IS NOT NULL) AS outs
                       FROM balls b LEFT JOIN dis d ON d.delivery_id = b.delivery_id AND d.player_out_id = b.batter_id AND d.bowler_credited
                       WHERE {bw} GROUP BY 1, 2 ORDER BY balls DESC LIMIT 8""", p)
    trend = db.q(f"""SELECT b.season, round(6.0 * sum(runs_total) / count(*) FILTER (WHERE legal), 2) AS run_rate,
                            round(100.0 * count(*) FILTER (WHERE is_four OR is_six) / count(*) FILTER (WHERE wides = 0), 1) AS boundary_pct,
                            round(100.0 * count(*) FILTER (WHERE legal AND runs_total = 0) / count(*) FILTER (WHERE legal), 1) AS dot_pct,
                            count(DISTINCT match_id) AS matches, min(start_date) AS d0
                     FROM balls b WHERE b.competition = ? AND b.gender = ? GROUP BY 1 ORDER BY d0""", [name, gender])
    for r in trend:
        r["d0"] = str(r["d0"])
    for L in (runs, wk, sr, econ, hs, bf):
        for r in L:
            r["name"] = _nm(db, r["pid"])
            if "start_date" in r:
                r["start_date"] = str(r["start_date"])
    for x in parts:
        x["p1_name"], x["p2_name"], x["start_date"] = _nm(db, x["p1"]), _nm(db, x["p2"]), str(x["start_date"])
    for x in battles:
        x["batter"], x["bowler"] = _nm(db, x["batter_id"]), _nm(db, x["bowler_id"])
    matches = db.q(f"""SELECT match_id, start_date, team1, team2, winner, event_stage, venue, i1_runs, i1_wkts, i2_runs, i2_wkts FROM team_results
                       WHERE {w} ORDER BY start_date DESC LIMIT 60""", p)
    for x in matches:
        x["start_date"] = str(x["start_date"])
    return {"name": name, "gender": gender, "format": fmt, "season": season, "matches_total": base["n"], "first": str(base["d0"]), "last": str(base["d1"]),
            "coverage": coverage_note(db, name, gender), "editions": editions, "teams": teams,
            "leaders": {"runs": runs, "wickets": wk, "strike_rate": sr, "economy": econ}, "min_balls": minb,
            "highest_scores": hs, "best_figures": bf, "partnerships": parts, "battles": battles, "trend": trend, "matches": matches,
            "definitions": {"strike_rate": f"Runs per 100 balls faced, minimum {minb} balls.", "economy": f"Runs conceded per 6 legal balls, minimum {minb} balls.",
                            "final_winner": "Winner of the match recorded as the final (Cricsheet event stage). Blank where no final is in the data."}}


# ------------------------------------------------------------------ Rivalry (team v team) and team overview
def rivalry_page(db: DB, a: str, b: str | None, gender: str, fmt: str | None = None, competition: str | None = None) -> dict | None:
    a = canon(a)
    if not b:
        w, p = "(ta = ? OR tb = ?) AND gender = ?", [a, a, gender]
        if fmt:
            w += " AND format_group = ?"; p.append(fmt)
        opp = db.q(f"""SELECT CASE WHEN ta = ? THEN tb ELSE ta END AS opponent, count(*) AS played, count(*) FILTER (WHERE winner_c = ?) AS won,
                              count(*) FILTER (WHERE winner_c IS NOT NULL AND winner_c <> ?) AS lost FROM team_results WHERE {w}
                       GROUP BY 1 ORDER BY played DESC""", [a, a, a] + p)
        if not opp:
            return None
        return {"team": a, "gender": gender, "format": fmt, "opponents": opp, "played": sum(o["played"] for o in opp),
                "won": sum(o["won"] for o in opp), "lost": sum(o["lost"] for o in opp)}
    b = canon(b)
    ta, tb = sorted([a, b])
    w, p = "ta = ? AND tb = ? AND gender = ?", [ta, tb, gender]
    if fmt:
        w += " AND format_group = ?"; p.append(fmt)
    if competition:
        w += " AND competition = ?"; p.append(competition)
    ms = db.q(f"SELECT * FROM team_results WHERE {w} ORDER BY start_date DESC", p)
    if not ms:
        return None
    for x in ms:
        x["start_date"] = str(x["start_date"])
    res = {"a": ta, "b": tb, "gender": gender, "format": fmt, "competition": competition, "played": len(ms),
           "wins": {ta: sum(1 for x in ms if x["winner_c"] == ta), tb: sum(1 for x in ms if x["winner_c"] == tb)},
           "no_result": sum(1 for x in ms if not x["winner_c"]), "matches": ms[:40],
           "formats": sorted({x["format_group"] for x in ms}), "competitions": sorted({x["competition"] or "Bilateral" for x in ms})}
    res["biggest_totals"] = sorted([{"team": x["i1_team"], "runs": x["i1_runs"], "wkts": x["i1_wkts"], "match_id": x["match_id"], "date": x["start_date"]} for x in ms if x["i1_runs"]]
                                   + [{"team": x["i2_team"], "runs": x["i2_runs"], "wkts": x["i2_wkts"], "match_id": x["match_id"], "date": x["start_date"]} for x in ms if x["i2_runs"]],
                                   key=lambda r: -r["runs"])[:5]
    close = [x for x in ms if (x["win_by_runs"] is not None and x["win_by_runs"] <= 10) or (x["win_by_wickets"] is not None and x["win_by_wickets"] <= 2)
             or x["result"] == "tie"]
    res["closest"] = close[:6]
    res["biggest_wins"] = sorted([x for x in ms if x["win_by_runs"]], key=lambda x: -x["win_by_runs"])[:3] + \
        sorted([x for x in ms if x["win_by_wickets"] and x["i2_balls"]], key=lambda x: x["i2_balls"])[:3]
    ids = [x["match_id"] for x in ms]
    q = ",".join("?" * len(ids))
    res["run_environment"] = db.q(f"""SELECT format_group, round(avg(i1_runs), 1) AS avg_first_innings, count(*) AS matches,
                                          round(6.0 * sum(i1_runs + coalesce(i2_runs, 0)) / sum(i1_balls + coalesce(i2_balls, 0)), 2) AS run_rate
                                   FROM team_results WHERE match_id IN ({q}) GROUP BY 1""", ids)
    bats = db.q(f"""SELECT batter_id AS pid, any_value(team) AS team, sum(runs) AS runs, sum(balls) AS balls, count(*) AS inns, max(runs) AS hs
                    FROM bat_innings WHERE match_id IN ({q}) GROUP BY 1 ORDER BY runs DESC LIMIT 8""", ids)
    bowls = db.q(f"""SELECT bowler_id AS pid, any_value(team) AS team, sum(wickets) AS wickets, sum(runs) AS runs, sum(balls) AS balls
                     FROM bowl_innings WHERE match_id IN ({q}) GROUP BY 1 ORDER BY wickets DESC, runs LIMIT 8""", ids)
    parts = db.q(f"""SELECT partnership_id, match_id, innings_no, p1, p2, runs, balls, batting_team, start_date FROM partnerships WHERE match_id IN ({q})
                     ORDER BY runs DESC LIMIT 6""", ids)
    battles = db.q(f"""SELECT b.batter_id, b.bowler_id, count(*) FILTER (WHERE b.wides = 0) AS balls, sum(b.runs_batter) AS runs,
                              count(DISTINCT b.match_id) AS matches, count(*) FILTER (WHERE d.delivery_id IS NOT NULL) AS outs
                       FROM balls b LEFT JOIN dis d ON d.delivery_id = b.delivery_id AND d.player_out_id = b.batter_id AND d.bowler_credited
                       WHERE b.match_id IN ({q}) GROUP BY 1, 2 HAVING count(DISTINCT b.match_id) >= 3 ORDER BY balls DESC LIMIT 10""", ids)
    inn = db.q(f"""SELECT match_id, innings_no, batter_id AS pid, runs, balls, not_out, team, start_date FROM bat_innings WHERE match_id IN ({q})
                   ORDER BY runs DESC LIMIT 5""", ids)
    spl = db.q(f"""SELECT match_id, innings_no, bowler_id AS pid, wickets, runs, balls, team, start_date FROM bowl_innings WHERE match_id IN ({q})
                   ORDER BY wickets DESC, runs LIMIT 5""", ids)
    trend = db.q(f"""SELECT year, count(*) AS played, count(*) FILTER (WHERE winner_c = ?) AS a_won, count(*) FILTER (WHERE winner_c = ?) AS b_won
                     FROM team_results WHERE match_id IN ({q}) GROUP BY 1 ORDER BY 1""", [ta, tb] + ids)
    for L in (bats, bowls, inn, spl):
        for r in L:
            r["name"] = _nm(db, r["pid"])
            if "start_date" in r:
                r["start_date"] = str(r["start_date"])
    for x in parts:
        x["p1_name"], x["p2_name"], x["start_date"] = _nm(db, x["p1"]), _nm(db, x["p2"]), str(x["start_date"])
    for x in battles:
        x["batter"], x["bowler"] = _nm(db, x["batter_id"]), _nm(db, x["bowler_id"])
    res.update(batters=bats, bowlers=bowls, partnerships=parts, battles=battles, innings=inn, spells=spl, trend=trend,
               renamed_note="Renamed franchises are grouped (e.g. Kings XI Punjab → Punjab Kings); original names stay on each match." if
               any(k in (ta, tb) for k in TEAM_CANON.values()) else None)
    return res


# ------------------------------------------------------------------ Career explorer
def career(db: DB, pid: str, year: int | None = None) -> dict | None:
    prof = db.q1("SELECT name, genders, teams FROM player_profile WHERE person_id = ?", [pid])
    if not prof:
        return None
    years = db.q("""WITH b AS (SELECT year, format_group, sum(runs) AS runs, sum(balls) AS balls, count(*) AS inns, count(*) FILTER (WHERE NOT not_out) AS outs,
                                    count(*) FILTER (WHERE runs >= 50 AND runs < 100) AS fifties, count(*) FILTER (WHERE runs >= 100) AS hundreds, max(runs) AS hs
                             FROM bat_innings WHERE batter_id = ? GROUP BY 1, 2),
                         w AS (SELECT year, format_group, sum(wickets) AS wickets, sum(balls) AS bballs, sum(runs) AS bruns, count(*) AS spells
                             FROM bowl_innings WHERE bowler_id = ? GROUP BY 1, 2)
                    SELECT coalesce(b.year, w.year) AS year, coalesce(b.format_group, w.format_group) AS format, b.*, w.* EXCLUDE (year, format_group)
                    FROM b FULL JOIN w ON b.year = w.year AND b.format_group = w.format_group ORDER BY 1, 2""", [pid, pid])
    for y in years:
        y.pop("format_group", None)
        y["sr"] = round(100 * y["runs"] / y["balls"], 1) if y.get("balls") else None
        y["avg"] = round(y["runs"] / y["outs"], 1) if y.get("outs") else None
        y["econ"] = round(6 * y["bruns"] / y["bballs"], 2) if y.get("bballs") else None
    ys = sorted({y["year"] for y in years})
    span = list(range(ys[0], ys[-1] + 1)) if ys else []
    gaps = [x for x in span if x not in ys]
    teams = db.q("""SELECT year, list(DISTINCT team) AS teams, list(DISTINCT competition) AS comps FROM bat_innings WHERE batter_id = ? GROUP BY 1
                    UNION ALL SELECT year, list(DISTINCT team), list(DISTINCT competition) FROM bowl_innings WHERE bowler_id = ? GROUP BY 1""", [pid, pid])
    by_year_teams: dict = {}
    for t in teams:
        x = by_year_teams.setdefault(t["year"], {"teams": set(), "comps": set()})
        x["teams"] |= set(t["teams"] or []); x["comps"] |= {c for c in (t["comps"] or []) if c}
    milestones = db.q("""WITH c AS (SELECT format_group, start_date, match_id, innings_no, runs,
                              sum(runs) OVER (PARTITION BY format_group ORDER BY start_date, match_id, innings_no) AS cum FROM bat_innings WHERE batter_id = ?)
                         SELECT format_group, min(start_date) FILTER (WHERE cum >= 1000) AS d1000, min(start_date) FILTER (WHERE cum >= 5000) AS d5000,
                                min(start_date) FILTER (WHERE cum >= 10000) AS d10000, min(start_date) FILTER (WHERE runs >= 100) AS first_100,
                                min(start_date) FILTER (WHERE runs >= 50) AS first_50 FROM c GROUP BY 1""", [pid])
    ms = []
    for m in milestones:
        for k, lab in (("first_50", "First fifty"), ("first_100", "First hundred"), ("d1000", "1,000 runs"), ("d5000", "5,000 runs"), ("d10000", "10,000 runs")):
            if m[k]:
                ms.append({"format": m["format_group"], "label": f"{lab} ({m['format_group']}, covered data)", "date": str(m[k]), "year": m[k].year})
    ms.sort(key=lambda x: x["date"])
    # peaks and troughs: years with >= 300 balls (T20) / 500 (ODI), best and worst strike rate per format
    pt = []
    for f, minb in (("T20", 300), ("ODI", 500)):
        q = [y for y in years if y["format"] == f and (y.get("balls") or 0) >= minb]
        if len(q) >= 3:
            hi, lo = max(q, key=lambda y: y["sr"]), min(q, key=lambda y: y["sr"])
            pt += [{"format": f, "kind": "peak", "year": hi["year"], "sr": hi["sr"], "balls": hi["balls"]},
                   {"format": f, "kind": "trough", "year": lo["year"], "sr": lo["sr"], "balls": lo["balls"]}]
    out = {"pid": pid, "name": prof["name"], "years": years, "span": span, "gaps": gaps, "milestones": ms, "peaks_troughs": pt,
           "teams_by_year": {y: {"teams": sorted(v["teams"]), "competitions": sorted(v["comps"])} for y, v in by_year_teams.items()},
           "note": "Covered data only. Years with no covered matches are shown as gaps; nothing is interpolated.",
           "peak_rule": "Peak/trough = best/worst strike-rate year with at least 300 (T20) or 500 (ODI) balls faced; needs 3+ qualifying years."}
    if year:
        inn = db.q("""SELECT match_id, innings_no, runs, balls, not_out, opponent, competition, format_group, start_date FROM bat_innings
                      WHERE batter_id = ? AND year = ? ORDER BY runs DESC LIMIT 12""", [pid, year])
        spl = db.q("""SELECT match_id, innings_no, wickets, runs, balls, opponent, competition, format_group, start_date FROM bowl_innings
                      WHERE bowler_id = ? AND year = ? ORDER BY wickets DESC, runs LIMIT 8""", [pid, year])
        opp = db.q("""SELECT bowler_id, count(*) FILTER (WHERE wides = 0) AS balls, sum(runs_batter) AS runs, count(*) FILTER (WHERE n_wickets > 0) AS w
                      FROM balls WHERE batter_id = ? AND year = ? GROUP BY 1 ORDER BY balls DESC LIMIT 6""", [pid, year])
        opp_teams = db.q("""SELECT opponent, count(*) AS inns, sum(runs) AS runs, sum(balls) AS balls FROM bat_innings WHERE batter_id = ? AND year = ?
                            GROUP BY 1 ORDER BY inns DESC LIMIT 6""", [pid, year])
        phase = db.q("""SELECT phase, count(*) FILTER (WHERE wides = 0) AS balls, round(100.0 * sum(runs_batter) / count(*) FILTER (WHERE wides = 0), 1) AS sr
                        FROM balls WHERE batter_id = ? AND year = ? GROUP BY 1""", [pid, year])
        for L in (inn, spl):
            for r in L:
                r["start_date"] = str(r["start_date"])
        for o in opp:
            o["bowler"] = _nm(db, o["bowler_id"])
        out["year_detail"] = {"year": year, "innings": inn, "spells": spl, "bowlers_faced": opp, "opponents": opp_teams, "phases": phase,
                              "in_gap": year in gaps}
    return out
