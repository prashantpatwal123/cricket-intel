"""Historical Live Lab performance benchmark (Phase 5).

python -m cricintel.live.bench --dataset cricsheet
Simulates deliveries arriving one at a time for a featured match and times each stage of the live path.
"""
from __future__ import annotations

import argparse
import json
import statistics
import time

from ..db import DB
from ..model import baseline
from . import baselines as B
from . import insights as I
from . import service as S
from .contract import Event
from .cricsheet_provider import HistoricalCricsheetProvider
from .engine import Engine, EventLog, recompute, replay


def _pct(xs, q):
    xs = sorted(xs)
    return round(xs[min(len(xs) - 1, int(q * len(xs)))], 3)


def summary(xs, unit="ms"):
    return {"median": _pct(xs, 0.5), "p95": _pct(xs, 0.95), "max": round(max(xs), 3), "n": len(xs), "unit": unit}


def run(db: DB, mid: str = "1298150") -> dict:
    out: dict = {"match_id": mid}
    t = time.perf_counter()
    base = B.for_match(db, mid)
    out["baselines_build_ms_once_per_match"] = round(1000 * (time.perf_counter() - t))
    prov = HistoricalCricsheetProvider(db, mid)
    evs = list(prov.events())
    # 1. ingestion: EventLog.add per event (dedupe digest + ordering)
    log, ing = EventLog(), []
    for e in evs:
        t = time.perf_counter(); log.add(e); ing.append(1e6 * (time.perf_counter() - t))
    out["event_ingestion"] = summary(ing, "µs")
    # 2. incremental state: Engine.apply for one delivery
    eng, app = Engine(log.meta), []
    started = set()
    for d in log.ordered():
        if d["innings"] not in started:
            eng.start_innings(log.innings[d["innings"]]); started.add(d["innings"])
        t = time.perf_counter(); eng.apply(d); app.append(1e6 * (time.perf_counter() - t))
    out["state_update_one_delivery"] = summary(app, "µs")
    # 3. correction late in the match: recompute from the nearest checkpoint v full replay
    full = replay(log)
    target = log.ordered()[-30]["event_id"]
    log.add(Event("bench-corr", mid, "correction", {"op": "update", "target_event_id": target,
                                                     "delivery": {"runs": {"batter": 3, "wides": 0, "noballs": 0, "byes": 0, "legbyes": 0, "penalty": 0}, "boundary": None, "wickets": []}}))
    t = time.perf_counter(); eng2, reapplied = recompute(log, full); rc = 1000 * (time.perf_counter() - t)
    t = time.perf_counter(); eng3 = replay(log); fr = 1000 * (time.perf_counter() - t)
    out["correction_recompute"] = {"from_checkpoint_ms": round(rc, 2), "deliveries_reapplied": reapplied, "full_replay_ms": round(fr, 2),
                                   "identical_hash": eng2.hash() == eng3.hash()}
    # 4. Right Now generation per ball (candidates + ranking) on states 1..N
    lg2 = EventLog()
    for e in evs:
        lg2.add(e)
    rn = []
    for n in range(1, prov.total + 1):
        st = replay(lg2, upto=n).state
        t = time.perf_counter(); I.select(I.candidates(st, base)); rn.append(1000 * (time.perf_counter() - t))
    out["right_now_generation"] = summary(rn)
    # 5. prediction request (model only)
    try:
        whn = baseline.load(db.dataset)
        row = {"fmt": base["format"], "phase": "death", "wk": "3-5", "press": "12+", "batter_id": "x", "bowler_id": "y"}
        pr = []
        for _ in range(2000):
            t = time.perf_counter(); whn.predict(row); pr.append(1e6 * (time.perf_counter() - t))
        out["prediction_model"] = summary(pr, "µs")
    except FileNotFoundError:
        whn = None
    # 6. end-to-end server response, simulating balls arriving (forward) and rewinding
    r = S.Replay(db, mid, whn)
    fwd = []
    for n in range(0, prov.total + 1):
        t = time.perf_counter(); r.at(n); fwd.append(1000 * (time.perf_counter() - t))
    out["response_forward_step"] = summary(fwd[1:])
    back = []
    for n in range(prov.total, 0, -7):
        t = time.perf_counter(); r.at(n); back.append(1000 * (time.perf_counter() - t))
    out["response_rewind"] = summary(back)
    t = time.perf_counter(); r.score_pick(prov.total // 2, "1"); out["play_pick_and_reveal_ms"] = round(1000 * (time.perf_counter() - t), 1)
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", default="cricsheet")
    ap.add_argument("--match", default="1298150")
    a = ap.parse_args()
    print(json.dumps(run(DB(a.dataset), a.match), indent=1))
