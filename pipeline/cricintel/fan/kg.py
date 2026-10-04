"""Explicit cricket knowledge graph for fan navigation (Phase 7).

Node types (id form → page):
  player:<pid>                      /players/<pid>
  team:<name>|<gender>              /rivalries?team=…        (a team's rivalries)
  match:<mid>                       /match/<mid>
  innings:<mid>|<inn>|<pid>         /innings/<mid>/<inn>/<pid>        (one batter's innings)
  spell:<mid>|<inn>|<pid>           /spell/<mid>/<inn>/<pid>          (one bowler's spell)
  battle:<bat>|<bowl>               /battle?bat=…&bowl=…              (batter v bowler, all meetings)
  partnership:<p1>|<p2>             /partnerships?p1=…&p2=…
  competition:<name>|<gender>       /competition?name=…&gender=…
  rivalry:<a>|<b>|<gender>          /rivalry?a=…&b=…&gender=…
  record:<record id>                /records/<record id>
  finding:<finding id>              the finding's evidence page
  delivery:<did>                    /delivery/<did>
  moment:<mid>|<cursor>             /live-lab/<mid>?n=<cursor>&game=1 (a spoiler-safe "what happened next?")

Every edge is a real relationship in covered data (who dismissed whom, who batted with whom, which match an innings
belongs to, …) with features the Rabbit-Hole ranker uses: relation, sample, strength, unusualness, recency and
recognisability, each 0–1 and each explained by the edge's `reason`. Nothing here is random.
"""
from __future__ import annotations

import math
from datetime import date
from functools import lru_cache

from ..db import DB
from ..analytics.entities import names

VERSION = "fan-graph-1.0"

NODE_TYPES = ["player", "team", "match", "innings", "spell", "battle", "partnership", "competition", "rivalry", "record", "finding",
              "delivery", "moment"]

# How interesting each relation tends to be for a fan. Only a prior: per-edge evidence moves the final score far more.
RELATION_PRIOR = {
    "dismissed_by": 1.0, "victim": 1.0, "dominated": 0.9, "punished_by": 0.9, "best_innings": 0.9, "best_spell": 0.9,
    "finding": 0.95, "record": 0.85, "similar": 0.8, "partner": 0.75, "play": 0.8, "compare": 0.7, "how_out": 0.7,
    "story": 0.6, "match": 0.6, "top_innings": 0.85, "top_spell": 0.8, "big_stand": 0.7, "player": 0.7, "dismissal": 0.75,
    "biggest_meeting": 0.7, "similar_battle": 0.65, "other_rival": 0.85, "rivalry": 0.5, "competition": 0.4, "next_match": 0.35,
    "latest_match": 0.4, "replay": 0.6, "edition": 0.4, "team": 0.35, "faced_most": 0.7, "teammate": 0.5, "related_record": 0.6, "records": 0.55,
}

MAJOR = ("Indian Premier League", "Women's Premier League")


def _r(x: float) -> float:
    return round(max(0.0, min(1.0, x)), 3)


def sample_score(n: float, full: float) -> float:
    """0..1: log-scaled sample size relative to the size that counts as 'plenty' for this kind of evidence."""
    return _r(math.log1p(max(0, n or 0)) / math.log1p(full))


def recency(d) -> float:
    if not d:
        return 0.3
    y = int(str(d)[:4])
    return _r(math.exp(-max(0, date.today().year - y) / 6))


@lru_cache(maxsize=4)
def _matches(db: DB) -> dict:
    return {r["person_id"]: r["matches"] or 0 for r in db.q("SELECT person_id, matches FROM player_profile")}


def recog(db: DB, *pids: str) -> float:
    """Recognisability: how much covered cricket the best-known person involved has played (log scale, 300 matches = 1)."""
    m = _matches(db)
    return _r(max((math.log1p(m.get(p, 0)) / math.log1p(300) for p in pids if p), default=0))


def comp_recog(comp: str | None) -> float:
    if not comp:
        return 0.5
    if comp in MAJOR or "World Cup" in comp and "Qualifier" not in comp:
        return 1.0
    return 0.55


def nm(db: DB, pid: str | None, fallback: str | None = None) -> str:
    return names(db).get(pid, fallback or pid or "?")


def node(typ: str, key: str) -> str:
    return f"{typ}:{key}"


def href(typ: str, key: str) -> str:
    k = key.split("|")
    return {"player": lambda: f"/players/{key}", "match": lambda: f"/match/{key}", "innings": lambda: f"/innings/{k[0]}/{k[1]}/{k[2]}",
            "spell": lambda: f"/spell/{k[0]}/{k[1]}/{k[2]}", "battle": lambda: f"/battle?bat={k[0]}&bowl={k[1]}",
            "partnership": lambda: f"/partnerships?p1={k[0]}&p2={k[1]}", "competition": lambda: f"/competition?name={k[0]}&gender={k[1]}",
            "rivalry": lambda: f"/rivalry?a={k[0]}&b={k[1]}&gender={k[2]}", "record": lambda: f"/records/{key}",
            "delivery": lambda: f"/delivery/{key}", "moment": lambda: f"/live-lab/{k[0]}?n={k[1]}&game=1",
            "team": lambda: f"/rivalries?team={k[0]}&gender={k[1]}"}[typ]()


def edge(typ: str, key: str, label: str, relation: str, reason: str, *, n: float = 0, full: float = 100, strength: float = 0.5,
         unusual: float = 0.3, when=None, rec: float = 0.5, unit: str | None = None, href_: str | None = None, view: str | None = None) -> dict:
    # `view` marks a different page about the same entity (its story, replay, how-out drill): a separate destination
    return {"type": typ, "id": f"view:{view}:{key}" if view else node(typ, key), "label": label, "href": href_ or href(typ, key), "relation": relation, "reason": reason,
            "sample": n, "sample_unit": unit,
            "f": {"sample": sample_score(n, full), "strength": _r(strength), "unusual": _r(unusual), "recency": recency(when), "recog": _r(rec),
                  "prior": RELATION_PRIOR.get(relation, 0.5)}}


def _fig(r) -> str:
    return f"{r['runs']}{'*' if r.get('not_out') else ''}"


# ------------------------------------------------------------------------------------------------ neighbours
def neighbours(db: DB, typ: str, key: str) -> list[dict]:
    fn = {"player": _player, "battle": _battle, "match": _match, "innings": _innings, "spell": _spell, "delivery": _delivery,
          "competition": _competition, "rivalry": _rivalry, "partnership": _partnership, "record": _record, "finding": _finding,
          "team": _team}.get(typ)
    if not fn:
        return []
    out, seen = [], set()
    for e in fn(db, key):
        if e["id"] != node(typ, key) and (e["id"], e["relation"]) not in seen:
            seen.add((e["id"], e["relation"]))
            out.append(e)
    return out


@lru_cache(maxsize=8192)
def role(db: DB, pid: str) -> dict:
    """Primary role from covered data: balls faced v legal balls bowled (used to order the player home)."""
    # per-innings tables (T20/ODI, ~170k rows) instead of scanning 3.3M deliveries
    r = db.q1("""SELECT (SELECT sum(balls) FROM bat_innings WHERE batter_id = ?) AS bat,
                        (SELECT sum(balls) FROM bowl_innings WHERE bowler_id = ?) AS bowl""", [pid, pid])
    bat, bowl = r["bat"] or 0, r["bowl"] or 0
    primary = "bowler" if bowl > bat * 1.3 else "batter"
    return {"primary": primary, "balls_faced": bat, "balls_bowled": bowl,
            "allrounder": bat >= 1000 and bowl >= 1000 and min(bat, bowl) >= 0.35 * max(bat, bowl)}


def _player(db: DB, pid: str) -> list[dict]:
    from . import index, moments, similar, records2
    ix = index.get(db)
    out: list[dict] = []
    me = recog(db, pid)
    for r in ix["best_innings"].get(pid, []):
        out.append(edge("innings", f"{r['match_id']}|{r['innings_no']}|{pid}", f"{_fig(r)} ({r['balls']}) v {r['opponent']}, {str(r['start_date'])[:4]}",
                        "best_innings", "Highest covered score" if not out else "One of their highest covered scores", n=r["balls"], full=60,
                        strength=min(1, r["runs"] / 120), unusual=min(1, r["runs"] / 150), when=r["start_date"], rec=comp_recog(r["competition"])))
    for r in ix["best_spells"].get(pid, []):
        out.append(edge("spell", f"{r['match_id']}|{r['innings_no']}|{pid}", f"{r['wickets']}/{r['runs']} v {r['opponent']}, {str(r['start_date'])[:4]}",
                        "best_spell", "Best covered bowling figures", n=r["balls"], full=24, strength=min(1, r["wickets"] / 5),
                        unusual=min(1, r["wickets"] / 6), when=r["start_date"], rec=comp_recog(r["competition"])))
    bat_rows = ix["battles_bat"].get(pid, [])
    # as batter: who dismissed them most, and whom they dominated
    for r in sorted((x for x in bat_rows if x["balls"] >= 24 and x["outs"] >= 3), key=lambda x: (-x["outs"], x["balls"]))[:3]:
        exp = r["balls"] * (r["bat_or"] or 0)
        out.append(edge("battle", f"{pid}|{r['bowler_id']}", f"v {nm(db, r['bowler_id'])}", "dismissed_by",
                        f"Dismissed them {r['outs']} times in {r['balls']} balls" + (f" (about {exp:.1f} expected)" if exp else ""),
                        n=r["balls"], full=240, strength=min(1, r["outs"] / 8), unusual=min(1, (r["outs"] / exp - 1) / 2) if exp else 0.3,
                        when=r["last"], rec=recog(db, r["bowler_id"]), unit="balls"))
    for r in sorted((x for x in bat_rows if x["balls"] >= 60), key=lambda x: -(x["runs"] + 60 * (x["bat_rpb"] or 0)) / (x["balls"] + 60))[:2]:
        sr, usual = 100 * r["runs"] / r["balls"], 100 * (r["bat_rpb"] or 0)
        if sr <= usual * 1.1:
            continue
        out.append(edge("battle", f"{pid}|{r['bowler_id']}", f"v {nm(db, r['bowler_id'])}", "dominated",
                        f"Strike rate {sr:.0f} against them (usual {usual:.0f}), {r['outs']} out in {r['balls']} balls",
                        n=r["balls"], full=240, strength=min(1, (sr / usual - 1) * 2) if usual else 0.3, unusual=min(1, (sr / usual - 1) * 1.5) if usual else 0.3,
                        when=r["last"], rec=recog(db, r["bowler_id"]), unit="balls"))
    bowl_rows = ix["battles_bowl"].get(pid, [])
    # as bowler: victims, and who took them apart
    for r in sorted((x for x in bowl_rows if x["outs"] >= 3), key=lambda x: (-x["outs"], x["balls"]))[:3]:
        exp = r["balls"] * (r["bat_or"] or 0)
        out.append(edge("battle", f"{r['batter_id']}|{pid}", f"bowling to {nm(db, r['batter_id'])}", "victim",
                        f"Dismissed them {r['outs']} times in {r['balls']} balls" + (f" (about {exp:.1f} expected)" if exp else ""),
                        n=r["balls"], full=240, strength=min(1, r["outs"] / 8), unusual=min(1, (r["outs"] / exp - 1) / 2) if exp else 0.3,
                        when=r["last"], rec=recog(db, r["batter_id"]), unit="balls"))
    for r in sorted((x for x in bowl_rows if x["balls"] >= 60), key=lambda x: -(x["runs"] + 60 * (x["bowl_rpb"] or 0)) / (x["balls"] + 60))[:1]:
        sr, usual = 100 * r["runs"] / r["balls"], 100 * (r["bowl_rpb"] or 0)
        if sr <= usual * 1.15:
            continue
        out.append(edge("battle", f"{r['batter_id']}|{pid}", f"bowling to {nm(db, r['batter_id'])}", "punished_by",
                        f"Went at {sr:.0f} per 100 balls against them (they usually concede {usual:.0f})", n=r["balls"], full=240,
                        strength=min(1, (sr / usual - 1) * 2) if usual else 0.3, unusual=min(1, (sr / usual - 1) * 1.5) if usual else 0.3,
                        when=r["last"], rec=recog(db, r["batter_id"]), unit="balls"))
    for r in ix["partners"].get(pid, [])[:2]:
        a, b = sorted([pid, r["partner"]])
        out.append(edge("partnership", f"{a}|{b}", f"with {nm(db, r['partner'])}", "partner", f"{r['runs']} runs together in {r['n']} stands",
                        n=r["n"], full=80, strength=min(1, r["runs"] / 3000), unusual=0.3, when=r["last"], rec=recog(db, r["partner"]), unit="stands"))
    for s in similar.for_player(db, pid, k=2):
        out.append(edge("player", s["pid"], s["name"], "similar", f"Similar {s['role']} profile ({s['format']}): {s['why_short']}",
                        n=s["sample"], full=3000, strength=s["closeness"], unusual=0.35, when=s.get("last"), rec=recog(db, s["pid"])))
        out.append(edge("player", s["pid"], f"Compare with {s['name']}", "compare", "Side by side: where each leads, and where it's a tie",
                        n=s["sample"], full=3000, strength=s["closeness"] * 0.8, unusual=0.3, rec=recog(db, s["pid"]),
                        href_=f"/compare?ids={pid},{s['pid']}", view="compare"))
    for rec_ in records2.held_by(db, pid)[:3]:
        out.append(edge("record", rec_["id"], rec_["title"], "record", f"#{rec_['rank']} on this list: {rec_['value_fmt']}", n=rec_["sample"],
                        full=500, strength=1 - (rec_["rank"] - 1) / 10, unusual=0.6 if rec_["rank"] == 1 else 0.4, when=rec_.get("last_date"), rec=me))
    for f in findings_for(db, pid)[:2]:
        e = edge("finding", f["id"], f["headline"], "finding", f["type_label"], n=f["n"], full=2000, strength=0.7,
                 unusual=min(1, -math.log10(max(f["p"], 1e-12)) / 8), when=f["last_date"], rec=me, href_=f["href"])
        # a finding about a pair is the same destination as that partnership / battle: never list both
        if f["type"] == "partnership":
            e["entity"] = "partnership:" + "|".join(sorted(f["entities"][:2]))
        elif f["type"] == "matchup":
            e["entity"] = f"battle:{f['entities'][0]}|{f['entities'][1]}"
        out.append(e)
    m = moments.for_player(db, pid)
    if m:
        out.append(edge("moment", m["key"], m["title"], "play", "What happened next? Call the ball before it is revealed", n=1, full=1,
                        strength=0.7, unusual=0.5, when=m["date"], rec=comp_recog(m.get("competition")), href_=m["href"]))
    n_out = ix["outs"].get(pid, 0)
    if n_out >= 10:
        out.append(edge("player", pid, "How they get out", "how_out", f"{n_out} dismissals, step by step", n=n_out, full=300,
                        strength=0.6, unusual=0.3, rec=me, href_=f"/how-out/{pid}", view="how-out"))
    r = ix["comp"].get(pid)
    if r:
        out.append(edge("competition", f"{r['competition']}|{r['g']}", r["competition"], "competition", f"Most of their covered innings ({r['n']})",
                        n=r["n"], full=100, strength=0.4, unusual=0.1, when=r["last"], rec=comp_recog(r["competition"])))
    r = ix["latest"].get(pid)
    if r:
        out.append(edge("match", r["match_id"], f"v {r['opponent']}, {r['start_date']}", "latest_match", "Most recent covered match",
                        n=1, full=1, strength=0.3, unusual=0.1, when=r["start_date"], rec=0.5))
    return out


def findings_for(db: DB, pid: str) -> list[dict]:
    from . import didnt_know
    return [f for f in didnt_know.pool(db) if pid in f["entities"]]


def _battle(db: DB, key: str) -> list[dict]:
    from . import moments
    bat, bowl = key.split("|")
    out = []
    b = db.q1("SELECT sum(balls) AS balls, sum(runs) AS runs, sum(outs) AS outs FROM battles WHERE batter_id = ? AND bowler_id = ?", [bat, bowl])
    for r in db.q("""SELECT delivery_id, kind, start_date, phase FROM dis WHERE player_out_id = ? AND bowler_id = ? AND bowler_credited
                     ORDER BY start_date DESC LIMIT 1""", [bat, bowl]):
        out.append(edge("delivery", r["delivery_id"], f"Latest dismissal: {r['kind']} ({str(r['start_date'])[:10]})", "dismissal",
                        "The most recent time the bowler got them out", n=1, full=1, strength=0.6, unusual=0.4, when=r["start_date"], rec=0.6))
    for r in db.q("""SELECT match_id, count(*) FILTER (WHERE wides = 0) AS balls, sum(runs_batter) AS runs, any_value(start_date) AS d,
                     any_value(competition) AS comp FROM balls WHERE batter_id = ? AND bowler_id = ? GROUP BY 1 ORDER BY runs DESC LIMIT 1""", [bat, bowl]):
        out.append(edge("match", r["match_id"], f"Biggest meeting: {r['runs']} off {r['balls']} ({str(r['d'])[:4]})", "biggest_meeting",
                        "Most runs the batter took off this bowler in one match", n=r["balls"], full=30, strength=min(1, r["runs"] / 40),
                        unusual=0.4, when=r["d"], rec=comp_recog(r["comp"])))
    # the batter's other hardest matchups, and the bowler's other victims
    for r in db.q("""SELECT bowler_id, sum(balls) AS balls, sum(outs) AS outs, max(last_date) AS last FROM battles WHERE batter_id = ? AND bowler_id <> ?
                     GROUP BY 1 HAVING sum(outs) >= 3 ORDER BY outs DESC, balls LIMIT 2""", [bat, bowl]):
        out.append(edge("battle", f"{bat}|{r['bowler_id']}", f"{nm(db, bat)} v {nm(db, r['bowler_id'])}", "other_rival",
                        f"Another bowler who troubled {nm(db, bat)}: {r['outs']} dismissals in {r['balls']} balls", n=r["balls"], full=240,
                        strength=min(1, r["outs"] / 8), unusual=0.5, when=r["last"], rec=recog(db, r["bowler_id"]), unit="balls"))
    for r in db.q("""SELECT batter_id, sum(balls) AS balls, sum(outs) AS outs, max(last_date) AS last FROM battles WHERE bowler_id = ? AND batter_id <> ?
                     GROUP BY 1 HAVING sum(outs) >= 3 ORDER BY outs DESC, balls LIMIT 2""", [bowl, bat]):
        out.append(edge("battle", f"{r['batter_id']}|{bowl}", f"{nm(db, r['batter_id'])} v {nm(db, bowl)}", "other_rival",
                        f"Another batter {nm(db, bowl)} dismissed often: {r['outs']} times in {r['balls']} balls", n=r["balls"], full=240,
                        strength=min(1, r["outs"] / 8), unusual=0.5, when=r["last"], rec=recog(db, r["batter_id"]), unit="balls"))
    from ..analytics.libraries import similar_battles
    for r in similar_battles(db, bat, bowl, 2).get("rows", []):
        out.append(edge("battle", f"{r['batter_id']}|{r['bowler_id']}", f"{r['batter']} v {r['bowler']}", "similar_battle",
                        "A battle with a similar shape (balls, scoring, dismissals)", n=r.get("balls", 100), full=240, strength=0.5, unusual=0.3,
                        rec=recog(db, r["batter_id"], r["bowler_id"])))
    out.append(edge("player", bat, nm(db, bat), "player", "The batter", n=1, full=1, strength=0.5, unusual=0.1, rec=recog(db, bat)))
    out.append(edge("player", bowl, nm(db, bowl), "player", "The bowler", n=1, full=1, strength=0.5, unusual=0.1, rec=recog(db, bowl)))
    if b and b["outs"]:
        out.append(edge("player", bat, f"Every way {nm(db, bowl)} dismissed {nm(db, bat)}", "how_out", f"{b['outs']} dismissals, step by step",
                        n=b["outs"], full=10, strength=0.6, unusual=0.4, rec=recog(db, bat), href_=f"/how-out/{bat}?bowler={bowl}", view="how-out"))
    m = moments.for_battle(db, bat, bowl)
    if m:
        out.append(edge("moment", m["key"], m["title"], "play", "What happened next? Call the ball before it is revealed", n=1, full=1,
                        strength=0.7, unusual=0.5, when=m["date"], rec=0.7, href_=m["href"]))
    return out


def _match(db: DB, mid: str) -> list[dict]:
    from . import moments
    m = db.q1("SELECT * FROM team_results WHERE match_id = ?", [mid])
    if not m:
        return []
    cr = comp_recog(m["competition"])
    out = []
    for r in db.q("SELECT innings_no, batter_id, runs, balls, not_out FROM bat_innings WHERE match_id = ? AND balls > 0 ORDER BY runs DESC LIMIT 3", [mid]):
        out.append(edge("innings", f"{mid}|{r['innings_no']}|{r['batter_id']}", f"{nm(db, r['batter_id'])} {_fig(r)} ({r['balls']})", "top_innings",
                        "Top score in the match" if not out else "Another major innings in the match", n=r["balls"], full=60,
                        strength=min(1, r["runs"] / 100), unusual=min(1, r["runs"] / 120), when=m["start_date"], rec=recog(db, r["batter_id"])))
    for r in db.q("SELECT innings_no, bowler_id, wickets, runs, balls FROM bowl_innings WHERE match_id = ? ORDER BY wickets DESC, runs LIMIT 2", [mid]):
        if r["wickets"]:
            out.append(edge("spell", f"{mid}|{r['innings_no']}|{r['bowler_id']}", f"{nm(db, r['bowler_id'])} {r['wickets']}/{r['runs']}", "top_spell",
                            "Best bowling in the match", n=r["balls"], full=24, strength=min(1, r["wickets"] / 4), unusual=min(1, r["wickets"] / 5),
                            when=m["start_date"], rec=recog(db, r["bowler_id"])))
    for r in db.q("SELECT p1, p2, runs, balls, wicket_no FROM partnerships WHERE match_id = ? ORDER BY runs DESC LIMIT 1", [mid]):
        a, b = sorted([r["p1"], r["p2"]])
        out.append(edge("partnership", f"{a}|{b}", f"{nm(db, r['p1'])} & {nm(db, r['p2'])}", "big_stand",
                        f"Biggest stand of the match: {r['runs']} off {r['balls']} for wicket {r['wicket_no'] + 1}", n=r["balls"], full=60,
                        strength=min(1, r["runs"] / 100), unusual=0.4, when=m["start_date"], rec=recog(db, r["p1"], r["p2"])))
    from . import records2
    seen_rec = set()
    keys = [("match", mid)] + [("innings", f"{mid}|{r['innings_no']}|{r['batter_id']}") for r in db.q(
        "SELECT innings_no, batter_id FROM bat_innings WHERE match_id = ? ORDER BY runs DESC LIMIT 4", [mid])] + \
        [("spell", f"{mid}|{r['innings_no']}|{r['bowler_id']}") for r in db.q("SELECT innings_no, bowler_id FROM bowl_innings WHERE match_id = ? ORDER BY wickets DESC LIMIT 2", [mid])]
    for nt, k_ in keys:
        for rec_ in records2.containing(db, nt, k_):
            if rec_["id"] not in seen_rec and len(seen_rec) < 2:
                seen_rec.add(rec_["id"])
                out.append(edge("record", rec_["id"], rec_["title"], "record", f"Something from this match is #{rec_['rank']} on this list", n=1, full=1,
                                strength=1 - (rec_["rank"] - 1) / 10, unusual=0.7, when=m["start_date"], rec=cr))
    out.append(edge("match", mid, "Replay it ball by ball", "replay", "Historical replay: not live, nothing revealed ahead of the cursor",
                    n=1, full=1, strength=0.5, unusual=0.3, rec=cr, href_=f"/live-lab/{mid}", view="replay"))
    mo = moments.for_match(db, mid)
    if mo:
        out.append(edge("moment", mo["key"], mo["title"], "play", "What happened next? Call the ball before it is revealed", n=1, full=1,
                        strength=0.75, unusual=0.6, when=m["start_date"], rec=cr, href_=mo["href"]))
    if m["competition"]:
        out.append(edge("competition", f"{m['competition']}|{m['gender']}", f"{m['competition']} {m['season']}", "edition", "This edition",
                        n=1, full=1, strength=0.3, unusual=0.1, rec=cr,
                        href_=f"/competition?name={m['competition']}&gender={m['gender']}&season={m['season']}"))
    out.append(edge("rivalry", f"{m['ta']}|{m['tb']}|{m['gender']}", f"{m['ta']} v {m['tb']}", "rivalry", "Every covered meeting of these teams",
                    n=1, full=1, strength=0.4, unusual=0.1, rec=cr))
    for r in db.q("""SELECT match_id, team1, team2, start_date FROM team_results WHERE competition IS NOT DISTINCT FROM ? AND gender = ? AND start_date > ?
                     ORDER BY start_date LIMIT 1""", [m["competition"], m["gender"], m["start_date"]]):
        out.append(edge("match", r["match_id"], f"Next: {r['team1']} v {r['team2']}", "next_match", "Next match in the same competition",
                        n=1, full=1, strength=0.2, unusual=0.1, when=r["start_date"], rec=cr))
    return out


def _innings(db: DB, key: str) -> list[dict]:
    from . import moments, records2
    mid, inn, pid = key.split("|")
    b = db.q1("SELECT * FROM bat_innings WHERE match_id = ? AND innings_no = ? AND batter_id = ?", [mid, int(inn), pid])
    if not b:
        return []
    cr = comp_recog(b["competition"])
    out = [edge("match", mid, f"{b['team']} v {b['opponent']}", "match", "The match this innings belongs to", n=1, full=1, strength=0.6,
                unusual=0.2, when=b["start_date"], rec=cr)]
    mo = moments.for_innings(db, mid, int(inn), pid)
    if mo:
        out.append(edge("moment", mo["key"], mo["title"], "play", "What happened next? Call the ball before it is revealed", n=1, full=1,
                        strength=0.8, unusual=0.6, when=b["start_date"], rec=cr, href_=mo["href"]))
    if b["out_bowler_id"]:
        out.append(edge("battle", f"{pid}|{b['out_bowler_id']}", f"{nm(db, pid)} v {nm(db, b['out_bowler_id'])}", "dismissed_by",
                        "The bowler who dismissed them here: every meeting", n=1, full=1, strength=0.7, unusual=0.5, when=b["start_date"],
                        rec=recog(db, b["out_bowler_id"])))
        out.append(edge("delivery", b["out_delivery_id"], "The dismissal", "dismissal", "Replay the wicket", n=1, full=1, strength=0.5,
                        unusual=0.3, when=b["start_date"], rec=cr))
    for r in db.q("""SELECT bowler_id, count(*) FILTER (WHERE wides = 0) AS balls, sum(runs_batter) AS runs FROM balls WHERE match_id = ? AND innings_no = ?
                     AND batter_id = ? GROUP BY 1 ORDER BY balls DESC LIMIT 2""", [mid, int(inn), pid]):
        if r["bowler_id"] == b["out_bowler_id"]:
            continue
        out.append(edge("battle", f"{pid}|{r['bowler_id']}", f"{nm(db, pid)} v {nm(db, r['bowler_id'])}", "faced_most",
                        f"Faced them most in this innings: {r['runs']} off {r['balls']}", n=r["balls"], full=24, strength=0.5, unusual=0.3,
                        when=b["start_date"], rec=recog(db, r["bowler_id"])))
    for r in db.q("""SELECT p1, p2, runs, balls FROM partnerships WHERE match_id = ? AND innings_no = ? AND (p1 = ? OR p2 = ?) ORDER BY runs DESC LIMIT 1""",
                  [mid, int(inn), pid, pid]):
        partner = r["p2"] if r["p1"] == pid else r["p1"]
        a, c = sorted([pid, partner])
        out.append(edge("partnership", f"{a}|{c}", f"with {nm(db, partner)}", "partner", f"Biggest stand in this innings: {r['runs']} off {r['balls']}",
                        n=r["balls"], full=60, strength=min(1, r["runs"] / 100), unusual=0.3, when=b["start_date"], rec=recog(db, partner)))
        out.append(edge("player", partner, nm(db, partner), "teammate", "Their partner in the biggest stand", n=1, full=1, strength=0.4,
                        unusual=0.2, rec=recog(db, partner)))
    for rec_ in records2.containing(db, "innings", key)[:2]:
        out.append(edge("record", rec_["id"], rec_["title"], "record", f"This innings is #{rec_['rank']} on this list", n=1, full=1,
                        strength=1 - (rec_["rank"] - 1) / 10, unusual=0.7, when=b["start_date"], rec=cr))
    out.append(edge("player", pid, nm(db, pid), "player", "The batter", n=1, full=1, strength=0.5, unusual=0.1, rec=recog(db, pid)))
    return out


def _spell(db: DB, key: str) -> list[dict]:
    from . import records2
    mid, inn, pid = key.split("|")
    s = db.q1("SELECT * FROM bowl_innings WHERE match_id = ? AND innings_no = ? AND bowler_id = ?", [mid, int(inn), pid])
    when = s["start_date"] if s else None
    out = [edge("match", mid, f"{s['team']} v {s['opponent']}" if s else "The match", "match", "The match this spell belongs to", n=1, full=1,
                strength=0.6, unusual=0.2, when=when, rec=comp_recog(s["competition"] if s else None))]
    for r in db.q("""SELECT player_out_id, player_out, delivery_id, batter_runs_before FROM dis WHERE match_id = ? AND innings_no = ? AND bowler_id = ?
                     AND bowler_credited ORDER BY batter_runs_before DESC LIMIT 3""", [mid, int(inn), pid]):
        out.append(edge("battle", f"{r['player_out_id']}|{pid}", f"v {nm(db, r['player_out_id'], r['player_out'])}", "victim",
                        f"Dismissed in this spell on {r['batter_runs_before']}: every meeting", n=1, full=1, strength=0.6,
                        unusual=min(1, (r["batter_runs_before"] or 0) / 60), when=when, rec=recog(db, r["player_out_id"])))
    for r in db.q("""SELECT batter_id, sum(runs_batter) AS runs, count(*) FILTER (WHERE wides = 0) AS balls FROM balls WHERE match_id = ? AND innings_no = ?
                     AND bowler_id = ? GROUP BY 1 ORDER BY runs DESC LIMIT 1""", [mid, int(inn), pid]):
        if r["runs"] >= 12:
            out.append(edge("battle", f"{r['batter_id']}|{pid}", f"v {nm(db, r['batter_id'])}", "punished_by",
                            f"Scored most off this spell: {r['runs']} off {r['balls']}", n=r["balls"], full=24, strength=0.5, unusual=0.4,
                            when=when, rec=recog(db, r["batter_id"])))
    for r in db.q("""SELECT match_id, innings_no, wickets, runs, opponent, start_date FROM bowl_innings WHERE bowler_id = ? AND wickets >= 3
                     AND NOT (match_id = ? AND innings_no = ?) ORDER BY wickets DESC, runs LIMIT 1""", [pid, mid, int(inn)]):
        out.append(edge("spell", f"{r['match_id']}|{r['innings_no']}|{pid}", f"{r['wickets']}/{r['runs']} v {r['opponent']}", "best_spell",
                        "Their best other covered spell", n=1, full=1, strength=min(1, r["wickets"] / 5), unusual=0.5, when=r["start_date"], rec=recog(db, pid)))
    for rec_ in records2.containing(db, "spell", key)[:2]:
        out.append(edge("record", rec_["id"], rec_["title"], "record", f"This spell is #{rec_['rank']} on this list", n=1, full=1,
                        strength=1 - (rec_["rank"] - 1) / 10, unusual=0.7, when=when, rec=0.7))
    out.append(edge("player", pid, nm(db, pid), "player", "The bowler", n=1, full=1, strength=0.5, unusual=0.1, rec=recog(db, pid),
                    href_=f"/players/{pid}"))
    return out


def _delivery(db: DB, did: str) -> list[dict]:
    r = db.q1("SELECT match_id, innings_no, batter_id, bowler_id, start_date FROM balls WHERE delivery_id = ?", [did])
    if not r:
        return []
    return [edge("innings", f"{r['match_id']}|{r['innings_no']}|{r['batter_id']}", f"{nm(db, r['batter_id'])}'s innings", "player",
                 "The batter's innings", n=1, full=1, strength=0.6, unusual=0.2, when=r["start_date"], rec=recog(db, r["batter_id"])),
            edge("spell", f"{r['match_id']}|{r['innings_no']}|{r['bowler_id']}", f"{nm(db, r['bowler_id'])}'s spell", "player",
                 "The bowler's spell", n=1, full=1, strength=0.6, unusual=0.2, when=r["start_date"], rec=recog(db, r["bowler_id"])),
            edge("battle", f"{r['batter_id']}|{r['bowler_id']}", f"{nm(db, r['batter_id'])} v {nm(db, r['bowler_id'])}", "faced_most",
                 "Every meeting of these two", n=1, full=1, strength=0.7, unusual=0.3, rec=recog(db, r["batter_id"], r["bowler_id"])),
            edge("match", r["match_id"], "The match", "match", "Scorecard, events and battles", n=1, full=1, strength=0.5, unusual=0.1,
                 when=r["start_date"], rec=0.5)]


def _competition(db: DB, key: str) -> list[dict]:
    name, gender = key.split("|")
    cr = comp_recog(name)
    out = []
    for r in db.q("""SELECT match_id, team1, team2, season, start_date FROM team_results WHERE competition = ? AND gender = ? AND event_stage = 'Final'
                     ORDER BY start_date DESC LIMIT 2""", [name, gender]):
        out.append(edge("match", r["match_id"], f"{r['season']} final: {r['team1']} v {r['team2']}", "top_innings", "A final", n=1, full=1,
                        strength=0.7, unusual=0.5, when=r["start_date"], rec=cr))
    for r in db.q("""SELECT batter_id, sum(runs) AS runs FROM bat_innings WHERE competition = ? AND gender = ? GROUP BY 1 ORDER BY runs DESC LIMIT 1""",
                  [name, gender]):
        out.append(edge("player", r["batter_id"], nm(db, r["batter_id"]), "record", f"Most runs in covered data ({r['runs']})", n=r["runs"],
                        full=3000, strength=0.8, unusual=0.5, rec=recog(db, r["batter_id"])))
    for r in db.q("""SELECT bowler_id, sum(wickets) AS w FROM bowl_innings WHERE competition = ? AND gender = ? GROUP BY 1 ORDER BY w DESC LIMIT 1""",
                  [name, gender]):
        out.append(edge("player", r["bowler_id"], nm(db, r["bowler_id"]), "record", f"Most wickets in covered data ({r['w']})", n=r["w"],
                        full=150, strength=0.8, unusual=0.5, rec=recog(db, r["bowler_id"])))
    for r in db.q("""SELECT ta, tb, count(*) AS n FROM team_results WHERE competition = ? AND gender = ? GROUP BY 1, 2 ORDER BY n DESC LIMIT 1""",
                  [name, gender]):
        out.append(edge("rivalry", f"{r['ta']}|{r['tb']}|{gender}", f"{r['ta']} v {r['tb']}", "rivalry", f"Most frequent fixture ({r['n']} matches)",
                        n=r["n"], full=40, strength=0.5, unusual=0.2, rec=cr,
                        href_=f"/rivalry?a={r['ta']}&b={r['tb']}&gender={gender}&competition={name}"))
    out.append(edge("competition", key, "Records in this competition", "records", "Build any leaderboard for this competition", n=1, full=1,
                    strength=0.5, unusual=0.3, rec=cr, href_=f"/records?metric=runs&competition={name}&gender={gender}", view="records"))
    return out


def _rivalry(db: DB, key: str) -> list[dict]:
    a, b, g = key.split("|")
    out = []
    for r in db.q("""SELECT batter_id, bowler_id, count(*) AS n, count(DISTINCT match_id) AS m FROM balls WHERE gender = ?
                     AND ((batting_team = ? AND bowling_team = ?) OR (batting_team = ? AND bowling_team = ?)) GROUP BY 1, 2 ORDER BY n DESC LIMIT 2""",
                  [g, a, b, b, a]):
        out.append(edge("battle", f"{r['batter_id']}|{r['bowler_id']}", f"{nm(db, r['batter_id'])} v {nm(db, r['bowler_id'])}", "other_rival",
                        f"The recurring battle inside this rivalry: {r['n']} balls in {r['m']} matches", n=r["n"], full=240, strength=0.6,
                        unusual=0.4, rec=recog(db, r["batter_id"], r["bowler_id"])))
    for r in db.q("""SELECT match_id, start_date, competition FROM team_results WHERE ta = ? AND tb = ? AND gender = ? ORDER BY start_date DESC LIMIT 1""",
                  [a, b, g]):
        out.append(edge("match", r["match_id"], f"Latest meeting: {r['start_date']}", "latest_match", "Most recent covered meeting", n=1, full=1,
                        strength=0.4, unusual=0.1, when=r["start_date"], rec=comp_recog(r["competition"])))
    for r in db.q("""SELECT batter_id, sum(runs) AS runs FROM bat_innings WHERE gender = ? AND ((team = ? AND opponent = ?) OR (team = ? AND opponent = ?))
                     GROUP BY 1 ORDER BY runs DESC LIMIT 1""", [g, a, b, b, a]):
        out.append(edge("player", r["batter_id"], nm(db, r["batter_id"]), "record", f"Most runs in this rivalry ({r['runs']})", n=r["runs"],
                        full=1500, strength=0.7, unusual=0.4, rec=recog(db, r["batter_id"])))
    return out


def _partnership(db: DB, key: str) -> list[dict]:
    a, b = key.split("|")
    out = []
    for r in db.q("""SELECT match_id, innings_no, runs, balls, start_date FROM partnerships WHERE (p1 = ? AND p2 = ?) OR (p1 = ? AND p2 = ?)
                     ORDER BY runs DESC LIMIT 1""", [a, b, b, a]):
        out.append(edge("match", r["match_id"], f"Their biggest stand: {r['runs']} off {r['balls']} ({str(r['start_date'])[:4]})", "big_stand",
                        "The match of their highest partnership", n=r["balls"], full=60, strength=min(1, r["runs"] / 150), unusual=0.5,
                        when=r["start_date"], rec=0.6))
    for p in (a, b):
        out.append(edge("player", p, nm(db, p), "player", "One of the pair", n=1, full=1, strength=0.5, unusual=0.1, rec=recog(db, p)))
    return out


def _record(db: DB, rid: str) -> list[dict]:
    from . import records2
    rec_ = records2.get(db, rid)
    if not rec_:
        return []
    out = []
    for row in rec_["rows"][:3]:
        if row.get("href"):
            typ = row["href"].split("/")[1].split("?")[0]
            rel = {"innings": "top_innings", "spell": "top_spell", "match": "match", "battle": "other_rival", "partnership": "big_stand"}.get(row["node_type"], "player")
            out.append(edge(row["node_type"], row["node_key"], row["label"], rel, f"#{row['rank']}: {row['value_fmt']}", n=row.get("sample") or 1, full=200,
                            strength=1 - (row["rank"] - 1) / 5, unusual=0.6, when=row.get("date"), rec=recog(db, *row["ids"]) if row["ids"] else 0.6,
                            href_=row["href"]))
            for pid_ in row["ids"][:2]:
                if row["node_type"] != "player":
                    out.append(edge("player", pid_, nm(db, pid_), "player", f"On this list: #{row['rank']}", n=1, full=1, strength=0.5, unusual=0.3,
                                    rec=recog(db, pid_)))
    for other in records2.siblings(db, rid)[:2]:
        out.append(edge("record", other["id"], other["title"], "related_record", f"Another {other['category'].lower()} record", n=1, full=1,
                        strength=0.4, unusual=0.3, rec=0.6))
    return out


def _finding(db: DB, fid: str) -> list[dict]:
    from . import didnt_know
    f = next((x for x in didnt_know.pool(db) if x["id"] == fid), None)
    if not f:
        return []
    return [edge("player", p, nm(db, p), "player", "Involved in this finding", n=1, full=1, strength=0.5, unusual=0.2, rec=recog(db, p))
            for p in f["entities"]]


def _team(db: DB, key: str) -> list[dict]:
    t, g = key.split("|")
    out = []
    for r in db.q("""SELECT ta, tb, count(*) AS n FROM team_results WHERE gender = ? AND (ta = ? OR tb = ?) GROUP BY 1, 2 ORDER BY n DESC LIMIT 3""", [g, t, t]):
        out.append(edge("rivalry", f"{r['ta']}|{r['tb']}|{g}", f"{r['ta']} v {r['tb']}", "rivalry", f"{r['n']} covered meetings", n=r["n"], full=60,
                        strength=0.5, unusual=0.2, rec=0.6))
    return out
