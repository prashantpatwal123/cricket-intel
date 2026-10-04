"""Performance in difficult chase situations. EXPERIMENTAL (uses SDX v0.1, a MODELLED quantity).

We deliberately do not say "clutch". `clutch_evidence()` tests whether "doing better than expected when the chase is hard"
is a stable trait in our data (split-half reliability across players). Unless that test passes, results are worded as
"in difficult chases" and always compared with the player's own baseline AND peers.
"""
from __future__ import annotations

import math
from functools import lru_cache

from ..db import DB
from .filters import FULL_MEMBERS
from .stats import Z90, benjamini_hochberg, wilson

_FM = ",".join("'" + t + "'" for t in FULL_MEMBERS)
# Mismatches (e.g. associate v associate blowouts) put weak batting sides into "hard" chases and flatter their opponents'
# bowlers, so we restrict to internationals between full members plus all league matches.
SCOPE = f"(b.team_type = 'club' OR (b.batting_team IN ({_FM}) AND b.bowling_team IN ({_FM})))"

HARD = 70.0   # SDX >= 70: historically at least 70% of chases from this demand failed
EASY = 30.0
MIN_HARD = {"T20": 120, "ODI": 150}
K = 60  # pseudo-balls of shrinkage toward the expected (peer-adjusted) rate


@lru_cache(maxsize=16)
def _league(db: DB, fmt: str, gender: str, role: str) -> dict:
    out = db.q(f"""SELECT CASE WHEN s.sdx >= {HARD} THEN 'hard' WHEN s.sdx < {EASY} THEN 'easy' ELSE 'mid' END AS band,
                          count(*) AS n, sum(b.runs_batter{' + b.wides + b.noballs' if role == 'bowling' else ''}) AS r,
                          sum(CASE WHEN b.n_wickets > 0 THEN 1 ELSE 0 END) AS w
                   FROM balls b JOIN situation s USING (delivery_id)
                   WHERE b.format_group = ? AND b.gender = ? AND {SCOPE} AND {'b.wides = 0' if role == 'batting' else 'b.legal'} GROUP BY 1""", [fmt, gender])
    d = {r["band"]: r for r in out}
    n = sum(r["n"] for r in out); rr = sum(r["r"] for r in out); w = sum(r["w"] for r in out)
    d["all"] = {"n": n, "r": rr, "w": w}
    return d


def _player_rows(db: DB, fmt: str, gender: str, role: str, pid: str | None = None):
    col = "batter_id" if role == "batting" else "bowler_id"
    runs = "(b.runs_batter" + (" + b.wides + b.noballs" if role == "bowling" else "") + ")"
    filt = "b.wides = 0" if role == "batting" else "b.legal"
    out_expr = ("(x.delivery_id IS NOT NULL)" if role == "batting" else "(b.n_wickets > 0 AND w.delivery_id IS NOT NULL)")
    join = ("LEFT JOIN (SELECT delivery_id, player_out_id FROM dis WHERE counts_as_dismissal) x ON x.delivery_id = b.delivery_id AND x.player_out_id = b.batter_id"
            if role == "batting" else "LEFT JOIN (SELECT DISTINCT delivery_id FROM wickets WHERE bowler_credited) w ON w.delivery_id = b.delivery_id")
    return db.q(f"""SELECT b.{col} AS pid, CASE WHEN s.sdx >= {HARD} THEN 'hard' WHEN s.sdx < {EASY} THEN 'easy' ELSE 'mid' END AS band,
                           b.year % 2 AS half, count(*) AS n, sum({runs}) AS r, sum({runs} * {runs}) AS rr, count(*) FILTER (WHERE {out_expr}) AS w
                    FROM balls b JOIN situation s USING (delivery_id) {join}
                    WHERE b.format_group = ? AND b.gender = ? AND {SCOPE} AND {filt} {'AND b.' + col + ' = ?' if pid else ''}
                    GROUP BY 1, 2, 3""", [fmt, gender] + ([pid] if pid else []))


def _summarise(rows) -> dict:
    P: dict[str, dict] = {}
    for r in rows:
        x = P.setdefault(r["pid"], {})
        for key in (r["band"], "all", f"{r['band']}|{r['half']}", f"all|{r['half']}"):
            y = x.setdefault(key, {"n": 0, "r": 0, "rr": 0, "w": 0})
            y["n"] += r["n"]; y["r"] += r["r"]; y["rr"] += r["rr"]; y["w"] += r["w"]
    return P


def _effect(me: dict, lg: dict, band="hard", suffix="") -> dict | None:
    h, a = me.get(band + suffix), me.get("all" + suffix)
    if not h or not a or not h["n"] or not a["n"]:
        return None
    lh, la = lg[band], lg["all"]
    # expected rate in hard chases if the player shifted exactly like the league: own overall × league ratio
    exp_rpb = (a["r"] / a["n"]) * ((lh["r"] / lh["n"]) / (la["r"] / la["n"]))
    obs_rpb = h["r"] / h["n"]
    shr = (h["r"] + K * exp_rpb) / (h["n"] + K)
    m = obs_rpb
    var = max(1e-9, (h["rr"] - h["n"] * m * m) / max(1, h["n"] - 1))
    se = math.sqrt(var / h["n"])
    exp_w = (a["w"] / a["n"]) * ((lh["w"] / lh["n"]) / (la["w"] / la["n"])) if la["w"] and lh["w"] else None
    wl, wh = wilson(h["w"], h["n"])
    return {"balls": h["n"], "observed": obs_rpb, "expected": exp_rpb, "shrunk": shr, "diff": shr - exp_rpb, "se": se,
            "z": (obs_rpb - exp_rpb) / se if se else 0.0, "outs": h["w"], "out_rate": h["w"] / h["n"], "out_interval": (wl, wh),
            "expected_out_rate": exp_w, "own_overall": a["r"] / a["n"]}


def leaderboard(db: DB, fmt: str = "T20", gender: str = "male", role: str = "batting", metric: str = "scoring", limit: int = 15) -> dict:
    lg = _league(db, fmt, gender, role)
    P = _summarise(_player_rows(db, fmt, gender, role))
    names = {r["person_id"]: r["name"] for r in db.q("SELECT person_id, name FROM player_profile")}
    rows, ps = [], []
    for pid, me in P.items():
        e = _effect(me, lg)
        if not e or e["balls"] < MIN_HARD[fmt]:
            continue
        p = math.erfc(abs(e["z"]) / math.sqrt(2))
        ps.append(p)
        mult = 100 if role == "batting" else 6
        rows.append({"person_id": pid, "name": names.get(pid, pid), "balls": e["balls"],
                     "observed": round(mult * e["observed"], 1), "expected": round(mult * e["expected"], 1),
                     "own_overall": round(mult * e["own_overall"], 1), "shrunk_diff": round(mult * e["diff"], 1),
                     "interval": [round(mult * (e["observed"] - Z90 * e["se"] - e["expected"]), 1), round(mult * (e["observed"] + Z90 * e["se"] - e["expected"]), 1)],
                     "out_per_100": round(100 * e["out_rate"], 2), "expected_out_per_100": round(100 * e["expected_out_rate"], 2) if e["expected_out_rate"] else None,
                     "p": p})
    sig = benjamini_hochberg([r["p"] for r in rows], 0.10) if rows else []
    for r, s in zip(rows, sig):
        r["passes_fdr"] = bool(s)
    key = {"scoring": (lambda r: -r["shrunk_diff"]) if role == "batting" else (lambda r: r["shrunk_diff"]),
           "survival": (lambda r: r["out_per_100"] - (r["expected_out_per_100"] or 0))}[metric]
    rows.sort(key=key)
    unit = "strike rate" if role == "batting" else "economy"
    return {"rows": rows[:limit], "qualified": len(rows), "passing_fdr": sum(1 for r in rows if r["passes_fdr"]), "format": fmt, "gender": gender,
            "role": role, "metric": metric, "unit": unit, "min_balls": MIN_HARD[fmt], "status": "EXPERIMENTAL", "prov": "MODELLED",
            "definition": (f"Balls {'faced' if role == 'batting' else 'bowled'} in chases with Situation Difficulty ≥ {HARD:.0f} (historically, "
                           f"≥{HARD:.0f}% of chases from that demand failed). Expected = the player's own overall {unit} × how much the whole "
                           f"league's {unit} changes in those situations. Shrunk {K} balls toward expected. Benjamini–Hochberg at q = 0.10.")}


def clutch_evidence(db: DB, fmt: str = "T20", gender: str = "male", role: str = "batting") -> dict:
    """Is beating expectation in hard chases a stable trait? Split-half (even v odd years) correlation across players."""
    lg = _league(db, fmt, gender, role)
    P = _summarise(_player_rows(db, fmt, gender, role))
    pairs = []
    for me in P.values():
        a, b = _effect(me, lg, suffix="|0"), _effect(me, lg, suffix="|1")
        if a and b and a["balls"] >= MIN_HARD[fmt] / 2 and b["balls"] >= MIN_HARD[fmt] / 2:
            pairs.append((a["observed"] - a["expected"], b["observed"] - b["expected"]))
    n = len(pairs)
    if n < 20:
        return {"players": n, "verdict": "insufficient data"}
    mx = sum(x for x, _ in pairs) / n; my = sum(y for _, y in pairs) / n
    sxy = sum((x - mx) * (y - my) for x, y in pairs); sxx = sum((x - mx) ** 2 for x, _ in pairs); syy = sum((y - my) ** 2 for _, y in pairs)
    r = sxy / math.sqrt(sxx * syy) if sxx and syy else 0.0
    zf = 0.5 * math.log((1 + r) / (1 - r)) if abs(r) < 1 else 0
    se = 1 / math.sqrt(n - 3)
    lo, hi = math.tanh(zf - Z90 * se), math.tanh(zf + Z90 * se)
    verdict = ("supported: the effect persists across halves" if lo > 0.2 else
               "weak: some persistence, too small to call a trait" if lo > 0 else
               "not supported: no reliable persistence across halves")
    return {"players": n, "split_half_r": round(r, 3), "interval_90": [round(lo, 3), round(hi, 3)], "verdict": verdict,
            "use_word_clutch": lo > 0.2, "format": fmt, "gender": gender, "role": role,
            "method": "For each player with enough hard-chase balls in both even and odd years, the difference between observed and "
                      "expected scoring in hard chases is computed separately in each half; we correlate the halves across players. "
                      "A real, stable skill would show a clearly positive correlation."}
