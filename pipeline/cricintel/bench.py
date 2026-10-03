"""Benchmark core queries. python -m cricintel.bench --dataset synthetic [--out docs/data/benchmarks-<label>.md]"""
from __future__ import annotations

import argparse
import json
import statistics
import time

from .analytics import player as P
from .analytics.filters import Filters
from .config import DOCS_DATA
from .db import DB

RECORDS_SQL = """
SELECT batter_id, any_value(batter) AS batter, count(*) FILTER (WHERE faced) AS balls, sum(runs_batter) AS runs,
       round(100.0 * sum(runs_batter) / count(*) FILTER (WHERE faced), 1) AS sr
FROM balls WHERE format_group = 'T20' AND bowler_family = 'spin' AND phase = 'death'
GROUP BY 1 HAVING count(*) FILTER (WHERE faced) >= 100 ORDER BY sr DESC LIMIT 20"""


def timeit(fn, n=7):
    fn()  # warm
    xs = []
    for _ in range(n):
        t = time.perf_counter(); fn(); xs.append((time.perf_counter() - t) * 1000)
    return {"median_ms": round(statistics.median(xs), 1), "p_max_ms": round(max(xs), 1)}


def run(dataset: str, label: str) -> dict:
    t = time.perf_counter()
    db = DB(dataset)
    startup = round(time.perf_counter() - t, 2)
    pid = db.q1("SELECT batter_id FROM balls GROUP BY 1 ORDER BY count(*) DESC LIMIT 1")["batter_id"]
    bowler = db.q1("SELECT bowler_id FROM balls WHERE batter_id = ? GROUP BY 1 ORDER BY count(*) DESC LIMIT 1", [pid])["bowler_id"]
    F, FT = Filters(), Filters(format="T20", phase="death")
    res = {
        "player page: profile": timeit(lambda: P.profile(db, pid, F)),
        "player page: dismissals": timeit(lambda: P.dismissals(db, pid, F)),
        "player page: situations": timeit(lambda: P.situations(db, pid, F)),
        "matchup: by bowler": timeit(lambda: P.matchups(db, pid, F, by="bowler")),
        "matchup: by bowler family (T20 death)": timeit(lambda: P.matchups(db, pid, FT, by="bowler_family")),
        "dismissal drill-down (route → deliveries)": timeit(lambda: P.delivery_query(db, F, out_id=pid, route="BOWLED", limit=20)),
        "delivery drill-down (batter v bowler, 20 cards)": timeit(lambda: P.delivery_query(db, F, batter_id=pid, bowler_id=bowler, limit=20)),
        "records: highest T20 SR v spin at death (min 100 balls)": timeit(lambda: db.q(RECORDS_SQL)),
    }
    counts = {k: db.q1(f"SELECT count(*) AS n FROM {k}")["n"] for k in ("matches", "deliveries", "wickets")}
    import os, platform
    out = {"label": label, "dataset": dataset, "synthetic": db.manifest["synthetic"], "counts": counts,
           "startup_materialize_s": startup, "results": res, "machine": f"{os.cpu_count()} vCPU, {platform.machine()}, DuckDB in-process"}
    L = [f"# Benchmarks: {label}", "", f"Dataset `{dataset}` ({'SYNTHETIC' if out['synthetic'] else 'real'}): "
         f"{counts['matches']:,} matches · {counts['deliveries']:,} deliveries · {counts['wickets']:,} wickets. Machine: {out['machine']}.", "",
         f"API cold start (load Parquet + materialise working tables): **{startup}s**", "",
         "| Query | Median | Max (of 7) |", "|---|---|---|"]
    L += [f"| {k} | {v['median_ms']} ms | {v['p_max_ms']} ms |" for k, v in res.items()]
    DOCS_DATA.mkdir(parents=True, exist_ok=True)
    (DOCS_DATA / f"benchmarks-{label}.md").write_text("\n".join(L) + "\n")
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", default="synthetic")
    ap.add_argument("--label", default="synthetic-small")
    a = ap.parse_args()
    print(json.dumps(run(a.dataset, a.label), indent=1))
