"""Phase 7 performance benchmark: server-side latency of the fan endpoints, cold (first request after an API restart, on
entities the warm-up does not pre-load where possible) and warm (repeat), plus the Phase 4/5 reference endpoints.

    python -m cricintel.fan.bench --base http://localhost:8000 [--out docs/data/benchmarks-phase7.json]
"""
from __future__ import annotations

import argparse
import json
import statistics
import time
import urllib.parse
import urllib.request

KOHLI, ZAMPA, BUMRAH, MANDHANA, ROHIT, LESSER = "ba607b88", "14f96089", "462411b3", "5d2eda89", "740742ef", "7b679de5"
# players outside the warm-up's top-40 by matches, so "cold" really is cold
COLD_PLAYERS = ["2c25d4f5", "b17e2f24", "dbe50b21", "45a13dcf"]

CASES = [
    ("Rabbit-Hole: player (not pre-warmed)", "/api/fan/next?type=player&key={cold0}"),
    ("Rabbit-Hole: player, with session memory", "/api/fan/next?type=player&key={cold0}&seen=player:" + KOHLI + "&shown=battle:" + KOHLI + "|" + ZAMPA),
    ("Rabbit-Hole: battle", "/api/fan/next?type=battle&key=" + KOHLI + "|" + ZAMPA),
    ("Rabbit-Hole: match", "/api/fan/next?type=match&key=1370353"),
    ("Rabbit-Hole: innings", "/api/fan/next?type=innings&key=1298150|2|" + KOHLI),
    ("Rabbit-Hole: record", "/api/fan/next?type=record&key=highest-score.male.T20.major"),
    ("Player home (not pre-warmed)", "/api/fan/player/{cold1}"),
    ("Player home (Kohli)", "/api/fan/player/" + KOHLI),
    ("Matchup discovery", "/api/fan/player/{cold2}/matchups"),
    ("Similar players", "/api/fan/player/" + ROHIT + "/similar"),
    ("Compare V2 (Kohli v Rohit)", "/api/fan/compare?ids=" + KOHLI + "," + ROHIT),
    ("Compare V2 (Bumrah v Starc)", "/api/fan/compare?ids=" + BUMRAH + ",3fb19989"),
    ("Record book catalogue", "/api/fan/records"),
    ("One record", "/api/fan/records/highest-score.male.T20.major"),
    ("Daily discovery (Explore)", "/api/fan/explore"),
    ("On This Day", "/api/fan/onthisday"),
    ("Play moment (innings)", "/api/fan/moment?type=innings&key=1513703|2|{cold3}"),
    ("Ask: scored fastest against", "/api/ask/v1?q=" + urllib.parse.quote("Who has Kohli scored fastest against?")),
    ("Ask: compare in chases", "/api/ask/v1?q=" + urllib.parse.quote("Compare Kohli and Rohit in chases")),
    # Phase 4/5 references, to show nothing regressed
    ("Reference: match page", "/api/match/1513703"),
    ("Reference: player profile", "/api/players/" + KOHLI + "/profile"),
    ("Reference: battle", "/api/battle?bat=" + KOHLI + "&bowl=" + ZAMPA),
    ("Reference: live replay step", "/api/live/1298150?cursor=120"),
]


def _get(base: str, path: str) -> tuple[float, int]:
    t = time.perf_counter()
    with urllib.request.urlopen(base + path, timeout=120) as r:
        r.read()
        code = r.status
    return (time.perf_counter() - t) * 1000, code


def run(base: str) -> dict:
    sub = {"cold0": COLD_PLAYERS[0], "cold1": COLD_PLAYERS[1], "cold2": COLD_PLAYERS[2], "cold3": COLD_PLAYERS[3]}
    out = []
    for name, path in CASES:
        p = path.format(**sub)
        cold, code = _get(base, p)
        warm = [_get(base, p)[0] for _ in range(5)]
        out.append({"endpoint": name, "path": p, "status": code, "cold_ms": round(cold, 1), "warm_median_ms": round(statistics.median(warm), 1),
                    "warm_max_ms": round(max(warm), 1)})
        print(f"{name:45s} cold {cold:7.1f} ms · warm {statistics.median(warm):6.1f} ms")
    return {"base": base, "measured_at": time.strftime("%Y-%m-%d %H:%M:%S"), "results": out}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="http://localhost:8000")
    ap.add_argument("--out")
    a = ap.parse_args()
    res = run(a.base)
    if a.out:
        with open(a.out, "w") as f:
            json.dump(res, f, indent=1)
