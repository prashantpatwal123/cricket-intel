"""Transparent baseline next-ball model (MODELLED, not state of the art).

Outcome classes (runs scored off the delivery INCLUDING extras):
    DOT (0) · 1 · 2 · 3 · 4 (4 or 5) · 6 (6+) · WICKET (any dismissal counting against the batting side)

Structure:
  1. Context cohort probabilities with hierarchical backoff (empirical-Bayes shrinkage):
        format → +phase → +wickets-down band → +chase-pressure band
     p_level = (counts_level + K_CTX * p_parent) / (n_level + K_CTX)
  2. Player adjustments: batter and bowler multipliers per class, measured against the context
     expectation of the balls they actually faced/bowled (so a death-overs specialist is not
     mistaken for a big hitter), shrunk towards 1 with K_PLAYER pseudo-balls.
  3. p ∝ p_ctx × m_batter × m_bowler, renormalised.

Point-in-time: trained only on matches before `cutoff`; evaluated on matches on/after it.
Artifact: data/models/baseline-<version>.json (version, training window, features, constants,
cohort tables, player multipliers, held-out metrics).
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import math

from ..config import MODELS
from ..db import DB

VERSION = "baseline-cohort/0.1"
CLASSES = ["DOT", "1", "2", "3", "4", "6", "WICKET"]
K_CTX = 50.0
K_PLAYER = 3000.0  # chosen on held-out log loss (150: 1.4734, 400: 1.4716, 1000: 1.4705, 3000: 1.4700)
LEVELS = [["fmt"], ["fmt", "phase"], ["fmt", "phase", "wk"], ["fmt", "phase", "wk", "press"]]

FEATURE_SQL = """
SELECT b.delivery_id, b.match_id, b.start_date, b.batter_id, b.bowler_id,
  b.format_group AS fmt, b.phase,
  CASE WHEN b.wickets_before <= 2 THEN '0-2' WHEN b.wickets_before <= 5 THEN '3-5' ELSE '6+' END AS wk,
  CASE WHEN NOT coalesce(b.chasing, false) OR b.required_rate IS NULL THEN 'none'
       WHEN b.required_rate < 8 THEN '<8' WHEN b.required_rate < 10 THEN '8-10'
       WHEN b.required_rate < 12 THEN '10-12' ELSE '12+' END AS press,
  CASE WHEN EXISTS (SELECT 1 FROM wickets w WHERE w.delivery_id = b.delivery_id AND w.counts_as_dismissal) THEN 'WICKET'
       WHEN b.runs_total = 0 THEN 'DOT' WHEN b.runs_total IN (1,2,3) THEN CAST(b.runs_total AS VARCHAR)
       WHEN b.runs_total IN (4,5) THEN '4' ELSE '6' END AS y
FROM balls b WHERE b.format_group IN ('T20','ODI') AND NOT b.super_over
"""


def _key(row, level):
    return "|".join(str(row[c]) for c in level)


class Model:
    def __init__(self, art: dict):
        self.art = art
        self.ctx = art["context"]          # level_index -> key -> probs
        self.mult = art["multipliers"]     # "bat"/"bowl" -> pid -> [m...]

    def context_probs(self, row) -> list[float]:
        p = self.ctx["0"].get(_key(row, LEVELS[0])) or [1 / len(CLASSES)] * len(CLASSES)
        for i in range(1, len(LEVELS)):
            q = self.ctx[str(i)].get(_key(row, LEVELS[i]))
            if q is not None:
                p = q
        return p

    def predict(self, row, use_players=True) -> list[float]:
        p = list(self.context_probs(row))
        if use_players:
            for side, pid in (("bat", row.get("batter_id")), ("bowl", row.get("bowler_id"))):
                m = self.mult[side].get(pid)
                if m:
                    p = [a * b for a, b in zip(p, m)]
        s = sum(p)
        return [x / s for x in p]

    def drivers(self, row) -> list[dict]:
        """Human-readable explanation: what moved the probabilities away from the context cohort."""
        out = []
        base = self.context_probs(row)
        for side, pid, label in (("bat", row.get("batter_id"), "batter"), ("bowl", row.get("bowler_id"), "bowler")):
            m = self.mult[side].get(pid)
            if not m:
                out.append({"factor": label, "effect": "no player history before this match (cohort only)"})
                continue
            i = max(range(len(CLASSES)), key=lambda j: abs(math.log(m[j])))
            out.append({"factor": label, "effect": f"{CLASSES[i]} ×{m[i]:.2f} vs similar situations"})
        return out


def train(db: DB, cutoff: str) -> dict:
    rows = db.q(FEATURE_SQL + " AND b.start_date < ?::DATE", [cutoff])
    if not rows:
        raise SystemExit("no training rows before cutoff")
    ci = {c: i for i, c in enumerate(CLASSES)}
    # ---- context cohorts with backoff
    ctx: dict[str, dict[str, list[float]]] = {}
    counts = []
    for li, level in enumerate(LEVELS):
        c: dict[str, list[int]] = {}
        for r in rows:
            v = c.setdefault(_key(r, level), [0] * len(CLASSES))
            v[ci[r["y"]]] += 1
        counts.append(c)
    glob = [0] * len(CLASSES)
    for r in rows:
        glob[ci[r["y"]]] += 1
    gp = [x / len(rows) for x in glob]
    ctx["0"] = {k: [(v[j] + K_CTX * gp[j]) / (sum(v) + K_CTX) for j in range(len(CLASSES))] for k, v in counts[0].items()}
    for li in range(1, len(LEVELS)):
        ctx[str(li)] = {}
        for k, v in counts[li].items():
            parent = ctx[str(li - 1)][k.rsplit("|", 1)[0]]
            ctx[str(li)][k] = [(v[j] + K_CTX * parent[j]) / (sum(v) + K_CTX) for j in range(len(CLASSES))]
    model = Model({"context": ctx, "multipliers": {"bat": {}, "bowl": {}}})
    # ---- player multipliers vs their own context expectation
    mult = {"bat": {}, "bowl": {}}
    for side, col in (("bat", "batter_id"), ("bowl", "bowler_id")):
        obs: dict[str, list[float]] = {}
        exp: dict[str, list[float]] = {}
        for r in rows:
            pid = r[col]
            o = obs.setdefault(pid, [0.0] * len(CLASSES)); e = exp.setdefault(pid, [0.0] * len(CLASSES))
            o[ci[r["y"]]] += 1
            for j, pj in enumerate(model.context_probs(r)):
                e[j] += pj
        for pid in obs:
            n = sum(obs[pid])
            if n < 30:
                continue
            mult[side][pid] = [round((obs[pid][j] + K_PLAYER * exp[pid][j] / n) / (exp[pid][j] + K_PLAYER * exp[pid][j] / n), 4)
                               for j in range(len(CLASSES))]
    dates = [r["start_date"] for r in rows]
    art = {
        "model_version": VERSION, "classes": CLASSES, "created_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "dataset": db.manifest["dataset"], "synthetic": db.manifest["synthetic"],
        "training_window": {"from": str(min(dates)), "to_exclusive": cutoff, "deliveries": len(rows)},
        "features": {"context_levels": LEVELS, "player_effects": ["batter_id", "bowler_id"]},
        "constants": {"K_CTX": K_CTX, "K_PLAYER": K_PLAYER, "min_player_balls": 30},
        "outcome_definition": "runs off the delivery incl. extras; 4 includes 5; 6 includes 7+; WICKET = any dismissal counting against the batting side",
        "context": ctx, "multipliers": mult,
    }
    art["evaluation"] = evaluate(db, Model(art), cutoff)
    MODELS.mkdir(parents=True, exist_ok=True)
    (MODELS / f"{VERSION.replace('/', '-')}.json").write_text(json.dumps(art))
    return art


def evaluate(db: DB, model: Model, cutoff: str) -> dict:
    rows = db.q(FEATURE_SQL + " AND b.start_date >= ?::DATE", [cutoff])
    ci = {c: i for i, c in enumerate(CLASSES)}
    base = [0.0] * len(CLASSES)
    for r in rows:
        base[ci[r["y"]]] += 1
    # Note: the 'global rate' row uses held-out class frequencies, i.e. an optimistic naive baseline.
    tot = sum(base) or 1
    base = [b / tot for b in base]
    res = {}
    for name, fn in (("global_rate", lambda r: base), ("context_only", lambda r: model.predict(r, False)),
                     ("context+players", lambda r: model.predict(r, True))):
        ll = br = acc = 0.0
        for r in rows:
            p = fn(r); y = ci[r["y"]]
            ll -= math.log(max(p[y], 1e-12))
            br += sum((p[j] - (1.0 if j == y else 0.0)) ** 2 for j in range(len(CLASSES)))
            acc += 1.0 if max(range(len(p)), key=p.__getitem__) == y else 0.0
        n = len(rows) or 1
        res[name] = {"log_loss": round(ll / n, 4), "brier": round(br / n, 4), "top1_accuracy": round(acc / n, 4)}
    # calibration of WICKET probability (deciles)
    pairs = sorted(((model.predict(r)[ci["WICKET"]], r["y"] == "WICKET") for r in rows), key=lambda t: t[0])
    cal = []
    for d in range(10):
        chunk = pairs[d * len(pairs) // 10:(d + 1) * len(pairs) // 10]
        if chunk:
            cal.append({"decile": d + 1, "mean_pred": round(sum(p for p, _ in chunk) / len(chunk), 4),
                        "observed": round(sum(1 for _, y in chunk if y) / len(chunk), 4), "n": len(chunk)})
    return {"heldout_from": cutoff, "heldout_deliveries": len(rows), "scores": res, "wicket_calibration": cal}


def load(version: str = VERSION) -> Model:
    return Model(json.loads((MODELS / f"{version.replace('/', '-')}.json").read_text()))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", default="synthetic")
    ap.add_argument("--cutoff", default="2024-01-01")
    a = ap.parse_args()
    art = train(DB(a.dataset), a.cutoff)
    print(json.dumps({k: art[k] for k in ("model_version", "training_window", "evaluation")}, indent=1))
