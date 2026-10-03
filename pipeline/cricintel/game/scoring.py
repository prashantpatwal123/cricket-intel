"""Prediction scoring schemes + simulation used to choose one (see docs/game-scoring.md).

All schemes score a single pick from {DOT,1,2,3,4,6,WICKET} given the model's pre-ball probabilities
p (MODELLED) and the actual outcome (OBSERVED).
"""
from __future__ import annotations

import math
import random
import statistics

CLASSES = ["DOT", "1", "2", "3", "4", "6", "WICKET"]


def inverse_prob(p, pick, actual):
    return 10.0 / p[pick] if pick == actual else 0.0


def log_score(p, pick, actual):
    return 10.0 * math.log2(1.0 / p[pick]) if pick == actual else 0.0


def flat(p, pick, actual):  # = one-hot Brier: all correct picks equal
    return 10.0 if pick == actual else 0.0


def capped_rarity(p, pick, actual, cap=4.0, alpha=0.5):
    """10 × min(cap, (p_mode / p_pick)^alpha). The modal outcome is worth 10; rarer picks earn more, sub-linearly and capped."""
    if pick != actual:
        return 0.0
    return round(10.0 * min(cap, (max(p) / p[pick]) ** alpha))


SCHEMES = {"inverse 10/p": inverse_prob, "log 10·log2(1/p)": log_score, "flat (one-hot Brier)": flat,
           "capped rarity √, ×4 cap": capped_rarity}


def brier_confidence(dist, actual):
    """Confidence mode (Cricket IQ): user submits a distribution; proper scoring (0..100)."""
    bs = sum((dist[j] - (1.0 if j == actual else 0.0)) ** 2 for j in range(len(dist)))
    return round(100 * (1 - bs / 2), 1)


def simulate(samples: list[tuple[list[float], int]], seed=1, informed_q=0.15, session=20):
    """samples: (model probs, actual class index). Returns metrics per scheme × strategy."""
    r = random.Random(seed)
    k = len(CLASSES)
    strategies = {
        "model favourite (argmax)": lambda p, a: max(range(k), key=p.__getitem__),
        "jackpot hunter (rarest)": lambda p, a: min(range(k), key=p.__getitem__),
        "always WICKET": lambda p, a: CLASSES.index("WICKET"),
        "always SIX": lambda p, a: CLASSES.index("6"),
        "random ~ model": lambda p, a: r.choices(range(k), p)[0],
        "uniform random": lambda p, a: r.randrange(k),
        f"informed fan (knows {int(informed_q * 100)}% of outcomes)": lambda p, a: a if r.random() < informed_q else max(range(k), key=p.__getitem__),
    }
    out = {}
    for sname, sfn in SCHEMES.items():
        out[sname] = {}
        for stname, st in strategies.items():
            pts = [sfn(p, st(p, a), a) for p, a in samples]
            sessions = [sum(pts[i:i + session]) for i in range(0, len(pts) - session + 1, session)]
            top = sorted(pts, reverse=True)
            top5 = sum(top[: max(1, len(top) // 20)]) / (sum(pts) or 1)
            out[sname][stname] = {
                "mean": round(statistics.fmean(pts), 2), "hit_rate": round(sum(1 for x in pts if x > 0) / len(pts), 3),
                "max_single": round(max(pts), 1), "top5pct_share": round(top5, 3),
                "session_cv": round(statistics.pstdev(sessions) / (statistics.fmean(sessions) or 1), 2) if sessions else None,
            }
    return out
