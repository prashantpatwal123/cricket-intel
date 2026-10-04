"""Historical Live Lab service: one replay per match, answering "what is the state at ball N?" spoiler-safely (Phase 5).

The response for cursor N is built from provider events up to N (plus the identity of who faces/bowls next). The
"Right Now" novelty memory is a causal walk: ball n's flags depend only on balls 1..n, and the walk never runs past
the highest cursor requested, like a live system that has only received the balls bowled so far.
"""
from __future__ import annotations

import threading
import time

from ..analytics.entities import coverage_note, names
from ..db import DB
from ..game import scoring
from . import baselines as B
from . import insights as I
from .contract import Event
from .cricsheet_provider import HistoricalCricsheetProvider
from .engine import EventLog, replay

LABEL = "HISTORICAL REPLAY — NOT LIVE"
FEATURED = ["1298150", "1370353", "1513703", "1490443", "1384439", "1216517", "1490709"]
STAGE_NAME = {"1-10": "new", "11-30": "settling", "31+": "set"}
CLASSES = ["DOT", "1", "2", "3", "4", "6", "WICKET"]


def featured(db: DB) -> list[dict]:
    q = ",".join("?" * len(FEATURED))
    rows = {r["match_id"]: r for r in db.q(f"""SELECT match_id, competition, season, event_stage, start_date, venue, city, team1, team2,
                                                     gender, format_group, team_type FROM matches WHERE match_id IN ({q})""", FEATURED)}
    out = []
    for mid in FEATURED:
        r = rows.get(mid)
        if not r:
            continue
        out.append({"match_id": mid, "title": f"{r['team1']} v {r['team2']}", "competition": r["competition"], "stage": r["event_stage"],
                    "season": r["season"], "date": str(r["start_date"]), "venue": r["venue"], "city": r["city"],
                    "tags": [("Women" if r["gender"] == "female" else "Men"), r["format_group"], "international" if r["team_type"] == "international" else "league"]})
    return out


class Replay:
    def __init__(self, db: DB, mid: str, whn_model=None, sdx=None):
        self.db, self.mid = db, mid
        self.prov = HistoricalCricsheetProvider(db, mid)
        self.base = B.for_match(db, mid)
        self.cov = coverage_note(db, self.prov.m["competition"], self.prov.m["gender"])
        self.whn, self.sdx = whn_model, sdx
        self.names = names(db)
        self.lock = threading.Lock()
        self.walk_pos = 0
        self.seen: set[str] = set()
        self.new_at: dict[int, list[str]] = {}
        self.ckpts: dict[int, dict] = {}
        self.lg: EventLog | None = None
        self.fetched = -1

    # ------------------------------------------------------------------ core
    def log(self, n: int) -> EventLog:
        """The consumer's event log. It only grows (like a live feed); earlier cursors are truncated replays of it."""
        with self.lock:
            if self.lg is None or n > self.fetched:
                lg = self.lg or EventLog()
                for e in self.prov.events(n):
                    if e.event_id not in lg.seen or e.kind == "pre_ball":
                        lg.add(self._named(e))
                self.lg, self.fetched = lg, n
            return self.lg

    def _named(self, e):
        """Display names from the player register instead of the scorecard spelling ('V Kohli' → 'Virat Kohli')."""
        def fix(x):
            if isinstance(x, dict):
                if "id" in x and "name" in x and len(x) == 2:
                    return {"id": x["id"], "name": self.names.get(x["id"], x["name"])}
                return {k: fix(v) for k, v in x.items()}
            if isinstance(x, list):
                return [fix(v) for v in x]
            return x
        return Event(e.event_id, e.match_id, e.kind, fix(e.payload), e.seq) if e.kind in ("delivery", "pre_ball", "playing_xi") else e

    def _state(self, lg: EventLog, n: int):
        base = max((c for c in self.ckpts if c <= n), default=0)
        eng = replay(lg, upto=n if n < len(lg.deliveries) else None,
                     base=(base, self.ckpts[base], self.ckpts) if base else None)
        for k, v in eng.checkpoints.items():
            self.ckpts.setdefault(k, v)
        return eng

    def walk_to(self, n: int, lg: EventLog):
        """Causal novelty memory: process balls walk_pos+1 .. n in order, recording which insights were new at each."""
        with self.lock:
            while self.walk_pos < n:
                k = self.walk_pos + 1
                eng = self._state(lg, k)
                self._last = (k, lg.version, eng)       # the response for k can reuse this state
                st = eng.state
                keys = [c["key"] for c in I.select(I.candidates(st, self.base))]
                self.new_at[k] = [x for x in keys if x not in self.seen]
                self.seen.update(keys)
                self.walk_pos = k

    # ------------------------------------------------------------------ response
    def at(self, n: int, experimental: bool = False) -> dict:
        t0 = time.perf_counter()
        n = max(0, min(n, self.prov.total))
        lg = self.log(n)
        self.walk_to(n, lg)
        last = getattr(self, "_last", None)
        eng = last[2] if last and last[0] == n and last[1] == lg.version else self._state(lg, n)
        st = eng.state
        inn = st["innings"][-1] if st["innings"] else None
        rn = I.right_now(st, None, self.base)
        new = set(self.new_at.get(n, []))
        for c in rn["items"]:
            c["new"] = c["key"] in new
        rn["nothing_new"] = not any(c["new"] for c in rn["items"])
        out = {
            "replay": {"label": LABEL, "cursor": n, "has_prev": n > 0, "has_next": n < self.prov.total,
                       "position": (st["last"] or {}).get("label"), "innings": inn["innings"] if inn else None,
                       "ended": st["match_end"] is not None},
            "meta": {**(lg.meta or {}), "result": (st["match_end"] or {}).get("result")},
            "coverage": self.cov,
            "scoreboard": [{"innings": i["innings"], "team": i["batting_team"], "runs": i["runs"], "wickets": i["wickets"],
                            "overs": _ov(i["legal"]), "target": i["target"], "closed": i["closed"], "super_over": i["super_over"],
                            "limit_overs": _ov(i["limit_balls"]) if i["limit_balls"] else None} for i in st["innings"]],
            "now": self._now(st, inn),
            "battle": self._battle(st, inn),
            "right_now": rn,
            "record_watch": I.record_watch(st, self.base, self.cov),
            "timeline": I.timeline(st, self.base),
            "worm": [{"innings": i["innings"], "team": i["batting_team"], "super_over": i["super_over"],
                      "overs": [{"over": o["over"] + 1, "runs": o["runs"], "wickets": o["wickets"]} for o in i["overs"]]} for i in st["innings"]],
            "prediction": self._prediction(st, inn),
            "sdx": self._sdx(inn) if experimental else None,
            "asof": {"baselines_before": self.base["asof"], "note": "Every historical comparison uses only covered matches that started before this one."},
            "state_hash": eng.hash(),
        }
        out["timing_ms"] = round(1000 * (time.perf_counter() - t0), 1)
        return out

    def _now(self, st, inn):
        if not inn:
            pb = st.get("pre_ball")
            return {"status": "Match about to start", "pre_ball": pb}
        pb = st.get("pre_ball") if st.get("pre_ball") and st["pre_ball"]["innings"] == inn["innings"] else None
        s_id = pb["striker"]["id"] if pb else inn["striker"]
        ns_id = pb["non_striker"]["id"] if pb else inn["non_striker"]
        bw_id = pb["bowler"]["id"] if pb else inn["current_bowler"]
        bats = []
        for pid, on in ((s_id, True), (ns_id, False)):
            if not pid:
                continue
            b = inn["batters"].get(pid)
            nm = b["name"] if b else (pb["striker" if on else "non_striker"]["name"] if pb else pid)
            bats.append(self._batter_state(pid, nm, b, on))
        bowler = None
        if bw_id:
            w = inn["bowlers"].get(bw_id)
            nm = w["name"] if w else (pb["bowler"]["name"] if pb else bw_id)
            bowler = self._bowler_state(bw_id, nm, w, inn)
        p = inn["partnership"] if (inn["partnership"] and not _pair_changed(inn["partnership"], s_id, ns_id)) else None
        part = None
        if p:
            a, b2 = sorted([p["a"], p["b"]])
            h = self.base["pairs"].get(f"{a}|{b2}")
            part = {**p, "names": {p["a"]: _bn(inn, p["a"]), p["b"]: _bn(inn, p["b"])},
                    "history": {"stands": h["stands"], "runs": h["runs"], "average": round(h["runs"] / h["stands"], 1), "best": h["best"], "fifties": h["fifties"]}
                    if h and h["stands"] >= 1 else None}
        chase = None
        if inn["target"]:
            need, left = inn["target"] - inn["runs"], (inn["limit_balls"] or 0) - inn["legal"]
            chase = {"target": inn["target"], "runs_required": max(0, need), "balls_remaining": max(0, left),
                     "required_rate": round(6 * need / left, 2) if left > 0 and need > 0 else None,
                     "current_rate": round(6 * inn["runs"] / inn["legal"], 2) if inn["legal"] else None,
                     "target_overs": inn["target_overs"], "reached": inn["target_reached"],
                     "rain_rule": bool((st["meta"] or {}).get("rain_rule")),
                     "note": "Target as recorded by Cricsheet" + (" (final D/L target; when it was set is not recorded)" if (st["meta"] or {}).get("rain_rule") and inn["innings"] == 2 else "")}
        lo = inn["overs"][-1] if inn["overs"] else None
        over_now = {"over": lo["over"] + 1, "bowler": lo["bowler"], "runs": lo["runs"],
                    "balls": [g for g in inn["recent"] if g["label"].split(".")[0] == str(lo["over"])]} if lo else None
        return {"innings": inn["innings"], "batting_team": inn["batting_team"], "bowling_team": inn["bowling_team"], "super_over": inn["super_over"],
                "score": f"{inn['runs']}/{inn['wickets']}", "overs": _ov(inn["legal"]), "run_rate": round(6 * inn["runs"] / inn["legal"], 2) if inn["legal"] else None,
                "phase": I._phase(self.base["format"], inn["legal"]), "batters": bats, "bowler": bowler, "partnership": part, "chase": chase,
                "recent": inn["recent"], "this_over": over_now, "last_ball": st["last"], "closed": inn["closed"], "close_reason": inn["close_reason"],
                "extras": inn["extras"], "fow": inn["fow"],
                "next": {"striker": pb["striker"]["name"], "non_striker": pb["non_striker"]["name"], "bowler": pb["bowler"]["name"]} if pb else None,
                "batting_card": [{"id": pid, **{k: inn["batters"][pid][k] for k in ("name", "runs", "balls", "fours", "sixes", "out", "how")}} for pid in inn["batting_order"]],
                "bowling_card": [{"id": pid, "name": w["name"], "overs": _ov(w["balls"]), "runs": w["runs"], "wickets": w["wickets"], "maidens": w["maidens"],
                                  "dots": w["dots"]} for pid, w in ((p_, inn["bowlers"][p_]) for p_ in inn["bowling_order"])]}

    def _batter_state(self, pid, name, b, on_strike):
        b = b or {"runs": 0, "balls": 0, "fours": 0, "sixes": 0, "dots": 0, "last": [], "out": False}
        stage = B.stage_of(b["balls"])
        hist = self.base["bat"].get(pid, {})
        hs = hist.get("stage", {}).get(stage)
        return {"id": pid, "name": name, "on_strike": on_strike, "runs": b["runs"], "balls": b["balls"],
                "sr": round(100 * b["runs"] / b["balls"], 1) if b["balls"] else None, "fours": b["fours"], "sixes": b["sixes"], "dots": b["dots"],
                "last6": b["last"], "stage": STAGE_NAME[stage], "stage_def": "new = 0–9 balls faced, settling = 10–29, set = 30+",
                "usual_at_stage": {"sr": B.sr(hs), "balls": hs["balls"], "out_every": round(hs["balls"] / hs["outs"], 1) if hs["outs"] else None}
                if hs and hs["balls"] >= 60 else None,
                "career": {"balls": hist.get("all", {}).get("balls"), "sr": B.sr(hist.get("all")), "innings": hist.get("innings", {}).get("innings")}
                if hist else None}

    def _bowler_state(self, pid, name, w, inn):
        ph = I._phase(self.base["format"], inn["legal"])
        hist = self.base["bowl"].get(pid, {})
        hp = hist.get("phase", {}).get(ph)
        if not w:
            return {"id": pid, "name": name, "figures": "0-0-0-0", "spell": None, "usual_in_phase": {"econ": B.econ(hp), "balls": hp["balls"], "phase": ph} if hp and hp["balls"] >= 60 else None}
        sp = w["spell"]
        return {"id": pid, "name": name, "figures": f"{_ov(w['balls'])}-{w['maidens']}-{w['runs']}-{w['wickets']}", "overs": _ov(w["balls"]),
                "runs": w["runs"], "wickets": w["wickets"], "dots": w["dots"], "boundaries": w["fours"] + w["sixes"], "wides": w["wides"], "noballs": w["noballs"],
                "economy": round(6 * w["runs"] / w["balls"], 2) if w["balls"] else None,
                "spell": {**sp, "overs_label": _ov(sp["balls"]), "economy": round(6 * sp["runs"] / sp["balls"], 2) if sp["balls"] else None} if sp else None,
                "usual_in_phase": {"econ": B.econ(hp), "balls": hp["balls"], "phase": ph, "dot_pct": round(100 * hp["dots"] / hp["balls"], 1)}
                if hp and hp["balls"] >= 60 else None,
                "links": {"fingerprint": f"/players/{pid}?tab=bowling", "spell": f"/spell/{self.mid}/{inn['innings']}/{pid}"}}

    def _battle(self, st, inn):
        if not inn:
            return None
        pb = st.get("pre_ball") if st.get("pre_ball") and st["pre_ball"]["innings"] == inn["innings"] else None
        s, bw = (pb["striker"]["id"], pb["bowler"]["id"]) if pb else (inn["striker"], inn["current_bowler"])
        if not s or not bw:
            return None
        h = self.base["battles"].get(f"{s}|{bw}")
        usual = self.base["bat"].get(s, {}).get("all")
        today = (inn.get("matchups") or {}).get(f"{s}|{bw}") or {"balls": 0, "runs": 0, "outs": 0, "dots": 0, "fours": 0, "sixes": 0}
        hist = None
        if h:
            hist = {**h, "sr": round(100 * h["runs"] / h["balls"], 1) if h["balls"] else None,
                    "usual_sr": B.sr(usual), "expected_outs": round(h["balls"] * usual["outs"] / usual["balls"], 1) if usual and usual["balls"] else None,
                    "small_sample": h["balls"] < 60}
        bname = (pb["striker"]["name"] if pb else _bn(inn, s))
        wname = (pb["bowler"]["name"] if pb else inn["bowlers"].get(bw, {}).get("name", bw))
        return {"batter": {"id": s, "name": bname}, "bowler": {"id": bw, "name": wname}, "history": hist, "today": today,
                "history_scope": f"{self.base['format']} {'men' if self.base['gender'] == 'male' else 'women'}, covered matches before {self.base['asof']}",
                "href": f"/battle?bat={s}&bowl={bw}&from=live:{self.mid}:{st['n']}",
                "href_note": "The full battle page shows all covered meetings, including any after this match."}

    def _prediction(self, st, inn):
        if not self.whn or not inn or st["match_end"] or not st.get("pre_ball") or inn["super_over"]:
            return None
        pb = st["pre_ball"]
        if pb["innings"] != inn["innings"] or self.base["format"] not in ("T20", "ODI"):
            return None
        row = self._row(inn, pb)
        probs = self.whn.predict(row)
        cutoff = self.whn.art["training_window"]["to_exclusive"]
        return {"probs": [{"outcome": c, "p": round(p, 4)} for c, p in zip(CLASSES, probs)], "pick": CLASSES[max(range(7), key=lambda j: probs[j])],
                "model": self.whn.art.get("model_version"), "trained_before": cutoff, "in_sample": self.base["asof"] < cutoff,
                "in_sample_note": "This match is inside the model's training window, so these probabilities are in-sample (the model has seen this match)."
                if self.base["asof"] < cutoff else "Out of sample: the model was trained only on matches before this one.",
                "outcome_definition": "Runs off the delivery including extras (5 counts as 4, 7+ as 6). WICKET = any dismissal counting against the batting side.",
                "prov": "MODELLED"}

    def _row(self, inn, pb):
        legal = inn["legal"]
        need, left = (inn["target"] - inn["runs"], (inn["limit_balls"] or 0) - legal) if inn["target"] else (None, None)
        rrr = 6 * need / left if inn["target"] and left and left > 0 else None
        wk = inn["wickets"]
        return {"fmt": self.base["format"], "phase": I._phase(self.base["format"], legal),
                "wk": "0-2" if wk <= 2 else "3-5" if wk <= 5 else "6+",
                "press": "none" if rrr is None else "<8" if rrr < 8 else "8-10" if rrr < 10 else "10-12" if rrr < 12 else "12+",
                "batter_id": pb["striker"]["id"], "bowler_id": pb["bowler"]["id"]}

    def _sdx(self, inn):
        if not self.sdx or not inn or not inn["target"] or inn["super_over"] or not inn["limit_balls"]:
            return None
        fmt, g = self.base["format"], self.base["gender"]
        if not self.sdx.available(fmt, g):
            return None
        series = []
        for legal, runs, wk in inn.get("prog", []):
            sc = self.sdx.score(fmt, g, inn["target"] - runs, inn["limit_balls"] - legal, wk)
            if sc:
                series.append({"legal": legal, "sdx": sc["sdx"]})
        cutoff = self.sdx.a.get("trained_before")
        return {"label": "Situation Difficulty — Experimental", "series": series, "now": series[-1]["sdx"] if series else None,
                "version": self.sdx.a.get("version"), "trained_before": cutoff, "in_sample": bool(cutoff and self.base["asof"] < cutoff),
                "definition": self.sdx.a.get("definition"), "not": "Not pressure, not a win probability.", "prov": "MODELLED"}

    # ------------------------------------------------------------------ Match Ask
    def ask(self, n: int, question: str) -> dict:
        from .ask import match_ask
        n = max(0, min(n, self.prov.total))
        lg = self.log(n)
        st = self._state(lg, n).state
        inn = st["innings"][-1] if st["innings"] else None
        pb = st.get("pre_ball") if st.get("pre_ball") and inn and st["pre_ball"]["innings"] == inn["innings"] else None
        nm = lambda pid: (inn["batters"].get(pid) or {}).get("name") or self.names.get(pid, pid)  # noqa: E731
        ctx = {"date": self.base["asof"], "format": self.base["format"], "gender": self.base["gender"], "match_id": self.mid,
               "batting_team": inn["batting_team"] if inn else None, "bowling_team": inn["bowling_team"] if inn else None,
               "squads": (lg.xi or {}).get("teams")}
        if pb:
            ctx.update(striker=pb["striker"], non_striker=pb["non_striker"], bowler=pb["bowler"])
        elif inn:
            ctx.update(striker={"id": inn["striker"], "name": nm(inn["striker"])} if inn["striker"] else None,
                       non_striker={"id": inn["non_striker"], "name": nm(inn["non_striker"])} if inn["non_striker"] else None,
                       bowler={"id": inn["current_bowler"], "name": inn["bowlers"][inn["current_bowler"]]["name"]} if inn["current_bowler"] else None)
        res = match_ask(self.db, question, ctx, st, self.base)
        res["cursor"] = n
        return res

    # ------------------------------------------------------------------ What Happens Next
    def score_pick(self, n: int, pick: str) -> dict:
        if pick not in CLASSES:
            raise ValueError("bad pick")
        if n >= self.prov.total:
            raise ValueError("no next ball")
        before = self.at(n)
        pred = before["prediction"]
        after = self.at(n + 1)
        lb = after["now"]["last_ball"] if after["now"] and after["now"].get("last_ball") else None
        if not pred or not lb:
            return {"cursor": n + 1, "state": after, "scored": False, "reason": "No model prediction for this ball (super over or non-limited-overs)."}
        actual = "WICKET" if lb["wicket"] else ("DOT" if lb["runs"] == 0 else str(lb["runs"]) if lb["runs"] in (1, 2, 3) else "4" if lb["runs"] in (4, 5) else "6")
        probs = [p["p"] for p in pred["probs"]]
        ai, pi, mi = CLASSES.index(actual), CLASSES.index(pick), CLASSES.index(pred["pick"])
        return {"cursor": n + 1, "state": after, "scored": True, "actual": actual, "pick": pick, "correct": pi == ai,
                "points": scoring.capped_rarity(probs, pi, ai), "model": {"pick": pred["pick"], "correct": mi == ai, "points": scoring.capped_rarity(probs, mi, ai),
                                                                         "p_actual": probs[ai], "in_sample": pred["in_sample"]},
                "probs": pred["probs"]}


def _pair_changed(p, s, ns):
    return bool(s and ns and sorted([p["a"], p["b"]]) != sorted([s, ns]))


def _bn(inn, pid):
    return inn["batters"].get(pid, {}).get("name", pid)


def _ov(balls: int) -> str:
    return f"{balls // 6}.{balls % 6}"


_REPLAYS: dict = {}
_RLOCK = threading.Lock()


def get(db: DB, mid: str, whn=None, sdx=None) -> Replay:
    key = (getattr(db, "stamp", None) or id(db), mid)
    with _RLOCK:
        r = _REPLAYS.get(key)
    if r is None:
        r = Replay(db, mid, whn, sdx)
        with _RLOCK:
            _REPLAYS[key] = r
            if len(_REPLAYS) > 24:
                _REPLAYS.pop(next(iter(_REPLAYS)))
    if sdx is not None and r.sdx is None:
        r.sdx = sdx
    return r


def seek(db: DB, mid: str, cursor: int, to: str) -> int:
    """Server-side navigation. Returns only a cursor number (the count of deliveries); no outcome data."""
    prov = HistoricalCricsheetProvider(db, mid)
    rows = db.q("SELECT innings_no, over FROM live_deliveries WHERE match_id = ? ORDER BY innings_no, seq", [mid])
    n = len(rows)
    if to == "next_over":
        if cursor >= n:
            return n
        k = cursor
        cur = (rows[k]["innings_no"], rows[k]["over"])     # the over the next ball belongs to
        while k < n and (rows[k]["innings_no"], rows[k]["over"]) == cur:
            k += 1
        return k
    if to == "prev_over":
        k = max(0, cursor - 1)
        if k == 0:
            return 0
        cur = (rows[k - 1]["innings_no"], rows[k - 1]["over"])
        while k > 0 and (rows[k - 1]["innings_no"], rows[k - 1]["over"]) == cur:
            k -= 1
        return k
    if to.startswith("innings:"):
        want = int(to.split(":")[1])
        return next((i for i, r in enumerate(rows) if r["innings_no"] == want), n)
    if to == "end":
        return n
    if to == "start":
        return 0
    del prov
    raise ValueError(to)
