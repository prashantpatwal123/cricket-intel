"""Reconcile the event-driven engine against Cricsheet's recorded innings totals.

python -m cricintel.live.validate --dataset cricsheet [--limit N]
For every match: replay all events through the engine, then compare runs / wickets / legal balls per innings with the
`innings` table (which the engine never reads). Mismatches are listed with their cause where known.
"""
from __future__ import annotations

import argparse
import json
import time

from ..db import DB
from .cricsheet_provider import HistoricalCricsheetProvider
from .engine import EventLog, replay


def run(db: DB, where: str = "format_group IN ('T20','ODI')", limit: int | None = None) -> dict:
    ids = [r["match_id"] for r in db.q(f"SELECT match_id FROM matches WHERE {where} ORDER BY start_date, match_id" + (f" LIMIT {int(limit)}" if limit else ""))]
    bad, n_inn, t0, balls = [], 0, time.perf_counter(), 0
    for mid in ids:
        prov = HistoricalCricsheetProvider(db, mid)
        log = EventLog()
        for e in prov.events():
            log.add(e)
        st = replay(log).state
        balls += st["n"]
        rec = {r["innings_no"]: r for r in db.q("SELECT innings_no, total_runs, total_wickets, legal_balls, penalty_runs_post FROM innings WHERE match_id = ?", [mid])}
        for inn in st["innings"]:
            r = rec.get(inn["innings"])
            n_inn += 1
            if r is None:
                bad.append({"match_id": mid, "innings": inn["innings"], "why": "innings missing from table"})
                continue
            exp_runs = (r["total_runs"] or 0)
            got = (inn["runs"] + (r["penalty_runs_post"] or 0), inn["wickets"], inn["legal"])
            if got != (exp_runs, r["total_wickets"], r["legal_balls"]):
                bad.append({"match_id": mid, "innings": inn["innings"], "engine": got, "recorded": (exp_runs, r["total_wickets"], r["legal_balls"])})
    dt = time.perf_counter() - t0
    return {"matches": len(ids), "innings": n_inn, "deliveries": balls, "mismatches": len(bad), "examples": bad[:20],
            "seconds": round(dt, 1), "deliveries_per_second": round(balls / dt) if dt else None}


EDGE_CASES = {
    "retired hurt": "kind = 'retired hurt'", "retired out": "kind = 'retired out'", "retired not out": "kind = 'retired not out'",
    "obstructing the field": "kind = 'obstructing the field'", "timed out": "kind = 'timed out'", "hit the ball twice": "kind = 'hit the ball twice'",
    "stumped": "kind = 'stumped'", "run out": "kind = 'run out'", "hit wicket": "kind = 'hit wicket'",
}


def edge_report(db: DB, per_case: int = 25) -> dict:
    """Replay real matches containing each rare case and reconcile them. Also ties/super overs and D/L targets."""
    out = {}
    for name, cond in EDGE_CASES.items():
        ids = [r["match_id"] for r in db.q(f"""SELECT DISTINCT w.match_id FROM wickets w JOIN matches m USING (match_id)
                                               WHERE {cond} AND m.format_group IN ('T20','ODI') ORDER BY 1 LIMIT {per_case}""")]
        out[name] = run(db, "match_id IN (" + ",".join(f"'{i}'" for i in ids) + ")") if ids else {"matches": 0}
    so = [r["match_id"] for r in db.q("SELECT DISTINCT match_id FROM innings WHERE super_over ORDER BY 1")]
    out["super overs (all covered)"] = run(db, "match_id IN (" + ",".join(f"'{i}'" for i in so) + ")")
    dl = [r["match_id"] for r in db.q(f"SELECT match_id FROM matches WHERE method = 'D/L' AND format_group IN ('T20','ODI') ORDER BY 1 LIMIT {per_case * 4}")]
    out["D/L revised targets"] = run(db, "match_id IN (" + ",".join(f"'{i}'" for i in dl) + ")")
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", default="cricsheet")
    ap.add_argument("--limit", type=int)
    ap.add_argument("--where", default="format_group IN ('T20','ODI')")
    ap.add_argument("--edge", action="store_true", help="replay real matches containing each rare case")
    a = ap.parse_args()
    db = DB(a.dataset)
    print(json.dumps(edge_report(db) if a.edge else run(db, a.where, a.limit), indent=1, default=str))
