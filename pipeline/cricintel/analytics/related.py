"""Rabbit-hole navigation: deterministic "Explore next" recommendations for every major object.

Each recommendation is a relationship in the knowledge graph plus a stated reason ("Longest battle: 385 balls").
No randomness and no collaborative filtering: the same object always yields the same, explainable next steps.
"""
from __future__ import annotations

from ..db import DB
from .entities import _nm


def _r(kind: str, label: str, href: str, reason: str) -> dict:
    return {"kind": kind, "label": label, "href": href, "reason": reason}


def related(db: DB, typ: str, key: str) -> list[dict]:
    fn = {"player": _player, "battle": _battle, "match": _match, "innings": _innings, "spell": _spell, "competition": _competition,
          "rivalry": _rivalry, "delivery": _delivery}.get(typ)
    if not fn:
        return []
    out, seen = [], set()
    for r in fn(db, key):
        if r["href"] not in seen:
            seen.add(r["href"]); out.append(r)
    return out[:8]


def _player(db, pid):
    out = []
    for r in db.q("SELECT match_id, innings_no, runs, balls, not_out, opponent, start_date FROM bat_innings WHERE batter_id = ? ORDER BY runs DESC LIMIT 2", [pid]):
        out.append(_r("innings", f"{r['runs']}{'*' if r['not_out'] else ''} v {r['opponent']} ({str(r['start_date'])[:4]})",
                      f"/innings/{r['match_id']}/{r['innings_no']}/{pid}", "Highest covered scores"))
    for r in db.q("""SELECT batter_id, bowler_id, balls, runs, outs FROM battles WHERE batter_id = ? ORDER BY balls DESC LIMIT 1""", [pid]):
        out.append(_r("battle", f"v {_nm(db, r['bowler_id'])}", f"/battle?bat={pid}&bowl={r['bowler_id']}", f"Longest battle as batter: {r['balls']} balls, {r['outs']} out"))
    for r in db.q("""SELECT batter_id, balls, outs FROM battles WHERE bowler_id = ? AND balls >= 30 AND outs >= 2 ORDER BY outs DESC, balls LIMIT 1""", [pid]):
        out.append(_r("battle", f"bowling to {_nm(db, r['batter_id'])}", f"/battle?bat={r['batter_id']}&bowl={pid}", f"Dismissed them {r['outs']} times"))
    for r in db.q("""SELECT CASE WHEN p1 = ? THEN p2 ELSE p1 END AS partner, sum(runs) AS runs, count(*) AS n FROM partnerships WHERE p1 = ? OR p2 = ?
                     GROUP BY 1 ORDER BY runs DESC LIMIT 1""", [pid, pid, pid]):
        out.append(_r("partnership", f"with {_nm(db, r['partner'])}", f"/partnerships?p1={pid}&p2={r['partner']}", f"Most runs together: {r['runs']} in {r['n']} stands"))
    for r in db.q("""SELECT match_id, innings_no, wickets, runs, opponent FROM bowl_innings WHERE bowler_id = ? AND wickets >= 3 ORDER BY wickets DESC, runs LIMIT 1""", [pid]):
        out.append(_r("spell", f"{r['wickets']}/{r['runs']} v {r['opponent']}", f"/spell/{r['match_id']}/{r['innings_no']}/{pid}", "Best covered bowling figures"))
    for r in db.q("""SELECT competition, any_value(gender) AS g, count(*) AS n FROM bat_innings WHERE batter_id = ? AND competition IS NOT NULL
                     GROUP BY 1 ORDER BY n DESC LIMIT 1""", [pid]):
        out.append(_r("competition", r["competition"], f"/competition?name={r['competition']}&gender={r['g']}", f"Most innings in this competition ({r['n']})"))
    for r in db.q("""SELECT match_id, opponent, start_date FROM bat_innings WHERE batter_id = ? ORDER BY start_date DESC LIMIT 1""", [pid]):
        out.append(_r("match", f"v {r['opponent']}, {r['start_date']}", f"/match/{r['match_id']}", "Most recent covered match"))
    out.append(_r("career", "Career explorer", f"/players/{pid}?tab=career", "Year by year through covered data"))
    return out


def _battle(db, key):
    bat, bowl = key.split("|")
    out = []
    for r in db.q("""SELECT d.delivery_id, d.match_id, d.kind, d.start_date FROM dis d WHERE d.player_out_id = ? AND d.bowler_id = ? AND d.bowler_credited
                     ORDER BY d.start_date DESC LIMIT 1""", [bat, bowl]):
        out.append(_r("delivery", f"Latest dismissal: {r['kind']} ({str(r['start_date'])[:10]})", f"/delivery/{r['delivery_id']}", "The most recent time the bowler got them out"))
    for r in db.q("""SELECT match_id, count(*) FILTER (WHERE wides = 0) AS balls, sum(runs_batter) AS runs, any_value(start_date) AS d FROM balls
                     WHERE batter_id = ? AND bowler_id = ? GROUP BY 1 ORDER BY runs DESC LIMIT 1""", [bat, bowl]):
        out.append(_r("match", f"Biggest meeting: {r['runs']} off {r['balls']} ({str(r['d'])[:4]})", f"/match/{r['match_id']}", "Most runs in a single meeting"))
    for r in db.q("""SELECT match_id, innings_no FROM balls WHERE batter_id = ? AND bowler_id = ? ORDER BY start_date DESC LIMIT 1""", [bat, bowl]):
        out.append(_r("spell", f"{_nm(db, bowl)}'s spell in their latest meeting", f"/spell/{r['match_id']}/{r['innings_no']}/{bowl}", "Latest meeting"))
    out.append(_r("story", "What this battle shows", f"/story/battle?bat={bat}&bowl={bowl}", "Deterministic evidence story"))
    from .libraries import similar_battles
    s = similar_battles(db, bat, bowl, 2)
    for r in s.get("rows", []):
        out.append(_r("battle", f"{r['batter']} v {r['bowler']}", f"/battle?bat={r['batter_id']}&bowl={r['bowler_id']}", "Statistically similar battle"))
    out.append(_r("player", _nm(db, bat), f"/players/{bat}", "Batter"))
    out.append(_r("player", _nm(db, bowl), f"/players/{bowl}?tab=bowling", "Bowler"))
    return out


def _match(db, mid):
    m = db.q1("SELECT * FROM team_results WHERE match_id = ?", [mid])
    if not m:
        return []
    out = []
    for r in db.q("SELECT innings_no, batter_id, runs, balls, not_out FROM bat_innings WHERE match_id = ? ORDER BY runs DESC LIMIT 2", [mid]):
        out.append(_r("innings", f"{_nm(db, r['batter_id'])} {r['runs']}{'*' if r['not_out'] else ''}", f"/innings/{mid}/{r['innings_no']}/{r['batter_id']}", "Top score in the match"))
    for r in db.q("SELECT innings_no, bowler_id, wickets, runs FROM bowl_innings WHERE match_id = ? ORDER BY wickets DESC, runs LIMIT 1", [mid]):
        out.append(_r("spell", f"{_nm(db, r['bowler_id'])} {r['wickets']}/{r['runs']}", f"/spell/{mid}/{r['innings_no']}/{r['bowler_id']}", "Best bowling in the match"))
    out.append(_r("story", "How the match unfolded", f"/story/match/{mid}", "Deterministic evidence story"))
    if m["competition"]:
        out.append(_r("competition", f"{m['competition']} {m['season']}", f"/competition?name={m['competition']}&gender={m['gender']}&season={m['season']}", "This edition"))
    out.append(_r("rivalry", f"{m['ta']} v {m['tb']}", f"/rivalry?a={m['ta']}&b={m['tb']}&gender={m['gender']}", "Every covered meeting of these teams"))
    for r in db.q("""SELECT match_id, team1, team2, start_date FROM team_results WHERE competition IS NOT DISTINCT FROM ? AND gender = ? AND start_date > ?
                     ORDER BY start_date LIMIT 1""", [m["competition"], m["gender"], m["start_date"]]):
        out.append(_r("match", f"Next: {r['team1']} v {r['team2']}", f"/match/{r['match_id']}", "Next match in the same competition"))
    return out


def _innings(db, key):
    mid, inn, pid = key.split("|")
    b = db.q1("SELECT * FROM bat_innings WHERE match_id = ? AND innings_no = ? AND batter_id = ?", [mid, int(inn), pid])
    if not b:
        return []
    out = [_r("match", f"{b['team']} v {b['opponent']}", f"/match/{mid}", "The match"),
           _r("story", "How this innings unfolded", f"/story/innings/{mid}/{inn}/{pid}", "Deterministic evidence story")]
    if b["out_bowler_id"]:
        out.append(_r("battle", f"v {b['out_bowler']}", f"/battle?bat={pid}&bowl={b['out_bowler_id']}", "The bowler who dismissed them: every meeting"))
        out.append(_r("delivery", "The dismissal", f"/delivery/{b['out_delivery_id']}", "Replay the wicket"))
    for r in db.q("""SELECT p1, p2, runs FROM partnerships WHERE match_id = ? AND innings_no = ? AND (p1 = ? OR p2 = ?) ORDER BY runs DESC LIMIT 1""", [mid, int(inn), pid, pid]):
        partner = r["p2"] if r["p1"] == pid else r["p1"]
        out.append(_r("partnership", f"with {_nm(db, partner)}", f"/partnerships?p1={pid}&p2={partner}", f"Biggest stand in this innings: {r['runs']}"))
    out.append(_r("player", _nm(db, pid), f"/players/{pid}?tab=innings", "More of their innings"))
    return out


def _spell(db, key):
    mid, inn, pid = key.split("|")
    out = [_r("match", "The match", f"/match/{mid}", "Full scorecard and events")]
    for r in db.q("""SELECT player_out_id, player_out, delivery_id FROM dis WHERE match_id = ? AND innings_no = ? AND bowler_id = ? AND bowler_credited
                     ORDER BY batter_runs_before DESC LIMIT 2""", [mid, int(inn), pid]):
        out.append(_r("battle", f"v {_nm(db, r['player_out_id'], r['player_out'])}", f"/battle?bat={r['player_out_id']}&bowl={pid}", "A batter they dismissed: every meeting"))
    out.append(_r("player", _nm(db, pid), f"/players/{pid}?tab=bowling", "Bowler fingerprint and spells"))
    return out


def _competition(db, key):
    name, gender = key.split("|")
    out = []
    for r in db.q("SELECT match_id, team1, team2, season FROM team_results WHERE competition = ? AND gender = ? AND event_stage = 'Final' ORDER BY start_date DESC LIMIT 2",
                  [name, gender]):
        out.append(_r("match", f"{r['season']} final: {r['team1']} v {r['team2']}", f"/match/{r['match_id']}", "A final"))
    for r in db.q("""SELECT ta, tb, count(*) AS n FROM team_results WHERE competition = ? AND gender = ? GROUP BY 1, 2 ORDER BY n DESC LIMIT 1""", [name, gender]):
        out.append(_r("rivalry", f"{r['ta']} v {r['tb']}", f"/rivalry?a={r['ta']}&b={r['tb']}&gender={gender}&competition={name}", f"Most frequent fixture ({r['n']} matches)"))
    for r in db.q("SELECT batter_id, sum(runs) AS runs FROM bat_innings WHERE competition = ? AND gender = ? GROUP BY 1 ORDER BY runs DESC LIMIT 1", [name, gender]):
        out.append(_r("player", _nm(db, r["batter_id"]), f"/players/{r['batter_id']}", f"Most runs in covered data ({r['runs']})"))
    out.append(_r("records", "Records in this competition", f"/records?metric=runs&competition={name}&gender={gender}", "Build any leaderboard"))
    return out


def _rivalry(db, key):
    a, b, g = key.split("|")
    out = []
    for r in db.q("""SELECT batter_id, bowler_id, count(*) AS n FROM balls WHERE gender = ? AND ((batting_team = ? AND bowling_team = ?) OR (batting_team = ? AND bowling_team = ?))
                     GROUP BY 1, 2 ORDER BY n DESC LIMIT 2""", [g, a, b, b, a]):
        out.append(_r("battle", f"{_nm(db, r['batter_id'])} v {_nm(db, r['bowler_id'])}", f"/battle?bat={r['batter_id']}&bowl={r['bowler_id']}", "Recurring battle in this rivalry"))
    for r in db.q("""SELECT match_id, team1, team2, start_date FROM team_results WHERE ta = ? AND tb = ? AND gender = ? ORDER BY start_date DESC LIMIT 1""", [a, b, g]):
        out.append(_r("match", f"Latest: {r['start_date']}", f"/match/{r['match_id']}", "Most recent covered meeting"))
    return out


def _delivery(db, did):
    r = db.q1("SELECT match_id, innings_no, batter_id, bowler_id FROM balls WHERE delivery_id = ?", [did])
    if not r:
        return []
    return [_r("innings", f"{_nm(db, r['batter_id'])}'s innings", f"/innings/{r['match_id']}/{r['innings_no']}/{r['batter_id']}", "The batter's innings"),
            _r("spell", f"{_nm(db, r['bowler_id'])}'s spell", f"/spell/{r['match_id']}/{r['innings_no']}/{r['bowler_id']}", "The bowler's spell"),
            _r("battle", f"{_nm(db, r['batter_id'])} v {_nm(db, r['bowler_id'])}", f"/battle?bat={r['batter_id']}&bowl={r['bowler_id']}", "Every meeting"),
            _r("match", "The match", f"/match/{r['match_id']}", "Scorecard, events and battles")]
