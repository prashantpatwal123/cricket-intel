"""Innings Library, Spell Library and Battle Universe: discovery surfaces over the knowledge graph.

Every category has an explicit definition and minimum sample, returned with the rows.
Similar Battles: standardized-feature nearest neighbours (definition and validation below and in
docs/research/similar-battles.md). No language model is involved.
"""
from __future__ import annotations

import math
from functools import lru_cache

from ..db import DB
from .entities import _nm
from .filters import FULL_MEMBERS

_FM = ",".join("'" + t + "'" for t in FULL_MEMBERS)

T20, ODI = "T20", "ODI"


def _scope(alias: str, gender, fmt, competition, team_type, year_from, year_to, team=None, full_members=True):
    w, p = [], []
    if full_members:  # default: internationals between ICC full members, plus all league cricket (visible, removable)
        w.append(f"({alias}.team_type = 'club' OR ({alias}.team IN ({_FM}) AND {alias}.opponent IN ({_FM})))")
    for col, v in (("gender", gender), ("format_group", fmt), ("competition", competition), ("team_type", team_type), ("team", team)):
        if v:
            w.append(f"{alias}.{col} = ?"); p.append(v)
    if year_from:
        w.append(f"{alias}.year >= ?"); p.append(int(year_from))
    if year_to:
        w.append(f"{alias}.year <= ?"); p.append(int(year_to))
    return (" AND ".join(w) or "TRUE"), p


# key: (label, definition, where (format-aware via {min}), order, minimum by format)
INNINGS_CATS = {
    "highest": ("Highest scores", "Most runs in an innings.", "TRUE", "runs DESC, balls ASC", None),
    "fastest": ("Fastest substantial innings", "Highest strike rate with at least {min} runs.", "runs >= {min}", "runs * 1.0 / balls DESC", {T20: 30, ODI: 50}),
    "boundary_heavy": ("Boundary-heavy innings", "Highest share of balls faced hit for 4 or 6, at least {min} balls.", "balls >= {min}",
                       "(fours + sixes) * 1.0 / balls DESC", {T20: 20, ODI: 40}),
    "low_dot": ("Fewest dots", "Lowest share of balls faced with no run off the bat, at least {min} balls.", "balls >= {min}", "dots * 1.0 / balls ASC",
                {T20: 25, ODI: 60}),
    "difficult_chase": ("Difficult successful chases", "In a chase the team won, arriving when the required rate was at least {min} an over, then scoring 30+.",
                        "chasing AND won AND rrr_at_arrival >= {min} AND runs >= 30", "runs DESC", {T20: 9.0, ODI: 6.5}),
    "late_acceleration": ("Biggest late acceleration", "Strike rate over the final 10 balls faced minus strike rate before them, at least {min} balls faced.",
                          "balls >= {min} AND b10 = 10", "(100.0 * r10 / 10) - (100.0 * (runs - r10) / (balls - 10)) DESC", {T20: 30, ODI: 60}),
    "death_hitting": ("Death-overs hitting", "Most runs in death overs (T20 16–20, ODI 41–50) within one innings, at least {min} death balls.",
                      "death_balls >= {min}", "death_runs DESC, death_balls ASC", {T20: 10, ODI: 20}),
    "longest": ("Longest innings", "Most balls faced in an innings.", "TRUE", "balls DESC", None),
}

SPELL_CATS = {
    "best_figures": ("Best figures", "Most wickets, then fewest runs, in one innings.", "TRUE", "wickets DESC, runs ASC", None),
    "economical": ("Most economical substantial spells", "Lowest economy with at least {min} legal balls.", "balls >= {min}", "runs * 1.0 / balls ASC, wickets DESC",
                   {T20: 24, ODI: 48}),
    "most_dots": ("Most dot balls", "Most legal balls conceding no runs off the bat or as wides/no-balls.", "TRUE", "dots DESC, runs ASC", None),
    "death_spells": ("Strongest death-over spells", "Most wickets then lowest economy in death overs, at least {min} death balls.",
                     "death_balls >= {min}", "death_wkts DESC, death_runs * 1.0 / death_balls ASC", {T20: 12, ODI: 24}),
    "wicket_bursts": ("Wicket bursts", "Most bowler-credited wickets within any 12 consecutive deliveries of the bowler.", "best_burst12 >= 3",
                      "best_burst12 DESC, wickets DESC, runs ASC", None),
    "vs_set": ("Spells against set batters", "Most wickets of batters who had faced 30+ balls, at least {min} balls to set batters.",
               "set_balls >= {min} AND set_wkts >= 2", "set_wkts DESC, set_runs * 1.0 / set_balls ASC", {T20: 12, ODI: 30}),
    "defending": ("Defending a total", "Spells in the second innings of matches the bowler's side won, most wickets then lowest economy, at least {min} balls.",
                  "defending AND won AND balls >= {min}", "wickets DESC, runs * 1.0 / balls ASC", {T20: 18, ODI: 42}),
}


def innings_library(db: DB, cat: str, gender: str = "male", fmt: str | None = None, competition: str | None = None, team_type: str | None = None,
                    year_from=None, year_to=None, limit: int = 25, full_members: bool = True) -> dict:
    label, definition, where, order, mins = INNINGS_CATS[cat]
    f = fmt or T20
    m = (mins or {}).get(f)
    w, p = _scope("b", gender, fmt or (T20 if mins else None), competition, team_type, year_from, year_to, full_members=full_members)
    rows = db.q(f"""SELECT match_id, innings_no, batter_id, runs, balls, fours, sixes, dots, not_out, team, opponent, competition, start_date, format_group,
                           r10, rrr_at_arrival, death_runs, death_balls, arrived_score, arrived_wickets, won
                    FROM bat_innings b WHERE {w} AND balls > 0 AND {where.format(min=m)} ORDER BY {order} LIMIT ?""", [*p, limit])
    for r in rows:
        r["name"] = _nm(db, r["batter_id"])
        r["start_date"] = str(r["start_date"])
        r["sr"] = round(100 * r["runs"] / r["balls"], 1)
        r["metric"] = {"fastest": f"SR {r['sr']}", "boundary_heavy": f"{round(100 * (r['fours'] + r['sixes']) / r['balls'], 1)}% boundaries",
                       "low_dot": f"{round(100 * r['dots'] / r['balls'], 1)}% dots",
                       "difficult_chase": f"arrived needing {round(r['rrr_at_arrival'], 1) if r['rrr_at_arrival'] else '–'} an over",
                       "late_acceleration": f"last 10 balls: {r['r10']} runs" if r["r10"] is not None else "",
                       "death_hitting": f"{r['death_runs']} off {r['death_balls']} at the death", "longest": f"{r['balls']} balls"}.get(cat, f"{r['balls']} balls")
    return {"category": cat, "label": label, "definition": definition.format(min=m), "format": fmt or (T20 if mins else "all"),
            "rows": rows, "categories": {k: v[0] for k, v in INNINGS_CATS.items()}, "prov": "DERIVED from OBSERVED deliveries",
            "scope": "Full members & leagues" if full_members else "All teams",
            "note": "Covered data only; not official records." + (" Minimums depend on format; T20 is used when no format is chosen." if mins else "")}


def spell_library(db: DB, cat: str, gender: str = "male", fmt: str | None = None, competition: str | None = None, team_type: str | None = None,
                  year_from=None, year_to=None, limit: int = 25, full_members: bool = True) -> dict:
    label, definition, where, order, mins = SPELL_CATS[cat]
    f = fmt or T20
    m = (mins or {}).get(f)
    w, p = _scope("s", gender, fmt or (T20 if mins else None), competition, team_type, year_from, year_to, full_members=full_members)
    rows = db.q(f"""SELECT match_id, innings_no, bowler_id, wickets, runs, balls, dots, boundaries, death_balls, death_runs, death_wkts, set_wkts, set_balls,
                           best_burst12, team, opponent, competition, start_date, format_group, defending, won
                    FROM bowl_innings s WHERE {w} AND balls > 0 AND {where.format(min=m)} ORDER BY {order} LIMIT ?""", [*p, limit])
    for r in rows:
        r["name"] = _nm(db, r["bowler_id"])
        r["start_date"] = str(r["start_date"])
        r["figures"] = f"{r['wickets']}/{r['runs']}"
        r["overs"] = f"{r['balls'] // 6}.{r['balls'] % 6}"
        r["economy"] = round(6 * r["runs"] / r["balls"], 2)
        r["metric"] = {"economical": f"economy {r['economy']}", "most_dots": f"{r['dots']} dots", "death_spells": f"death: {r['death_wkts']}/{r['death_runs']} off {r['death_balls']}",
                       "wicket_bursts": f"{r['best_burst12']} wickets in 12 balls", "vs_set": f"{r['set_wkts']} set batters out"}.get(cat, f"economy {r['economy']}")
    return {"category": cat, "label": label, "definition": definition.format(min=m), "format": fmt or (T20 if mins else "all"), "rows": rows,
            "categories": {k: v[0] for k, v in SPELL_CATS.items()}, "prov": "DERIVED from OBSERVED deliveries",
            "scope": "Full members & leagues" if full_members else "All teams",
            "note": "A 'spell' here is the bowler's full figures in one innings. Covered data only; not official records."}


# ------------------------------------------------------------------ Battle universe
BATTLE_MIN = 120
BATTLE_CATS = {
    "most_balls": ("Most balls", "Most balls the batter faced from the bowler.", "TRUE", "balls DESC"),
    "most_runs": ("Most runs", "Most runs the batter scored off the bowler.", "TRUE", "runs DESC"),
    "most_dismissals": ("Most dismissals", "Most times the bowler dismissed the batter (bowler-credited).", "TRUE", "outs DESC, balls ASC"),
    "lowest_sr": ("Bowler on top", f"Lowest batter strike rate, at least {BATTLE_MIN} balls.", f"balls >= {BATTLE_MIN}", "runs * 1.0 / balls ASC"),
    "highest_sr": ("Batter on top", f"Highest batter strike rate, at least {BATTLE_MIN} balls.", f"balls >= {BATTLE_MIN}", "runs * 1.0 / balls DESC"),
    "one_sided": ("Unusually one-sided", "Dismissals far above what the batter's usual dismissal rate predicts (Poisson tail), at least 60 balls.",
                  "balls >= 60 AND outs >= 3", None),
    "longest_running": ("Longest-running", "Longest span between the first and latest meeting, at least 60 balls.", "balls >= 60",
                        "date_diff('day', first_date, last_date) DESC"),
    "recent": ("Recent battles", "Most balls in meetings that continued into the latest covered season, at least 30 balls.",
               "balls >= 30 AND year(last_date) >= (SELECT max(year) - 1 FROM team_results)", "balls DESC"),
}


def _pois_upper(k: int, lam: float) -> float:
    term, cdf = math.exp(-lam), 0.0
    for i in range(k):
        cdf += term
        term *= lam / (i + 1)
    return max(1e-300, 1 - cdf)


def battle_universe(db: DB, cat: str, gender: str = "male", fmt: str | None = None, limit: int = 25) -> dict:
    label, definition, where, order = BATTLE_CATS[cat]
    w, p = "gender = ?", [gender]
    if fmt:
        w += " AND list_contains(formats, ?) AND len(formats) = 1"; p.append(fmt)
    if cat == "one_sided":
        rows = db.q(f"SELECT * FROM battles WHERE {w} AND {where}", p)
        for r in rows:
            r["expected"] = r["balls"] * (r["batter_out_rate"] or 0)
            r["p"] = _pois_upper(r["outs"], r["expected"]) if r["expected"] > 0 else 1
        rows = sorted([r for r in rows if r["outs"] > r["expected"] * 1.8], key=lambda r: r["p"])[:limit]
    else:
        rows = db.q(f"SELECT * FROM battles WHERE {w} AND {where} ORDER BY {order} LIMIT ?", [*p, limit])
    for r in rows:
        r["batter"], r["bowler"] = _nm(db, r["batter_id"], r["batter_name"]), _nm(db, r["bowler_id"], r["bowler_name"])
        r["sr"] = round(100 * r["runs"] / r["balls"], 1)
        r["first_date"], r["last_date"] = str(r["first_date"]), str(r["last_date"])
        r["expected_outs"] = round(r["balls"] * (r["batter_out_rate"] or 0), 1)
        r.pop("competitions", None)
    return {"category": cat, "label": label, "definition": definition, "rows": rows, "categories": {k: v[0] for k, v in BATTLE_CATS.items()},
            "note": "Bowler-credited dismissals only. Across T20 and ODI unless a format is chosen (then only battles entirely in that format)."}


# ------------------------------------------------------------------ Similar battles
SIM_MIN = 60
K_SHRINK = 60
FEATURES = [("sr_vs_batter", 1.0), ("sr_vs_bowler", 1.0), ("out_vs_batter", 1.0), ("log_balls", 0.4), ("pp_share", 0.5), ("death_share", 0.5), ("t20_share", 0.6)]


def _features(r: dict) -> list[float]:
    b, br, bo = r["balls"], r["batter_rpb"] or 1e-6, r["batter_out_rate"] or 1e-6
    rpb = (r["runs"] + K_SHRINK * br) / (b + K_SHRINK)                         # shrink small samples toward the batter's usual rate
    out = (r["outs"] + K_SHRINK * bo) / (b + K_SHRINK)
    return [math.log(rpb / br), math.log(rpb / (r["bowler_rpb"] or 1e-6)), math.log(out / bo), math.log(b), r["pp_share"], r["death_share"], r["t20_share"]]


@lru_cache(maxsize=4)
def _sim_space(db: DB, gender: str):
    rows = db.q("SELECT * FROM battles WHERE gender = ? AND balls >= ?", [gender, SIM_MIN])
    X = [_features(r) for r in rows]
    n = len(X)
    mu = [sum(x[j] for x in X) / n for j in range(len(FEATURES))]
    sd = [math.sqrt(sum((x[j] - mu[j]) ** 2 for x in X) / n) or 1 for j in range(len(FEATURES))]
    Z = [[(x[j] - mu[j]) / sd[j] for j in range(len(FEATURES))] for x in X]
    return rows, Z, mu, sd


def similar_battles(db: DB, bat: str, bowl: str, limit: int = 6) -> dict:
    me = db.q1("SELECT * FROM battles WHERE batter_id = ? AND bowler_id = ? ORDER BY balls DESC LIMIT 1", [bat, bowl])
    if not me or me["balls"] < SIM_MIN:
        return {"available": False, "reason": f"Similar battles need at least {SIM_MIN} balls in this battle." if me else "These players haven't met in covered data."}
    rows, Z, mu, sd = _sim_space(db, me["gender"])
    z = [(v - mu[j]) / sd[j] for j, v in enumerate(_features(me))]
    w = [f[1] for f in FEATURES]
    d = []
    for r, zz in zip(rows, Z):
        if r["batter_id"] == bat and r["bowler_id"] == bowl:
            continue
        dist = math.sqrt(sum(w[j] * (zz[j] - z[j]) ** 2 for j in range(len(w))))
        d.append((dist, r))
    d.sort(key=lambda x: x[0])
    out = []
    for dist, r in d[:limit]:
        out.append({"batter_id": r["batter_id"], "bowler_id": r["bowler_id"], "batter": _nm(db, r["batter_id"]), "bowler": _nm(db, r["bowler_id"]),
                    "balls": r["balls"], "runs": r["runs"], "outs": r["outs"], "sr": round(100 * r["runs"] / r["balls"], 1), "distance": round(dist, 2),
                    "shared": _why_similar(_features(me), _features(r))})
    return {"available": True, "rows": out, "features": [f[0] for f in FEATURES],
            "method": f"Battles with {SIM_MIN}+ balls, same gender, described by: strike rate relative to the batter's usual and to what the bowler "
                      f"usually concedes, dismissal rate relative to the batter's usual (all shrunk {K_SHRINK} balls toward usual), sample size (log), "
                      "share of balls in powerplay and death overs, and share in T20s. Features are standardized; distance is weighted Euclidean "
                      "(outcome features weight 1, context 0.5–0.6, size 0.4). Validated by split-half self-retrieval (docs/research/similar-battles.md)."}


def _why_similar(a: list[float], b: list[float]) -> list[str]:
    out = []
    if (a[0] > 0.1) == (b[0] > 0.1) and (a[0] < -0.1) == (b[0] < -0.1):
        out.append("batter scores " + ("faster than usual" if a[0] > 0.1 else "slower than usual" if a[0] < -0.1 else "about as usual"))
    if abs(a[2] - b[2]) < 0.25:
        out.append("bowler dismisses them " + ("more often than usual" if a[2] > 0.15 else "less often than usual" if a[2] < -0.15 else "about as usual"))
    if abs(a[6] - b[6]) < 0.2:
        out.append("mostly T20" if a[6] > 0.6 else "mostly ODI" if a[6] < 0.4 else "mixed formats")
    return out


def validate_similarity(db: DB, gender: str = "male", min_balls: int = 160) -> dict:
    """Split-half self-retrieval: features from even-numbered and odd-numbered meetings of the same battle should be closer to each
    other than to other battles. Reports the median percentile rank of the true partner (0% = always nearest; 50% = chance)."""
    rows = db.q(f"""WITH m AS (SELECT batter_id, bowler_id, match_id, dense_rank() OVER (PARTITION BY batter_id, bowler_id ORDER BY start_date, match_id) % 2 AS half
                               FROM (SELECT DISTINCT batter_id, bowler_id, match_id, start_date FROM balls WHERE gender = ? AND format_group IN ('T20','ODI'))),
                     h AS (SELECT b.batter_id, b.bowler_id, m.half, count(*) FILTER (WHERE b.wides = 0) AS balls, sum(b.runs_batter) AS runs,
                                  count(*) FILTER (WHERE d.delivery_id IS NOT NULL) AS outs, avg(CASE WHEN b.phase = 'powerplay' THEN 1.0 ELSE 0 END) AS pp_share,
                                  avg(CASE WHEN b.phase = 'death' THEN 1.0 ELSE 0 END) AS death_share, avg(CASE WHEN b.format_group = 'T20' THEN 1.0 ELSE 0 END) AS t20_share
                           FROM balls b JOIN m USING (batter_id, bowler_id, match_id)
                           LEFT JOIN dis d ON d.delivery_id = b.delivery_id AND d.player_out_id = b.batter_id AND d.bowler_credited
                           GROUP BY 1, 2, 3)
                SELECT h.*, t.batter_rpb, t.batter_out_rate, t.bowler_rpb FROM h JOIN battles t ON t.batter_id = h.batter_id AND t.bowler_id = h.bowler_id AND t.gender = ?
                WHERE t.balls >= ?""", [gender, gender, min_balls])
    halves: dict = {}
    for r in rows:
        halves.setdefault((r["batter_id"], r["bowler_id"]), {})[r["half"]] = r
    pairs = [(v[0], v[1]) for v in halves.values() if 0 in v and 1 in v and v[0]["balls"] >= 40 and v[1]["balls"] >= 40]
    _, _, mu, sd = _sim_space(db, gender)
    w = [f[1] for f in FEATURES]
    zf = lambda r: [(v - mu[j]) / sd[j] for j, v in enumerate(_features(r))]  # noqa: E731
    A = [zf(a) for a, _ in pairs]
    B = [zf(b) for _, b in pairs]
    ranks, ranks_outcome = [], []
    for i, a in enumerate(A):
        ds = [math.sqrt(sum(w[j] * (a[j] - b[j]) ** 2 for j in range(len(w)))) for b in B]
        mine = ds[i]
        ranks.append(sum(1 for x in ds if x < mine) / (len(ds) - 1))
        do = [math.sqrt(sum((a[j] - b[j]) ** 2 for j in (0, 1, 2))) for b in B]
        ranks_outcome.append(sum(1 for x in do if x < do[i]) / (len(do) - 1))
    ranks.sort(); ranks_outcome.sort()
    med = lambda v: v[len(v) // 2] if v else None  # noqa: E731
    return {"gender": gender, "battles": len(pairs), "median_rank_all_features": round(100 * med(ranks), 1),
            "median_rank_outcome_features_only": round(100 * med(ranks_outcome), 1), "chance": 50.0,
            "top10pct_share": round(100 * sum(1 for x in ranks if x <= 0.1) / len(ranks), 1) if ranks else None}
