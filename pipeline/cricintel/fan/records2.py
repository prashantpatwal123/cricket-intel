"""Records V2: a browsable record book with human-readable titles, organised by what fans look for.

Every record = one named definition × one scope (gender, format). Each carries its definition, minimum sample, filters,
coverage statement and, per row, a link to the evidence (the innings, spell, battle, match or player). Career/rate
records reuse the shared leaderboard engine (analytics/records.py) so a number means the same thing everywhere.
Precomputed once per data build (python -m cricintel.precompute) and served from a JSON file.
"""
from __future__ import annotations

import json
import time
from functools import lru_cache

from ..db import DB
from ..analytics import records as REC
from ..analytics.entities import names
from ..analytics.filters import Filters

VERSION = "records-v2-1.1"
SCOPES = [("male", "T20"), ("female", "T20"), ("male", "ODI"), ("female", "ODI")]
from ..analytics.filters import FULL_MEMBERS  # noqa: E402
FM = ",".join("'" + t + "'" for t in FULL_MEMBERS)


def major_sql(a: str, b: str) -> str:
    """Leagues plus matches between ICC full members (a/b = the two team columns of the table)."""
    return f" AND (team_type = 'club' OR ({a} IN ({FM}) AND {b} IN ({FM})))"


MAJOR_COLS = {"innings": ("team", "opponent"), "fifty": ("batting_team", "bowling_team"), "spell": ("team", "opponent"),
              "stand": ("batting_team", "bowling_team"), "pair": ("batting_team", "bowling_team"), "chase": ("team1", "team2"),
              "total": ("team1", "team2"), "wins": ("team1", "team2")}
GL = {"male": "Men's", "female": "Women's"}
COVERAGE = ("Covered data only: IPL, WPL, men's and women's T20Is and ODIs from Cricsheet. Matches involving Afghanistan men are withheld by "
            "Cricsheet, and T20I completeness is unknown. These are not official records.")
CATEGORIES = ["Batting", "Bowling", "Partnerships", "Matchups", "Phases", "Chasing", "Setting a target", "Wickets down", "Innings progression",
              "Competitions", "Teams", "Eras", "Fielding"]

# id, category, title, definition, kind, spec
DEFS: list[dict] = [
    # ---- batting (single innings)
    dict(id="highest-score", cat="Batting", title="Highest individual scores", kind="innings", order="runs DESC, balls",
         value="runs", fmtv=lambda r: f"{r['runs']}{'*' if r['not_out'] else ''} ({r['balls']})",
         definition="Runs off the bat in one innings. * = not out; balls faced in brackets.", min_sample=None),
    dict(id="fastest-fifty", cat="Batting", title="Fewest balls to a fifty", kind="fifty",
         definition="Balls faced (no-balls included, wides not) when the batter's score first reached 50.", min_sample=None),
    dict(id="most-sixes-innings", cat="Batting", title="Most sixes in an innings", kind="innings", order="sixes DESC, balls", value="sixes",
         fmtv=lambda r: f"{r['sixes']} sixes ({r['runs']} off {r['balls']})", definition="Balls hit for six by one batter in one innings.", min_sample=None),
    dict(id="highest-sr-innings", cat="Batting", title="Highest strike rate in an innings (25+ balls)", kind="innings",
         where="balls >= 25", order="runs * 1.0 / balls DESC", value="sr", fmtv=lambda r: f"{100 * r['runs'] / r['balls']:.0f} ({r['runs']} off {r['balls']})",
         definition="Runs per 100 balls in one innings, minimum 25 balls faced.", min_sample="25 balls"),
    dict(id="most-runs", cat="Batting", title="Most runs in covered matches", kind="board", metric="runs", filters={},
         definition="Career runs off the bat in covered matches only."),
    # ---- bowling
    dict(id="best-figures", cat="Bowling", title="Best bowling figures", kind="spell", order="wickets DESC, runs", value="wickets",
         fmtv=lambda r: f"{r['wickets']}/{r['runs']}", definition="Most bowler-credited wickets in one innings, then fewest runs conceded.", min_sample=None),
    dict(id="economical-spell", cat="Bowling", title="Most economical full spells", kind="spell", where="balls >= {full}",
         order="runs * 1.0 / balls, wickets DESC", value="econ", fmtv=lambda r: f"{6 * r['runs'] / r['balls']:.2f} an over ({r['wickets']}/{r['runs']})",
         definition="Runs per over in one innings, minimum a full allocation (4 overs in T20, 10 in ODIs).", min_sample="a full allocation"),
    dict(id="most-dots-spell", cat="Bowling", title="Most dot balls in a spell", kind="spell", order="dots DESC, runs", value="dots",
         fmtv=lambda r: f"{r['dots']} dots ({r['wickets']}/{r['runs']})", definition="Legal balls conceding no runs, in one innings.", min_sample=None),
    dict(id="most-wickets", cat="Bowling", title="Most wickets in covered matches", kind="board", metric="wickets", filters={},
         definition="Bowler-credited wickets in covered matches only."),
    # ---- partnerships
    dict(id="highest-stand", cat="Partnerships", title="Highest partnerships", kind="stand",
         definition="Runs added while two batters were together (extras included), one innings."),
    dict(id="pair-runs", cat="Partnerships", title="Most runs together", kind="pair",
         definition="Total partnership runs for a pair across covered matches (at least 5 stands)."),
    # ---- matchups
    dict(id="pair-dismissals", cat="Matchups", title="Most dismissals of one batter by one bowler", kind="board", metric="pair_dismissals", filters={},
         definition="Bowler-credited dismissals of the batter by that bowler."),
    dict(id="pair-sr", cat="Matchups", title="Highest strike rate against one bowler (60+ balls)", kind="board", metric="pair_strike_rate", filters={},
         definition="A batter's strike rate against a single bowler, minimum 60 balls."),
    dict(id="pair-bpd", cat="Matchups", title="Fewest balls per dismissal by one bowler (60+ balls)", kind="board", metric="pair_balls_per_dismissal",
         filters={}, definition="Balls the batter faced per dismissal by that bowler, minimum 60 balls."),
    # ---- phases
    dict(id="death-sr", cat="Phases", title="Highest death-overs strike rate", kind="board", metric="strike_rate", filters={"phase": "death", "full_members": True},
         min=300, definition="Runs per 100 balls in the death overs (T20: 16–20; ODI: 41–50), minimum 300 balls."),
    dict(id="death-economy", cat="Phases", title="Best death-overs economy", kind="board", metric="economy", filters={"phase": "death", "full_members": True},
         min=300, definition="Runs conceded per over in the death overs, minimum 300 legal balls."),
    dict(id="pp-economy", cat="Phases", title="Best powerplay economy", kind="board", metric="economy", filters={"phase": "powerplay", "full_members": True},
         min=300, definition="Runs conceded per over in powerplay overs, minimum 300 legal balls."),
    dict(id="pp-sr", cat="Phases", title="Highest powerplay strike rate", kind="board", metric="strike_rate", filters={"phase": "powerplay", "full_members": True},
         min=300, definition="Runs per 100 balls in powerplay overs, minimum 300 balls."),
    # ---- chasing / setting
    dict(id="chase-sr", cat="Chasing", title="Highest strike rate while chasing", kind="board", metric="strike_rate", filters={"chasing": True, "full_members": True},
         min=500, definition="Runs per 100 balls in second-innings chases, minimum 500 balls."),
    dict(id="biggest-chases", cat="Chasing", title="Biggest successful chases", kind="chase",
         definition="Highest second-innings totals by the side that won the match chasing (rain-adjusted targets included and labelled)."),
    dict(id="highest-totals", cat="Setting a target", title="Highest totals batting first", kind="total",
         definition="First-innings team totals."),
    dict(id="set-sr", cat="Setting a target", title="Highest strike rate batting first", kind="board", metric="strike_rate",
         filters={"chasing": False, "full_members": True}, min=500, definition="Runs per 100 balls when batting first, minimum 500 balls."),
    # ---- wickets down
    dict(id="sr-3-down", cat="Wickets down", title="Highest strike rate with 3+ wickets down", kind="board", metric="strike_rate",
         filters={"wk_from": 3, "full_members": True}, min=300, definition="Runs per 100 balls faced when three or more wickets had fallen, minimum 300 balls."),
    dict(id="avg-0-2-down", cat="Wickets down", title="Highest average with 0–2 wickets down", kind="board", metric="average",
         filters={"wk_to": 2, "full_members": True}, min=500, definition="Runs per dismissal while 0–2 wickets had fallen, minimum 500 balls."),
    # ---- innings progression
    dict(id="after30-sr", cat="Innings progression", title="Highest strike rate after 30 balls", kind="board", metric="strike_rate",
         filters={"faced_from": 30, "full_members": True}, min=300, definition="Runs per 100 balls once the batter had faced 30 balls in the innings, minimum 300 such balls."),
    dict(id="first10-dots", cat="Innings progression", title="Fewest dot balls in the first 10 balls", kind="board", metric="dot_pct",
         filters={"faced_to": 9, "full_members": True}, min=200, definition="Share of the first 10 balls of an innings with no run off the bat (lowest first), minimum 200 such balls."),
    # ---- competitions, teams, eras, fielding
    dict(id="season-runs", cat="Competitions", title="Most runs in one league season", kind="season", stat="runs",
         definition="Runs off the bat in one season of one league (IPL, WPL)."),
    dict(id="season-wickets", cat="Competitions", title="Most wickets in one league season", kind="season", stat="wickets",
         definition="Bowler-credited wickets in one season of one league (IPL, WPL)."),
    dict(id="biggest-wins", cat="Teams", title="Biggest wins by runs", kind="wins", definition="Margin of victory in runs."),
    dict(id="runs-since-2020", cat="Eras", title="Most runs since 2020", kind="board", metric="runs", filters={"year_from": 2020},
         definition="Runs off the bat in covered matches from 2020 onward."),
    dict(id="wickets-2010s", cat="Eras", title="Most wickets in the 2010s", kind="board", metric="wickets", filters={"year_from": 2010, "year_to": 2019},
         definition="Bowler-credited wickets in covered matches 2010–2019. Coverage of the early 2010s is thinner."),
    dict(id="keeper-catches", cat="Fielding", title="Most catches as wicketkeeper", kind="board", metric="keeper_catches", filters={},
         definition="Catches by the fielding side's inferred wicketkeeper (DERIVED keeper identity)."),
]


def _path(db: DB):
    return db.dataset_dir / "derived" / "fan_records.json"


def _nm(db, pid):
    return names(db).get(pid, pid)


def _rows_innings(db, d, g, f, mj=""):
    where = d.get("where", "balls > 0") + mj
    rows = db.q(f"""SELECT match_id, innings_no, batter_id, runs, balls, sixes, not_out, opponent, team, start_date, venue FROM bat_innings
                    WHERE gender = ? AND format_group = ? AND {where} ORDER BY {d['order']} LIMIT 10""", [g, f])
    return [dict(label=f"{_nm(db, r['batter_id'])}", detail=f"{r['team']} v {r['opponent']}, {r['start_date']}", value_fmt=d["fmtv"](r),
                 ids=[r["batter_id"]], node_type="innings", node_key=f"{r['match_id']}|{r['innings_no']}|{r['batter_id']}",
                 href=f"/innings/{r['match_id']}/{r['innings_no']}/{r['batter_id']}", date=str(r["start_date"]), sample=r["balls"]) for r in rows]


def _rows_fifty(db, d, g, f, mj=""):
    rows = db.q(f"""SELECT match_id, innings_no, batter_id, batter_balls_before + 1 AS balls, batting_team, bowling_team, start_date FROM balls
                   WHERE gender = ? AND format_group = ? AND faced AND batter_runs_before < 50 AND batter_runs_before + runs_batter >= 50 {mj}
                   ORDER BY balls, start_date LIMIT 10""", [g, f])
    return [dict(label=_nm(db, r["batter_id"]), detail=f"{r['batting_team']} v {r['bowling_team']}, {r['start_date']}", value_fmt=f"{r['balls']} balls",
                 ids=[r["batter_id"]], node_type="innings", node_key=f"{r['match_id']}|{r['innings_no']}|{r['batter_id']}",
                 href=f"/innings/{r['match_id']}/{r['innings_no']}/{r['batter_id']}", date=str(r["start_date"]), sample=r["balls"]) for r in rows]


def _rows_spell(db, d, g, f, mj=""):
    where = d.get("where", "balls > 0").format(full=24 if f == "T20" else 60) + mj
    rows = db.q(f"""SELECT match_id, innings_no, bowler_id, wickets, runs, balls, dots, team, opponent, start_date FROM bowl_innings
                    WHERE gender = ? AND format_group = ? AND {where} ORDER BY {d['order']} LIMIT 10""", [g, f])
    return [dict(label=_nm(db, r["bowler_id"]), detail=f"{r['team']} v {r['opponent']}, {r['start_date']}", value_fmt=d["fmtv"](r), ids=[r["bowler_id"]],
                 node_type="spell", node_key=f"{r['match_id']}|{r['innings_no']}|{r['bowler_id']}",
                 href=f"/spell/{r['match_id']}/{r['innings_no']}/{r['bowler_id']}", date=str(r["start_date"]), sample=r["balls"]) for r in rows]


def _rows_stand(db, d, g, f, mj=""):
    rows = db.q(f"""SELECT match_id, p1, p2, runs, balls, wicket_no, batting_team, bowling_team, start_date FROM partnerships
                   WHERE gender = ? AND format_group = ? {mj} ORDER BY runs DESC, balls LIMIT 10""", [g, f])
    out = []
    for r in rows:
        a, b = sorted([r["p1"], r["p2"]])
        out.append(dict(label=f"{_nm(db, r['p1'])} & {_nm(db, r['p2'])}", detail=f"wicket {r['wicket_no'] + 1} · {r['batting_team']} v {r['bowling_team']}, {r['start_date']}",
                        value_fmt=f"{r['runs']} ({r['balls']})", ids=[r["p1"], r["p2"]], node_type="match", node_key=r["match_id"],
                        href=f"/match/{r['match_id']}", date=str(r["start_date"]), sample=r["balls"]))
    return out


def _rows_pair(db, d, g, f, mj=""):
    rows = db.q(f"""SELECT least(p1, p2) AS a, greatest(p1, p2) AS b, sum(runs) AS runs, count(*) AS n, max(start_date) AS last FROM partnerships
                   WHERE gender = ? AND format_group = ? {mj} GROUP BY 1, 2 HAVING count(*) >= 5 ORDER BY runs DESC LIMIT 10""", [g, f])
    return [dict(label=f"{_nm(db, r['a'])} & {_nm(db, r['b'])}", detail=f"{r['n']} stands", value_fmt=f"{r['runs']} runs", ids=[r["a"], r["b"]],
                 node_type="partnership", node_key=f"{r['a']}|{r['b']}", href=f"/partnerships?p1={r['a']}&p2={r['b']}&format={f}", date=str(r["last"]),
                 sample=r["n"]) for r in rows]


def _rows_chase(db, d, g, f, mj=""):
    rows = db.q(f"""SELECT match_id, i2_team, i1_team, i2_runs, i2_wkts, i1_runs, start_date, method FROM team_results
                   WHERE gender = ? AND format_group = ? {mj} AND winner = i2_team AND i2_runs IS NOT NULL ORDER BY i2_runs DESC LIMIT 10""", [g, f])
    return [dict(label=f"{r['i2_team']} v {r['i1_team']}", detail=f"chasing {r['i1_runs'] + 1}, {r['start_date']}" + (f" · {r['method']}" if r["method"] else ""),
                 value_fmt=f"{r['i2_runs']}/{r['i2_wkts']}", ids=[], node_type="match", node_key=r["match_id"], href=f"/match/{r['match_id']}",
                 date=str(r["start_date"]), sample=None) for r in rows]


def _rows_total(db, d, g, f, mj=""):
    rows = db.q(f"""SELECT match_id, i1_team, i2_team, i1_runs, i1_wkts, start_date FROM team_results WHERE gender = ? AND format_group = ? {mj}
                   AND i1_runs IS NOT NULL ORDER BY i1_runs DESC LIMIT 10""", [g, f])
    return [dict(label=f"{r['i1_team']} v {r['i2_team']}", detail=str(r["start_date"]), value_fmt=f"{r['i1_runs']}/{r['i1_wkts']}", ids=[],
                 node_type="match", node_key=r["match_id"], href=f"/match/{r['match_id']}", date=str(r["start_date"]), sample=None) for r in rows]


def _rows_wins(db, d, g, f, mj=""):
    rows = db.q(f"""SELECT match_id, winner, team1, team2, win_by_runs, start_date FROM team_results WHERE gender = ? AND format_group = ? {mj}
                   AND win_by_runs IS NOT NULL ORDER BY win_by_runs DESC LIMIT 10""", [g, f])
    return [dict(label=f"{r['winner']} beat {r['team2'] if r['winner'] == r['team1'] else r['team1']}", detail=str(r["start_date"]),
                 value_fmt=f"by {r['win_by_runs']} runs", ids=[], node_type="match", node_key=r["match_id"], href=f"/match/{r['match_id']}",
                 date=str(r["start_date"]), sample=None) for r in rows]


def _rows_season(db, d, g, f, mj=""):
    if f != "T20":
        return []
    if d["stat"] == "runs":
        rows = db.q("""SELECT batter_id AS pid, competition, season, sum(runs) AS v, count(*) AS n, max(start_date) AS last FROM bat_innings
                       WHERE gender = ? AND format_group = 'T20' AND team_type = 'club' GROUP BY 1, 2, 3 ORDER BY v DESC LIMIT 10""", [g])
        unit = "runs"
    else:
        rows = db.q("""SELECT bowler_id AS pid, competition, season, sum(wickets) AS v, count(*) AS n, max(start_date) AS last FROM bowl_innings
                       WHERE gender = ? AND format_group = 'T20' AND team_type = 'club' GROUP BY 1, 2, 3 ORDER BY v DESC LIMIT 10""", [g])
        unit = "wickets"
    return [dict(label=_nm(db, r["pid"]), detail=f"{r['competition']} {r['season']} · {r['n']} innings", value_fmt=f"{r['v']} {unit}", ids=[r["pid"]],
                 node_type="player", node_key=r["pid"], href=f"/competition?name={r['competition']}&gender={g}&season={r['season']}",
                 date=str(r["last"]), sample=r["n"]) for r in rows]


def _rows_board(db, d, g, f):
    fl = Filters.parse({**{k: v for k, v in d["filters"].items()}, "format": f})
    lb = REC.leaderboard(db, d["metric"], fl, d.get("min"), limit=10, gender=g)
    out = []
    for r in lb["rows"]:
        if len(r["ids"]) == 2:
            node_type, key, h = "battle", f"{r['ids'][0]}|{r['ids'][1]}", f"/battle?bat={r['ids'][0]}&bowl={r['ids'][1]}"
            label = f"{r['names'][0]} v {r['names'][1]}"
        else:
            node_type, key, h = "player", r["ids"][0], f"/players/{r['ids'][0]}"
            label = r["names"][0]
        out.append(dict(label=label, detail=f"{r['sample']} {lb['sample_unit']} · {r['matches']} matches", value_fmt=r["value_fmt"], ids=r["ids"],
                        node_type=node_type, node_key=key, href=h, date=str(r["last_date"]), sample=r["sample"]))
    return out, lb


KIND = {"innings": _rows_innings, "fifty": _rows_fifty, "spell": _rows_spell, "stand": _rows_stand, "pair": _rows_pair, "chase": _rows_chase,
        "total": _rows_total, "wins": _rows_wins, "season": _rows_season}


def _filters_text(d, f) -> list[str]:
    T = {"phase": lambda v: f"{v} overs", "full_members": lambda v: "leagues + full-member internationals",
         "chasing": lambda v: "chasing" if v else "batting first", "wk_from": lambda v: f"{v}+ wickets down", "wk_to": lambda v: f"0–{v} wickets down",
         "faced_from": lambda v: f"after {v} balls faced", "faced_to": lambda v: f"first {int(v) + 1} balls", "year_from": lambda v: f"from {v}",
         "year_to": lambda v: f"to {v}"}
    return [f] + [T[k](v) if k in T else f"{k}={v}" for k, v in d.get("filters", {}).items()]


def build(db: DB) -> dict:
    t0 = time.time()
    recs = []
    for d in DEFS:
        # single-match records get a "major teams" view first (leagues + full-member internationals), then everything covered
        variants = [True, False] if d["kind"] in MAJOR_COLS else [False]
        for g, f in SCOPES:
            for major in variants:
                if d["kind"] == "board":
                    rows, lb = _rows_board(db, d, g, f)
                    min_sample = f"{lb['min_sample']} {lb['sample_unit']}" if lb["min_sample"] else None
                else:
                    mj = major_sql(*MAJOR_COLS[d["kind"]]) if major else ""
                    rows, min_sample = KIND[d["kind"]](db, d, g, f, mj), d.get("min_sample")
                if not rows:
                    continue
                for i, r in enumerate(rows, 1):
                    r["rank"] = i
                recs.append({"id": f"{d['id']}.{g}.{f}" + (".major" if major else ""), "def_id": d["id"], "category": d["cat"], "title": d["title"],
                             "scope": f"{GL[g]} {f}" + (" · major teams" if major else (" · all covered" if d["kind"] in MAJOR_COLS else "")),
                             "gender": g, "format": f, "major": major, "definition": d["definition"], "min_sample": min_sample,
                             "filters": _filters_text(d, f) + (["leagues + full-member internationals"] if major else []),
                             "coverage": COVERAGE, "prov": "DERIVED" if d["id"] == "keeper-catches" else "OBSERVED", "rows": rows})
    out = {"version": VERSION, "built_at": db.manifest["built_at"], "categories": CATEGORIES, "records": recs, "seconds": round(time.time() - t0, 1)}
    _path(db).write_text(json.dumps(out, default=str))
    return {"records": len(recs), "seconds": out["seconds"]}


@lru_cache(maxsize=2)
def load(db: DB) -> dict:
    p = _path(db)
    if p.exists():
        d = json.loads(p.read_text())
        if d.get("built_at") == db.manifest["built_at"] and d.get("version") == VERSION:
            return _index(d)
    return _index({"records": [], "categories": CATEGORIES})


def _index(d: dict) -> dict:
    d["by_id"] = {r["id"]: r for r in d["records"]}
    held, contains = {}, {}
    for r in d["records"]:
        for row in r["rows"]:
            for pid in row["ids"]:
                held.setdefault(pid, []).append({"id": r["id"], "title": f"{r['title']} · {r['scope']}", "rank": row["rank"], "value_fmt": row["value_fmt"],
                                                 "sample": row.get("sample") or 0, "last_date": row.get("date"), "category": r["category"]})
            contains.setdefault((row["node_type"], row["node_key"]), []).append({"id": r["id"], "title": f"{r['title']} · {r['scope']}", "rank": row["rank"]})
    for v in held.values():
        v.sort(key=lambda x: (x["rank"], x["title"]))
    d["held"], d["contains"] = held, contains
    return d


def get(db: DB, rid: str) -> dict | None:
    return load(db)["by_id"].get(rid)


def held_by(db: DB, pid: str) -> list[dict]:
    # one entry per record definition (its best rank across scopes), so one list doesn't fill the page
    seen, out = set(), []
    for h in load(db)["held"].get(pid, []):
        base = h["id"].split(".")[0]
        if base not in seen:
            seen.add(base)
            out.append(h)
    return out


def containing(db: DB, node_type: str, key: str) -> list[dict]:
    seen, out = set(), []
    for c in sorted(load(db)["contains"].get((node_type, key), []), key=lambda c: c["rank"]):
        base = c["id"].split(".")[0]
        if base not in seen:
            seen.add(base); out.append(c)
    return out


def siblings(db: DB, rid: str) -> list[dict]:
    d = load(db)
    r = d["by_id"].get(rid)
    if not r:
        return []
    out, seen = [], set()
    for x in d["records"]:
        if x["category"] == r["category"] and x["def_id"] != r["def_id"] and x["gender"] == r["gender"] and x["format"] == r["format"] \
                and x["def_id"] not in seen and (x.get("major") or x["def_id"] not in {y["def_id"] for y in d["records"] if y.get("major")}):
            seen.add(x["def_id"]); out.append(x)
    return out


def catalog(db: DB) -> dict:
    d = load(db)
    cats = []
    for c in d["categories"]:
        defs = {}
        for r in d["records"]:
            if r["category"] != c:
                continue
            e = defs.setdefault(r["def_id"], {"def_id": r["def_id"], "title": r["title"], "definition": r["definition"], "scopes": []})
            top = r["rows"][0]
            e["scopes"].append({"id": r["id"], "scope": r["scope"], "leader": top["label"], "value_fmt": top["value_fmt"], "href": top["href"]})
        if defs:
            cats.append({"category": c, "records": list(defs.values())})
    return {"categories": cats, "coverage": COVERAGE, "count": len(d["records"])}
