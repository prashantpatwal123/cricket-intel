"""Match Ask: Ask with the replay's context (Phase 5).

Context words resolve deterministically from the state at the cursor:
  this batter / the batter / the striker       → the batter on strike for the next ball
  the non-striker / the other batter           → the non-striker
  this bowler / the bowler                     → the bowler of the next ball
  this pair / these two / this partnership     → striker and non-striker
  this team / them                             → the team the named player is playing AGAINST (else the bowling side)
  this match / today                           → the replay so far (answered from the engine state, never the full match)
Every historical answer is restricted to covered matches that started BEFORE this match (filter `before_date`), so asking
mid-replay can never reveal what happened later. The resolved context is shown as chips.
"""
from __future__ import annotations

import re

from ..ask import v1 as ASK1
from ..db import DB


def _sub(q: str, pat: str, val: str, used: list, label: str) -> str:
    if re.search(pat, q, re.I):
        used.append({"key": f"ctx.{label}", "label": f"{label} → {val}", "removable": False})
        return re.sub(pat, val, q, flags=re.I)
    return q


def match_ask(db: DB, question: str, ctx: dict, state: dict | None = None, base: dict | None = None) -> dict:
    q = question.strip()
    chips: list = []
    s, ns, bw = ctx.get("striker"), ctx.get("non_striker"), ctx.get("bowler")
    if bw:
        q = _sub(q, r"\b(this|the|current) bowler\b", bw["name"], chips, "this bowler")
    if s and ns:
        q = _sub(q, r"\b(this|the current) (pair|partnership)\b|\bthese two\b", f"{s['name']} and {ns['name']}", chips, "this pair")
    if ns:
        q = _sub(q, r"\b(the|this) non-?striker\b|\bthe other batter\b", ns["name"], chips, "the non-striker")
    if s:
        q = _sub(q, r"\b(this|the|current) (batter|batsman|striker)\b", s["name"], chips, "this batter")
    if re.search(r"\bthis (team|side)\b|\bagainst them\b", q, re.I):
        team = _opponent_of_named(q, ctx)
        q = re.sub(r"\bthis (team|side)\b|\bthem\b", team, q, flags=re.I)
        chips.append({"key": "ctx.team", "label": f"this team → {team}", "removable": False})
    before = ctx["date"]
    chips.append({"key": "ctx.before", "label": f"only matches before this one ({before})", "removable": False})
    low = q.lower()
    out = {"question": question, "resolved_question": q, "context_chips": chips, "before_date": before,
           "generated_by": "deterministic parser + shared analytics engines (no language model)"}

    if re.search(r"\bthis (match|game)\b|\btoday\b", low):
        return {**out, **_this_match(low, ctx, state)}
    if re.search(r"partnership compare|compare (this|the) partnership|how does .* partnership compare|how do .* and .* compare", low) or \
            (re.search(r"\bcompare\b", low) and "partnership" in question.lower()):
        return {**out, **_pair(ctx, state, base, compare=True)}
    if re.search(r"(batted|batting) together before|\bbefore together\b|have .* batted together", low):
        return {**out, **_pair(ctx, state, base, compare=False)}
    m = re.search(r"(?:faced|after|has had|reached) (\d+) balls", low)
    if m and re.search(r"usually|typically|what happens|normally", low):
        who = _named(db, q) or s
        return {**out, **_after_n(db, who, int(m.group(1)), ctx)}

    it = ASK1.parse(db, q)
    it.filters["before_date"] = before
    supported = ASK1.V3_SUPPORTED.get(it.kind, None)
    if "format" not in it.filters and ctx.get("format") in ("T20", "ODI") and (supported is None or "format" in supported):
        it.filters["format"] = ctx["format"]
    if not it.gender:
        it.gender = ctx.get("gender")
    res = ASK1.execute(db, it)
    res["interpretation"] = chips + [c for c in res.get("interpretation", []) if c.get("key") != "filters.before_date"]
    return {**out, **res}


def _named(db: DB, q: str):
    it = ASK1.parse(db, q)
    return {"id": it.subject["person_id"], "name": it.subject["name"]} if it.subject else None


def _opponent_of_named(q: str, ctx: dict) -> str:
    squads = ctx.get("squads") or {}
    for team, members in squads.items():
        for m in members:
            if m["name"].lower() in q.lower() or m["name"].split()[-1].lower() in q.lower():
                others = [t for t in squads if t != team]
                if others:
                    return others[0]
    return ctx.get("bowling_team") or ""


def _pair(ctx, state, base, compare: bool) -> dict:
    s, ns = ctx.get("striker"), ctx.get("non_striker")
    if not (s and ns and base):
        return {"status": "needs_clarification", "message": "There is no partnership at the crease at this point of the replay."}
    a, b = sorted([s["id"], ns["id"]])
    h = base["pairs"].get(f"{a}|{b}")
    inn = state["innings"][-1] if state and state["innings"] else None
    p = inn["partnership"] if inn else None
    today = f" Today: {p['runs']} off {p['balls']} so far." if p and sorted([p["a"], p["b"]]) == [a, b] else ""
    if not h:
        return {"status": "ok", "answer": f"No covered stands for {s['name']} and {ns['name']} in {base['format']} before this match.{today}",
                "numbers": [], "items": []}
    avg = round(h["runs"] / h["stands"], 1)
    rr = round(6 * h["runs"] / h["balls"], 2) if h["balls"] else None
    ans = (f"{s['name']} and {ns['name']} had batted together {h['stands']} times in covered {base['format']} matches before this one: "
           f"{h['runs']} runs, average {avg}, best {h['best']}, {h['fifties']} fifty-plus stands, {rr} an over.{today}")
    if compare and p:
        where = "above" if p["runs"] > avg else "below"
        ans += f" This stand is {where} their average" + (" and is their highest" if p["runs"] > (h["best"] or 0) else "") + "."
    return {"status": "ok", "answer": ans, "numbers": [{"label": "stands", "value": h["stands"]}, {"label": "average", "value": avg},
                                                       {"label": "best", "value": h["best"]}],
            "link": {"href": f"/partnerships?p1={a}&p2={b}&format={base['format']}"}, "caveat": "Observed outcomes only; not a measure of how well they bat together."}


def _after_n(db: DB, who, n: int, ctx) -> dict:
    if not who:
        return {"status": "needs_clarification", "message": "Which batter? Name one or ask about 'this batter'."}
    fmt, g, d = ctx["format"], ctx["gender"], ctx["date"]
    inns = db.q1("""SELECT count(*) AS reached, avg(runs) AS avg_final, count(*) FILTER (WHERE runs >= 50) AS fifty,
                           count(*) FILTER (WHERE NOT not_out) AS dismissed
                    FROM bat_innings WHERE batter_id = ? AND format_group = ? AND gender = ? AND start_date < ?::DATE AND balls >= ?""",
                 [who["id"], fmt, g, d, n])
    after = db.q1("""SELECT count(*) FILTER (WHERE b.faced) AS balls, sum(b.runs_batter) AS runs, count(x.delivery_id) AS outs
                     FROM balls b LEFT JOIN dis x ON x.delivery_id = b.delivery_id AND x.player_out_id = b.batter_id
                     WHERE b.batter_id = ? AND b.format_group = ? AND b.gender = ? AND b.start_date < ?::DATE AND b.batter_balls_before >= ?""",
                  [who["id"], fmt, g, d, n])
    before = db.q1("""SELECT count(*) FILTER (WHERE b.faced) AS balls, sum(b.runs_batter) AS runs FROM balls b
                      WHERE b.batter_id = ? AND b.format_group = ? AND b.gender = ? AND b.start_date < ?::DATE AND b.batter_balls_before < ?""",
                   [who["id"], fmt, g, d, n])
    if not inns["reached"]:
        return {"status": "ok", "answer": f"{who['name']} had not faced {n} balls in a covered {fmt} innings before this match.", "numbers": []}
    sr_after = round(100 * (after["runs"] or 0) / after["balls"], 1) if after["balls"] else None
    sr_before = round(100 * (before["runs"] or 0) / before["balls"], 1) if before["balls"] else None
    ans = (f"Before this match, {who['name']} faced {n}+ balls in {inns['reached']} covered {fmt} innings. From ball {n + 1} on they scored at a strike rate of "
           f"{sr_after} (v {sr_before} up to ball {n}); those innings averaged {round(inns['avg_final'], 1)} and {inns['fifty']} reached 50.")
    return {"status": "ok", "answer": ans, "numbers": [{"label": "innings", "value": inns["reached"]}, {"label": f"SR after ball {n}", "value": sr_after},
                                                       {"label": f"SR up to ball {n}", "value": sr_before}, {"label": "reached 50", "value": inns["fifty"]}],
            "interpretation": [{"key": "kind", "label": f"After {n} balls", "removable": False}, {"key": "subject", "label": who["name"], "removable": False},
                               {"key": "fmt", "label": fmt, "removable": False}],
            "link": {"href": f"/players/{who['id']}?tab=states"}, "caveat": f"Sample: {after['balls']} balls after ball {n}. Observed outcomes; not a forecast."}


def _this_match(low: str, ctx, state) -> dict:
    """Questions about 'this match' are answered from the replay state at the cursor, never from the finished scorecard."""
    if not state or not state["innings"]:
        return {"status": "ok", "answer": "The match has not started at this point of the replay.", "numbers": []}
    inn = state["innings"][-1]
    s = ctx.get("striker")
    if s and s["id"] in inn["batters"]:
        b = inn["batters"][s["id"]]
        bnd = f"{b['fours']} fours and {b['sixes']} sixes"
        return {"status": "ok", "answer": f"So far in this match (replay at {inn['legal'] // 6}.{inn['legal'] % 6} overs): {b['name']} {b['runs']} off {b['balls']}, {bnd}; "
                                          f"{inn['batting_team']} {inn['runs']}/{inn['wickets']}.", "numbers": [],
                "caveat": "Answered from the replay up to this ball only."}
    return {"status": "ok", "answer": f"So far: {inn['batting_team']} {inn['runs']}/{inn['wickets']} after {inn['legal'] // 6}.{inn['legal'] % 6} overs.", "numbers": []}
