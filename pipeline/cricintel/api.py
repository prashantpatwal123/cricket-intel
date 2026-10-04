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
               "wk_from", "wk_to", "faced_from", "faced_to", "rrr_from", "innings_no", "full_members",
               "chase_state", "batter_stage", "non_striker_id", "team"]


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
    return envelope({"manifest": m, "competitions": comps, "source": SOURCES[m["source_id"]], "experimental": experimental()}, t0)


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
def records_ep(request: Request, metric: str, min_sample: int | None = None, gender: str | None = None, limit: int = 25,
               min_matches: int | None = None):
    t0 = time.perf_counter()
    try:
        return envelope(REC.leaderboard(db(), metric, filters(request), min_sample, limit, gender, min_matches), t0)
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


# ------------------------------------------------------------------ Phase 3: context engine, replay, stories, partnerships
def experimental() -> bool:
    """Experimental models (Situation Difficulty) are served only when explicitly enabled. Never on by default."""
    return os.environ.get("CRICINTEL_EXPERIMENTAL") == "1"


def sdx_model():
    if not experimental():
        return None
    from .model import situation as S
    d = db()
    key = ("sdx", _DB.get("stamp"))
    if _DB.get("sdx_key") != key:
        path = S.artifact_path(d)
        _DB["sdx"], _DB["sdx_key"] = (S.SDX.load(path) if path.exists() else None), key
    return _DB["sdx"]


def require_experimental():
    if not experimental():
        raise HTTPException(404, "experimental features are disabled (set CRICINTEL_EXPERIMENTAL=1)")


@app.get("/api/deliveries/{did}/replay")
def replay_ep(did: str):
    from .analytics import replay as R
    t0 = time.perf_counter()
    r = R.delivery_replay(db(), did, sdx_model())
    if not r:
        raise HTTPException(404, "delivery not found")
    return envelope(r, t0)


@app.get("/api/players/{pid}/innings")
def innings_list_ep(pid: str, sort: str = "recent", format: str | None = None, limit: int = Query(30, le=100)):
    from .analytics import replay as R
    t0 = time.perf_counter()
    if sort not in ("recent", "runs", "sr"):
        raise HTTPException(400, "sort must be recent, runs or sr")
    return envelope(R.player_innings(db(), pid, sort, limit, format), t0)


@app.get("/api/innings/{match_id}/{inn}/{pid}")
def innings_story_ep(match_id: str, inn: int, pid: str):
    from .analytics import replay as R
    t0 = time.perf_counter()
    r = R.innings_story(db(), match_id, inn, pid, sdx_model())
    if not r:
        raise HTTPException(404, "that player did not bat in that innings")
    return envelope(r, t0)


@app.get("/api/players/{pid}/spells")
def spells_list_ep(pid: str, sort: str = "recent", format: str | None = None, limit: int = Query(30, le=100)):
    from .analytics import replay as R
    t0 = time.perf_counter()
    if sort not in ("recent", "wickets", "economy"):
        raise HTTPException(400, "sort must be recent, wickets or economy")
    return envelope(R.player_spells(db(), pid, sort, limit, format), t0)


@app.get("/api/spells/{match_id}/{inn}/{pid}")
def spell_story_ep(match_id: str, inn: int, pid: str):
    from .analytics import replay as R
    t0 = time.perf_counter()
    r = R.spell_story(db(), match_id, inn, pid, sdx_model())
    if not r:
        raise HTTPException(404, "that player did not bowl in that innings")
    return envelope(r, t0)


@app.get("/api/players/{pid}/states")
def states_ep(pid: str, role: str = "batting", format: str | None = None, team_type: str | None = None):
    from .analytics import states as ST
    t0 = time.perf_counter()
    if role not in ("batting", "bowling"):
        raise HTTPException(400, "role must be batting or bowling")
    return envelope(ST.states(db(), pid, role, format, team_type), t0)


@app.get("/api/players/{pid}/partners")
def partners_ep(pid: str, format: str | None = None, team_type: str | None = None):
    from .analytics import partnerships as PT
    t0 = time.perf_counter()
    return envelope(PT.player_partners(db(), pid, format, team_type), t0)


@app.get("/api/partnerships")
def partnerships_ep(gender: str = "male", format: str | None = None, team_type: str | None = None, sort: str = "runs",
                    phase: str | None = None, min_innings: int = 8, limit: int = Query(20, le=50)):
    from .analytics import partnerships as PT
    t0 = time.perf_counter()
    if sort not in ("runs", "run_rate", "average", "innings"):
        raise HTTPException(400, "bad sort")
    return envelope(PT.best_pairs(db(), gender, format, team_type, sort, min_innings, 120 if phase else 240, phase, limit), t0)


@app.get("/api/partnerships/stands")
def stands_ep(gender: str = "male", format: str | None = None, team_type: str | None = None, limit: int = Query(20, le=50)):
    from .analytics import partnerships as PT
    t0 = time.perf_counter()
    return envelope(PT.top_stands(db(), gender, format, team_type, limit), t0)


@app.get("/api/partnerships/pair")
def pair_ep(p1: str, p2: str, format: str | None = None):
    t0 = time.perf_counter()
    a, b = sorted([p1, p2])
    w, p = "p1 = ? AND p2 = ?", [a, b]
    if format:
        w += " AND format_group = ?"; p.append(format)
    rows = db().q(f"""SELECT partnership_id, match_id, innings_no, part_no, runs, balls, wicket_no, p1_runs, p1_balls, p2_runs, p2_balls, ended,
                             start_date, competition, format_group, batting_team, bowling_team, boundaries, dots, rotations
                      FROM partnerships WHERE {w} ORDER BY start_date DESC""", p)
    names = {r["person_id"]: r["name"] for r in db().q("SELECT person_id, name FROM player_profile WHERE person_id IN (?, ?)", [a, b])}
    for r in rows:
        r["start_date"] = str(r["start_date"])
    tot = {k: sum(r[k] for r in rows) for k in ("runs", "balls", "p1_runs", "p2_runs", "boundaries", "dots", "rotations")}
    w_ = sum(1 for r in rows if r["ended"] == "wicket")
    return envelope({"p1": {"id": a, "name": names.get(a, a)}, "p2": {"id": b, "name": names.get(b, b)}, "rows": rows, "innings": len(rows),
                     "totals": {**tot, "run_rate": round(6 * tot["runs"] / tot["balls"], 2) if tot["balls"] else None,
                                "average": round(tot["runs"] / w_, 1) if w_ else None, "wickets": w_, "best": max((r["runs"] for r in rows), default=None)},
                     "prov": "DERIVED from OBSERVED deliveries"}, t0)


@app.get("/api/context/features")
def context_features_ep():
    from .analytics import context as CX
    t0 = time.perf_counter()
    return envelope({"version": CX.CONTEXT_VERSION, "features": [{"key": k, "label": v[0], "definition": v[1], "prov": v[2], "format_note": v[3]}
                                                                   for k, v in CX.FEATURES.items()]}, t0)


@app.get("/api/discover")
def discover_ep():
    from .analytics import discovery as D
    t0 = time.perf_counter()
    return envelope(D.discover(db(), experimental() and db().has_situation), t0)


@app.get("/api/exp/situation")
def exp_situation_ep(format: str, gender: str, runs_required: int, balls_left: int, wickets_lost: int):
    require_experimental()
    t0 = time.perf_counter()
    m = sdx_model()
    if not m or not m.available(format, gender):
        raise HTTPException(404, "no model for that format and gender")
    return envelope({"score": m.score(format, gender, runs_required, balls_left, wickets_lost),
                     "swing": m.swing(format, gender, runs_required, balls_left, wickets_lost), "version": m.a["version"],
                     "definition": m.a["definition"], "status": "EXPERIMENTAL", "prov": "MODELLED"}, t0)


@app.get("/api/exp/situation/validation")
def exp_validation_ep():
    require_experimental()
    t0 = time.perf_counter()
    import json
    from pathlib import Path
    p = Path(__file__).resolve().parents[2] / "docs" / "models" / "situation-difficulty-validation.json"
    if not p.exists():
        raise HTTPException(404, "validation report not generated")
    return envelope(json.loads(p.read_text()), t0)


@app.get("/api/exp/difficulty")
def exp_difficulty_ep(format: str = "T20", gender: str = "male", role: str = "batting", metric: str = "scoring"):
    require_experimental()
    from .analytics import difficulty as DF
    t0 = time.perf_counter()
    return envelope({"leaderboard": DF.leaderboard(db(), format, gender, role, metric), "trait_test": DF.clutch_evidence(db(), format, gender, role)}, t0)


# ------------------------------------------------------------------ Phase 4: knowledge graph, search, stories, discovery
import functools  # noqa: E402
import threading as _th  # noqa: E402

_CACHE: dict = {}
_CACHE_MAX = 1024


def cached(fn):
    """Memoise deterministic GET handlers per dataset build (results only change when the data is rebuilt)."""
    @functools.wraps(fn)
    def wrap(*a, **k):
        key = (fn.__name__, _DB.get("stamp"), experimental(), a, tuple(sorted(k.items())))
        if key in _CACHE:
            return _CACHE[key]
        v = fn(*a, **k)
        if len(_CACHE) >= _CACHE_MAX:
            _CACHE.pop(next(iter(_CACHE)))
        _CACHE[key] = v
        return v
    return wrap


def _env(data, t0):
    return envelope(data, t0)


@app.on_event("startup")
def _warm():
    """Warm per-process caches in the background so the first visitor doesn't pay for them."""
    def go():
        try:
            from .analytics import discovery as D, entities as EN, libraries as L, search as SR
            d = db()
            EN.names(d)
            SR_INDEX()
            D.discover(d, experimental() and d.has_situation)
            for g in ("male", "female"):
                L._sim_space(d, g)
            # Historical Live Lab: as-of baselines for the featured replays
            from .live import service as LS
            for mid in LS.FEATURED:
                try:
                    _replay(mid)
                except Exception:  # noqa: BLE001
                    pass
            # Pre-render the most visited competition and rivalry pages
            for c in _comp_index()[:10]:
                _competition(c["competition"], c["gender"], None)
            for g in ("male", "female"):
                for r in d.q("SELECT ta, tb FROM team_results WHERE gender = ? GROUP BY 1, 2 ORDER BY count(*) DESC LIMIT 8", [g]):
                    _rivalry(r["ta"], r["tb"], g, None, None)
        except Exception:  # noqa: BLE001 - warm-up must never take the server down
            pass
    _th.Thread(target=go, daemon=True).start()


# ------------------------------------------------------------------ Historical Live Lab (Phase 5)
def _replay(mid: str):
    from .live import service as LS
    from .model import baseline
    d = db()
    if not getattr(d, "has_live", False):
        raise HTTPException(503, "live tables missing: run python -m cricintel.precompute")
    if "whn_model" not in _DB:
        try:
            _DB["whn_model"] = baseline.load(d.dataset)
        except FileNotFoundError:
            _DB["whn_model"] = None
    try:
        return LS.get(d, mid, _DB["whn_model"], sdx_model())
    except KeyError:
        raise HTTPException(404, "match not found")


@app.get("/api/live/featured")
def live_featured():
    from .live import service as LS
    t0 = time.perf_counter()
    return envelope({"matches": LS.featured(db()), "label": LS.LABEL,
                     "note": "Completed matches replayed ball by ball through the same event pipeline a live feed would use. Nothing here is live."}, t0)


@app.get("/api/live/{mid}")
def live_state(mid: str, cursor: int = Query(0, ge=0)):
    t0 = time.perf_counter()
    return envelope(_replay(mid).at(cursor, experimental()), t0)


@app.get("/api/live/{mid}/seek")
def live_seek(mid: str, cursor: int = Query(0, ge=0), to: str = Query(..., pattern=r"^(next_over|prev_over|start|end|innings:\d+)$")):
    from .live import service as LS
    t0 = time.perf_counter()
    _replay(mid)
    return envelope({"cursor": LS.seek(db(), mid, cursor, to)}, t0)


@app.get("/api/live/{mid}/play")
def live_play(mid: str, cursor: int = Query(..., ge=0), pick: str = Query(..., pattern=r"^(DOT|1|2|3|4|6|WICKET)$")):
    t0 = time.perf_counter()
    try:
        return envelope(_replay(mid).score_pick(cursor, pick), t0)
    except ValueError as e:
        raise HTTPException(400, str(e))


@app.get("/api/live/{mid}/ask")
def live_ask(mid: str, q: str = Query(min_length=3, max_length=300), cursor: int = Query(0, ge=0)):
    t0 = time.perf_counter()
    return envelope(_replay(mid).ask(cursor, q), t0)


def SR_INDEX():
    from .analytics import search as SR
    key = ("search", _DB.get("stamp"))
    if _DB.get("search_key") != key:
        _DB["search"], _DB["search_key"] = SR.load(db()), key
    return _DB["search"]


@app.get("/api/search")
def search_ep(q: str = Query(min_length=1, max_length=120)):
    t0 = time.perf_counter()
    return _env(SR_INDEX().search(q), t0)


@cached
def _match(mid):
    from .analytics import entities as EN
    return EN.match_page(db(), mid, sdx_model())


@app.get("/api/match/{mid}")
def match_ep(mid: str):
    t0 = time.perf_counter()
    r = _match(mid)
    if not r:
        raise HTTPException(404, "match not found")
    return _env(r, t0)


@app.get("/api/competitions")
def competitions_ep():
    from .analytics import entities as EN
    t0 = time.perf_counter()
    return _env(_comp_index(), t0)


@cached
def _comp_index():
    from .analytics import entities as EN
    return EN.competitions_index(db())


@cached
def _competition(name, gender, season):
    from .analytics import entities as EN
    return EN.competition_page(db(), name, gender, season)


@app.get("/api/competition")
def competition_ep(name: str, gender: str = "male", season: str | None = None):
    t0 = time.perf_counter()
    r = _competition(name, gender, season)
    if not r:
        raise HTTPException(404, "competition not found")
    return _env(r, t0)


@cached
def _rivalry(a, b, gender, fmt, competition):
    from .analytics import entities as EN
    return EN.rivalry_page(db(), a, b, gender, fmt, competition)


@app.get("/api/rivalry")
def rivalry_ep(a: str, b: str | None = None, gender: str = "male", format: str | None = None, competition: str | None = None):
    t0 = time.perf_counter()
    r = _rivalry(a, b, gender, format, competition)
    if not r:
        raise HTTPException(404, "no covered matches")
    return _env(r, t0)


@app.get("/api/rivalries")
def rivalries_ep(gender: str = "male", limit: int = Query(24, le=60)):
    t0 = time.perf_counter()
    rows = db().q("""SELECT ta, tb, count(*) AS n, count(*) FILTER (WHERE winner_c = ta) AS a_won, count(*) FILTER (WHERE winner_c = tb) AS b_won,
                            max(start_date) AS last FROM team_results WHERE gender = ? GROUP BY 1, 2 ORDER BY n DESC LIMIT ?""", [gender, limit])
    for r in rows:
        r["last"] = str(r["last"])
    return _env(rows, t0)


@cached
def _career(pid, year):
    from .analytics import entities as EN
    return EN.career(db(), pid, year)


@app.get("/api/players/{pid}/career")
def career_ep(pid: str, year: int | None = None):
    t0 = time.perf_counter()
    r = _career(pid, year)
    if not r:
        raise HTTPException(404, "player not found")
    return _env(r, t0)


@cached
def _lib(kind, cat, gender, fmt, competition, year_from, year_to, full_members):
    from .analytics import libraries as L
    fn = L.innings_library if kind == "innings" else L.spell_library
    return fn(db(), cat, gender, fmt, competition, None, year_from, year_to, 25, full_members)


@app.get("/api/library/{kind}")
def library_ep(kind: str, cat: str, gender: str = "male", format: str | None = None, competition: str | None = None,
               year_from: int | None = None, year_to: int | None = None, full_members: bool = True):
    from .analytics import libraries as L
    t0 = time.perf_counter()
    cats = L.INNINGS_CATS if kind == "innings" else L.SPELL_CATS if kind == "spells" else None
    if cats is None or cat not in cats:
        raise HTTPException(400, "unknown library or category")
    return _env(_lib(kind, cat, gender, format, competition, year_from, year_to, full_members), t0)


@cached
def _universe(cat, gender, fmt):
    from .analytics import libraries as L
    return L.battle_universe(db(), cat, gender, fmt)


@app.get("/api/battles/universe")
def universe_ep(cat: str = "most_balls", gender: str = "male", format: str | None = None):
    from .analytics import libraries as L
    t0 = time.perf_counter()
    if cat not in L.BATTLE_CATS:
        raise HTTPException(400, "unknown category")
    return _env(_universe(cat, gender, format), t0)


@app.get("/api/battles/similar")
def similar_ep(bat: str, bowl: str):
    from .analytics import libraries as L
    t0 = time.perf_counter()
    return _env(L.similar_battles(db(), bat, bowl), t0)


@cached
def _related(typ, key):
    from .analytics import related as RL
    return RL.related(db(), typ, key)


@app.get("/api/related")
def related_ep(type: str, key: str):
    t0 = time.perf_counter()
    return _env(_related(type, key), t0)


@cached
def _story(kind, a, b, c):
    from .analytics import stories as ST
    if kind == "innings":
        return ST.innings_story(db(), a, int(b), c)
    if kind == "battle":
        return ST.battle_story(db(), a, b)
    if kind == "match":
        return ST.match_story(db(), a)
    return None


@app.get("/api/story/innings/{mid}/{inn}/{pid}")
def story_innings_ep(mid: str, inn: int, pid: str):
    t0 = time.perf_counter()
    r = _story("innings", mid, inn, pid)
    if not r:
        raise HTTPException(404, "innings not found")
    return _env(r, t0)


@app.get("/api/story/battle")
def story_battle_ep(bat: str, bowl: str):
    t0 = time.perf_counter()
    r = _story("battle", bat, bowl, None)
    if not r:
        raise HTTPException(404, "these players haven't met")
    return _env(r, t0)


@app.get("/api/story/match/{mid}")
def story_match_ep(mid: str):
    t0 = time.perf_counter()
    r = _story("match", mid, None, None)
    if not r:
        raise HTTPException(404, "match not found")
    return _env(r, t0)


@app.get("/api/feed")
def feed_ep(day: str | None = None):
    from .analytics import feed as F
    t0 = time.perf_counter()
    return _env(F.daily(db(), day, False), t0)


@cached
def _method():
    from .analytics import methodology as M
    return M.methodology(db(), experimental())


@app.get("/api/methodology")
def methodology_ep():
    t0 = time.perf_counter()
    return _env(_method(), t0)


@app.get("/api/teams")
def teams_ep(gender: str = "male"):
    t0 = time.perf_counter()
    rows = db().q("""SELECT t, count(*) AS n FROM (SELECT ta AS t FROM team_results WHERE gender = ? UNION ALL SELECT tb FROM team_results WHERE gender = ?)
                     GROUP BY 1 ORDER BY n DESC""", [gender, gender])
    return _env([r["t"] for r in rows], t0)
