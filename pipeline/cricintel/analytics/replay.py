"""Delivery Replay, Innings Story and Spell Story: walk through real cricket ball by ball.

Only event data is used. Each field carries its provenance; nothing about the ball's flight, pitch point,
line, length, shot or fielder position is produced, because the source doesn't record it.
"""
from __future__ import annotations

from ..db import DB
from .player import delivery_cards

CTX_FIELDS = ["wickets_in_hand", "balls_left", "progress_pct", "chase_state", "batter_stage", "batter_balls_since_boundary",
              "team_balls_since_boundary", "recent_window", "recent_runs", "recent_wickets", "team_dot_streak", "batter_dot_streak",
              "team_boundary_streak", "partnership_runs_before", "partnership_balls_before", "current_rate", "limit_uncertain"]


def symbol(r: dict) -> str:
    """Scorebook symbol for a delivery: W, 4, 6, '•' for a dot, '1wd', '1nb', 'lb', 'b'."""
    if r.get("n_wickets"):
        return "W"
    if r.get("wides"):
        return f"{r['wides']}wd"
    if r.get("noballs"):
        return f"{r['runs_batter'] or ''}nb".lstrip("0") if r["runs_batter"] else "nb"
    if r.get("is_six"):
        return "6"
    if r.get("is_four"):
        return "4"
    if r["runs_total"] == 0:
        return "•"
    if r["runs_batter"] == 0 and (r.get("byes") or r.get("legbyes")):
        return f"{r['runs_extras']}{'b' if r.get('byes') else 'lb'}"
    return str(r["runs_total"])


def _result_line(m: dict) -> str | None:
    if m.get("winner"):
        if m.get("win_by_runs"):
            margin = f"by {m['win_by_runs']} run{'s' if m['win_by_runs'] != 1 else ''}"
        elif m.get("win_by_wickets"):
            margin = f"by {m['win_by_wickets']} wicket{'s' if m['win_by_wickets'] != 1 else ''}"
        else:
            margin = ""
        return f"{m['winner']} won {margin}".strip() + (f" ({m['method']})" if m.get("method") else "")
    return {"tie": "Match tied", "no result": "No result", "draw": "Draw"}.get(m.get("result") or "", m.get("result"))


def match_meta(db: DB, match_id: str) -> dict:
    m = db.q1("""SELECT match_id, start_date, competition, gender, format_group, team_type, venue, city, team1, team2, toss_winner,
                        toss_decision, winner, win_by_runs, win_by_wickets, result, method, event_stage, player_of_match
                 FROM matches WHERE match_id = ?""", [match_id])
    if not m:
        return {}
    inns = db.q("""SELECT innings_no, batting_team, total_runs, total_wickets, legal_balls, target_runs FROM innings
                   WHERE match_id = ? AND NOT super_over ORDER BY innings_no""", [match_id])
    m["result_line"] = _result_line(m)
    m["innings"] = [{**i, "overs": f"{i['legal_balls'] // 6}.{i['legal_balls'] % 6}" if i["legal_balls"] is not None else None} for i in inns]
    m["start_date"] = str(m["start_date"])
    return m


def delivery_replay(db: DB, did: str, sdx=None) -> dict | None:
    cards = delivery_cards(db, [did])
    if not cards:
        return None
    c = cards[0]
    b = db.q1(f"""SELECT seq, legal, n_wickets, wides, noballs, byes, legbyes, runs_batter, runs_extras, runs_total, is_four, is_six,
                         batter_runs_before, batter_balls_before, wickets_before, score_before, runs_required, balls_left, chasing,
                         format_group, gender, legal_balls_before, innings_balls_limit, target_runs, required_rate, phase, {', '.join(CTX_FIELDS)}
                  FROM balls WHERE delivery_id = ?""", [did])
    mid, inn = c["match_id"], c["innings_no"]
    nb = db.q("""SELECT delivery_id, seq, innings_no FROM balls WHERE match_id = ? AND
                   ((innings_no = ? AND seq IN (?, ?)) OR (innings_no = ? + 1 AND seq = 1) OR (innings_no = ? - 1))
                 ORDER BY innings_no, seq""", [mid, inn, b["seq"] - 1, b["seq"] + 1, inn, inn])
    prev = next((x["delivery_id"] for x in nb if x["innings_no"] == inn and x["seq"] == b["seq"] - 1), None)
    if prev is None:
        prev = next((x["delivery_id"] for x in reversed(nb) if x["innings_no"] == inn - 1), None)
    nxt = next((x["delivery_id"] for x in nb if x["innings_no"] == inn and x["seq"] == b["seq"] + 1), None)
    if nxt is None:
        nxt = next((x["delivery_id"] for x in nb if x["innings_no"] == inn + 1 and x["seq"] == 1), None)
    recent = db.q("""SELECT delivery_id, ball_label, batter, n_wickets, wides, noballs, byes, legbyes, runs_batter, runs_extras, runs_total,
                            is_four, is_six FROM balls WHERE match_id = ? AND innings_no = ? AND seq < ? ORDER BY seq DESC LIMIT 12""",
                  [mid, inn, b["seq"]])
    nexts = db.q("""SELECT delivery_id, ball_label, batter, n_wickets, wides, noballs, byes, legbyes, runs_batter, runs_extras, runs_total,
                           is_four, is_six FROM balls WHERE match_id = ? AND innings_no = ? AND seq > ? ORDER BY seq LIMIT 6""",
                 [mid, inn, b["seq"]])
    wk = db.q("""SELECT player_out_id, player_out, kind, route, route_prov, route_confidence, fielder, fielder_id, substitute, keeper_id,
                        keeper_conf, bowler_credited, striker_out FROM dis WHERE delivery_id = ? ORDER BY wicket_idx""", [did])
    spell = db.q1("""SELECT spell_no FROM spells WHERE match_id = ? AND innings_no = ? AND bowler_id = ? AND over = ?""",
                  [mid, inn, c["bowler"]["id"], c["over"]]) if getattr(db, "has_context", False) else None
    after = db.q1("""SELECT score_before, wickets_before FROM balls WHERE match_id = ? AND innings_no = ? AND seq > ? ORDER BY seq LIMIT 1""",
                  [mid, inn, b["seq"]])
    bat_after_r = b["batter_runs_before"] + b["runs_batter"]
    bat_after_b = b["batter_balls_before"] + (0 if b["wides"] else 1)
    out = {**c, "seq": b["seq"], "legal": b["legal"], "symbol": symbol(b),
           "match": match_meta(db, mid),
           "batter_innings": {"before": f"{b['batter_runs_before']} ({b['batter_balls_before']})", "after": f"{bat_after_r} ({bat_after_b})",
                              "prov": "DERIVED"},
           "context_v1": {k: b[k] for k in CTX_FIELDS} | {"prov": "DERIVED"},
           "situation": {"format": b["format_group"], "innings_no": inn, "score": b["score_before"], "wickets": b["wickets_before"],
                         "legal_balls": b["legal_balls_before"], "limit_balls": b["innings_balls_limit"], "target": b["target_runs"],
                         "runs_required": b["runs_required"], "balls_left": b["balls_left"], "rrr": b["required_rate"], "crr": b["current_rate"],
                         "phase": b["phase"], "prov": "DERIVED"},
           "wicket_detail": wk,
           "recent": [{**r, "symbol": symbol(r)} for r in reversed(recent)],
           "following": [{**r, "symbol": symbol(r)} for r in nexts],
           "prev_id": prev, "next_id": nxt,
           "links": {"innings": {"match_id": mid, "innings_no": inn, "batter_id": c["batter"]["id"]},
                     "spell": {"match_id": mid, "innings_no": inn, "bowler_id": c["bowler"]["id"], "spell_no": spell["spell_no"] if spell else None}},
           "score_after_next": f"{after['score_before']}/{after['wickets_before']}" if after else None,
           "not_recorded": ["ball path", "pitch point", "line", "length", "speed", "shot", "bat contact / edge", "fielder positions"]}
    if sdx and b["chasing"] and b["runs_required"] is not None:
        s = sdx.score(b["format_group"], b["gender"], b["runs_required"], b["balls_left"], b["wickets_before"])
        if s:
            out["experimental"] = {"sdx": s, "swing": sdx.swing(b["format_group"], b["gender"], b["runs_required"], b["balls_left"],
                                                                 b["wickets_before"]), "version": sdx.a["version"], "prov": "MODELLED"}
    return out


def player_innings(db: DB, pid: str, sort: str = "recent", limit: int = 30, fmt: str | None = None, q: str | None = None) -> list[dict]:
    w, p = "batter_id = ?", [pid]
    if fmt:
        w += " AND format_group = ?"; p.append(fmt)
    order = {"recent": "start_date DESC", "runs": "runs DESC, balls ASC", "sr": "CASE WHEN balls >= 15 THEN runs * 1.0 / balls END DESC NULLS LAST"}[sort]
    rows = db.q(f"""
      WITH x AS (
        SELECT match_id, innings_no, any_value(start_date) AS start_date, any_value(competition) AS competition,
               any_value(format_group) AS format_group, any_value(bowling_team) AS opponent, any_value(batting_team) AS team,
               sum(runs_batter) AS runs, count(*) FILTER (WHERE wides = 0) AS balls,
               count(*) FILTER (WHERE is_four) AS fours, count(*) FILTER (WHERE is_six) AS sixes, any_value(winner) AS winner,
               min(over) AS from_over, max(over) AS to_over
        FROM balls WHERE {w} GROUP BY 1, 2)
      SELECT x.*, d.kind AS out_kind, d.bowler AS out_bowler FROM x
      LEFT JOIN dis d ON d.match_id = x.match_id AND d.innings_no = x.innings_no AND d.player_out_id = ? AND d.counts_as_dismissal
      ORDER BY {order} LIMIT ?""", [*p, pid, limit])
    for r in rows:
        r["not_out"] = r["out_kind"] is None
        r["start_date"] = str(r["start_date"])
        r["result"] = "won" if r["winner"] == r["team"] else ("lost" if r["winner"] else "no result/tie")
    if q:
        rows = [r for r in rows if q.lower() in (r["opponent"] + r["competition"]).lower()]
    return rows


def innings_story(db: DB, match_id: str, inn: int, pid: str, sdx=None) -> dict | None:
    team = db.q(f"""SELECT delivery_id, seq, ball_label, over, phase, legal, batter_id, batter, non_striker_id, non_striker, bowler_id, bowler,
                          runs_batter, runs_extras, runs_total, is_four, is_six, wides, noballs, byes, legbyes, n_wickets, score_before,
                          wickets_before, batter_runs_before, batter_balls_before, required_rate, runs_required, balls_left, chasing,
                          format_group, gender, partnership_runs_before, partnership_balls_before
                    FROM balls WHERE match_id = ? AND innings_no = ? ORDER BY seq""", [match_id, inn])
    involved = [r for r in team if pid in (r["batter_id"], r["non_striker_id"])]
    if not involved:
        return None
    first, last = involved[0]["seq"], involved[-1]["seq"]
    span = [r for r in team if first <= r["seq"] <= last]
    wk = {(r["delivery_id"], r["player_out_id"]): r for r in db.q(
        "SELECT delivery_id, player_out_id, player_out, kind, route, fielder, bowler_credited FROM dis WHERE match_id = ? AND innings_no = ?",
        [match_id, inn])}
    prof = db.q1("SELECT name FROM player_profile WHERE person_id = ?", [pid])
    name = prof["name"] if prof else (next(r["batter"] for r in team if r["batter_id"] == pid) if any(r["batter_id"] == pid for r in team) else
                                      next(r["non_striker"] for r in involved))
    balls, events = [], []
    runs = faced = 0
    prev_phase, prev_partner, milestones = None, None, {50: False, 100: False, 150: False}
    window: list[int] = []
    for r in span:
        on_strike = r["batter_id"] == pid
        partner_id = r["non_striker_id"] if on_strike else r["batter_id"]
        partner = r["non_striker"] if on_strike else r["batter"]
        if r["phase"] != prev_phase:
            events.append({"seq": r["seq"], "kind": "phase", "label": f"{r['phase']} overs begin", "ball_label": r["ball_label"]})
            prev_phase = r["phase"]
        if partner_id != prev_partner:
            events.append({"seq": r["seq"], "kind": "partner", "label": f"new partner: {partner}", "partner_id": partner_id, "ball_label": r["ball_label"],
                           "score": f"{r['score_before']}/{r['wickets_before']}"})
            prev_partner = partner_id
        ball = {"delivery_id": r["delivery_id"], "seq": r["seq"], "ball_label": r["ball_label"], "on_strike": on_strike, "symbol": symbol(r),
                "bowler": r["bowler"], "bowler_id": r["bowler_id"], "partner": partner, "score_before": f"{r['score_before']}/{r['wickets_before']}",
                "required_rate": r["required_rate"], "runs_required": r["runs_required"], "balls_left": r["balls_left"], "phase": r["phase"]}
        if on_strike:
            runs += r["runs_batter"]
            if not r["wides"]:
                faced += 1
                window.append(r["runs_batter"]); window = window[-10:]
            ball.update(runs=r["runs_batter"], cum_runs=runs, cum_balls=faced, four=r["is_four"], six=r["is_six"],
                        dot=(r["runs_batter"] == 0 and not r["wides"]), rolling_sr=round(100 * sum(window) / len(window), 1) if window else None)
            for m in (50, 100, 150):
                if not milestones[m] and runs >= m:
                    milestones[m] = True
                    events.append({"seq": r["seq"], "kind": "milestone", "label": f"{m} up off {faced} balls", "ball_label": r["ball_label"]})
        else:
            ball.update(cum_runs=runs, cum_balls=faced)
        for (did, out_id), w in wk.items():
            if did == r["delivery_id"]:
                if out_id == pid:
                    ball["out"] = w
                    events.append({"seq": r["seq"], "kind": "dismissed", "label": f"out: {w['kind']}", "ball_label": r["ball_label"]})
                else:
                    ball["partner_out"] = w
                    events.append({"seq": r["seq"], "kind": "partner_out", "label": f"{w['player_out']} out ({w['kind']})", "ball_label": r["ball_label"]})
        if sdx and r["chasing"] and r["runs_required"] is not None:
            s = sdx.score(r["format_group"], r["gender"], r["runs_required"], r["balls_left"], r["wickets_before"])
            ball["sdx"] = s["sdx"] if s else None
        balls.append(ball)
    # strike changes: consecutive balls where this batter's strike status flips
    strike_changes = sum(1 for a, b2 in zip(balls, balls[1:]) if a["on_strike"] != b2["on_strike"])
    out_ball = next((b2 for b2 in balls if b2.get("out")), None)
    parts = db.q("""SELECT partnership_id, part_no, wicket_no, runs, balls, p1, p2, p1_runs, p1_balls, p2_runs, p2_balls, ended, first_over, last_over,
                           score_start FROM partnerships WHERE match_id = ? AND innings_no = ? AND (p1 = ? OR p2 = ?) ORDER BY part_no""",
                 [match_id, inn, pid, pid]) if getattr(db, "has_context", False) else []
    names = {x["person_id"]: x["name"] for x in db.q(
        f"SELECT person_id, name FROM player_profile WHERE person_id IN ({','.join('?' * len({p for x in parts for p in (x['p1'], x['p2'])}) or ['?'])})",
        list({p for x in parts for p in (x["p1"], x["p2"])}) or ["-"])}
    for x in parts:
        me_first = x["p1"] == pid
        x["partner_id"] = x["p2"] if me_first else x["p1"]
        x["partner"] = names.get(x["partner_id"], x["partner_id"])
        x["my_runs"], x["my_balls"] = (x["p1_runs"], x["p1_balls"]) if me_first else (x["p2_runs"], x["p2_balls"])
        x["partner_runs"], x["partner_balls"] = (x["p2_runs"], x["p2_balls"]) if me_first else (x["p1_runs"], x["p1_balls"])
    return {"match": match_meta(db, match_id), "innings_no": inn, "batter": {"id": pid, "name": name},
            "teams": db.q1("SELECT batting_team, bowling_team FROM innings WHERE match_id = ? AND innings_no = ?", [match_id, inn]),
            "summary": {"runs": runs, "balls": faced, "fours": sum(1 for b2 in balls if b2.get("four")), "sixes": sum(1 for b2 in balls if b2.get("six")),
                        "dots": sum(1 for b2 in balls if b2.get("dot")), "strike_rate": round(100 * runs / faced, 1) if faced else None,
                        "not_out": out_ball is None, "how_out": out_ball["out"] if out_ball else None, "strike_changes": strike_changes,
                        "team_deliveries_at_crease": len(balls), "arrived": f"{span[0]['score_before']}/{span[0]['wickets_before']}",
                        "arrived_over": span[0]["ball_label"], "left_over": span[-1]["ball_label"]},
            "balls": balls, "events": events, "partnerships": parts, "prov": "OBSERVED events; cumulative values DERIVED",
            "experimental": bool(sdx)}


def player_spells(db: DB, pid: str, sort: str = "recent", limit: int = 30, fmt: str | None = None) -> list[dict]:
    w, p = "s.bowler_id = ?", [pid]
    if fmt:
        w += " AND m.format_group = ?"; p.append(fmt)
    order = {"recent": "start_date DESC, innings_no", "wickets": "wickets DESC, runs ASC", "economy": "CASE WHEN balls >= 18 THEN runs * 6.0 / balls END ASC NULLS LAST"}[sort]
    rows = db.q(f"""SELECT s.match_id, s.innings_no, s.spell_no, any_value(m.start_date) AS start_date, any_value(m.competition) AS competition,
                          any_value(m.format_group) AS format_group, any_value(i.batting_team) AS opponent, count(*) AS overs,
                          sum(s.runs) AS runs, sum(s.balls) AS balls, sum(s.wickets) AS wickets, sum(s.dots) AS dots,
                          sum(s.boundaries) AS boundaries, min(s.over) AS from_over, max(s.over) AS to_over
                   FROM spells s JOIN matches m USING (match_id) JOIN innings i USING (match_id, innings_no)
                   WHERE {w} GROUP BY s.match_id, s.innings_no, s.spell_no ORDER BY {order} LIMIT ?""", [*p, limit])
    for r in rows:
        r["start_date"] = str(r["start_date"])
        r["economy"] = round(6 * r["runs"] / r["balls"], 2) if r["balls"] else None
    return rows


def spell_story(db: DB, match_id: str, inn: int, pid: str, sdx=None) -> dict | None:
    overs = db.q("""SELECT * FROM spells WHERE match_id = ? AND innings_no = ? AND bowler_id = ? ORDER BY over""", [match_id, inn, pid])
    if not overs:
        return None
    ball_rows = db.q("""SELECT delivery_id, over, seq, ball_label, batter_id, batter, n_wickets, wides, noballs, byes, legbyes, runs_batter,
                               runs_extras, runs_total, is_four, is_six, legal, score_before, wickets_before, required_rate, runs_required,
                               balls_left, chasing, format_group, gender, batter_stage, batter_balls_before
                        FROM balls WHERE match_id = ? AND innings_no = ? AND bowler_id = ? ORDER BY seq""", [match_id, inn, pid])
    wk = {r["delivery_id"]: r for r in db.q("""SELECT delivery_id, player_out, kind, bowler_credited FROM dis
                                                WHERE match_id = ? AND innings_no = ? AND bowler_id = ?""", [match_id, inn, pid])}
    by_over: dict[int, list] = {}
    for r in ball_rows:
        item = {"delivery_id": r["delivery_id"], "ball_label": r["ball_label"], "batter": r["batter"], "batter_id": r["batter_id"],
                "symbol": symbol(r), "runs_conceded": r["runs_batter"] + r["wides"] + r["noballs"], "legal": r["legal"],
                "batter_stage": r["batter_stage"], "wicket": wk.get(r["delivery_id"])}
        if sdx and r["chasing"] and r["runs_required"] is not None:
            s = sdx.score(r["format_group"], r["gender"], r["runs_required"], r["balls_left"], r["wickets_before"])
            item["sdx"] = s["sdx"] if s else None
        by_over.setdefault(r["over"], []).append(item)
    first = {r["over"]: r for r in ball_rows if r["seq"] == min(x["seq"] for x in ball_rows if x["over"] == r["over"])}
    out_overs = []
    for o in overs:
        st = first[o["over"]]
        out_overs.append({**o, "balls_list": by_over.get(o["over"], []),
                          "state": {"score": f"{st['score_before']}/{st['wickets_before']}", "required_rate": st["required_rate"],
                                    "runs_required": st["runs_required"], "balls_left": st["balls_left"]}})
    batters: dict[str, dict] = {}
    for r in ball_rows:
        x = batters.setdefault(r["batter_id"], {"batter_id": r["batter_id"], "batter": r["batter"], "balls": 0, "runs": 0, "dismissed": False})
        x["balls"] += 0 if r["wides"] else 1
        x["runs"] += r["runs_batter"]
        if r["delivery_id"] in wk and wk[r["delivery_id"]]["bowler_credited"]:
            x["dismissed"] = True
    spells = {}
    for o in out_overs:
        s = spells.setdefault(o["spell_no"], {"spell_no": o["spell_no"], "overs": 0, "runs": 0, "balls": 0, "wickets": 0, "dots": 0, "boundaries": 0})
        for k in ("runs", "balls", "wickets", "dots", "boundaries"):
            s[k] += o[k]
        s["overs"] += 1
    tot = {k: sum(o[k] for o in out_overs) for k in ("runs", "balls", "wickets", "dots", "boundaries")}
    # consecutive-dot pressure: longest run of legal dots across the bowler's balls
    best = cur = 0
    for r in ball_rows:
        if r["legal"]:
            cur = cur + 1 if r["runs_total"] == 0 else 0
            best = max(best, cur)
    return {"match": match_meta(db, match_id), "innings_no": inn, "bowler": {"id": pid, "name": (db.q1("SELECT name FROM player_profile WHERE person_id = ?", [pid]) or {}).get("name", ball_rows[0]["batter"] and pid)},
            "overs": out_overs, "spells": list(spells.values()), "batters": list(batters.values()),
            "totals": {**tot, "economy": round(6 * tot["runs"] / tot["balls"], 2) if tot["balls"] else None,
                       "figures": f"{len(out_overs)}-{tot['runs']}-{tot['wickets']}", "longest_dot_sequence": best},
            "spell_definition": "A spell is a run of overs where each follows the bowler's previous over by at most two overs "
                                "(bowling from one end). A longer gap starts a new spell.",
            "prov": "OBSERVED events; spells and totals DERIVED", "experimental": bool(sdx)}
