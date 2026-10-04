"""Research gate: can this dataset support a defensible PRE-BALL win-probability model?

Research only. Nothing here is imported by the product. Run:

    python -m cricintel.research.winprob --dataset cricsheet

Writes docs/models/win-probability-research.json (all numbers quoted by docs/models/win-probability-research.md).

Design summary (details in the markdown write-up):
* Population: T20 + ODI, men + women, both innings, result decided normally. Excluded: no result, D/L (and any
  other `method`, e.g. "Awarded"), missing 2nd innings, limit_uncertain, non-standard / unequal innings limits
  (reduced-overs matches), target != 1st-innings total + 1, incomplete 1st innings, inconsistent 2nd innings.
  Ties (including ties later decided by a super over) are labelled 0.5 for both sides (super over ignored).
* Target: P(batting team wins | pre-ball state). Features are pre-ball state only (score, wickets, legal balls
  bowled, balls left, target / runs required, format, gender, innings). No team, player, venue or match-level info.
* Chronological split: train < 2023-01-01, validation = 2023, test >= 2024-01-01 (2024, 2025, 2026 reported apart).
* Models: B0 constant, B1 required-rate logistic (innings 2), A empirical-Bayes state table, B engineered logistic,
  plus Platt recalibration fitted on the validation year only. Selection uses validation only.
* Uncertainty: 200 match-level bootstrap resamples (fixed seed). Effective n reported in matches and deliveries.
* Acceptance criteria are fixed in ACCEPTANCE below, before any test metric is computed.
"""
from __future__ import annotations

import argparse
import json
import math
import random
import time
import zlib
from collections import defaultdict
from pathlib import Path

from ..db import DB

# --------------------------------------------------------------------------------------------------------------
# Fixed configuration and PRE-REGISTERED acceptance rules (written before looking at any test-set number).
# --------------------------------------------------------------------------------------------------------------
CONFIG = {
    "train_end": "2023-01-01",          # train: start_date < this
    "val_start": "2023-01-01", "val_end": "2023-12-31",
    "test_start": "2024-01-01",         # test: start_date >= this
    "std_limit": {"T20": 120, "ODI": 300},
    "fit_thin": 3,                      # logistic fits use legal balls with legal_balls_before % 3 == 0 (train)
    "eval_thin": 1,                     # validation + test use every legal ball
    "n_boot": 200,
    "seed": 20261004,
    "tie_label": 0.5,
    "clip": 1e-4,                       # probabilities clipped to [clip, 1-clip] for log loss / logit
    "A_k_grid": [10, 30, 100, 300, 1000, 3000],
    "B_l2_grid": [0.1, 10.0, 1000.0],
}
COHORTS = [("T20", "male"), ("T20", "female"), ("ODI", "male"), ("ODI", "female")]
BANDS = [(0.0, 0.1), (0.1, 0.3), (0.3, 0.7), (0.7, 0.9), (0.9, 1.0000001)]
ACCEPTANCE = {
    "min_test_matches": 150,            # cohort (format x gender, both innings) needs >= 150 test matches
    "slope_range": [0.9, 1.1],          # calibration slope of logit(p), pooled innings
    "max_abs_citl": 0.02,               # |mean(y) - mean(p)|, pooled innings
    "max_ece": 0.03,                    # 10 equal-width bins, pooled innings
    "max_ece_per_innings": 0.04,        # each innings separately
    "band_rule": "for every probability band with >= 30 test matches: |obs - pred| <= 0.05 OR the 95% "
                 "match-bootstrap CI of (obs - pred) contains 0",
    "band_tol": 0.05, "band_min_matches": 30,
    "brier_skill_vs_b1_innings2": 0.0,  # Brier skill vs baseline 1 on innings-2 balls must be > 0
    "max_ece_per_year": 0.04,           # every test year with >= 50 matches in the cohort
    "year_min_matches": 50,
    "selected_model": "the variant (A, A+Platt, B, B+Platt) with the lowest validation log loss per "
                      "format x gender x innings; Platt variants scored by 2-fold match-split cross-fitting "
                      "inside the validation year",
}

OUT_JSON = Path(__file__).resolve().parents[3] / "docs" / "models" / "win-probability-research.json"


# --------------------------------------------------------------------------------------------------------------
# Small numerics (pure Python)
# --------------------------------------------------------------------------------------------------------------
def sigmoid(z: float) -> float:
    if z >= 0:
        return 1.0 / (1.0 + math.exp(-z))
    e = math.exp(z)
    return e / (1.0 + e)


def clipp(p: float) -> float:
    c = CONFIG["clip"]
    return c if p < c else (1 - c if p > 1 - c else p)


def logit(p: float) -> float:
    p = clipp(p)
    return math.log(p / (1 - p))


def logloss(p: float, y: float) -> float:
    p = clipp(p)
    return -(y * math.log(p) + (1 - y) * math.log(1 - p))


def solve(A: list[list[float]], b: list[float]) -> list[float]:
    """Gaussian elimination with partial pivoting (small dense systems)."""
    n = len(b)
    M = [row[:] + [b[i]] for i, row in enumerate(A)]
    for c in range(n):
        piv = max(range(c, n), key=lambda r: abs(M[r][c]))
        M[c], M[piv] = M[piv], M[c]
        if abs(M[c][c]) < 1e-12:
            M[c][c] = 1e-12
        for r in range(c + 1, n):
            f = M[r][c] / M[c][c]
            if f:
                for k in range(c, n + 1):
                    M[r][k] -= f * M[c][k]
    x = [0.0] * n
    for r in range(n - 1, -1, -1):
        x[r] = (M[r][n] - sum(M[r][k] * x[k] for k in range(r + 1, n))) / M[r][r]
    return x


def fit_logistic(X: list[list[float]], y: list[float], w: list[float] | None = None, l2: float = 0.0,
                 iters: int = 30, tol: float = 1e-9) -> list[float]:
    """Deterministic IRLS / Newton logistic regression; y may be fractional (ties = 0.5). L2 not on intercept."""
    d = len(X[0])
    beta = [0.0] * d
    w = w or [1.0] * len(y)
    for _ in range(iters):
        H = [[0.0] * d for _ in range(d)]
        g = [0.0] * d
        for xi, yi, wi in zip(X, y, w):
            z = 0.0
            for j in range(d):
                z += beta[j] * xi[j]
            p = sigmoid(z)
            r = wi * (yi - p)
            v = wi * p * (1 - p)
            for j in range(d):
                xj = xi[j]
                g[j] += r * xj
                vj = v * xj
                Hj = H[j]
                for k in range(j + 1):
                    Hj[k] += vj * xi[k]
        for j in range(d):
            for k in range(j):
                H[k][j] = H[j][k]
        for j in range(1, d):
            g[j] -= l2 * beta[j]
            H[j][j] += l2
        step = solve(H, g)
        beta = [b + s for b, s in zip(beta, step)]
        if max(abs(s) for s in step) < tol:
            break
    return beta


def fit_platt_agg(agg: dict) -> tuple[float, float]:
    """Logistic fit y ~ a + b*x on aggregated {x: [n, sum_y]}; returns (a, b)."""
    keys = list(agg.keys())
    X = [[1.0, x] for x in keys]
    n = [agg[x][0] for x in keys]
    yb = [agg[x][1] / agg[x][0] for x in keys]
    a, b = fit_logistic(X, yb, w=n, l2=0.0, iters=50)
    return a, b


def pct(vals: list[float], q: float) -> float:
    s = sorted(vals)
    if not s:
        return float("nan")
    i = min(len(s) - 1, max(0, int(round(q * (len(s) - 1)))))
    return s[i]


def wilson(k: float, n: float, z: float = 1.96) -> tuple[float, float]:
    if n <= 0:
        return (float("nan"), float("nan"))
    p = k / n
    den = 1 + z * z / n
    c = (p + z * z / (2 * n)) / den
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return (max(0.0, c - h), min(1.0, c + h))


def r4(x):
    if x is None or (isinstance(x, float) and (math.isnan(x) or math.isinf(x))):
        return None
    return round(x, 4) if isinstance(x, float) else x


# --------------------------------------------------------------------------------------------------------------
# Population
# --------------------------------------------------------------------------------------------------------------
def pop_sql() -> str:
    t20, odi = CONFIG["std_limit"]["T20"], CONFIG["std_limit"]["ODI"]
    return f"""
    WITH i1 AS (SELECT match_id, batting_team bt1, total_runs t1, total_wickets w1, legal_balls lb1
                FROM innings WHERE innings_no = 1 AND NOT super_over),
         i2 AS (SELECT match_id, batting_team bt2, total_runs t2, total_wickets w2, legal_balls lb2, target_runs tg
                FROM innings WHERE innings_no = 2 AND NOT super_over),
         lim AS (SELECT match_id, min(innings_balls_limit) lmin, max(innings_balls_limit) lmax,
                        bool_or(coalesce(limit_uncertain, false)) unc FROM balls GROUP BY 1),
         base AS (
           SELECT m.match_id, m.format_group fg, m.gender, m.start_date, year(m.start_date) yr, m.team_type,
                  m.winner, m.result, m.method, m.eliminator, i1.* EXCLUDE (match_id), i2.* EXCLUDE (match_id), lim.* EXCLUDE (match_id),
                  CASE m.format_group WHEN 'T20' THEN {t20} WHEN 'ODI' THEN {odi} END L
           FROM matches m LEFT JOIN i1 USING (match_id) LEFT JOIN i2 USING (match_id) LEFT JOIN lim USING (match_id)
           WHERE m.format_group IN ('T20', 'ODI'))
    SELECT *,
      CASE
        WHEN result = 'no result' THEN 'no_result'
        WHEN method = 'D/L' THEN 'method_dl'
        WHEN method IS NOT NULL THEN 'method_other'
        WHEN i1_missing THEN 'no_first_innings'
        WHEN bt2 IS NULL THEN 'no_second_innings'
        WHEN unc THEN 'limit_uncertain'
        WHEN lmin <> L OR lmax <> L THEN 'nonstandard_or_unequal_limit'
        WHEN lb1 > L OR lb2 > L THEN 'more_legal_balls_than_limit'
        WHEN tg IS NULL OR tg <> t1 + 1 THEN 'target_mismatch'
        WHEN NOT (lb1 = L OR w1 >= 10) THEN 'incomplete_first_innings'
        WHEN result IS NULL AND winner IS NULL THEN 'no_winner_recorded'
        WHEN result IS NULL AND winner = bt2 AND t2 < tg THEN 'inconsistent_second_innings'
        WHEN result IS NULL AND winner = bt1 AND t2 >= tg THEN 'inconsistent_second_innings'
        WHEN result IS NULL AND winner = bt1 AND NOT (lb2 = L OR w2 >= 10) THEN 'inconsistent_second_innings'
        ELSE 'eligible' END AS status,
      CASE WHEN result = 'tie' THEN {CONFIG['tie_label']} WHEN winner = bt1 THEN 1.0 ELSE 0.0 END AS y1,
      CASE WHEN start_date < DATE '{CONFIG['train_end']}' THEN 'train'
           WHEN start_date <= DATE '{CONFIG['val_end']}' THEN 'val'
           WHEN start_date >= DATE '{CONFIG['test_start']}' THEN 'test' ELSE 'gap' END AS split
    FROM (SELECT *, bt1 IS NULL i1_missing FROM base)
    """


def load(db: DB):
    pops = db.q(pop_sql())
    excl = defaultdict(lambda: defaultdict(int))
    for r in pops:
        excl[f"{r['fg']}|{r['gender']}|{r['split']}"][r["status"]] += 1
    elig = {r["match_id"]: r for r in pops if r["status"] == "eligible"}
    ties = defaultdict(int)
    for r in elig.values():
        if r["result"] == "tie":
            ties[f"{r['split']}|{'super_over' if r['eliminator'] else 'plain'}"] += 1
    sql = f"""
      WITH pop AS ({pop_sql()})
      SELECT b.match_id, b.innings_no, p.fg, p.gender, p.yr, p.L, b.legal_balls_before, b.score_before,
             b.wickets_before, b.target_runs, CASE WHEN b.innings_no = 1 THEN p.y1 ELSE 1 - p.y1 END y,
             p.team_type, p.split, CASE WHEN b.innings_no = 1 THEN p.t1 END final1
      FROM balls b JOIN pop p USING (match_id)
      WHERE p.status = 'eligible' AND b.legal AND p.split <> 'gap'
      ORDER BY b.match_id, b.innings_no, b.seq"""
    cur = db.con.cursor()
    res = cur.execute(sql)
    train_all, fit_rows, val_rows, test_rows = [], [], [], []
    thin = CONFIG["fit_thin"]
    while True:
        chunk = res.fetchmany(200_000)
        if not chunk:
            break
        for t in chunk:
            mid, inn, fg, g, yr, L, bb, s, w, tg, y, tt, split, final1 = t
            row = (mid, inn, fg, g, yr, L, bb, s, w, tg, float(y), tt)
            if split == "train":
                train_all.append((inn, fg, g, L, bb, s, w, tg, float(y), final1))
                if bb % thin == 0:
                    fit_rows.append(row)
            elif split == "val":
                val_rows.append(row)
            else:
                test_rows.append(row)
    cur.close()
    return pops, elig, excl, ties, train_all, fit_rows, val_rows, test_rows


# --------------------------------------------------------------------------------------------------------------
# Training-only lookup tables: par score, remaining-runs resource table, first-innings total distribution
# --------------------------------------------------------------------------------------------------------------
class Ctx:
    def __init__(self, fg: str, g: str, L: int):
        self.fg, self.g, self.L = fg, g, L
        self.par = [0.0] * (L + 1)
        self.E = [[0.0] * 10 for _ in range(L + 1)]
        self.S = [[1.0] * 10 for _ in range(L + 1)]
        self.mu = 0.0
        self.sd = 1.0


def build_ctx(train_all) -> dict:
    ctxs = {}
    agg_par = defaultdict(lambda: [0, 0.0])
    agg_rem = defaultdict(lambda: [0, 0.0, 0.0])
    finals = defaultdict(dict)
    for inn, fg, g, L, bb, s, w, tg, y, final1 in train_all:
        if inn != 1:
            continue
        a = agg_par[(fg, g, bb)]
        a[0] += 1; a[1] += s
        rem = final1 - s
        b = agg_rem[(fg, g, L - bb, w)]
        b[0] += 1; b[1] += rem; b[2] += rem * rem
    for (fg, g) in COHORTS:
        L = CONFIG["std_limit"][fg]
        c = Ctx(fg, g, L)
        last = 0.0
        for bb in range(L + 1):
            a = agg_par.get((fg, g, bb))
            last = a[1] / a[0] if a and a[0] else last
            c.par[bb] = last
        W0 = 3 if fg == "T20" else 6
        for w in range(10):
            for bl in range(1, L + 1):
                W = W0
                while True:
                    n = sm = sq = 0.0
                    for d in range(max(1, bl - W), min(L, bl + W) + 1):
                        b = agg_rem.get((fg, g, d, w))
                        if b:
                            n += b[0]; sm += b[1]; sq += b[2]
                    if n >= 40 or W > L:
                        break
                    W *= 2
                if n > 0:
                    m = sm / n
                    v = max(sq / n - m * m, 0.0)
                    c.E[bl][w] = m
                    c.S[bl][w] = max(math.sqrt(v), 3.0)
                else:
                    c.E[bl][w] = float("nan")
        # fill / monotone: E non-increasing in wickets lost, non-decreasing in balls left
        for bl in range(1, L + 1):
            for w in range(10):
                if math.isnan(c.E[bl][w]):
                    c.E[bl][w] = c.E[bl][w - 1] if w else 0.0
                    c.S[bl][w] = c.S[bl][w - 1] if w else 3.0
            for w in range(1, 10):
                c.E[bl][w] = min(c.E[bl][w], c.E[bl][w - 1])
        for w in range(10):
            for bl in range(2, L + 1):
                c.E[bl][w] = max(c.E[bl][w], c.E[bl - 1][w])
        ctxs[(fg, g)] = c
    # first-innings total distribution: exactly one row per innings has legal_balls_before == 0
    totals = defaultdict(list)
    for inn, fg, g, L, bb, s, w, tg, y, final1 in train_all:
        if inn == 1 and bb == 0:
            totals[(fg, g)].append(final1)
    for k, c in ctxs.items():
        t = totals[k]
        c.mu = sum(t) / len(t)
        c.sd = math.sqrt(sum((x - c.mu) ** 2 for x in t) / (len(t) - 1))
        c.n_innings = len(t)
    return ctxs


# --------------------------------------------------------------------------------------------------------------
# Feature maps
# --------------------------------------------------------------------------------------------------------------
def feats_B(ctx: Ctx, inn: int, bb: int, s: int, w: int, tg) -> list[float]:
    L = ctx.L
    bl = L - bb
    E, S = ctx.E[bl][w], ctx.S[bl][w]
    f = bb / L
    if inn == 1:
        z = (s + E - ctx.mu) / math.sqrt(S * S + ctx.sd * ctx.sd)
        return [1.0, z, z * f, f, w / 10.0]
    R = tg - s
    z = max(-8.0, min(8.0, (E - R) / S))
    lr = math.log((R + 1.0) / (E + 1.0))
    return [1.0, z, z * f, lr, f, w / 10.0]


def feats_B1(ctx: Ctx, bb: int, s: int, w: int, tg) -> list[float]:
    bl = ctx.L - bb
    rrr = min(36.0, 6.0 * (tg - s) / bl)
    return [1.0, rrr, float(w)]


def bins_A(ctx: Ctx, inn: int, bb: int, s: int, w: int, tg) -> list:
    """Hierarchy of cell keys for Candidate A, finest first. Last entry is the cohort root."""
    L = ctx.L
    bl = L - bb
    if ctx.fg == "T20":
        blb = (bl - 1) // 6
        if inn == 1:
            v = max(-60, min(60, s - ctx.par[bb]))
            rb = int(math.floor(v / 5.0))
        else:
            rb = min(60, (tg - s) // 4)
    else:
        blb = (bl - 1) // 12
        if inn == 1:
            v = max(-120, min(120, s - ctx.par[bb]))
            rb = int(math.floor(v / 8.0))
        else:
            rb = min(50, (tg - s) // 8)
    wg1 = w // 2
    wg2 = 0 if w <= 2 else (1 if w <= 5 else 2)
    return [(0, blb, w, rb), (1, blb // 2, wg1, rb // 2), (2, blb // 4, wg2, rb // 4), (3, blb // 8, rb // 8), (4,)]


class ModelA:
    def __init__(self):
        self.cnt = {}   # (fg,g,inn) -> {key: [n, sy]}
        self.k = {}

    def fit(self, ctxs, train_all):
        for inn, fg, g, L, bb, s, w, tg, y, final1 in train_all:
            d = self.cnt.setdefault((fg, g, inn), {})
            for key in bins_A(ctxs[(fg, g)], inn, bb, s, w, tg):
                a = d.get(key)
                if a is None:
                    d[key] = [1, y]
                else:
                    a[0] += 1; a[1] += y

    def predict(self, ctx, inn, bb, s, w, tg, k=None):
        d = self.cnt[(ctx.fg, ctx.g, inn)]
        k = self.k[(ctx.fg, ctx.g, inn)] if k is None else k
        keys = bins_A(ctx, inn, bb, s, w, tg)
        root = d[keys[-1]]
        p = root[1] / root[0]
        for key in reversed(keys[:-1]):
            a = d.get(key)
            if a:
                p = (a[1] + k * p) / (a[0] + k)
        return p


# --------------------------------------------------------------------------------------------------------------
# Metrics
# --------------------------------------------------------------------------------------------------------------
def band_of(p: float) -> int:
    for i, (lo, hi) in enumerate(BANDS):
        if lo <= p < hi:
            return i
    return len(BANDS) - 1


def per_match_stats(rows, preds):
    """Aggregate per match: n, sum brier, sum logloss, sum p, sum y, rel bins (10), bands (5), logit bins."""
    pm = {}
    for r, p in zip(rows, preds):
        mid, y = r[0], r[10]
        a = pm.get(mid)
        if a is None:
            a = pm[mid] = {"n": 0, "b": 0.0, "l": 0.0, "p": 0.0, "y": 0.0,
                           "rel": [[0, 0.0, 0.0] for _ in range(10)], "band": [[0, 0.0, 0.0] for _ in range(5)]}
        a["n"] += 1
        a["b"] += (p - y) ** 2
        a["l"] += logloss(p, y)
        a["p"] += p
        a["y"] += y
        rb = a["rel"][min(9, int(p * 10))]
        rb[0] += 1; rb[1] += p; rb[2] += y
        bd = a["band"][band_of(p)]
        bd[0] += 1; bd[1] += p; bd[2] += y
    return pm


def ece_from(rel) -> float:
    N = sum(b[0] for b in rel)
    return sum(abs(b[1] - b[2]) for b in rel if b[0]) / N if N else float("nan")


def calib_slope(rows, preds, width: float = 0.001) -> tuple[float, float]:
    agg = defaultdict(lambda: [0, 0.0])
    for r, p in zip(rows, preds):
        x = round(logit(p) / width) * width
        a = agg[x]
        a[0] += 1; a[1] += r[10]
    a, b = fit_platt_agg(agg)
    return a, b


def point_metrics(rows, preds) -> dict:
    n = len(rows)
    if n == 0:
        return {}
    sb = sl = sp = sy = 0.0
    rel = [[0, 0.0, 0.0] for _ in range(10)]
    for r, p in zip(rows, preds):
        y = r[10]
        sb += (p - y) ** 2; sl += logloss(p, y); sp += p; sy += y
        b = rel[min(9, int(p * 10))]
        b[0] += 1; b[1] += p; b[2] += y
    a, s = calib_slope(rows, preds)
    return {"deliveries": n, "matches": len({r[0] for r in rows}), "brier": sb / n, "logloss": sl / n,
            "mean_pred": sp / n, "obs_rate": sy / n, "citl": (sy - sp) / n, "ece": ece_from(rel),
            "calib_intercept": a, "calib_slope": s}


def boot_draws(mids: list[str], tag: str) -> list[list[int]]:
    rng = random.Random(CONFIG["seed"] ^ zlib.crc32(tag.encode()))
    m = len(mids)
    draws = []
    for _ in range(CONFIG["n_boot"]):
        cnt = [0] * m
        for _ in range(m):
            cnt[rng.randrange(m)] += 1
        draws.append(cnt)
    return draws


# --------------------------------------------------------------------------------------------------------------
# Main study
# --------------------------------------------------------------------------------------------------------------
def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", default="cricsheet")
    ap.add_argument("--out", default=str(OUT_JSON))
    args = ap.parse_args()
    t0 = time.time()
    timing = {}
    db = DB(args.dataset)
    pops, elig, excl, ties, train_all, fit_rows, val_rows, test_rows = load(db)
    timing["load_s"] = round(time.time() - t0, 1)

    # ---- population report
    status_tot = defaultdict(lambda: defaultdict(int))
    for r in pops:
        status_tot[f"{r['fg']}|{r['gender']}"][r["status"]] += 1
    split_counts = defaultdict(lambda: defaultdict(int))
    for r in elig.values():
        split_counts[f"{r['fg']}|{r['gender']}"][r["split"]] += 1
    population = {
        "status_by_cohort": {k: dict(v) for k, v in status_tot.items()},
        "status_by_cohort_split": {k: dict(v) for k, v in excl.items()},
        "eligible_matches_by_split": {k: dict(v) for k, v in split_counts.items()},
        "ties_labelled_half": dict(ties),
        "legal_deliveries": {"train_all": len(train_all), "train_fit_thinned": len(fit_rows),
                             "validation": len(val_rows), "test": len(test_rows)},
        "d_l_excluded_total": sum(1 for r in pops if r["status"] == "method_dl"),
    }

    # ---- training-only tables
    ctxs = build_ctx(train_all)
    ctx_report = {f"{k[0]}|{k[1]}": {"first_innings_total_mean": c.mu, "first_innings_total_sd": c.sd,
                                     "n_first_innings": c.n_innings,
                                     "expected_remaining_runs_at_start_0_down": c.E[c.L][0],
                                     "par_at_half_innings": c.par[c.L // 2]} for k, c in ctxs.items()}
    A = ModelA()
    A.fit(ctxs, train_all)
    del train_all
    timing["tables_s"] = round(time.time() - t0, 1)

    groups = [(fg, g, inn) for fg, g in COHORTS for inn in (1, 2)]

    def rows_of(rows, fg, g, inn):
        return [r for r in rows if r[2] == fg and r[3] == g and r[1] == inn]

    # ---- Baseline 0 (constant), Baseline 1 (RRR logistic, innings 2), Candidate B (engineered logistic)
    b0, b1, Bcoef = {}, {}, {}
    hyper = {}
    val_scores = {}
    for fg, g, inn in groups:
        ctx = ctxs[(fg, g)]
        tr = rows_of(fit_rows, fg, g, inn)
        va = rows_of(val_rows, fg, g, inn)
        # B0: share of wins for the batting side (one value per match innings, i.e. weight each match once)
        seen = {}
        for r in tr:
            seen[r[0]] = r[10]
        b0[(fg, g, inn)] = sum(seen.values()) / len(seen)
        if inn == 2:
            X = [feats_B1(ctx, r[6], r[7], r[8], r[9]) for r in tr]
            b1[(fg, g, inn)] = fit_logistic(X, [r[10] for r in tr], l2=0.0)
        Xtr = [feats_B(ctx, inn, r[6], r[7], r[8], r[9]) for r in tr]
        ytr = [r[10] for r in tr]
        Xva = [feats_B(ctx, inn, r[6], r[7], r[8], r[9]) for r in va]
        best = None
        for lam in CONFIG["B_l2_grid"]:
            beta = fit_logistic(Xtr, ytr, l2=lam)
            ll = sum(logloss(sigmoid(sum(b * x for b, x in zip(beta, xi))), r[10]) for xi, r in zip(Xva, va)) / len(va)
            if best is None or ll < best[0] - 1e-12:
                best = (ll, lam, beta)
        Bcoef[(fg, g, inn)] = best[2]
        bestA = None
        for k in CONFIG["A_k_grid"]:
            ll = sum(logloss(A.predict(ctx, inn, r[6], r[7], r[8], r[9], k=k), r[10]) for r in va) / len(va)
            if bestA is None or ll < bestA[0] - 1e-12:
                bestA = (ll, k)
        A.k[(fg, g, inn)] = bestA[1]
        hyper[f"{fg}|{g}|{inn}"] = {"B_l2": best[1], "B_coef": best[2], "A_k": bestA[1],
                                    "B1_coef": b1.get((fg, g, inn)), "B0": b0[(fg, g, inn)],
                                    "train_fit_deliveries": len(tr), "train_fit_matches": len({r[0] for r in tr}),
                                    "val_deliveries": len(va), "val_matches": len({r[0] for r in va})}
    timing["fit_s"] = round(time.time() - t0, 1)

    def raw_pred(model, r):
        mid, inn, fg, g, yr, L, bb, s, w, tg, y, tt = r
        ctx = ctxs[(fg, g)]
        if model == "B0":
            return b0[(fg, g, inn)]
        if model == "B1":
            if inn != 2:
                return None
            beta = b1[(fg, g, inn)]
            return sigmoid(sum(b * x for b, x in zip(beta, feats_B1(ctx, bb, s, w, tg))))
        if model == "A":
            return A.predict(ctx, inn, bb, s, w, tg)
        if model == "B":
            beta = Bcoef[(fg, g, inn)]
            return sigmoid(sum(b * x for b, x in zip(beta, feats_B(ctx, inn, bb, s, w, tg))))
        raise ValueError(model)

    # ---- Platt recalibration on validation, model selection on validation (pre-registered rule)
    platt, selected = {}, {}
    for fg, g, inn in groups:
        va = rows_of(val_rows, fg, g, inn)
        sc = {}
        for m in ("A", "B"):
            pr = [raw_pred(m, r) for r in va]
            sc[m] = sum(logloss(p, r[10]) for p, r in zip(pr, va)) / len(va)
            full = defaultdict(lambda: [0, 0.0])
            folds = [defaultdict(lambda: [0, 0.0]), defaultdict(lambda: [0, 0.0])]
            fold_of = []
            for p, r in zip(pr, va):
                x = round(logit(p), 3)
                f = zlib.crc32(r[0].encode()) % 2
                fold_of.append(f)
                for agg in (full, folds[f]):
                    a = agg[x]; a[0] += 1; a[1] += r[10]
            ab = [fit_platt_agg(folds[1]), fit_platt_agg(folds[0])]  # model for fold f is fitted on other fold
            cv = 0.0
            for p, r, f in zip(pr, va, fold_of):
                a, b = ab[f]
                cv += logloss(sigmoid(a + b * logit(p)), r[10])
            sc[m + "+Platt"] = cv / len(va)
            platt[(m, fg, g, inn)] = fit_platt_agg(full)
        sel = min(sc, key=lambda k: (sc[k], k))
        selected[(fg, g, inn)] = sel
        val_scores[f"{fg}|{g}|{inn}"] = {"val_logloss": sc, "selected": sel,
                                         "platt_A": platt[("A", fg, g, inn)], "platt_B": platt[("B", fg, g, inn)]}

    def pred(model, r):
        inn, fg, g = r[1], r[2], r[3]
        if model in ("B0", "B1", "A", "B"):
            return raw_pred(model, r)
        if model in ("A+Platt", "B+Platt"):
            base = model.split("+")[0]
            a, b = platt[(base, fg, g, inn)]
            return sigmoid(a + b * logit(raw_pred(base, r)))
        if model == "WP":
            return pred(selected[(fg, g, inn)], r)
        raise ValueError(model)

    MODELS = ["B0", "B1", "A", "A+Platt", "B", "B+Platt", "WP"]
    # ---- predictions on test (all legal balls)
    P = {m: [pred(m, r) for r in test_rows] for m in MODELS}
    timing["predict_s"] = round(time.time() - t0, 1)

    # ---- evaluation slices
    def idx_where(cond):
        return [i for i, r in enumerate(test_rows) if cond(r)]

    slices = {"overall": idx_where(lambda r: True)}
    for fg, g in COHORTS:
        slices[f"{fg}|{g}"] = idx_where(lambda r, fg=fg, g=g: r[2] == fg and r[3] == g)
        for inn in (1, 2):
            slices[f"{fg}|{g}|inn{inn}"] = idx_where(lambda r, fg=fg, g=g, inn=inn: r[2] == fg and r[3] == g and r[1] == inn)
    slices["inn1"] = idx_where(lambda r: r[1] == 1)
    slices["inn2"] = idx_where(lambda r: r[1] == 2)
    for fg, g in COHORTS:
        for tt in ("international", "club"):
            ix = idx_where(lambda r, fg=fg, g=g, tt=tt: r[2] == fg and r[3] == g and r[11] == tt)
            if ix:
                slices[f"{fg}|{g}|{tt}"] = ix

    results = {}
    for name, ix in slices.items():
        rows = [test_rows[i] for i in ix]
        out = {"deliveries": len(rows), "matches": len({r[0] for r in rows}), "models": {}}
        for m in MODELS:
            pr = [P[m][i] for i in ix]
            if any(p is None for p in pr):
                # B1 is innings-2 only: evaluate on the innings-2 subset
                sub = [(r, p) for r, p in zip(rows, pr) if p is not None]
                if not sub:
                    continue
                pm = point_metrics([s[0] for s in sub], [s[1] for s in sub])
                pm["subset"] = "innings 2 only"
            else:
                pm = point_metrics(rows, pr)
            out["models"][m] = pm
        # Brier skill on the same rows
        for m in MODELS:
            if m in out["models"] and m not in ("B0",):
                out["models"][m]["brier_skill_vs_B0"] = 1 - out["models"][m]["brier"] / out["models"]["B0"]["brier"] \
                    if "subset" not in out["models"][m] else None
        # skill vs B1 on innings-2 rows of the slice
        i2 = [i for i in ix if test_rows[i][1] == 2]
        if i2:
            yb = [test_rows[i][10] for i in i2]
            br = {m: sum((P[m][i] - y) ** 2 for i, y in zip(i2, yb)) / len(i2) for m in MODELS}
            for m in MODELS:
                if m in out["models"]:
                    out["models"][m]["brier_innings2"] = br[m]
                    out["models"][m]["brier_skill_vs_B1_innings2"] = 1 - br[m] / br["B1"]
                    out["models"][m]["brier_skill_vs_B0_innings2"] = 1 - br[m] / br["B0"]
        results[name] = out
    timing["point_metrics_s"] = round(time.time() - t0, 1)

    # ---- match bootstrap (all models: Brier, log loss, skill; WP: ECE, CITL, slope, bands, reliability)
    def boot_slice(name, ix, full_detail):
        rows = [test_rows[i] for i in ix]
        mids = sorted({r[0] for r in rows})
        pos = {m: j for j, m in enumerate(mids)}
        draws = boot_draws(mids, name)
        nm = len(mids)
        # per match sums for each model on all rows and innings-2 rows
        sums = {}
        for m in MODELS:
            arr = [[0, 0.0, 0.0, 0, 0.0] for _ in range(nm)]  # n, brier, logloss, n2, brier2
            for i in ix:
                p = P[m][i]
                r = test_rows[i]
                a = arr[pos[r[0]]]
                if r[1] == 2:
                    a[3] += 1; a[4] += (p - r[10]) ** 2
                if p is None:
                    continue
                a[0] += 1; a[1] += (p - r[10]) ** 2; a[2] += logloss(p, r[10])
            sums[m] = arr
        ci = {m: {"brier": [], "logloss": [], "skill_vs_B0": [], "skill_vs_B1_inn2": []} for m in MODELS}
        for cnt in draws:
            tot = {}
            for m in MODELS:
                n = b = l = n2 = b2 = 0.0
                for c, a in zip(cnt, sums[m]):
                    if c:
                        n += c * a[0]; b += c * a[1]; l += c * a[2]; n2 += c * a[3]; b2 += c * a[4]
                tot[m] = (n, b, l, n2, b2)
            for m in MODELS:
                n, b, l, n2, b2 = tot[m]
                if n:
                    ci[m]["brier"].append(b / n)
                    ci[m]["logloss"].append(l / n)
                if m != "B1" and n and tot["B0"][0]:
                    ci[m]["skill_vs_B0"].append(1 - (b / n) / (tot["B0"][1] / tot["B0"][0]))
                if n2 and tot["B1"][4]:
                    ci[m]["skill_vs_B1_inn2"].append(1 - b2 / tot["B1"][4])
        out = {m: {k: [pct(v, 0.025), pct(v, 0.975)] if v else None for k, v in d.items()} for m, d in ci.items()}
        detail = None
        if full_detail:
            pr = [P["WP"][i] for i in ix]
            pmd = per_match_stats(rows, pr)
            arr = [pmd[m] for m in mids]
            lg = [defaultdict(lambda: [0, 0.0]) for _ in range(nm)]
            for r, p in zip(rows, pr):
                a = lg[pos[r[0]]][round(logit(p) / 0.05) * 0.05]
                a[0] += 1; a[1] += r[10]
            bs = {"ece": [], "citl": [], "slope": [], "rel_obs": [[] for _ in range(10)],
                  "band_gap": [[] for _ in range(5)], "band_obs": [[] for _ in range(5)]}
            for cnt in draws:
                n = sp = sy = 0.0
                rel = [[0, 0.0, 0.0] for _ in range(10)]
                band = [[0, 0.0, 0.0] for _ in range(5)]
                agg = defaultdict(lambda: [0, 0.0])
                for c, a, lgm in zip(cnt, arr, lg):
                    if not c:
                        continue
                    n += c * a["n"]; sp += c * a["p"]; sy += c * a["y"]
                    for q in range(10):
                        b = a["rel"][q]
                        if b[0]:
                            t = rel[q]; t[0] += c * b[0]; t[1] += c * b[1]; t[2] += c * b[2]
                    for q in range(5):
                        b = a["band"][q]
                        if b[0]:
                            t = band[q]; t[0] += c * b[0]; t[1] += c * b[1]; t[2] += c * b[2]
                    for x, v in lgm.items():
                        t = agg[x]; t[0] += c * v[0]; t[1] += c * v[1]
                bs["ece"].append(ece_from(rel))
                bs["citl"].append((sy - sp) / n)
                bs["slope"].append(fit_platt_agg(agg)[1])
                for q in range(10):
                    if rel[q][0]:
                        bs["rel_obs"][q].append(rel[q][2] / rel[q][0])
                for q in range(5):
                    if band[q][0]:
                        bs["band_gap"][q].append((band[q][2] - band[q][1]) / band[q][0])
                        bs["band_obs"][q].append(band[q][2] / band[q][0])
            # point tables
            rel_tab, band_tab = [], []
            for q in range(10):
                n_ = sum(a["rel"][q][0] for a in arr)
                if not n_:
                    rel_tab.append({"bin": f"{q/10:.1f}-{(q+1)/10:.1f}", "deliveries": 0, "matches": 0})
                    continue
                sp_ = sum(a["rel"][q][1] for a in arr); sy_ = sum(a["rel"][q][2] for a in arr)
                rel_tab.append({"bin": f"{q/10:.1f}-{(q+1)/10:.1f}", "deliveries": n_,
                                "matches": sum(1 for a in arr if a["rel"][q][0]), "mean_pred": sp_ / n_,
                                "obs_rate": sy_ / n_, "obs_ci95": [pct(bs["rel_obs"][q], .025), pct(bs["rel_obs"][q], .975)]})
            for q, (lo, hi) in enumerate(BANDS):
                n_ = sum(a["band"][q][0] for a in arr)
                lab = f"{int(lo*100)}-{min(100, int(round(hi*100)))}%"
                if not n_:
                    band_tab.append({"band": lab, "deliveries": 0, "matches": 0})
                    continue
                sp_ = sum(a["band"][q][1] for a in arr); sy_ = sum(a["band"][q][2] for a in arr)
                band_tab.append({"band": lab, "deliveries": n_, "matches": sum(1 for a in arr if a["band"][q][0]),
                                 "mean_pred": sp_ / n_, "obs_rate": sy_ / n_, "gap": (sy_ - sp_) / n_,
                                 "obs_ci95": [pct(bs["band_obs"][q], .025), pct(bs["band_obs"][q], .975)],
                                 "gap_ci95": [pct(bs["band_gap"][q], .025), pct(bs["band_gap"][q], .975)]})
            detail = {"ece_ci95": [pct(bs["ece"], .025), pct(bs["ece"], .975)],
                      "citl_ci95": [pct(bs["citl"], .025), pct(bs["citl"], .975)],
                      "slope_ci95": [pct(bs["slope"], .025), pct(bs["slope"], .975)],
                      "reliability": rel_tab, "bands": band_tab}
        return out, detail

    for name, ix in slices.items():
        full = not name.endswith(("|international", "|club"))
        ci, detail = boot_slice(name, ix, full)
        results[name]["bootstrap_ci95"] = ci
        if detail:
            results[name]["WP_detail"] = detail
    timing["bootstrap_s"] = round(time.time() - t0, 1)

    # ---- temporal stability per test year (selected model WP and raw candidates)
    years = {}
    for fg, g in COHORTS:
        for yr in (2024, 2025, 2026):
            ix = [i for i, r in enumerate(test_rows) if r[2] == fg and r[3] == g and r[4] == yr]
            if not ix:
                continue
            rows = [test_rows[i] for i in ix]
            ent = {"deliveries": len(rows), "matches": len({r[0] for r in rows})}
            for m in ("B0", "A", "B", "WP"):
                ent[m] = point_metrics(rows, [P[m][i] for i in ix])
            i2 = [i for i in ix if test_rows[i][1] == 2]
            if i2:
                b1b = sum((P["B1"][i] - test_rows[i][10]) ** 2 for i in i2)
                wpb = sum((P["WP"][i] - test_rows[i][10]) ** 2 for i in i2)
                ent["WP_brier_skill_vs_B1_innings2"] = 1 - wpb / b1b
            years[f"{fg}|{g}|{yr}"] = ent

    # ---- calibration at fan-visible moments (one row per match per moment -> independent rows)
    def moments_for(fg):
        L = CONFIG["std_limit"][fg]
        return [("inn1_start", 1, 0), ("inn1_half", 1, L // 2), ("inn2_start", 2, 0),
                ("inn2_after_10_overs" if fg == "T20" else "inn2_after_25_overs", 2, L // 2),
                ("inn2_last_5_overs_start", 2, L - 30), ("inn2_last_2_overs_start", 2, L - 12)]

    moments = {}
    for fg, g in COHORTS:
        for mname, inn, bbm in moments_for(fg):
            seen, rows, prs = set(), [], []
            for i, r in enumerate(test_rows):
                if r[2] == fg and r[3] == g and r[1] == inn and r[6] == bbm and r[0] not in seen:
                    seen.add(r[0]); rows.append(r); prs.append(P["WP"][i])
            if not rows:
                continue
            n = len(rows)
            sy = sum(r[10] for r in rows); sp = sum(prs)
            ent = {"matches": n, "brier": sum((p - r[10]) ** 2 for p, r in zip(prs, rows)) / n,
                   "brier_B0": sum((b0[(fg, g, inn)] - r[10]) ** 2 for r in rows) / n,
                   "mean_pred": sp / n, "obs_rate": sy / n, "citl": (sy - sp) / n, "bands": []}
            for lo, hi, lab in ((0, .3, "<30%"), (.3, .7, "30-70%"), (.7, 1.01, ">70%")):
                sel = [(p, r[10]) for p, r in zip(prs, rows) if lo <= p < hi]
                if sel:
                    k = sum(y for _, y in sel)
                    ent["bands"].append({"band": lab, "matches": len(sel), "mean_pred": sum(p for p, _ in sel) / len(sel),
                                         "obs_rate": k / len(sel), "obs_wilson95": list(wilson(k, len(sel)))})
            moments[f"{fg}|{g}|{mname}"] = ent

    # ---- sanity: monotonicity of the selected model on a grid (innings 2)
    mono = {}
    for fg, g in COHORTS:
        ctx = ctxs[(fg, g)]
        L = ctx.L
        viol_r = viol_w = checks = 0
        tg = 400 if fg == "ODI" else 250
        for bb in range(0, L, 6):
            for w in range(10):
                for R in range(1, (200 if fg == "T20" else 350), 3):
                    def wp(R_, w_):
                        r = ("grid", 2, fg, g, 2025, L, bb, tg - R_, w_, tg, 0.0, "international")
                        return pred("WP", r)
                    p = wp(R, w)
                    checks += 1
                    if wp(R + 1, w) > p + 1e-9:
                        viol_r += 1
                    if w < 9 and wp(R, w + 1) > p + 1e-9:
                        viol_w += 1
        mono[f"{fg}|{g}"] = {"grid_states": checks, "more_runs_required_raises_p": viol_r,
                             "more_wickets_lost_raises_p": viol_w}

    # ---- apply the pre-registered acceptance rules
    verdicts = {}
    for fg, g in COHORTS:
        key = f"{fg}|{g}"
        res = results[key]
        wpm = res["models"]["WP"]
        det = res["WP_detail"]
        checks, reasons = {}, []
        nmatch = res["matches"]
        checks["min_test_matches"] = {"value": nmatch, "pass": nmatch >= ACCEPTANCE["min_test_matches"]}
        lo, hi = ACCEPTANCE["slope_range"]
        checks["calibration_slope"] = {"value": wpm["calib_slope"], "ci95": det["slope_ci95"],
                                       "pass": lo <= wpm["calib_slope"] <= hi}
        checks["citl"] = {"value": wpm["citl"], "ci95": det["citl_ci95"], "pass": abs(wpm["citl"]) <= ACCEPTANCE["max_abs_citl"]}
        checks["ece"] = {"value": wpm["ece"], "ci95": det["ece_ci95"], "pass": wpm["ece"] <= ACCEPTANCE["max_ece"]}
        per_inn = {}
        for inn in (1, 2):
            e = results[f"{key}|inn{inn}"]["models"]["WP"]["ece"]
            per_inn[f"inn{inn}"] = e
        checks["ece_per_innings"] = {"value": per_inn,
                                     "pass": all(v <= ACCEPTANCE["max_ece_per_innings"] for v in per_inn.values())}
        band_fail = []
        for b in det["bands"]:
            if b.get("matches", 0) < ACCEPTANCE["band_min_matches"]:
                continue
            ok = abs(b["gap"]) <= ACCEPTANCE["band_tol"] or (b["gap_ci95"][0] <= 0 <= b["gap_ci95"][1])
            if not ok:
                band_fail.append(b["band"])
        checks["bands"] = {"failed_bands": band_fail, "pass": not band_fail}
        sk = res["models"]["WP"]["brier_skill_vs_B1_innings2"]
        checks["brier_skill_vs_B1_innings2"] = {"value": sk, "ci95": res["bootstrap_ci95"]["WP"]["skill_vs_B1_inn2"],
                                                "pass": sk > ACCEPTANCE["brier_skill_vs_b1_innings2"]}
        yr_ece, yr_fail = {}, []
        for yr in (2024, 2025, 2026):
            e = years.get(f"{key}|{yr}")
            if not e:
                continue
            yr_ece[str(yr)] = {"ece": e["WP"]["ece"], "matches": e["matches"],
                               "gated": e["matches"] >= ACCEPTANCE["year_min_matches"]}
            if e["matches"] >= ACCEPTANCE["year_min_matches"] and e["WP"]["ece"] > ACCEPTANCE["max_ece_per_year"]:
                yr_fail.append(str(yr))
        checks["ece_per_year"] = {"value": yr_ece, "failed_years": yr_fail, "pass": not yr_fail}
        for k, v in checks.items():
            if not v["pass"]:
                reasons.append(k)
        verdicts[key] = {"verdict": "ACCEPT-FOR-RESEARCH" if not reasons else "REJECT", "failed": reasons,
                         "checks": checks, "selected_models": {f"inn{i}": selected[(fg, g, i)] for i in (1, 2)}}

    timing["total_s"] = round(time.time() - t0, 1)
    out = {
        "generated_by": "python -m cricintel.research.winprob --dataset " + args.dataset,
        "dataset": args.dataset, "dataset_built_at": db.manifest.get("built_at"),
        "config": CONFIG, "acceptance_rules_preregistered": ACCEPTANCE,
        "population": population, "training_tables": ctx_report,
        "hyperparameters": {k: v for k, v in hyper.items()}, "validation_selection": val_scores,
        "test": results, "test_by_year": years, "moments": moments, "monotonicity_grid": mono,
        "verdicts": verdicts, "timing_s": timing,
    }

    def clean(o):
        if isinstance(o, dict):
            return {str(k): clean(v) for k, v in o.items()}
        if isinstance(o, (list, tuple)):
            return [clean(v) for v in o]
        if isinstance(o, float):
            return r4(o) if abs(o) >= 1e-3 or o == 0 else (None if math.isnan(o) else float(f"{o:.6g}"))
        return o

    Path(args.out).write_text(json.dumps(clean(out), indent=1))
    print(json.dumps({"verdicts": {k: (v["verdict"], v["failed"]) for k, v in verdicts.items()},
                      "timing": timing}, indent=1))


if __name__ == "__main__":
    main()
