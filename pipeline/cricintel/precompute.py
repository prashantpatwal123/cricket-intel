"""Precompute everything consumer requests depend on, so they are served from materialized data.

    python -m cricintel.precompute --dataset cricsheet [--full]

Steps (each timed and reported): Context Engine parquet → Situation Difficulty (experimental) → persisted working DuckDB
with knowledge-graph tables → search index → discovery (both modes) → Explore feed → daily-feed pools → fan similarity
index (validated) → Records V2.
Incremental: a step is skipped when its output already matches the current dataset build, unless --full.
"""
from __future__ import annotations

import argparse
import json
import time


def run(dataset: str, full: bool = False) -> dict:
    from .build import dataset_dir
    rep, t_all = {}, time.time()
    d = dataset_dir(dataset) / "derived"

    def step(name, fn, skip=False):
        if skip:
            rep[name] = "skipped (up to date)"
            return
        t = time.time()
        out = fn()
        rep[name] = {"seconds": round(time.time() - t, 2), **({"result": out} if isinstance(out, dict) else {})}

    from .analytics import context as CX
    step("context", lambda: CX.build_context(dataset), skip=not full and (d / "delivery_context.parquet").exists())

    def sit():
        from .db import connect
        from .model import situation as S
        db = connect(dataset)
        art = S.fit(db)
        S.artifact_path(db).write_text(json.dumps(art))
        S.score_all(db, S.SDX(art))
        return {"version": art["version"]}
    step("situation_experimental", sit, skip=not full and (d / "situation.parquet").exists())
    from .db import DB, WORKING_VERSION, build_working
    manifest = json.loads((dataset_dir(dataset) / "manifest.json").read_text())

    def working_ok():
        try:
            import duckdb
            con = duckdb.connect(str(d / "working.duckdb"), read_only=True)
            m = con.execute("SELECT built_at, version FROM _meta").fetchone()
            con.close()
            return m == (manifest["built_at"], WORKING_VERSION)
        except Exception:  # noqa: BLE001 - any failure means rebuild
            return False
    step("working_db", lambda: build_working(dataset), skip=not full and working_ok())
    db = DB(dataset)
    from .analytics import discovery as D, explore as EX, feed as F, search as SR
    if full:
        for f in ("search_index.json", "discovery_cache.json", "discovery_cache_exp.json", "explore_cache.json", "feed_pools.json",
                  "fan_similar.json", "fan_records.json"):
            (d / f).unlink(missing_ok=True)
    step("search_index", lambda: {"entities": len(SR.load(db).E)})
    step("discovery", lambda: {"items": len(D.discover(db, False)["items"])})
    step("discovery_experimental", lambda: {"items": len(D.discover(db, db.has_situation)["items"])})
    step("explore", lambda: EX.feed(db) and None)
    step("feed_pools", lambda: {k: len(v) for k, v in F._pools(db, False).items()})
    # Phase 7 fan layer: validated similarity index (with holdout report) and the Records V2 book
    from .fan import records2 as R2, similar as SM
    step("fan_similar", lambda: {"pools": SM.build(db)}, skip=not full and SM.load(db) is not None)
    step("fan_records", lambda: R2.build(db), skip=not full and bool(R2.load(db)["records"]))
    rep["total_seconds"] = round(time.time() - t_all, 1)
    return rep


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", default="cricsheet")
    ap.add_argument("--full", action="store_true")
    a = ap.parse_args()
    print(json.dumps(run(a.dataset, a.full), indent=1, default=str))
