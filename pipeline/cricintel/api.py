"""HTTP API (FastAPI). Every response carries dataset/source attribution and provenance.

    CRICINTEL_DATASET=synthetic uvicorn cricintel.api:app --port 8000
"""
from __future__ import annotations

import os
import time
from functools import lru_cache

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware

from . import scene
from .analytics import player as P
from .analytics.filters import Filters
from .db import DB
from .provenance import SOURCES

app = FastAPI(title="cricintel", version="0.1.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["GET", "POST"], allow_headers=["*"])

FILTER_KEYS = ["format", "team_type", "competition", "year_from", "year_to", "opposition", "phase",
               "bowler_family", "bowler_arm", "bowler_style", "chasing", "over_from", "over_to"]


@lru_cache(maxsize=1)
def db() -> DB:
    return DB(os.environ.get("CRICINTEL_DATASET", "synthetic"))


def filters(req: Request) -> Filters:
    try:
        return Filters.parse({k: v for k, v in req.query_params.items() if k in FILTER_KEYS})
    except (ValueError, TypeError) as e:
        raise HTTPException(400, str(e))


def envelope(data, t0: float):
    m = db().manifest
    return {"data": data, "dataset": {"name": m["dataset"], "synthetic": m["synthetic"], "source_id": m["source_id"],
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
