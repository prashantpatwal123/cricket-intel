"""Situation Difficulty — Experimental (SDX) v0.1. MODELLED. Behind the CRICINTEL_EXPERIMENTAL flag.

Defined only for chases (second innings of T20s and ODIs), where "difficulty" has an objective anchor: the target.

  1. Resources. From first innings in the training window (no rain method, no revised overs), the mean runs still to
     come from each state (overs left, wickets lost), fitted separately per format and gender, forced monotone:
     more balls left → never fewer runs; more wickets lost → never more runs. "DLS-style", not DLS: the official
     DLS parameters are not public, so we fit our own table.
  2. Demand D = runs required ÷ expected runs from the chasing side's remaining resources.
     D = 1 means the side needs exactly what a typical side scores from here.
  3. SDX = 100 × P(chase fails | D), calibrated on training chases with an isotonic (monotone) fit.
     So SDX 70 reads: "of chases facing this demand, 70% failed."
  4. Swing (separate, not difficulty) = SDX after a wicket − SDX after a four, for this ball: how much the next
     ball could move the situation (the Leverage idea from baseball, Tango).

Properties (unit-tested): bounded 0–100; never falls when a wicket falls, when runs required rise with balls fixed,
or when a ball passes without runs; reproducible from the stored artifact; versioned.
Not used: player quality, venue, toss, momentum. Those either need outcome-fitted ratings (circular) or lack
evidence. Inputs are scoreboard facts only.
"""
from __future__ import annotations

import json
import math
from bisect import bisect_right
from pathlib import Path

from ..db import DB

VERSION = "sdx-0.1"
CUTOFF = "2025-01-01"
MIN_CELL = 25
D_BINS = [round(0.05 * i, 2) for i in range(0, 61)] + [3.5, 4.5, 6.0, 1e9]


def _pav(xs: list[float], ys: list[float], ws: list[float]) -> list[float]:
    """Weighted pool-adjacent-violators: the closest nondecreasing sequence to ys."""
    blocks = []  # [sum_wy, sum_w, count]
    for y, w in zip(ys, ws):
        blocks.append([y * w, w, 1])
        while len(blocks) > 1 and blocks[-2][0] / blocks[-2][1] > blocks[-1][0] / blocks[-1][1]:
            a = blocks.pop()
            blocks[-1][0] += a[0]; blocks[-1][1] += a[1]; blocks[-1][2] += a[2]
    out = []
    for s, w, c in blocks:
        out += [s / w] * c
    return out


def fit_resources(db: DB, fmt: str, gender: str, before: str = CUTOFF, after: str | None = None) -> dict:
    """Expected remaining runs by (overs left, wickets lost), monotone in both directions."""
    max_overs = 20 if fmt == "T20" else 50
    rows = db.q(f"""
      SELECT CAST(ceil((m.scheduled_overs * 6 - d.legal_balls_before) / 6.0) AS INTEGER) AS ol, d.wickets_before AS w,
             avg(i.total_runs - d.score_before) AS r, count(*) AS n
      FROM deliveries d JOIN matches m USING (match_id) JOIN innings i USING (match_id, innings_no)
      WHERE d.innings_no = 1 AND d.legal AND m.format_group = ? AND m.gender = ? AND m.method IS NULL
        AND i.target_overs IS NULL AND m.scheduled_overs = ? AND m.start_date < ? {"AND m.start_date >= ?" if after else ""}
        AND NOT i.super_over
      GROUP BY 1, 2""", [fmt, gender, max_overs, before] + ([after] if after else []))
    cell = {(r["ol"], r["w"]): (r["r"], r["n"]) for r in rows}
    # DLS functional form per wickets-lost w: Z(u) = Z0 * (1 - exp(-u / c)), u = overs left. Monotone in u by
    # construction and it extrapolates sensibly into rare states (e.g. no wicket down with 5 overs left).
    # c by grid search; Z0 in closed form (weighted least squares) for each c. Only cells with >= MIN_CELL balls.
    params = {}
    grid = [1.0 * (1.06 ** k) for k in range(0, 110)]  # c from 1 to ~600 overs
    for w in range(10):
        pts = [(ol, *cell[(ol, w)]) for ol in range(1, max_overs + 1) if cell.get((ol, w), (0, 0))[1] >= MIN_CELL]
        if len(pts) < 3:
            continue
        best = None
        for c in grid:
            g = [1 - math.exp(-u / c) for u, _, _ in pts]
            den = sum(n * gi * gi for (_, _, n), gi in zip(pts, g))
            z0 = sum(n * r * gi for (_, r, n), gi in zip(pts, g)) / den
            sse = sum(n * (r - z0 * gi) ** 2 for (_, r, n), gi in zip(pts, g))
            if best is None or sse < best[0]:
                best = (sse, z0, c)
        params[w] = {"z0": best[1], "c": best[2], "cells": len(pts)}
    table = [[0.0] * 11 for _ in range(max_overs + 1)]
    for ol in range(max_overs + 1):
        for w in range(11):
            if w == 10 or ol == 0:
                v = 0.0
            elif w in params:
                v = params[w]["z0"] * (1 - math.exp(-ol / params[w]["c"]))
            else:  # too few cells to fit this wicket: shrink the previous wicket's value
                v = table[ol][w - 1] * 0.6
            # more wickets lost never means more runs to come
            table[ol][w] = v if w == 0 else min(v, table[ol][w - 1])
    return {"format": fmt, "gender": gender, "max_overs": max_overs, "table": [[round(x, 2) for x in row] for row in table],
            "cells_used": sum(1 for v in cell.values() if v[1] >= MIN_CELL),
            "params": {str(k): {"z0": round(v["z0"], 2), "c": round(v["c"], 2), "cells": v["cells"]} for k, v in params.items()}}


def expected_runs(res: dict, balls_left: int, wickets_lost: int) -> float:
    """Interpolate the over-level table to ball level."""
    if wickets_lost >= 10 or balls_left <= 0:
        return 0.0
    t = res["table"]
    b = min(balls_left, res["max_overs"] * 6)
    lo, frac = divmod(b, 6)
    a = t[lo][wickets_lost]
    c = t[min(lo + 1, res["max_overs"])][wickets_lost]
    return a + (c - a) * frac / 6.0


def demand(res: dict, runs_required: int, balls_left: int, wickets_lost: int) -> float:
    e = expected_runs(res, balls_left, wickets_lost)
    if runs_required <= 0:
        return 0.0
    return runs_required / e if e > 0.5 else 99.0


def _bin(d: float) -> int:
    return min(bisect_right(D_BINS, d) - 1, len(D_BINS) - 2)


def fit_curve(db: DB, res: dict, before: str = CUTOFF, after: str | None = None) -> dict:
    """P(chase fails | demand) from training chases, isotonic in demand."""
    rows = db.q(f"""
      SELECT b.runs_required AS rr, b.balls_left AS bl, b.wickets_before AS w, (b.winner <> b.batting_team) AS fail
      FROM balls b WHERE b.innings_no = 2 AND b.legal AND b.chasing AND b.format_group = ? AND b.gender = ?
        AND b.method IS NULL AND b.winner IS NOT NULL AND b.start_date < ? {"AND b.start_date >= ?" if after else ""}
        AND b.balls_left > 0 AND b.runs_required > 0""",
                 [res["format"], res["gender"], before] + ([after] if after else []))
    n = [0] * (len(D_BINS) - 1); f = [0] * (len(D_BINS) - 1)
    for r in rows:
        k = _bin(demand(res, r["rr"], r["bl"], r["w"]))
        n[k] += 1; f[k] += 1 if r["fail"] else 0
    ks = [k for k in range(len(n)) if n[k]]
    fitted = _pav(ks, [f[k] / n[k] for k in ks], [n[k] for k in ks])
    curve = [None] * len(n)
    for k, v in zip(ks, fitted):
        curve[k] = v
    last = fitted[0] if fitted else 0.5
    for k in range(len(curve)):  # carry across empty bins
        curve[k] = last = curve[k] if curve[k] is not None else last
    return {"bins": D_BINS, "p_fail": [round(x, 4) for x in curve], "n": n, "train_deliveries": len(rows)}


class SDX:
    def __init__(self, artifact: dict):
        self.a = artifact
        self.key = lambda fmt, g: f"{fmt}|{g}"

    @classmethod
    def load(cls, path: Path) -> "SDX":
        return cls(json.loads(path.read_text()))

    def available(self, fmt: str, gender: str) -> bool:
        return self.key(fmt, gender) in self.a["models"]

    def score(self, fmt: str, gender: str, runs_required: int, balls_left: int, wickets_lost: int) -> dict | None:
        m = self.a["models"].get(self.key(fmt, gender))
        if not m or runs_required is None or balls_left is None:
            return None
        if runs_required <= 0:
            return {"sdx": 0.0, "demand": 0.0, "expected_runs": None}
        if balls_left <= 0 or wickets_lost >= 10:
            return {"sdx": 100.0, "demand": None, "expected_runs": 0.0}
        e = expected_runs(m["resources"], balls_left, wickets_lost)
        d = runs_required / e if e > 0.5 else 99.0
        c = m["curve"]
        k = _bin(d)
        # linear interpolation between bin midpoints keeps the score smooth and monotone
        lo, hi = c["bins"][k], c["bins"][k + 1]
        p = c["p_fail"][k]
        if k + 1 < len(c["p_fail"]) and hi < 1e8:
            mid, nxt = (lo + hi) / 2, c["p_fail"][k + 1]
            if d > mid:
                p = p + (nxt - p) * min(1.0, (d - mid) / (hi - lo))
        return {"sdx": round(100 * p, 1), "demand": round(d, 3), "expected_runs": round(e, 1)}

    def swing(self, fmt: str, gender: str, runs_required: int, balls_left: int, wickets_lost: int) -> float | None:
        """SDX after a wicket (dot) minus SDX after a four, on this ball. 0–100."""
        a = self.score(fmt, gender, runs_required, balls_left - 1, wickets_lost + 1)
        b = self.score(fmt, gender, runs_required - 4, balls_left - 1, wickets_lost)
        return None if not a or not b else round(max(0.0, a["sdx"] - b["sdx"]), 1)


def fit(db: DB, before: str = CUTOFF, after: str | None = None) -> dict:
    models = {}
    for fmt in ("T20", "ODI"):
        for g in ("male", "female"):
            res = fit_resources(db, fmt, g, before, after)
            if not res["cells_used"]:
                continue
            models[f"{fmt}|{g}"] = {"resources": res, "curve": fit_curve(db, res, before, after)}
    return {"version": VERSION, "trained_before": before, "trained_from": after, "dataset": db.dataset, "models": models,
            "status": "EXPERIMENTAL", "prov": "MODELLED",
            "definition": "100 × historical share of chases that failed from the same demand (runs required ÷ expected runs "
                          "from remaining balls and wickets). Chases only."}


def artifact_path(db: DB) -> Path:
    return db.dataset_dir / "derived" / f"{VERSION}-{db.dataset}.json"


def score_all(db: DB, model: SDX) -> Path:
    """Write derived/situation.parquet: SDX and swing for every chase delivery (T20/ODI)."""
    import duckdb  # local: only needed for writing
    rows = db.q("""SELECT delivery_id, format_group, gender, runs_required, balls_left, wickets_before
                   FROM balls WHERE chasing AND innings_no = 2 AND format_group IN ('T20','ODI') AND runs_required IS NOT NULL""")
    out = []
    for r in rows:
        s = model.score(r["format_group"], r["gender"], r["runs_required"], r["balls_left"], r["wickets_before"])
        if not s:
            continue
        sw = model.swing(r["format_group"], r["gender"], r["runs_required"], r["balls_left"], r["wickets_before"])
        out.append((r["delivery_id"], s["sdx"], s["demand"], s["expected_runs"], sw))
    import csv
    import tempfile
    p = db.dataset_dir / "derived" / "situation.parquet"
    with tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False, newline="") as fh:
        csv.writer(fh).writerows(out)
        tmp = fh.name
    con = duckdb.connect()
    con.execute(f"""COPY (SELECT * FROM read_csv('{tmp}', header=false, nullstr='',
        columns={{'delivery_id': 'VARCHAR', 'sdx': 'DOUBLE', 'demand': 'DOUBLE', 'expected_runs': 'DOUBLE', 'swing': 'DOUBLE'}}))
        TO '{p}' (FORMAT PARQUET)""")
    Path(tmp).unlink()
    return p
