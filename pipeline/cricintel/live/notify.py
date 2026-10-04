"""Notification architecture: DESIGN ONLY (Phase 5). Nothing here sends anything; there is no external integration.

`plan()` replays a match and returns the notifications a user WOULD receive under the rules below, so volume and
behaviour can be measured and tested before any delivery channel exists.

Event types (user opts in per type; default off except wicket and milestone):
  wicket            a team wicket
  milestone         batter 50/100/150/200, bowler 5 wickets
  battle_begins     a striker–bowler pairing begins whose covered history is unusual (Right Now 'battle' candidate qualifies)
  unusual_event     a statistically defined sequence: dot run / big over at or above the 99th percentile, wicket burst
  record_approach   a covered-data record (not an official record) comes within reach (Record Watch, kind 'record')
Rules:
  dedupe            each (type, key) is sent at most once per match
  priority          wicket > milestone > record_approach > unusual_event > battle_begins
  coalesce          several candidates on one ball → one notification (the highest priority; others listed inside it)
  per-over cap      at most 1 notification per over (6 legal balls) except wickets
  innings budget    at most 8 non-wicket notifications per innings; once spent, only wickets are sent
  quiet window      after any non-wicket notification, lower-priority types wait 12 legal balls
  no ball-by-ball   a delivery with no qualifying candidate produces nothing
"""
from __future__ import annotations

from . import insights as I

PRIORITY = {"wicket": 0, "milestone": 1, "record_approach": 2, "unusual_event": 3, "battle_begins": 4}
DEFAULT_OPT_IN = {"wicket", "milestone"}
PER_INNINGS = 8
QUIET_BALLS = 12


def candidates_at(prev: dict | None, st: dict, base: dict) -> list[dict]:
    inn = st["innings"][-1] if st["innings"] else None
    if not inn or not st.get("last") or st["last"]["innings"] != inn["innings"]:
        return []                                   # innings break: the last ball belongs to the previous innings
    out = []
    last = st["last"]
    if last["wicket"]:
        f = inn["fow"][-1]
        out.append({"type": "wicket", "key": f"w|{inn['innings']}|{f['wicket']}", "text": f"WICKET: {f['player']} {f['runs']} ({f['balls']}). {inn['batting_team']} {f['score']}/{f['wicket']}"})
    for m in inn.get("milestones", []):
        if m["event_id"] == last["event_id"] and m["kind"] == "milestone":
            out.append({"type": "milestone", "key": f"m|{m['text']}", "text": m["text"]})
    for w in inn["bowlers"].values():
        if w["wickets"] == 5 and last["bowler"]["id"] == w["id"] and last["wicket"]:
            out.append({"type": "milestone", "key": f"5w|{w['id']}", "text": f"{w['name']} takes five wickets"})
    for c in I.select(I.candidates(st, base)):
        if c["type"] in ("dot_sequence", "big_over", "wicket_burst"):
            out.append({"type": "unusual_event", "key": c["key"], "text": c["text"]})
        elif c["type"] == "battle":
            out.append({"type": "battle_begins", "key": c["key"], "text": c["text"]})
    for r in I.record_watch(st, base, None):
        if r["kind"] == "record":
            out.append({"type": "record_approach", "key": r["key"], "text": f"{r['text']} ({r['note']})"})
    return out


def plan(states: list[dict], base: dict, opt_in: set[str] | None = None) -> list[dict]:
    """states: engine states after balls 1..N in order. Returns the notifications that would be sent."""
    opt = DEFAULT_OPT_IN if opt_in is None else opt_in
    sent, keys, spent, quiet_until, last_over = [], set(), {}, {}, {}
    prev = None
    for n, st in enumerate(states, start=1):
        inn = st["innings"][-1] if st["innings"] else None
        if not inn:
            continue
        k = inn["innings"]
        cands = [c for c in candidates_at(prev, st, base) if c["type"] in opt and c["key"] not in keys]
        prev = st
        if not cands:
            continue
        for c in cands:
            keys.add(c["key"])                      # dedupe even if this one is suppressed below
        cands.sort(key=lambda c: PRIORITY[c["type"]])
        top = cands[0]
        legal = inn["legal"]
        if top["type"] != "wicket":
            if spent.get(k, 0) >= PER_INNINGS:
                continue
            if legal < quiet_until.get(k, -1) and PRIORITY[top["type"]] > 1:
                continue
            if last_over.get(k) == legal // 6:
                continue
            quiet_until[k] = legal + QUIET_BALLS
        last_over[k] = legal // 6
        if top["type"] != "wicket":
            spent[k] = spent.get(k, 0) + 1          # wickets always send and never use up the budget
        sent.append({"n": n, "innings": k, "label": st["last"]["label"], **top, "also": [c["text"] for c in cands[1:]]})
    return sent
