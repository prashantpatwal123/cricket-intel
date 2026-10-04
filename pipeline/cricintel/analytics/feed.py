"""Daily discovery feed: an editorial-feeling mix without an editor.

Card types: finding, innings, spell, battle, record, partnership, moment (a historical last-ball finish), play.
Selection is deterministic for a given day (seeded by the date), so the feed changes daily but is reproducible.
Diversity controls: no player, team or competition repeated across the feed; genders alternate where possible; insight
types rotate. Every card says why it was selected.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json

from ..db import DB
from . import discovery as D
from . import libraries as L
from .entities import _nm
from .filters import FULL_MEMBERS

FM = ",".join("'" + t + "'" for t in FULL_MEMBERS)

VERSION = "feed-1.1"
SLOTS = ["finding", "innings", "battle", "spell", "moment", "finding", "partnership", "record", "innings", "play", "finding", "spell", "battle", "finding"]


def _pools(db: DB, sdx: bool) -> dict:
    """Candidate pools (deterministic order). Cached per dataset build (they don't depend on the day)."""
    p = db.dataset_dir / "derived" / "feed_pools.json"
    if p.exists():
        d = json.loads(p.read_text())
        if d.get("built_at") == db.manifest["built_at"] and d.get("version") == VERSION:
            return d["pools"]
    pools: dict[str, list] = {k: [] for k in ("finding", "innings", "spell", "battle", "partnership", "record", "moment")}
    for c in D.discover(db, sdx)["items"]:
        pools["finding"].append({"type": "finding", "title": c["headline"], "text": c["statement"], "href": c["href"], "gender": c["gender"],
                                 "players": c["entities"], "teams": [], "competition": None, "numbers": c["numbers"][:2],
                                 "reason": f"{c['type_label']}: ranked by unusualness, sample, recency and recognisability (score {c['score']})",
                                 "label": c["type_label"]})
    for g in ("male", "female"):
        for cat in ("difficult_chase", "late_acceleration", "fastest", "highest"):
            lib = L.innings_library(db, cat, g, "T20", limit=12)
            for r in lib["rows"]:
                pools["innings"].append({"type": "innings", "title": f"{r['name']} {r['runs']}{'*' if r['not_out'] else ''} off {r['balls']} v {r['opponent']}",
                                         "text": f"{lib['label']}: {r['metric']}. {r['competition']}, {r['start_date']}.",
                                         "href": f"/innings/{r['match_id']}/{r['innings_no']}/{r['batter_id']}", "gender": g, "players": [r["batter_id"]],
                                         "teams": [r["team"], r["opponent"]], "competition": r["competition"], "label": lib["label"],
                                         "reason": f"In the Innings Library: {lib['label'].lower()} ({lib['definition']})",
                                         "numbers": [{"label": "Runs", "value": r["runs"]}, {"label": "Balls", "value": r["balls"]}]})
        for cat in ("best_figures", "death_spells", "wicket_bursts", "economical"):
            lib = L.spell_library(db, cat, g, "T20", limit=10)
            for r in lib["rows"]:
                pools["spell"].append({"type": "spell", "title": f"{r['name']} {r['figures']} v {r['opponent']}", "text": f"{lib['label']}: {r['metric']}. {r['competition']}, {r['start_date']}.",
                                       "href": f"/spell/{r['match_id']}/{r['innings_no']}/{r['bowler_id']}", "gender": g, "players": [r["bowler_id"]],
                                       "teams": [r["team"], r["opponent"]], "competition": r["competition"], "label": lib["label"],
                                       "reason": f"In the Spell Library: {lib['label'].lower()} ({lib['definition']})",
                                       "numbers": [{"label": "Figures", "value": r["figures"]}, {"label": "Overs", "value": r["overs"]}]})
        for cat in ("recent", "one_sided", "highest_sr", "lowest_sr"):
            u = L.battle_universe(db, cat, g, limit=10)
            for r in u["rows"]:
                pools["battle"].append({"type": "battle", "title": f"{r['batter']} v {r['bowler']}", "text": f"{u['label']}: {r['runs']} runs off {r['balls']} balls, {r['outs']} out "
                                        f"(expected {r['expected_outs']} at the batter's usual rate).", "href": f"/battle?bat={r['batter_id']}&bowl={r['bowler_id']}",
                                        "gender": g, "players": [r["batter_id"], r["bowler_id"]], "teams": [], "competition": None, "label": u["label"],
                                        "reason": f"Battle Universe: {u['label'].lower()} ({u['definition']})",
                                        "numbers": [{"label": "Balls", "value": r["balls"]}, {"label": "SR", "value": r["sr"]}]})
        for r in db.q("""SELECT p.*, t.competition AS comp FROM partnerships p JOIN team_results t USING (match_id) WHERE p.gender = ? AND p.runs >= 120
                         AND (p.team_type = 'club' OR p.batting_team IN ('India','Australia','England','South Africa','New Zealand','Pakistan','Sri Lanka','West Indies','Bangladesh','Zimbabwe','Ireland','Afghanistan'))
                         ORDER BY p.start_date DESC LIMIT 12""", [g]):
            pools["partnership"].append({"type": "partnership", "title": f"{_nm(db, r['p1'])} & {_nm(db, r['p2'])}: {r['runs']} off {r['balls']}",
                                         "text": f"For the {r['wicket_no'] + 1}{['st', 'nd', 'rd'][r['wicket_no']] if r['wicket_no'] < 3 else 'th'} wicket, {r['batting_team']} v {r['bowling_team']}, {r['start_date']}.",
                                         "href": f"/innings/{r['match_id']}/{r['innings_no']}/{r['p1']}", "gender": g, "players": [r["p1"], r["p2"]],
                                         "teams": [r["batting_team"], r["bowling_team"]], "competition": r["comp"], "label": "Big partnership",
                                         "reason": "A 120+ partnership among the most recent in covered data", "numbers": [{"label": "Stand", "value": r["runs"]}]})
        # Historical moments: matches won off the very last ball of the chase
        for r in db.q("""SELECT b.delivery_id, b.match_id, b.batting_team, b.bowling_team, b.competition, b.start_date, b.ball_label, b.batter_id, b.runs_total
                         FROM balls b JOIN team_results t USING (match_id)
                         WHERE b.gender = ? AND b.innings_no = 2 AND b.winner = b.batting_team AND b.balls_left = 1 AND b.legal AND b.format_group = 'T20'
                           AND b.seq = (SELECT max(seq) FROM balls x WHERE x.match_id = b.match_id AND x.innings_no = 2)
                           AND (t.team_type = 'club' OR (t.team1 IN ({fm}) AND t.team2 IN ({fm})))
                         ORDER BY b.start_date DESC LIMIT 12""".format(fm=FM), [g]):
            pools["moment"].append({"type": "moment", "title": f"{r['batting_team']} won off the last ball v {r['bowling_team']}",
                                    "text": f"{_nm(db, r['batter_id'])} scored {r['runs_total']} off ball {r['ball_label']}. {r['competition']}, {r['start_date']}.",
                                    "href": f"/delivery/{r['delivery_id']}", "gender": g, "players": [r["batter_id"]], "teams": [r["batting_team"], r["bowling_team"]],
                                    "competition": r["competition"], "label": "Historical moment", "reason": "A chase completed off the final ball (recorded outcome)",
                                    "numbers": [{"label": "Last ball", "value": r["runs_total"]}]})
    from .explore import feed as explore_feed
    for r in explore_feed(db)["records"]:
        top = r["top"][0]
        pools["record"].append({"type": "record", "title": f"{r['preset']['title']}: {' v '.join(top['names'])}", "text": f"{top['value_fmt']} · {r['definition']}",
                                "href": f"/records?preset={r['preset']['id']}&gender={r['gender']}", "gender": r["gender"], "players": top["ids"], "teams": [],
                                "competition": None, "label": "Record", "reason": "Leads a ready-made leaderboard (covered data, not official records)",
                                "numbers": [{"label": r["label"], "value": top["value_fmt"]}]})
    for k in pools:
        pools[k] = pools[k][:60]
    p.write_text(json.dumps({"built_at": db.manifest["built_at"], "version": VERSION, "pools": pools}, default=str))
    return pools


def daily(db: DB, day: str | None = None, sdx: bool = False, n: int = len(SLOTS)) -> dict:
    day = day or dt.date.today().isoformat()
    pools = _pools(db, sdx)
    seed = int(hashlib.sha256(day.encode()).hexdigest(), 16)
    used_players, used_teams, used_comps, used_titles = set(), set(), set(), set()
    out, last_gender = [], None
    for i, slot in enumerate(SLOTS[:n]):
        if slot == "play":
            out.append({"type": "play", "title": "What happens next?", "text": "A real moment from the archive. Call the next ball and try to beat the model.",
                        "href": "/play", "label": "Play", "reason": "One game card per feed"})
            continue
        pool = pools.get(slot, [])
        if not pool:
            continue
        start = (seed >> (i * 7)) % len(pool)
        pick = None
        for j in range(len(pool)):
            c = pool[(start + j) % len(pool)]
            if c["title"] in used_titles or set(c["players"]) & used_players:
                continue
            if any(t in used_teams for t in c["teams"] if t) and j < len(pool) - 1:
                continue
            if c["competition"] and c["competition"] in used_comps and j < len(pool) - 1:
                continue
            if last_gender and c["gender"] == last_gender and j < len(pool) // 2:
                continue
            pick = c
            break
        if not pick:
            continue
        used_titles.add(pick["title"]); used_players |= set(pick["players"])
        used_teams |= {t for t in pick["teams"] if t}
        if pick["competition"]:
            used_comps.add(pick["competition"])
        last_gender = pick["gender"]
        out.append(pick)
    return {"day": day, "cards": out, "version": VERSION,
            "method": "Deterministic daily selection (seeded by the date) from ranked pools; no player, team or competition repeats; genders "
                      "alternate; card types rotate. Each card states why it was chosen."}
