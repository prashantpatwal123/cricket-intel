"""HTTP API (FastAPI). Every response carries dataset/source attribution and provenance.

    CRICINTEL_DATASET=synthetic uvicorn cricintel.api:app --port 8000
"""
from __future__ import annotations

import os
import time

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware

from . import scene
from .analytics import player as P
from .analytics.filters import Filters
from .build import dataset_dir
from .db import DB
from .provenance import SOURCES

app = FastAPI(title="cricintel", version="0.1.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["GET", "POST"], allow_headers=["*"])

FILTER_KEYS = ["format", "team_type", "competition", "year_from", "year_to", "opposition", "phase", "gender",
               "bowler_family", "bowler_arm", "bowler_style", "chasing", "over_from", "over_to",
               "wk_from", "wk_to", "faced_from", "faced_to", "rrr_from", "innings_no", "full_members"]


_DB: dict = {}


def db() -> DB:
    """Current dataset. Reloads if the dataset was rebuilt (manifest changed), so the in-memory
    working tables can never drift from the Parquet files they were derived from."""
    mode = os.environ.get("CRICINTEL_MODE", "TEST_SYNTHETIC")
    name = os.environ.get("CRICINTEL_DATASET", "synthetic" if mode == "TEST_SYNTHETIC" else "cricsheet")
    if mode == "REAL_DATA" and name == "synthetic":
        raise RuntimeError("REAL_DATA mode refuses to serve the synthetic fixture")
    stamp = (dataset_dir(name) / "manifest.json").stat().st_mtime_ns
    if _DB.get("stamp") != stamp:
        _DB["db"], _DB["stamp"] = DB(name), stamp
    return _DB["db"]


def filters(req: Request) -> Filters:
    try:
        return Filters.parse({k: v for k, v in req.query_params.items() if k in FILTER_KEYS})
    except (ValueError, TypeError) as e:
        raise HTTPException(400, str(e))


def envelope(data, t0: float):
    m = db().manifest
    return {"data": data, "dataset": {"mode": "TEST_SYNTHETIC" if m["synthetic"] else "REAL_DATA", "name": m["dataset"], "synthetic": m["synthetic"], "source_id": m["source_id"],
                                      "attribution": m["attribution"], "built_at": m["built_at"]},
            "ms": round((time.perf_counter() - t0) * 1000, 1)}


@app.get("/api/meta")
def meta():
    t0 = time.perf_counter()
    m = db().manifest
    comps = db().q("""SELECT competition, gender, format_group, team_type, count(*) AS matches, min(start_date) AS first_date,
                      max(start_date) AS last_date FROM matches GROUP BY ALL ORDER BY matches DESC""")
    return envelope({"manifest": m, "competitions": comps, "source": SOURCES[m["source_id"]]}, t0)


@app.get("/api/players/search")
def search(q: str = Query(min_length=1), limit: int = 12):
    t0 = time.perf_counter()
    return envelope(P.search(db(), q, limit), t0)


@app.get("/api/players/featured")
def featured():
    t0 = time.perf_counter()
    return envelope(P.featured(db()), t0)


@app.get("/api/players/{pid}/profile")
def profile(pid: str, request: Request):
    t0 = time.perf_counter()
    r = P.profile(db(), pid, filters(request))
    if not r:
        raise HTTPException(404, "player not found")
    return envelope(r, t0)


@app.get("/api/players/{pid}/dismissals")
def dismissals(pid: str, request: Request):
    t0 = time.perf_counter()
    return envelope(P.dismissals(db(), pid, filters(request)), t0)


@app.get("/api/players/{pid}/matchups")
def matchups(pid: str, request: Request, by: str = "bowler", q: str | None = None, role: str = "batter", limit: int = 30):
    t0 = time.perf_counter()
    try:
        return envelope(P.matchups(db(), pid, filters(request), by=by, q=q, role=role, limit=limit), t0)
    except ValueError as e:
        raise HTTPException(400, str(e))


@app.get("/api/players/{pid}/situations")
def situations(pid: str, request: Request):
    t0 = time.perf_counter()
    return envelope(P.situations(db(), pid, filters(request)), t0)


@app.get("/api/deliveries")
def deliveries(request: Request, out_id: str | None = None, route: str | None = None, kind: str | None = None,
               batter_id: str | None = None, bowler_id: str | None = None, fielder_id: str | None = None,
               offset: int = 0, limit: int = Query(25, le=100)):
    t0 = time.perf_counter()
    return envelope(P.delivery_query(db(), filters(request), out_id=out_id, route=route, kind=kind, batter_id=batter_id,
                                     bowler_id=bowler_id, fielder_id=fielder_id, offset=offset, limit=limit), t0)


@app.get("/api/deliveries/{did}")
def delivery(did: str):
    t0 = time.perf_counter()
    cards = P.delivery_cards(db(), [did])
    if not cards:
        raise HTTPException(404, "delivery not found")
    c = cards[0]
    tr = db().q1("SELECT * FROM delivery_tracking WHERE delivery_id = ?", [did])
    sh = db().q1("SELECT * FROM delivery_shot WHERE delivery_id = ?", [did])
    c["scene"] = scene.build(c, tr, sh)
    return envelope(c, t0)


# ------------------------------------------------------------------ Ask Cricket v0
@app.get("/api/ask")
def ask(q: str = Query(min_length=3, max_length=300)):
    from .ask.intents import answer
    t0 = time.perf_counter()
    return envelope(answer(db(), q), t0)


@app.get("/api/ask/examples")
def ask_examples():
    from .ask.intents import EXAMPLES
    t0 = time.perf_counter()
    top = db().q("""SELECT pp.person_id, pp.name FROM player_profile pp JOIN (SELECT batter_id, count(*) n FROM balls GROUP BY 1) b
                    ON b.batter_id = pp.person_id ORDER BY n DESC LIMIT 2""")
    bw = db().q1("""SELECT pp.name FROM balls b JOIN player_profile pp ON pp.person_id = b.bowler_id
                    WHERE b.batter_id = ? GROUP BY 1 ORDER BY count(*) DESC LIMIT 1""", [top[0]["person_id"]])
    return envelope([e.format(p=top[i % len(top)]["name"], b=bw["name"] if bw else "<bowler>") for i, e in enumerate(EXAMPLES)], t0)


# ------------------------------------------------------------------ What Happens Next?
_GAME: dict = {}


def game():
    from .game.whn import Game
    d = db()
    if _GAME.get("db") is not d:
        _GAME["db"], _GAME["game"] = d, Game(d)
    return _GAME["game"]


@app.get("/api/whn/next")
def whn_next(exclude: str = ""):
    t0 = time.perf_counter()
    return envelope(game().random_moment(set(filter(None, exclude.split(",")))), t0)


@app.get("/api/whn/{mid}/reveal")
def whn_reveal(mid: str, pick: str | None = None):
    t0 = time.perf_counter()
    g = game()
    if mid not in g.by_id:
        raise HTTPException(404, "unknown moment")
    try:
        return envelope(g.reveal(mid, pick), t0)
    except ValueError as e:
        raise HTTPException(400, str(e))


@app.get("/api/whn/{mid}/points")
def whn_points(mid: str):
    """Points available per option BEFORE picking (transparent scoring). Reveals nothing about the outcome."""
    from .game import scoring
    from .model.baseline import CLASSES
    t0 = time.perf_counter()
    m = game().by_id.get(mid)
    if not m:
        raise HTTPException(404, "unknown moment")
    return envelope({c: scoring.capped_rarity(m["probs"], i, i) for i, c in enumerate(CLASSES)}, t0)


# ------------------------------------------------------------------ Phase 2 engines
from .analytics import battle as BT  # noqa: E402
from .analytics import fingerprint as FP  # noqa: E402
from .analytics import insights as INS  # noqa: E402
from .analytics import records as REC  # noqa: E402
from .ask import v1 as ASK1  # noqa: E402


@app.get("/api/players/{pid}/fingerprint")
def fingerprint_ep(pid: str, role: str = "auto", format: str | None = None, team_type: str | None = None):
    t0 = time.perf_counter()
    d = db()
    if role == "auto":
        bat = d.q1("SELECT count(*) FILTER (WHERE faced) AS n FROM balls WHERE batter_id = ?", [pid])["n"]
        bowl = d.q1("SELECT count(*) FILTER (WHERE legal) AS n FROM balls WHERE bowler_id = ?", [pid])["n"]
        role = "bowling" if bowl > 2 * bat else "batting"
    fn = FP.bowling_fingerprint if role == "bowling" else FP.fingerprint
    return envelope(fn(d, pid, format, team_type), t0)


@app.get("/api/players/{pid}/insights")
def insights_ep(pid: str, format: str | None = None, team_type: str | None = None):
    t0 = time.perf_counter()
    d = db()
    if not format:
        r = d.q1("""SELECT format_group FROM balls WHERE batter_id = ? AND faced GROUP BY 1 ORDER BY count(*) DESC LIMIT 1""", [pid])
        format = r["format_group"] if r else "T20"
    return envelope(INS.insights(d, pid, format, team_type), t0)


@app.get("/api/players/{pid}/dismissal-story")
def story_ep(pid: str, request: Request, route: str = Query(...)):
    t0 = time.perf_counter()
    return envelope(BT.dismissal_story(db(), pid, route, filters(request)), t0)


@app.get("/api/players/{pid}/timeline")
def timeline_ep(pid: str, request: Request, by: str = "year"):
    t0 = time.perf_counter()
    return envelope(BT.timeline(db(), pid, filters(request), by), t0)


@app.get("/api/battle")
def battle_ep(request: Request, bat: str, bowl: str):
    t0 = time.perf_counter()
    return envelope(BT.battle(db(), bat, bowl, filters(request)), t0)


@app.get("/api/battles/notable")
def notable_ep(gender: str | None = None, limit: int = 12):
    t0 = time.perf_counter()
    return envelope(BT.notable_battles(db(), gender, limit), t0)


@app.get("/api/compare")
def compare_ep(request: Request, ids: str):
    t0 = time.perf_counter()
    return envelope(BT.compare(db(), [x for x in ids.split(",") if x][:4], filters(request)), t0)


@app.get("/api/records")
def records_ep(request: Request, metric: str, min_sample: int | None = None, gender: str | None = None, limit: int = 25):
    t0 = time.perf_counter()
    try:
        return envelope(REC.leaderboard(db(), metric, filters(request), min_sample, limit, gender), t0)
    except ValueError as e:
        raise HTTPException(400, str(e))


@app.get("/api/records/catalog")
def records_catalog():
    t0 = time.perf_counter()
    return envelope({"metrics": [{"key": k, "label": v[0], "entity": v[1], "min": v[5], "definition": v[8]} for k, v in REC.METRICS.items()],
                     "presets": REC.PRESETS}, t0)


@app.get("/api/ask/v1")
def ask_v1(q: str = Query(min_length=2, max_length=300)):
    t0 = time.perf_counter()
    return envelope(ASK1.ask(db(), q), t0)


@app.post("/api/ask/v1/run")
async def ask_v1_run(request: Request):
    t0 = time.perf_counter()
    return envelope(ASK1.run_intent(db(), await request.json()), t0)


@app.get("/api/explore")
def explore_ep():
    from .analytics import explore as EX
    t0 = time.perf_counter()
    return envelope(EX.feed(db()), t0)
