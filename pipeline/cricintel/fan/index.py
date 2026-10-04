"""In-memory indexes for the fan layer, built once per data build (a few seconds, done by the startup warm-up).

Player-centric graph neighbours would otherwise be ~10 keyed queries over the innings, battle and partnership tables per
page (0.3–0.7 s cold). With these, a player's neighbourhood is pure Python lookups (a few ms). Values are exactly what the
queries returned; nothing is approximated.
"""
from __future__ import annotations

import threading
from collections import defaultdict

from ..db import DB

_IDX: dict = {}
_LOCK = threading.Lock()


def get(db: DB) -> dict:
    k = id(db)
    with _LOCK:
        if k in _IDX:
            return _IDX[k]
    d = build(db)
    with _LOCK:
        _IDX.clear()
        _IDX[k] = d
    return d


def _group(rows, key, limit=None):
    out = defaultdict(list)
    for r in rows:
        lst = out[r[key]]
        if limit is None or len(lst) < limit:
            lst.append(r)
    return dict(out)


def build(db: DB) -> dict:
    d = {}
    d["best_innings"] = _group(db.q("""SELECT batter_id, match_id, innings_no, runs, balls, not_out, opponent, start_date, competition FROM bat_innings
                                       WHERE balls > 0 QUALIFY row_number() OVER (PARTITION BY batter_id ORDER BY runs DESC, balls) <= 3
                                       ORDER BY batter_id, runs DESC, balls"""), "batter_id")
    d["best_innings15"] = {r["batter_id"]: r for r in db.q("""SELECT batter_id, match_id, innings_no FROM bat_innings WHERE balls >= 15
                                       QUALIFY row_number() OVER (PARTITION BY batter_id ORDER BY runs DESC) = 1""")}
    d["best_spells"] = _group(db.q("""SELECT bowler_id, match_id, innings_no, runs, balls, opponent, start_date, wickets, competition FROM bowl_innings
                                      WHERE wickets >= 3 QUALIFY row_number() OVER (PARTITION BY bowler_id ORDER BY wickets DESC, runs) <= 2
                                      ORDER BY bowler_id, wickets DESC, runs"""), "bowler_id")
    rows = db.q("""SELECT batter_id, bowler_id, sum(balls) AS balls, sum(runs) AS runs, sum(outs) AS outs, sum(matches) AS matches,
                   max(last_date) AS last, any_value(batter_out_rate) AS bat_or, any_value(batter_rpb) AS bat_rpb, any_value(bowler_rpb) AS bowl_rpb
                   FROM battles GROUP BY 1, 2""")
    d["battles_bat"] = _group(rows, "batter_id")
    d["battles_bowl"] = _group(rows, "bowler_id")
    d["partners"] = _group(db.q("""WITH x AS (SELECT p1 AS me, p2 AS other, runs, start_date FROM partnerships UNION ALL
                                              SELECT p2, p1, runs, start_date FROM partnerships)
                                   SELECT me, other AS partner, sum(runs) AS runs, count(*) AS n, max(start_date) AS last FROM x
                                   GROUP BY 1, 2 ORDER BY me, runs DESC"""), "me", limit=4)
    d["comp"] = {r["batter_id"]: r for r in db.q("""SELECT batter_id, competition, any_value(gender) AS g, count(*) AS n, max(start_date) AS last
                                       FROM bat_innings WHERE competition IS NOT NULL GROUP BY 1, 2
                                       QUALIFY row_number() OVER (PARTITION BY batter_id ORDER BY count(*) DESC) = 1""")}
    d["latest"] = {r["batter_id"]: r for r in db.q("""SELECT batter_id, match_id, opponent, start_date FROM bat_innings
                                       QUALIFY row_number() OVER (PARTITION BY batter_id ORDER BY start_date DESC) = 1""")}
    d["outs"] = {r["pid"]: r["n"] for r in db.q("SELECT player_out_id AS pid, count(*) AS n FROM dis WHERE counts_as_dismissal GROUP BY 1")}
    return d
