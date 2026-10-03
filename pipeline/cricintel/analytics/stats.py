"""Small, dependency-free statistics used by every evidence engine.

Conventions
- Rates are per ball unless stated. Intervals are 90% (z = 1.645) unless stated. Cricket samples are small, and
  90% intervals are honest without implying false precision.
- Shrinkage: empirical-Bayes pseudo-counts toward a stated baseline (the baseline is always reported).
- Multiple testing: Benjamini–Hochberg FDR across all splits tested for a player.
"""
from __future__ import annotations

import math

Z90 = 1.6448536269514722


def wilson(x: float, n: float, z: float = Z90) -> tuple[float | None, float | None]:
    if not n:
        return None, None
    p = x / n
    den = 1 + z * z / n
    c = (p + z * z / (2 * n)) / den
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return max(0.0, c - h), min(1.0, c + h)


def shrink_rate(x: float, n: float, prior_rate: float, k: float) -> float:
    return (x + k * prior_rate) / (n + k) if (n + k) else prior_rate


def rate_ratio(x1: int, n1: int, x0: int, n0: int, z: float = Z90) -> dict:
    """Ratio of two per-ball rates with a log-scale (Katz) interval; Haldane 0.5 correction when a count is 0."""
    if not n1 or not n0:
        return {"ratio": None, "lo": None, "hi": None, "p": None}
    a, b = (x1 or 0.5), (x0 or 0.5)
    r = (a / n1) / (b / n0)
    se = math.sqrt(max(1e-12, 1 / a - 1 / n1 + 1 / b - 1 / n0))
    lo, hi = r * math.exp(-z * se), r * math.exp(z * se)
    zz = math.log(r) / se
    return {"ratio": r, "lo": lo, "hi": hi, "p": 2 * (1 - _phi(abs(zz)))}


def mean_diff(s1: float, ss1: float, n1: int, s0: float, ss0: float, n0: int, z: float = Z90) -> dict:
    """Difference in mean runs per ball (x100 = strike-rate points). s = sum, ss = sum of squares."""
    if n1 < 2 or n0 < 2:
        return {"diff": None, "lo": None, "hi": None, "p": None}
    m1, m0 = s1 / n1, s0 / n0
    v1 = max(1e-9, (ss1 - n1 * m1 * m1) / (n1 - 1))
    v0 = max(1e-9, (ss0 - n0 * m0 * m0) / (n0 - 1))
    se = math.sqrt(v1 / n1 + v0 / n0)
    d = m1 - m0
    return {"diff": d, "lo": d - z * se, "hi": d + z * se, "p": 2 * (1 - _phi(abs(d / se)))}


def poisson_interval(k: int, z: float = Z90) -> tuple[float, float]:
    """Approximate interval for a Poisson count (Wilson–Hilferty style); used for observed dismissals."""
    if k == 0:
        return 0.0, -math.log(1 - 0.90)  # one-sided upper ~2.30 for 90%
    lo = k * (1 - 1 / (9 * k) - z / (3 * math.sqrt(k))) ** 3
    k1 = k + 1
    hi = k1 * (1 - 1 / (9 * k1) + z / (3 * math.sqrt(k1))) ** 3
    return max(0.0, lo), hi


def benjamini_hochberg(pvals: list[float], q: float = 0.10) -> list[bool]:
    m = len(pvals)
    order = sorted(range(m), key=lambda i: pvals[i])
    passed = [False] * m
    kmax = 0
    for rank, i in enumerate(order, start=1):
        if pvals[i] is not None and pvals[i] <= q * rank / m:
            kmax = rank
    for rank, i in enumerate(order, start=1):
        if rank <= kmax:
            passed[i] = True
    return passed


def percentile_rank(value: float, population: list[float]) -> float | None:
    if value is None or not population:
        return None
    below = sum(1 for v in population if v < value)
    equal = sum(1 for v in population if v == value)
    return round(100 * (below + 0.5 * equal) / len(population), 1)


def _phi(x: float) -> float:
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))
