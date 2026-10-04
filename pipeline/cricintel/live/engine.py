"""Event log + event-driven match-state engine (Phase 5).

EventLog   accepts events in ARRIVAL order and keeps the canonical, cricket-ordered view: duplicates ignored, deliveries
           ordered by `delivery_order` (not arrival), corrections applied (update / retract / insert-after).
Engine     folds ordered deliveries into state ONE AT A TIME. Nothing here can see a later delivery: `apply` receives a
           single delivery and the state built from the earlier ones. Checkpoints after every over plus a state hash make
           replay deterministic and let a correction recompute from the nearest earlier checkpoint instead of from ball 1.

State is plain JSON-able dicts so it can be hashed, cached, diffed and sent to a client.
"""
from __future__ import annotations

import copy
import hashlib
import json

from .contract import BOWLER_CREDITED, NOT_TEAM_WICKET, Event, delivery_order

VERSION = "live-engine-1.0"
RECENT = 12            # balls kept in the recent sequence
CHECKPOINT_EVERY = 6   # legal balls (one over)


# --------------------------------------------------------------------------------------------------- event log
class EventLog:
    def __init__(self):
        self.seen: dict[str, str] = {}            # event_id -> digest (duplicate detection)
        self.meta: dict | None = None
        self.xi: dict | None = None
        self.innings: dict[int, dict] = {}        # innings -> innings_start payload
        self.revisions: list[dict] = []
        self.deliveries: dict[str, dict] = {}     # event_id -> payload (with 'order')
        self.inserts: dict[str, int] = {}         # anchor event_id -> number of inserts after it
        self.pre_ball: dict | None = None
        self.innings_end: dict[int, dict] = {}
        self.match_end: dict | None = None
        self.anomalies: list[str] = []
        self.version = 0                          # bumps on every change; engines use it to know they are stale

    def add(self, ev: Event) -> bool:
        d = ev.digest()
        if ev.event_id in self.seen:
            if self.seen[ev.event_id] != d:
                self.anomalies.append(f"conflicting duplicate {ev.event_id}: kept the first version")
            return False
        self.seen[ev.event_id] = d
        p = ev.payload
        k = ev.kind
        if k == "match_meta":
            self.meta = dict(p)
        elif k == "playing_xi":
            self.xi = dict(p)
        elif k == "innings_start":
            self.innings[p["innings"]] = dict(p)
        elif k == "target_revision":
            self.revisions.append(dict(p))
        elif k == "pre_ball":
            self.pre_ball = dict(p)
        elif k == "delivery":
            self.deliveries[ev.event_id] = {**p, "event_id": ev.event_id, "order": delivery_order(p)}
            if self.pre_ball and self.pre_ball.get("innings") == p["innings"]:
                self.pre_ball = None  # the ball it announced has now been bowled
        elif k == "correction":
            self._correct(ev)
        elif k == "innings_end":
            self.innings_end[p["innings"]] = dict(p)
        elif k == "match_end":
            self.match_end = dict(p)
        self.version += 1
        return True

    def _correct(self, ev: Event):
        p, tid = ev.payload, ev.payload["target_event_id"]
        if p["op"] == "retract":
            if self.deliveries.pop(tid, None) is None:
                self.anomalies.append(f"retract of unknown delivery {tid}")
        elif p["op"] == "update":
            old = self.deliveries.get(tid)
            if old is None:
                self.anomalies.append(f"update of unknown delivery {tid}")
                return
            new = {**old, **p["delivery"]}
            new["order"] = old["order"]          # a correction changes what happened, not where it sits
            self.deliveries[tid] = new
        elif p["op"] == "insert":
            anchor = self.deliveries.get(tid)
            if anchor is None:
                self.anomalies.append(f"insert after unknown delivery {tid}")
                return
            n = self.inserts.get(tid, 0) + 1
            self.inserts[tid] = n
            nid = p["new_event_id"]
            self.deliveries[nid] = {**p["delivery"], "event_id": nid, "order": anchor["order"] + (n,)}
        else:
            raise ValueError(f"unknown correction op {p['op']}")

    def ordered(self) -> list[dict]:
        return sorted(self.deliveries.values(), key=lambda d: d["order"])


# --------------------------------------------------------------------------------------------------- engine
def _glyph(d: dict, wicket: bool) -> dict:
    r = d["runs"]
    tot = sum(r.get(k, 0) for k in ("batter", "wides", "noballs", "byes", "legbyes", "penalty"))
    if wicket:
        g = "W"
    elif r.get("wides"):
        g = f"{tot}wd" if tot > 1 else "wd"
    elif r.get("noballs"):
        g = f"{tot}nb" if tot > 1 else "nb"
    elif r.get("byes") or r.get("legbyes"):
        g = f"{tot}{'b' if r.get('byes') else 'lb'}"
    else:
        g = str(tot) if tot else "•"
    return {"g": g, "runs": tot, "boundary": d.get("boundary"), "wicket": wicket, "label": d["label"], "event_id": d["event_id"]}


def new_innings(start: dict, meta: dict | None) -> dict:
    sched = (meta or {}).get("scheduled_overs")
    if start.get("super_over"):
        limit = 6
    elif start.get("target_overs"):
        limit = int(round(float(start["target_overs"]) * 6))
    else:
        limit = int(sched * 6) if sched else None
    return {
        "innings": start["innings"], "batting_team": start["batting_team"], "bowling_team": start["bowling_team"],
        "super_over": bool(start.get("super_over")), "target": start.get("target_runs"), "target_overs": start.get("target_overs"),
        "limit_balls": limit, "max_wickets": 2 if start.get("super_over") else 10,
        "runs": int(start.get("penalty_runs") or 0), "wickets": 0, "legal": 0, "n": 0,
        "extras": {"wides": 0, "noballs": 0, "byes": 0, "legbyes": 0, "penalty": int(start.get("penalty_runs") or 0)},
        "batters": {}, "batting_order": [], "bowlers": {}, "bowling_order": [], "current_bowler": None,
        "partnership": None, "partnerships": [], "fow": [], "recent": [], "overs": [],
        "striker": None, "non_striker": None, "dot_streak": 0, "balls_since_boundary": 0,
        "events": [], "closed": False, "close_reason": None, "target_reached": False,
    }


def _batter(inn: dict, pid: str, name: str) -> dict:
    b = inn["batters"].get(pid)
    if b is None:
        b = {"id": pid, "name": name, "runs": 0, "balls": 0, "fours": 0, "sixes": 0, "dots": 0, "out": False, "how": None,
             "position": len(inn["batting_order"]) + 1, "arrived": {"score": inn["runs"], "wickets": inn["wickets"], "legal": inn["legal"]},
             "last": []}
        inn["batters"][pid] = b
        inn["batting_order"].append(pid)
    elif b["out"] and b["how"] in NOT_TEAM_WICKET:   # a retired batter returning
        b["out"], b["how"] = False, None
    return b


def _bowler(inn: dict, pid: str, name: str, over: int) -> dict:
    w = inn["bowlers"].get(pid)
    if w is None:
        w = {"id": pid, "name": name, "balls": 0, "runs": 0, "wickets": 0, "dots": 0, "fours": 0, "sixes": 0, "wides": 0, "noballs": 0,
             "maidens": 0, "overs": {}, "spell": None, "spells": 0, "last_over": None}
        inn["bowlers"][pid] = w
        inn["bowling_order"].append(pid)
    if w["last_over"] != over:
        # A spell = overs with at most one over between them (bowling alternate overs from one end).
        if w["spell"] is None or w["last_over"] is None or over - w["last_over"] > 2:
            w["spells"] += 1
            w["spell"] = {"number": w["spells"], "start_over": over, "overs": 0, "balls": 0, "runs": 0, "wickets": 0, "dots": 0, "boundaries": 0}
        w["spell"]["overs"] += 1
        w["overs"][str(over)] = {"runs": 0, "legal": 0, "wickets": 0}
        w["last_over"] = over
    return w


class Engine:
    """Sequential fold. `apply` takes one delivery; it has no access to any other delivery."""

    def __init__(self, meta: dict | None = None):
        self.state = {"meta": meta, "innings": [], "n": 0, "last": None, "pre_ball": None, "match_end": None}
        self.checkpoints: dict[int, dict] = {0: copy.deepcopy(self.state)}

    # -- structure
    def start_innings(self, start: dict):
        if self.state["innings"] and not self.state["innings"][-1]["closed"]:
            self.close_innings(self.state["innings"][-1]["innings"], "next innings started")
        self.state["innings"].append(new_innings(start, self.state["meta"]))

    def close_innings(self, n: int, reason: str):
        for inn in self.state["innings"]:
            if inn["innings"] == n and not inn["closed"]:
                inn["closed"], inn["close_reason"] = True, reason
                if inn["partnership"]:
                    inn["partnerships"].append(inn["partnership"])
                inn["events"].append({"kind": "innings_end", "text": f"{inn['batting_team']} {inn['runs']}/{inn['wickets']} ({_ov(inn['legal'])} ov) · {reason}",
                                      "n": self.state["n"], "legal": inn["legal"] + 1})

    def revise_target(self, rev: dict):
        for inn in self.state["innings"]:
            if inn["innings"] == rev["innings"]:
                inn["target"], inn["target_overs"] = rev["target_runs"], rev["target_overs"]
                if rev.get("target_overs"):
                    inn["limit_balls"] = int(round(float(rev["target_overs"]) * 6))
                inn["events"].append({"kind": "target_revision", "text": f"Target revised to {rev['target_runs']} from {rev['target_overs']} overs",
                                      "n": self.state["n"], "legal": inn["legal"]})

    # -- the fold
    def apply(self, d: dict):
        st = self.state
        inn = st["innings"][-1] if st["innings"] else None
        if inn is None or inn["innings"] != d["innings"]:
            raise ValueError(f"delivery {d['event_id']} for innings {d['innings']} before that innings started")
        r = d["runs"]
        rb, wd, nb, by, lb, pen = (r.get(k, 0) for k in ("batter", "wides", "noballs", "byes", "legbyes", "penalty"))
        total = rb + wd + nb + by + lb + pen
        legal = not wd and not nb
        faced = not wd
        st["n"] += 1
        inn["n"] += 1
        if inn.get("cur_over") != d["over"]:
            inn["cur_over"], inn["over_legal"] = d["over"], 0
        label = f"{d['over']}.{inn['over_legal'] + 1}"   # an illegal ball carries the number of the ball still to come
        inn["over_legal"] += 1 if legal else 0
        d = {**d, "label": label}

        bat = _batter(inn, d["batter"]["id"], d["batter"]["name"])
        _batter(inn, d["non_striker"]["id"], d["non_striker"]["name"])
        bowl = _bowler(inn, d["bowler"]["id"], d["bowler"]["name"], d["over"])
        inn["current_bowler"] = bowl["id"]
        pair = sorted([d["batter"]["id"], d["non_striker"]["id"]])
        p = inn["partnership"]
        if p is None or sorted([p["a"], p["b"]]) != pair:
            if p is not None:
                inn["partnerships"].append(p)
            a, b = pair
            p = inn["partnership"] = {"a": a, "b": b, "wicket": inn["wickets"] + 1, "runs": 0, "balls": 0, "runs_a": 0, "runs_b": 0,
                                      "balls_a": 0, "balls_b": 0, "extras": 0, "boundary_runs": 0, "start": {"score": inn["runs"], "wickets": inn["wickets"], "legal": inn["legal"]}}

        # team
        inn["runs"] += total
        inn["legal"] += 1 if legal else 0
        for k, v in (("wides", wd), ("noballs", nb), ("byes", by), ("legbyes", lb), ("penalty", pen)):
            inn["extras"][k] += v
        four, six = d.get("boundary") == 4, d.get("boundary") == 6
        inn["dot_streak"] = inn["dot_streak"] + 1 if (legal and total == 0) else 0
        inn["balls_since_boundary"] = 0 if (four or six) else inn["balls_since_boundary"] + (1 if legal else 0)

        # batter
        if faced:
            bat["balls"] += 1
            bat["dots"] += 1 if rb == 0 else 0
            bat["last"] = (bat["last"] + [rb])[-6:]
        bat["runs"] += rb
        bat["fours"] += 1 if four else 0
        bat["sixes"] += 1 if six else 0

        # bowler (byes/leg-byes/penalties are not charged to the bowler)
        conceded = rb + wd + nb
        bowl["runs"] += conceded
        bowl["balls"] += 1 if legal else 0
        bowl["wides"] += 1 if wd else 0
        bowl["noballs"] += 1 if nb else 0
        bowl["dots"] += 1 if (legal and conceded == 0) else 0
        bowl["fours"] += 1 if four else 0
        bowl["sixes"] += 1 if six else 0
        ov = bowl["overs"][str(d["over"])]
        ov["runs"] += conceded
        ov["legal"] += 1 if legal else 0
        sp = bowl["spell"]
        sp["balls"] += 1 if legal else 0
        sp["runs"] += conceded
        sp["dots"] += 1 if (legal and conceded == 0) else 0
        sp["boundaries"] += 1 if (four or six) else 0

        # this striker v this bowler, within this innings
        bb = inn.setdefault("matchups", {}).setdefault(f"{bat['id']}|{bowl['id']}", {"balls": 0, "runs": 0, "outs": 0, "dots": 0, "fours": 0, "sixes": 0})
        bb["balls"] += 1 if faced else 0
        bb["runs"] += rb
        bb["dots"] += 1 if (faced and rb == 0) else 0
        bb["fours"] += 1 if four else 0
        bb["sixes"] += 1 if six else 0
        bb["outs"] += sum(1 for w in d.get("wickets", []) if w["kind"] in BOWLER_CREDITED and w["player_out"]["id"] == bat["id"])

        # partnership
        p["runs"] += total
        p["balls"] += 1 if legal else 0
        side = "a" if d["batter"]["id"] == p["a"] else "b"
        p[f"runs_{side}"] += rb
        p[f"balls_{side}"] += 1 if faced else 0
        p["extras"] += total - rb
        p["boundary_runs"] += rb if (four or six) else 0

        # wickets
        team_w = False
        for w in d.get("wickets", []):
            out = inn["batters"].get(w["player_out"]["id"]) or _batter(inn, w["player_out"]["id"], w["player_out"]["name"])
            out["out"], out["how"] = True, w["kind"]
            out["dismissal"] = {"kind": w["kind"], "bowler": d["bowler"]["name"] if w["kind"] in BOWLER_CREDITED else None,
                                "fielders": w.get("fielders", []), "event_id": d["event_id"], "label": label}
            if w["kind"] in NOT_TEAM_WICKET:
                inn["events"].append({"kind": "retired", "text": f"{out['name']} {w['kind']} on {out['runs']} ({out['balls']})",
                                      "event_id": d["event_id"], "label": label, "n": st["n"], "legal": inn["legal"]})
                continue
            team_w = True
            inn["wickets"] += 1
            if w["kind"] in BOWLER_CREDITED:
                bowl["wickets"] += 1
                ov["wickets"] += 1
                sp["wickets"] += 1
            inn["fow"].append({"wicket": inn["wickets"], "score": inn["runs"], "legal": inn["legal"], "label": label,
                               "player": out["name"], "pid": out["id"], "runs": out["runs"], "balls": out["balls"], "kind": w["kind"],
                               "event_id": d["event_id"]})
        if ov["legal"] == 6 and ov["runs"] == 0 and str(d["over"]) in bowl["overs"]:
            bowl["maidens"] += 1

        # over summary + recent
        if not inn["overs"] or inn["overs"][-1]["over"] != d["over"]:
            inn["overs"].append({"over": d["over"], "runs": 0, "wickets": 0, "bowler": bowl["name"]})
        inn["overs"][-1]["runs"] += total
        inn["overs"][-1]["wickets"] += 1 if team_w else 0
        inn["recent"] = (inn["recent"] + [_glyph(d, team_w)])[-RECENT:]
        inn.setdefault("prog", []).append([inn["legal"], inn["runs"], inn["wickets"]])

        # factual landmarks crossed on this ball (each recorded once, when it happens)
        ms = inn.setdefault("milestones", [])
        def mark(kind, text):
            ms.append({"kind": kind, "text": text, "label": label, "event_id": d["event_id"], "legal": inn["legal"], "n": st["n"]})
        for m_ in (50, 100, 150, 200):
            if bat["runs"] - rb < m_ <= bat["runs"]:
                mark("milestone", f"{bat['name']} reached {m_} off {bat['balls']} balls")
        for m_ in (50, 100, 150, 200, 250):
            if p["runs"] - total < m_ <= p["runs"]:
                mark("partnership", f"{_nm(inn, p['a'])} and {_nm(inn, p['b'])}: {m_} partnership off {p['balls']} balls")
        if (inn["runs"] - total) // 50 < inn["runs"] // 50 and inn["runs"] >= 50:
            mark("team", f"{inn['batting_team']} {inn['runs'] // 50 * 50} up in {_ov(inn['legal'])} overs")
        if team_w and bowl["wickets"] >= 3 and any(w["kind"] in BOWLER_CREDITED for w in d.get("wickets", [])):
            mark("bowler", f"{bowl['name']} now has {bowl['wickets']} wickets ({bowl['wickets']}/{bowl['runs']})")
        if inn["dot_streak"] > inn.get("max_dot_streak", 0):
            inn["max_dot_streak"], inn["max_dot_streak_at"] = inn["dot_streak"], inn["legal"]

        # who is at the crease now (DERIVED from this ball; the next pre_ball event confirms who faces)
        at_crease = [x for x in (d["batter"]["id"], d["non_striker"]["id"]) if not inn["batters"][x]["out"]]
        inn["striker"], inn["non_striker"] = (at_crease + [None, None])[:2]
        if inn["target"] is not None and inn["runs"] >= inn["target"]:
            inn["target_reached"] = True

        st["last"] = {"event_id": d["event_id"], "label": label, "innings": inn["innings"], "runs": total, "batter_runs": rb,
                      "boundary": d.get("boundary"), "wicket": team_w, "extras": {k: v for k, v in (("wides", wd), ("noballs", nb), ("byes", by), ("legbyes", lb), ("penalty", pen)) if v},
                      "batter": d["batter"], "bowler": d["bowler"], "non_striker": d["non_striker"],
                      "dismissals": [w for w in d.get("wickets", [])]}
        enr = d.get("enrichment") or {}
        if enr:                                    # optional richer layers: carried, never used for scoring
            st["last"]["enrichment"] = enr
            inn["recent"][-1]["layers"] = sorted(enr)
            caps = st.setdefault("capabilities", {})
            for layer in enr:
                caps[layer] = caps.get(layer, 0) + 1
        st["pre_ball"] = None
        if legal and inn["legal"] % CHECKPOINT_EVERY == 0:
            self.checkpoints[st["n"]] = copy.deepcopy(st)

    def set_pre_ball(self, pb: dict | None):
        self.state["pre_ball"] = dict(pb) if pb else None

    def end_match(self, me: dict):
        self.state["match_end"] = dict(me)

    def hash(self) -> str:
        return state_hash(self.state)


def state_hash(state: dict) -> str:
    return hashlib.sha256(json.dumps(state, sort_keys=True, default=str).encode()).hexdigest()[:20]


def _nm(inn: dict, pid: str) -> str:
    return inn["batters"].get(pid, {}).get("name", pid)


def _ov(legal: int) -> str:
    return f"{legal // 6}.{legal % 6}"


# --------------------------------------------------------------------------------------------------- replay
def _sig(d: dict) -> str:
    return hashlib.sha256(json.dumps({k: v for k, v in d.items() if k != "order"}, sort_keys=True, default=str).encode()).hexdigest()[:16]


def replay(log: EventLog, upto: int | None = None, base: tuple[int, dict, dict] | None = None) -> Engine:
    """Deterministic state from an event log: the same ordered log gives the same state and hash, whatever the arrival order.

    upto  truncate to the first `upto` deliveries in cricket order. An innings appears once its innings_start is in the
          log and every earlier innings is complete within the cut (the innings break).
    base  (n, state, checkpoints): resume from a checkpoint taken after n deliveries instead of from ball 1.
    """
    eng = Engine(log.meta)
    start_n = 0
    if base is not None:
        start_n, st, cps = base
        eng.state = copy.deepcopy(st)
        eng.checkpoints = {k: v for k, v in cps.items() if k <= start_n}
        eng.state["pre_ball"], eng.state["match_end"] = None, None
    ordered = log.ordered()
    cut = ordered if upto is None else ordered[:upto]
    truncated = len(cut) < len(ordered)
    revs: dict = {}
    for r in log.revisions:
        revs.setdefault(r.get("after_event_id"), []).append(r)
    pos = {d["event_id"]: i for i, d in enumerate(cut)}
    for k in sorted(set(log.innings) | {d["innings"] for d in cut}):
        dels = [d for d in cut if d["innings"] == k]
        full = [d for d in ordered if d["innings"] == k]
        have = next((x for x in eng.state["innings"] if x["innings"] == k), None)
        if have is None:
            if k not in log.innings:
                eng.state.setdefault("anomalies", []).append(f"deliveries for innings {k} arrived before its innings_start")
            eng.start_innings(log.innings.get(k) or {"innings": k, "batting_team": "?", "bowling_team": "?"})
            for r in revs.get(None, []):
                if r["innings"] == k:
                    eng.revise_target(r)
        for d in dels:
            if pos[d["event_id"]] < start_n:
                continue
            eng.apply(d)
            for r in revs.get(d["event_id"], []):
                eng.revise_target(r)
        if len(dels) < len(full) or (truncated and k not in log.innings_end):
            break                       # this innings is still in progress at the cursor
        if k in log.innings_end:
            if not (have and have["closed"]):
                eng.close_innings(k, log.innings_end[k]["reason"])
        else:
            break                       # no innings_end yet: later innings cannot have started
    if not truncated:
        if log.pre_ball:
            eng.set_pre_ball(log.pre_ball)
        if log.match_end:
            eng.end_match(log.match_end)
    else:
        # What a live feed would announce before the next ball: identities only, never its outcome.
        nx = ordered[len(cut)]
        if any(i["innings"] == nx["innings"] for i in eng.state["innings"]):
            eng.set_pre_ball({"innings": nx["innings"], "striker": nx["batter"], "non_striker": nx["non_striker"], "bowler": nx["bowler"]})
    eng.sigs = [_sig(d) for d in cut]
    return eng


def recompute(log: EventLog, prev: Engine) -> tuple[Engine, int]:
    """Bring a previous engine up to date with a changed log (new balls, corrections, retractions, inserts).

    Finds the first ordered position whose delivery differs from what `prev` applied, restores the latest checkpoint at or
    before it and replays only from there. Returns (engine, deliveries re-applied). Must equal replay(log): tested.
    """
    new = [_sig(d) for d in log.ordered()]
    old = getattr(prev, "sigs", [])
    first = next((i for i, (a, b) in enumerate(zip(old, new)) if a != b), min(len(old), len(new)))
    if prev.state["meta"] != log.meta:
        first = 0
    n = max((c for c in prev.checkpoints if c <= first), default=0)
    if n == 0:
        eng = replay(log)
    else:
        eng = replay(log, base=(n, prev.checkpoints[n], prev.checkpoints))
    return eng, len(new) - n
