""""You probably didn't know…": surprising, defensible facts drawn from the Discovery Engine's full candidate set.

Bar for a fact (all must hold):
  * survives Benjamini–Hochberg at q = 0.01 across EVERY discovery candidate tested (multiple-comparison protection);
  * minimum sample per kind (below);
  * plain wording: the headline is a templated sentence from computed numbers, no causal language;
  * one tap to evidence (the finding's own page, filtered to the deliveries behind it).
Experimental (Situation Difficulty) findings are excluded. Daily selection is a deterministic rotation by date.
"""
from __future__ import annotations

import hashlib
import re
from datetime import date
from functools import lru_cache

from ..db import DB
from ..analytics import discovery as D

Q = 0.01
MIN_N = {"matchup": 60, "dismissal": 30, "partnership": 500, "state": 300, "trend": 300}
CAUSAL = re.compile(r"\b(because|handles? pressure|clutch|loses concentration|nerves|choke|mental|bottle)\b", re.I)


def bh(items: list[dict], q: float = Q) -> list[dict]:
    """Benjamini–Hochberg: keep the largest k with p_(k) <= k/m · q."""
    m = len(items)
    srt = sorted(items, key=lambda c: c["p"])
    k = 0
    for i, c in enumerate(srt, 1):
        if c["p"] <= i / m * q:
            k = i
    return srt[:k]


@lru_cache(maxsize=2)
def pool(db: DB) -> list[dict]:
    d = D.discover(db, False)
    allc = d.get("all") or d["items"]
    kept = bh(allc)
    out = []
    for c in kept:
        if c["type"] not in MIN_N or c["n"] < MIN_N[c["type"]] or CAUSAL.search(c["headline"] + " " + c["statement"]):
            continue
        out.append({"id": c["id"], "type": c["type"], "type_label": c["type_label"], "headline": c["headline"], "statement": c["statement"],
                    "entities": c["entities"], "people": c["people"], "gender": c["gender"], "format": c["format"], "n": c["n"], "p": c["p"],
                    "last_date": c["last_date"], "href": c["href"], "numbers": c.get("numbers", []), "why": c["why"], "score": c.get("score", 0),
                    "prov": "DERIVED"})
    out.sort(key=lambda c: -c["score"])
    return out


def method(db: DB) -> dict:
    d = D.discover(db, False)
    allc = d.get("all") or d["items"]
    return {"tested": len(allc), "survive_bh": len(bh(allc)), "shown_pool": len(pool(db)), "q": Q, "min_sample": MIN_N,
            "text": __doc__.strip()}


def daily(db: DB, day: str | None = None, exclude: set[str] | None = None, k: int = 4) -> list[dict]:
    """Deterministic for a given day: a rotating window over the ranked pool, one fact per lead player, mixed kinds."""
    p = [c for c in pool(db) if c["id"] not in (exclude or set())]
    if not p:
        return []
    day = day or date.today().isoformat()
    off = int(hashlib.sha256(day.encode()).hexdigest(), 16) % max(1, len(p))
    rot = p[off:] + p[:off]
    top = sorted(rot[:max(k * 6, 24)], key=lambda c: -c["score"])
    out, people, kinds = [], set(), {}
    for c in top:
        if c["entities"][0] in people or kinds.get(c["type"], 0) >= 2:
            continue
        out.append(c); people.add(c["entities"][0]); kinds[c["type"]] = kinds.get(c["type"], 0) + 1
        if len(out) >= k:
            break
    return out


def for_player(db: DB, pid: str, k: int = 3) -> list[dict]:
    return [c for c in pool(db) if pid in c["entities"]][:k]
