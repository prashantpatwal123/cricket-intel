"""Rabbit-Hole engine: rank where a fan should go next from any entity. Deterministic; no randomness, no tracking.

score(edge) = 0.22·strength + 0.20·unusual + 0.14·sample + 0.16·recognisability + 0.08·recency + 0.20·relation prior
then, greedily (maximal marginal relevance):
  − 0.16 for each already-picked edge with the same relation, − 0.08 for each with the same target type
  × 0.15 if the fan has already visited the target this browser session (sent by the page, kept in localStorage only);
         when at least k unvisited destinations exist, visited ones are left out altogether
  × 0.6  if the target was already recommended to them twice or more on other pages
An entity is never shown twice in one list (one destination per entity). The full component breakdown is returned
in `why` so the ranking is inspectable; fan-facing UI shows only the human reason.
"""
from __future__ import annotations

import threading
from collections import Counter

from ..db import DB
from . import kg

VERSION = "rabbit-hole-1.0"
W = {"strength": 0.22, "unusual": 0.20, "sample": 0.14, "recog": 0.16, "recency": 0.08, "prior": 0.20}
SAME_REL, SAME_TYPE, SEEN, SHOWN = 0.16, 0.08, 0.15, 0.6

_CACHE: dict = {}
_LOCK = threading.Lock()


def cached_neighbours(db: DB, typ: str, key: str) -> list[dict]:
    """Neighbour generation is the only expensive part; it depends only on the entity, so it is cached per data build.
    Ranking (which depends on the session) is pure Python over ~10–30 edges."""
    k = (id(db), typ, key)
    with _LOCK:
        if k in _CACHE:
            return _CACHE[k]
    v = kg.neighbours(db, typ, key)
    with _LOCK:
        if len(_CACHE) > 4000:
            _CACHE.clear()
        _CACHE[k] = v
    return v


def base_score(e: dict) -> float:
    return sum(W[k] * e["f"][k] for k in W)


def rank(edges: list[dict], seen: set[str] | None = None, shown: Counter | None = None, k: int = 6) -> list[dict]:
    seen, shown = seen or set(), shown or Counter()
    is_seen = lambda e: e["id"] in seen or e["href"] in seen or e.get("entity") in seen  # noqa: E731
    # with enough fresh destinations, already-opened ones are left out entirely (not just pushed down)
    if sum(1 for e in edges if not is_seen(e)) >= k:
        edges = [e for e in edges if not is_seen(e)]
    pool = []
    for e in edges:
        s = base_score(e)
        mult = 1.0
        if is_seen(e):
            mult *= SEEN
        if shown.get(e["id"], 0) >= 2:
            mult *= SHOWN
        pool.append((s, mult, e))
    picked, ids, rel, typ = [], set(), Counter(), Counter()
    while pool and len(picked) < k:
        best = max(pool, key=lambda x: (x[0] - SAME_REL * rel[x[2]["relation"]] - SAME_TYPE * typ[x[2]["type"]]) * x[1])
        pool.remove(best)
        s, mult, e = best
        ent = e.get("entity") or e["id"]
        if e["id"] in ids or ent in ids:
            continue
        pen = SAME_REL * rel[e["relation"]] + SAME_TYPE * typ[e["type"]]
        final = (s - pen) * mult
        ids.add(e["id"]); ids.add(ent); rel[e["relation"]] += 1; typ[e["type"]] += 1
        picked.append({**e, "score": round(final, 3),
                       "why": {"base": round(s, 3), "components": {c: round(W[c] * e["f"][c], 3) for c in W},
                               "diversity_penalty": round(pen, 3), "seen_this_session": is_seen(e),
                               "already_recommended": shown.get(e["id"], 0)}})
    return picked


def explore_next(db: DB, typ: str, key: str, seen: list[str] | None = None, shown: list[str] | None = None, k: int = 6) -> dict:
    edges = cached_neighbours(db, typ, key)
    out = rank(edges, set(seen or []), Counter(shown or []), k)
    return {"entity": kg.node(typ, key), "items": out, "candidates": len(edges), "version": VERSION,
            "method": "Every destination is a real relationship in covered data. Ranked by strength, unusualness, sample, recognisability, "
                      "recency and the kind of relationship; diversified so one entity or one kind of link does not dominate; and anything "
                      "you already opened this session is pushed down. Nothing is random and nothing leaves your browser except the list of "
                      "pages sent with this request."}


def chain(db: DB, typ: str, key: str, steps: int = 5) -> list[dict]:
    """A deterministic rabbit hole: follow the top recommendation from each stop, never revisiting a stop."""
    path, seen = [], {kg.node(typ, key)}
    cur = (typ, key)
    for _ in range(steps):
        nxt = [e for e in rank(cached_neighbours(db, *cur), seen, k=8) if e["id"] not in seen and e["type"] in
               ("player", "battle", "match", "innings", "spell", "partnership", "record", "competition", "rivalry")
               and not e["id"].startswith("view:")]
        if not nxt:
            break
        # a rabbit hole should change scenery: prefer a different kind of page from the last two stops when one scores close
        recent = {x["type"] for x in path[-2:]}
        e = next((x for x in nxt if x["type"] not in recent and x["score"] >= 0.6 * nxt[0]["score"]), nxt[0])
        path.append(e)
        seen.add(e["id"])
        cur = (e["type"], e["id"].split(":", 1)[1])
    return path
