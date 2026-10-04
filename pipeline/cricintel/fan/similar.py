"""Similar Players: nearest neighbours on the Cricket Fingerprint dimensions, separately for batting and bowling and per
format and gender. Similarity describes STYLE (how a player scores, survives and gets out relative to peers), never
quality: two batters can be alike and one far better.

Method
  1. For each pool (role × format × gender) take the fingerprint peer pool (same SQL as the fingerprint itself), limited to
     leagues and internationals between full members.
  2. Each rate is shrunk toward the pool mean with a pseudo-sample of the dimension's minimum (noisy small samples move
     less), then z-scored within the pool. Concentration dimensions are excluded (too noisy for distance).
  3. Distance = root-mean-square z difference over dimensions both players have; at least 8 shared dimensions.
  4. "Why similar" names the dimensions where both are distinctive (|z| ≥ 0.5) and closest; "how they differ" the largest gap.

Validation (holdout): the same vectors are rebuilt from two disjoint halves of each player's matches (by match id hash).
  self-retrieval: from a player's half-A vector, where does their own half-B vector rank among all half-B vectors?
  neighbour stability: overlap of top-5 neighbours computed on half A v half B.
Both are reported per pool against chance. A pool that fails the bar (top-5 self-retrieval < 5× chance) is not shown.
"""
from __future__ import annotations

import bisect
import json
import math
import time
from functools import lru_cache

from ..db import DB
from ..analytics import fingerprint as FP
from ..analytics.filters import FULL_MEMBERS

VERSION = "similar-1.1"
EXCLUDE = {"bowler_conc", "route_conc"}
MIN_SHARED = 8
POOLS = [(role, fmt, g) for role in ("batting", "bowling") for fmt in ("T20", "ODI") for g in ("male", "female")]


def _path(db: DB):
    return db.dataset_dir / "derived" / "fan_similar.json"


FM = ",".join("'" + t + "'" for t in FULL_MEMBERS)
# Peer pool scope: leagues plus internationals between full members, so neighbours are players a fan can place.
SCOPE = f" AND (team_type = 'club' OR (batting_team IN ({FM}) AND bowling_team IN ({FM})))"


def _rows(db: DB, role: str, fmt: str, g: str, half: int | None) -> dict:
    extra = SCOPE + (f" AND hash(match_id) % 2 = {half}" if half is not None else "")
    extra_dis = SCOPE.replace("team_type", "x.team_type").replace("batting_team", "x.batting_team").replace("bowling_team", "x.bowling_team") \
        + (f" AND hash(x.match_id) % 2 = {half}" if half is not None else "")
    if role == "batting":
        rr = FP.PRESSURE_RRR[fmt]
        rows = db.q(FP.AGG_SQL.format(extra=extra, extra_dis=extra_dis), [fmt, g, fmt, g, rr, rr, rr])
    else:
        rows = db.q(FP.BOWL_SQL.format(extra=extra, extra_dis=extra_dis.replace("x.", "")), [fmt, g, fmt, g])
    return {r["pid"]: r for r in rows}


def _dims(role):
    return [d for d in (FP.DIMS if role == "batting" else FP.BOWL_DIMS) if d[0] not in EXCLUDE]


def _vectors(rows: dict, role: str, fmt: str, min_balls: int) -> tuple[dict, dict]:
    dims = _dims(role)
    dmin = (FP.DIM_MIN if role == "batting" else FP.BOWL_DIM_MIN)[fmt]
    pool = {p: r for p, r in rows.items() if (r["balls"] or 0) >= min_balls}
    stats, raw = {}, {p: {} for p in pool}
    for key, _l, _g, val, samp, *_ in dims:
        minimum = 10 if key == "stumps_share" else dmin
        vals = []
        for p, r in pool.items():
            n = samp(r) or 0
            v = val(r)
            if v is not None and n >= minimum:
                raw[p][key] = (v, n, minimum)
                vals.append(v)
        if len(vals) < 20:
            continue
        mu = sum(vals) / len(vals)
        sd = math.sqrt(sum((v - mu) ** 2 for v in vals) / len(vals)) or 1
        stats[key] = (mu, sd)
    vec = {}
    for p, d in raw.items():
        z = {}
        for key, (v, n, k) in d.items():
            if key in stats:
                mu, sd = stats[key]
                shrunk = (v * n + mu * k) / (n + k)
                z[key] = (shrunk - mu) / sd
        if len(z) >= MIN_SHARED:
            vec[p] = z
    return vec, stats


def _dist(a: dict, b: dict) -> float | None:
    ks = [k for k in a if k in b]
    if len(ks) < MIN_SHARED:
        return None
    return math.sqrt(sum((a[k] - b[k]) ** 2 for k in ks) / len(ks))


def _knn(vec: dict, k: int = 8) -> dict:
    ids = list(vec)
    out = {}
    for p in ids:
        ds = []
        a = vec[p]
        for q in ids:
            if q == p:
                continue
            d = _dist(a, vec[q])
            if d is not None:
                ds.append((d, q))
        ds.sort()
        out[p] = ds[:k]
    return out


def _validate(db: DB, role: str, fmt: str, g: str) -> dict:
    peer_min = (FP.PEER_MIN if role == "batting" else FP.BOWL_PEER_MIN)[fmt]
    A, _ = _vectors(_rows(db, role, fmt, g, 0), role, fmt, peer_min // 2)
    B, _ = _vectors(_rows(db, role, fmt, g, 1), role, fmt, peer_min // 2)
    common = [p for p in A if p in B]
    if len(common) < 30:
        return {"players": len(common), "status": "insufficient"}
    top1 = top5 = 0
    for p in common:
        ds = sorted((d, q) for q in common if (d := _dist(A[p], B[q])) is not None)
        rank = next((i for i, (_, q) in enumerate(ds) if q == p), len(ds))
        top1 += rank == 0
        top5 += rank < 5
    nA, nB = _knn({p: A[p] for p in common}, 5), _knn({p: B[p] for p in common}, 5)
    overlap = sum(len({q for _, q in nA[p]} & {q for _, q in nB[p]}) / 5 for p in common) / len(common)
    n = len(common)
    res = {"players": n, "self_top1": round(top1 / n, 3), "self_top5": round(top5 / n, 3), "chance_top1": round(1 / n, 4),
           "chance_top5": round(5 / n, 4), "neighbour_overlap_top5": round(overlap, 3), "chance_overlap": round(5 / n, 4)}
    res["lift_top5"] = round(res["self_top5"] / res["chance_top5"], 1)
    res["status"] = "pass" if res["self_top5"] >= 5 * res["chance_top5"] and overlap >= 3 * res["chance_overlap"] else "fail"
    return res


def build(db: DB) -> dict:
    t0 = time.time()
    names = {r["person_id"]: r["name"] for r in db.q("SELECT person_id, name FROM player_profile")}
    out = {"version": VERSION, "built_at": db.manifest["built_at"], "pools": {}}
    for role, fmt, g in POOLS:
        peer_min = (FP.PEER_MIN if role == "batting" else FP.BOWL_PEER_MIN)[fmt]
        rows = _rows(db, role, fmt, g, None)
        vec, stats = _vectors(rows, role, fmt, peer_min)
        val = _validate(db, role, fmt, g)
        nn = _knn(vec, 8)
        labels = {d[0]: d[1] for d in _dims(role)}
        cols = {k: sorted(v[k] for v in vec.values() if k in v) for k in labels}
        players = {}
        for p, lst in nn.items():
            players[p] = {"balls": rows[p]["balls"], "z": {k: round(v, 3) for k, v in vec[p].items()},
                          "pc": {k: round(100 * bisect.bisect_left(cols[k], v) / max(1, len(cols[k]) - 1)) for k, v in vec[p].items()},
                          "nn": [{"pid": q, "d": round(d, 3)} for d, q in lst]}
        out["pools"][f"{role}|{fmt}|{g}"] = {"role": role, "format": fmt, "gender": g, "size": len(vec), "min_balls": peer_min,
                                             "labels": labels, "validation": val, "players": players}
    out["names"] = {p: names.get(p, p) for pool in out["pools"].values() for p in pool["players"]}
    out["seconds"] = round(time.time() - t0, 1)
    _path(db).write_text(json.dumps(out))
    return {k: {"size": v["size"], **v["validation"]} for k, v in out["pools"].items()}


@lru_cache(maxsize=2)
def load(db: DB) -> dict | None:
    p = _path(db)
    if not p.exists():
        return None
    d = json.loads(p.read_text())
    return d if d.get("built_at") == db.manifest["built_at"] and d.get("version") == VERSION else None


def explain(pool: dict, a: str, b: str) -> dict:
    za, zb = pool["players"][a]["z"], pool["players"][b]["z"]
    pa, pb = pool["players"][a]["pc"], pool["players"][b]["pc"]
    ks = [k for k in za if k in zb]
    alike = sorted((k for k in ks if abs(za[k]) >= 0.5 and abs(zb[k]) >= 0.5 and za[k] * zb[k] > 0), key=lambda k: abs(za[k] - zb[k]))[:3]
    if not alike:
        alike = sorted(ks, key=lambda k: abs(za[k] - zb[k]))[:3]
    differ = sorted(ks, key=lambda k: -abs(za[k] - zb[k]))[:1]
    L = pool["labels"]
    return {"alike": [{"key": k, "label": L[k], "a_pct": min(99, pa[k]), "b_pct": min(99, pb[k])} for k in alike],
            "differ": [{"key": k, "label": L[k], "a_pct": min(99, pa[k]), "b_pct": min(99, pb[k])} for k in differ],
            "shared_dims": len(ks)}


def similar(db: DB, pid: str, role: str | None = None, fmt: str | None = None, k: int = 6) -> dict:
    d = load(db)
    if not d:
        return {"available": False, "reason": "similarity index not built"}
    prof = db.q1("SELECT genders FROM player_profile WHERE person_id = ?", [pid])
    if not prof:
        return {"available": False, "reason": "unknown player"}
    g = prof["genders"][0]
    opts = [(key, p) for key, p in d["pools"].items() if pid in p["players"] and p["gender"] == g
            and (role is None or p["role"] == role) and (fmt is None or p["format"] == fmt)]
    if not opts:
        return {"available": False, "reason": "not enough covered balls in any format to place this player among peers"}
    passing = [o for o in opts if o[1]["validation"].get("status") == "pass"]
    if not passing:
        key, pool = max(opts, key=lambda x: x[1]["players"][pid]["balls"])
        return {"available": False, "reason": f"{'women' if g == 'female' else 'men'}'s {pool['format']} {pool['role']} similarity did not pass its "
                f"holdout stability test, so it is not shown", "validation": pool["validation"]}
    key, pool = max(passing, key=lambda x: x[1]["players"][pid]["balls"])
    rows = []
    for nb in pool["players"][pid]["nn"][:k]:
        ex = explain(pool, pid, nb["pid"])
        rows.append({"pid": nb["pid"], "name": d["names"].get(nb["pid"], nb["pid"]), "distance": nb["d"], "closeness": round(max(0.0, 1 - nb["d"] / 1.5), 3),
                     "balls": pool["players"][nb["pid"]]["balls"], **ex})
    others = [{"role": p["role"], "format": p["format"]} for kk, p in opts if kk != key]
    return {"available": True, "role": pool["role"], "format": pool["format"], "gender": g, "pool_size": pool["size"], "rows": rows,
            "other_views": others, "validation": pool["validation"],
            "note": "Similar style, not similar quality: two players can share a profile and differ greatly in output.",
            "method": __doc__.split("Method")[1].strip()}


def ordinal(n: int) -> str:
    return f"{n}{'th' if 10 <= n % 100 <= 20 else {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')}"


def for_player(db: DB, pid: str, k: int = 2) -> list[dict]:
    s = similar(db, pid, k=k)
    if not s.get("available"):
        return []
    out = []
    for r in s["rows"]:
        a = r["alike"][0] if r["alike"] else None
        why = f"{a['label'].lower()} ({ordinal(a['a_pct'])} v {ordinal(a['b_pct'])} percentile)" if a else "close on most dimensions"
        out.append({"pid": r["pid"], "name": r["name"], "role": s["role"], "format": s["format"], "why_short": why, "closeness": r["closeness"],
                    "sample": r["balls"]})
    return out
