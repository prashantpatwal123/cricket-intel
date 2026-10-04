"""Daily discovery for Explore (Phase 7). Everything comes from the database; nothing is a news feed.

Sections (deterministic for a date; the page passes what this browser has already seen so it can be skipped):
  worth_knowing   "You probably didn't know…" facts (BH-protected discovery findings)
  battles         great battles: long, recognisable batter-v-bowler contests, with their numbers
  on_this_day     matches, innings, spells, partnerships on today's date
  record_book     a record of the day plus one more from a different category
  rabbit_hole     a player and the first five stops the Rabbit-Hole engine takes from them
  play            "can you beat the model?" moments from recognisable close finishes
"""
from __future__ import annotations

import hashlib
from datetime import date
from functools import lru_cache

from ..db import DB
from ..analytics.entities import names
from . import didnt_know, kg, moments, onthisday, rabbit, records2

VERSION = "daily-1.0"


def _seed(day: str, salt: str) -> int:
    return int(hashlib.sha256(f"{day}:{salt}".encode()).hexdigest(), 16)


@lru_cache(maxsize=4)
def _battle_pool(db: DB) -> list[dict]:
    rows = db.q("""SELECT batter_id, bowler_id, sum(balls) AS balls, sum(runs) AS runs, sum(outs) AS outs, sum(matches) AS m, max(last_date) AS last
                   FROM battles GROUP BY 1, 2 HAVING sum(balls) >= 180 AND sum(matches) >= 6""")
    for r in rows:
        r["w"] = kg.recog(db, r["batter_id"]) * kg.recog(db, r["bowler_id"]) * (1 + r["outs"] / 10) * (0.6 + 0.4 * kg.recency(r["last"]))
    rows.sort(key=lambda r: -r["w"])
    return rows[:120]


@lru_cache(maxsize=4)
def _start_pool(db: DB) -> list[str]:
    return [r["person_id"] for r in db.q("SELECT person_id FROM player_profile ORDER BY matches DESC LIMIT 150")]


@lru_cache(maxsize=4)
def _match_pool(db: DB) -> list[str]:
    rows = db.q("""SELECT match_id, competition FROM team_results WHERE i2_runs IS NOT NULL AND
                   ((win_by_wickets IS NOT NULL AND win_by_wickets <= 3) OR (win_by_runs IS NOT NULL AND win_by_runs <= 10))""")
    return [r["match_id"] for r in rows if kg.comp_recog(r["competition"]) >= 1.0]


@lru_cache(maxsize=16)
def _day(db: DB, day: str) -> dict:
    nm = names(db)
    out = {"date": day, "version": VERSION}
    out["worth_knowing"] = didnt_know.daily(db, day, k=8)
    bp = _battle_pool(db)
    off = _seed(day, "battles") % max(1, len(bp))
    bat = []
    for r in (bp[off:] + bp[:off])[:12]:
        bat.append({"id": f"battle:{r['batter_id']}|{r['bowler_id']}", "title": f"{nm.get(r['batter_id'])} v {nm.get(r['bowler_id'])}",
                    "detail": f"{r['runs']} off {r['balls']} balls · out {r['outs']} times · {r['m']} matches",
                    "href": f"/battle?bat={r['batter_id']}&bowl={r['bowler_id']}"})
    out["battles"] = bat
    otd = onthisday.on_this_day(db, day, k=8)
    out["on_this_day"] = {"label": otd["label"], "items": otd["items"], "rule": otd["rule"]}
    cat = records2.load(db)["records"]
    if cat:
        r1 = cat[_seed(day, "rec") % len(cat)]
        others = [r for r in cat if r["category"] != r1["category"]]
        r2 = others[_seed(day, "rec2") % len(others)] if others else None
        out["record_book"] = [{"id": r["id"], "title": r["title"], "scope": r["scope"], "category": r["category"], "top": r["rows"][:3],
                               "href": f"/records/{r['id']}"} for r in (r1, r2) if r]
    else:
        out["record_book"] = []
    sp = _start_pool(db)
    start = sp[_seed(day, "hole") % len(sp)]
    out["rabbit_hole"] = {"start": {"id": f"player:{start}", "title": nm.get(start, start), "href": f"/players/{start}"},
                          "path": [{"id": e["id"], "title": e["label"], "reason": e["reason"], "href": e["href"], "type": e["type"]}
                                   for e in rabbit.chain(db, "player", start, 5)]}
    mp = _match_pool(db)
    plays = []
    for i in range(6):
        if not mp:
            break
        mid = mp[_seed(day, f"play{i}") % len(mp)]
        m = moments.for_match(db, mid)
        if m and all(p["key"] != m["key"] for p in plays):
            t = db.q1("SELECT team1, team2, competition, season FROM team_results WHERE match_id = ?", [mid])
            plays.append({**m, "id": f"moment:{m['key']}", "context": f"{t['competition']} {t['season']} · {t['team1']} v {t['team2']}"})
        if len(plays) >= 3:
            break
    out["play"] = plays
    return out


def explore(db: DB, day: str | None = None, seen: set[str] | None = None) -> dict:
    day = day or date.today().isoformat()
    d = _day(db, day)
    seen = seen or set()

    def keep(lst, n, key="id"):
        fresh = [x for x in lst if x.get(key) not in seen and x.get("href") not in seen]
        return (fresh or lst)[:n]
    return {**d, "worth_knowing": keep(d["worth_knowing"], 4), "battles": keep(d["battles"], 4),
            "play": keep(d["play"], 2), "seen_skipped": len(seen)}
