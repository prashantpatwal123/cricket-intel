"""Generic records / leaderboard engine. Every leaderboard is a (entity, metric, filters, minimum sample) query.

Definitions live in METRICS: one SQL definition shared by the Records page, Ask Cricket and Explore, so a
number means the same thing everywhere. Every result returns its definition, filters, threshold and coverage.
"""
from __future__ import annotations

from ..db import DB
from .filters import Filters

# entity -> (source table alias expression, id column, name column, sample column definition)
ENTITIES = {
    "batter": {"table": "balls", "id": "batter_id", "label": "Batter", "perspective": "batter"},
    "bowler": {"table": "balls", "id": "bowler_id", "label": "Bowler", "perspective": "bowler"},
    "pair": {"table": "balls", "id": "batter_id || '|' || bowler_id", "label": "Batter v bowler", "perspective": "batter"},
    "bowler_wk": {"table": "dis", "id": "bowler_id", "label": "Bowler", "perspective": "bowler"},
    "fielder": {"table": "dis", "id": "fielder_id", "label": "Fielder", "perspective": "bowler"},
    "dismissed": {"table": "dis", "id": "player_out_id", "label": "Batter (dismissed)", "perspective": "batter"},
}

# key: (label, entity, value SQL, sample SQL, sample unit, default min sample, order, format, definition)
METRICS = {
    "runs": ("Runs", "batter", "sum(runs_batter)", "count(*) FILTER (WHERE faced)", "balls", 0, "DESC", "{:.0f}",
             "Runs off the bat (extras excluded)."),
    "sixes": ("Sixes", "batter", "count(*) FILTER (WHERE is_six)", "count(*) FILTER (WHERE faced)", "balls", 0, "DESC", "{:.0f}",
              "Balls hit for six (all-run sixes excluded)."),
    "fours": ("Fours", "batter", "count(*) FILTER (WHERE is_four)", "count(*) FILTER (WHERE faced)", "balls", 0, "DESC", "{:.0f}",
              "Balls hit for four (all-run fours excluded)."),
    "strike_rate": ("Strike rate", "batter", "100.0 * sum(runs_batter) / nullif(count(*) FILTER (WHERE faced), 0)",
                    "count(*) FILTER (WHERE faced)", "balls", 250, "DESC", "{:.1f}", "Runs off the bat per 100 balls faced (wides not counted as balls faced)."),
    "dot_pct": ("Dot-ball %", "batter", "100.0 * count(*) FILTER (WHERE faced AND runs_batter = 0) / nullif(count(*) FILTER (WHERE faced), 0)",
                "count(*) FILTER (WHERE faced)", "balls", 100, "ASC", "{:.1f}", "Share of balls faced with no run off the bat (lowest first)."),
    "boundary_pct": ("Boundary %", "batter", "100.0 * count(*) FILTER (WHERE is_four OR is_six) / nullif(count(*) FILTER (WHERE faced), 0)",
                     "count(*) FILTER (WHERE faced)", "balls", 100, "DESC", "{:.1f}", "Share of balls faced hit for 4 or 6."),
    "balls_faced": ("Balls faced", "batter", "count(*) FILTER (WHERE faced)", "count(*) FILTER (WHERE faced)", "balls", 0, "DESC", "{:.0f}",
                    "Legal balls faced plus no-balls (wides excluded)."),
    "wickets": ("Wickets", "bowler", "sum(wk)", "count(*) FILTER (WHERE legal)", "legal balls", 0, "DESC", "{:.0f}",
                "Bowler-credited wickets (run-outs etc. excluded)."),
    "economy": ("Economy", "bowler", "6.0 * sum(runs_batter + wides + noballs) / nullif(count(*) FILTER (WHERE legal), 0)",
                "count(*) FILTER (WHERE legal)", "legal balls", 120, "ASC", "{:.2f}", "Runs conceded per 6 legal balls (byes/leg-byes excluded)."),
    "bowl_dot_pct": ("Dot-ball % (bowling)", "bowler", "100.0 * count(*) FILTER (WHERE legal AND runs_total = 0) / nullif(count(*) FILTER (WHERE legal), 0)",
                     "count(*) FILTER (WHERE legal)", "legal balls", 120, "DESC", "{:.1f}", "Legal balls with no runs of any kind."),
    "sixes_conceded": ("Sixes conceded", "bowler", "count(*) FILTER (WHERE is_six)", "count(*) FILTER (WHERE legal)", "legal balls", 0, "DESC",
                       "{:.0f}", "Sixes hit off the bowler."),
    "keeper_catches": ("Catches as wicketkeeper", "fielder", "count(*) FILTER (WHERE route = 'CAUGHT_KEEPER' AND fielder_id = keeper_id)",
                       "count(*)", "dismissals", 0, "DESC", "{:.0f}",
                       "Catches by the fielding side's inferred wicketkeeper (DERIVED). Unresolved keeper status is excluded."),
    "stumpings": ("Stumpings", "fielder", "count(*) FILTER (WHERE kind = 'stumped')", "count(*)", "dismissals", 0, "DESC", "{:.0f}", "Stumpings effected."),
    "catches": ("Catches (all fielders)", "fielder", "count(*) FILTER (WHERE kind = 'caught' AND NOT coalesce(substitute, false))",
                "count(*)", "dismissals", 0, "DESC", "{:.0f}", "Catches by a named, non-substitute fielder (first fielder listed)."),
    "run_out_involvements": ("Run-out involvements (fielder)", "fielder", "count(*) FILTER (WHERE kind = 'run out')", "count(*)", "dismissals", 0,
                             "DESC", "{:.0f}", "Run-outs where the player is the first-named fielder."),
    "times_run_out": ("Times run out", "dismissed", "count(*) FILTER (WHERE kind = 'run out')", "count(*) FILTER (WHERE counts_as_dismissal)",
                      "dismissals", 0, "DESC", "{:.0f}", "Times the player was run out (striker or non-striker)."),
    "times_bowled": ("Times bowled", "dismissed", "count(*) FILTER (WHERE kind = 'bowled')", "count(*) FILTER (WHERE counts_as_dismissal)",
                     "dismissals", 0, "DESC", "{:.0f}", "Times the player was bowled."),
    "pair_dismissals": ("Dismissals of one batter by one bowler", "pair", "count(*) FILTER (WHERE outflag)", "count(*) FILTER (WHERE faced)", "balls", 0,
                        "DESC", "{:.0f}", "Bowler-credited dismissals of the batter by that bowler."),
    "pair_strike_rate": ("Batter v bowler strike rate", "pair", "100.0 * sum(runs_batter) / nullif(count(*) FILTER (WHERE faced), 0)",
                         "count(*) FILTER (WHERE faced)", "balls", 60, "DESC", "{:.1f}", "Batter's strike rate against one bowler."),
    "pair_balls_per_dismissal": ("Batter v bowler: balls per dismissal", "pair",
                                 "count(*) FILTER (WHERE faced) * 1.0 / nullif(count(*) FILTER (WHERE outflag), 0)",
                                 "count(*) FILTER (WHERE faced)", "balls", 60, "ASC", "{:.1f}",
                                 "Balls the batter faced per dismissal by that bowler (lowest = bowler dominates)."),
}

PRESETS = [
    {"id": "death-sixes", "title": "Most sixes in death overs", "metric": "sixes", "filters": {"phase": "death"}},
    {"id": "dot-after30", "title": "Lowest dot-ball % after 30 balls faced", "metric": "dot_pct", "filters": {"faced_from": 30}, "min": 200},
    {"id": "one-bowler", "title": "Most dismissals of one batter by one bowler", "metric": "pair_dismissals", "filters": {}},
    {"id": "chase-sr", "title": "Highest strike rate while chasing (T20, full members & leagues)", "metric": "strike_rate",
     "filters": {"chasing": True, "format": "T20", "full_members": True}, "min": 500},
    {"id": "run-outs", "title": "Most times run out", "metric": "times_run_out", "filters": {}},
    {"id": "keeper-catches", "title": "Most catches as wicketkeeper", "metric": "keeper_catches", "filters": {}},
    {"id": "best-matchup", "title": "Best batter v bowler strike rate (min 60 balls)", "metric": "pair_strike_rate", "filters": {}},
    {"id": "death-economy", "title": "Best death-overs economy (T20, full members & leagues)", "metric": "economy",
     "filters": {"phase": "death", "format": "T20", "full_members": True}, "min": 300},
]


def leaderboard(db: DB, metric: str, f: Filters, min_sample: int | None = None, limit: int = 25, gender: str | None = None) -> dict:
    if metric not in METRICS:
        raise ValueError(f"unknown metric {metric}")
    label, entity, val, samp, unit, default_min, order, fmt, definition = METRICS[metric]
    E = ENTITIES[entity]
    w, p = f.where(E["perspective"])
    if gender:
        w, p = w + " AND gender = ?", [*p, gender]
    m = default_min if min_sample is None else min_sample
    src = E["table"]
    if entity == "pair":
        src = """(SELECT b.*, EXISTS (SELECT 1 FROM dis x WHERE x.delivery_id = b.delivery_id AND x.player_out_id = b.batter_id
                   AND x.bowler_credited) AS outflag FROM balls b)"""
    if entity == "bowler":
        src = """(SELECT b.*, coalesce(w.n, 0) AS wk FROM balls b LEFT JOIN
                   (SELECT delivery_id, count(*) AS n FROM wickets WHERE bowler_credited GROUP BY 1) w USING (delivery_id))"""
    if entity == "fielder":
        w += " AND fielder_id IS NOT NULL"
    rows = db.q(f"""SELECT {E['id']} AS k, {val} AS value, {samp} AS sample, count(DISTINCT match_id) AS matches,
                    min(start_date) AS first_date, max(start_date) AS last_date, any_value(gender) AS gender
                    FROM {src} WHERE {w} GROUP BY 1 HAVING {samp} >= ? AND {val} IS NOT NULL AND {val} > 0
                    ORDER BY value {order}, sample DESC LIMIT ?""", [*p, m, limit])
    ids = set()
    for r in rows:
        ids.update(str(r["k"]).split("|"))
    names = {x["person_id"]: x["name"] for x in db.q(
        f"SELECT person_id, name FROM player_profile WHERE person_id IN ({','.join('?' * len(ids))})", list(ids))} if ids else {}
    out = []
    for i, r in enumerate(rows, 1):
        parts = str(r["k"]).split("|")
        out.append({"rank": i, "ids": parts, "names": [names.get(x, x) for x in parts], "value": r["value"],
                    "value_fmt": fmt.format(r["value"]), "sample": r["sample"], "matches": r["matches"],
                    "first_date": r["first_date"], "last_date": r["last_date"], "gender": r["gender"]})
    return {"metric": metric, "label": label, "entity": entity, "entity_label": E["label"], "definition": definition,
            "order": "highest first" if order == "DESC" else "lowest first", "filters": f.active(), "gender": gender,
            "min_sample": m, "sample_unit": unit, "rows": out,
            "coverage": "Covered data only: IPL, WPL, men's and women's T20Is and ODIs from Cricsheet. Matches involving Afghanistan "
                        "men are withheld by Cricsheet, and T20I completeness is unknown. These are not official records."}
