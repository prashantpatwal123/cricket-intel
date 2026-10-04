"""'Right Now' intelligence, Record Watch and the factual timeline for a replay state (Phase 5).

Deterministic. Inputs: the engine state AT the cursor, the state one ball earlier, and as-of baselines (matches before
this one). Nothing reads later deliveries.

Each candidate insight carries transparent dimension scores in [0, 1]:
  relevance       how directly it concerns what is happening now (current striker v current bowler = 1)
  sample          evidence size relative to what the type needs (hard minimum: below it the candidate is dropped)
  unusualness     distance from the relevant baseline (type-specific, documented per generator)
  recency         how recent the historical evidence is (only where history is used)
  recognisability player prominence in covered data (log of balls involved)
score = 0.35·relevance + 0.20·sample + 0.30·unusualness + 0.05·recency + 0.10·recognisability

Selection: candidates below MIN_SCORE or MIN_UNUSUAL are not shown; at most one per type and one per subject; top 4.
Novelty: a candidate is NEW only if its `key` (which includes the bucket that makes it true, e.g. the milestone being
approached) did not qualify one ball earlier. If nothing is new, the response says so: no commentary just because a ball
was bowled.
"""
from __future__ import annotations

import math

from .baselines import econ, sr, stage_of

VERSION = "right-now-1.0"
W = {"relevance": 0.35, "sample": 0.20, "unusualness": 0.30, "recency": 0.05, "recognisability": 0.10}
MIN_SCORE, MIN_UNUSUAL, TOP = 0.45, 0.25, 4


def _cur(state):
    inns = [i for i in state["innings"]]
    return inns[-1] if inns else None


def _recog(base, *pids) -> float:
    n = 0
    for p in pids:
        n += (base["bat"].get(p, {}).get("all", {}).get("balls", 0) or 0) + (base["bowl"].get(p, {}).get("all", {}).get("balls", 0) or 0)
    return min(1.0, math.log10(1 + n) / 4)          # 10,000 balls in covered data → 1


def _recency(last: str | None, asof: str) -> float:
    if not last:
        return 0.0
    yrs = (int(asof[:4]) - int(last[:4]))
    return max(0.0, 1 - yrs / 5)


def _cand(kind, key, subject, text, numbers, rel, sample, unusual, recency, recog, href, prov="DERIVED", detail=None):
    dims = {"relevance": round(rel, 3), "sample": round(min(1, sample), 3), "unusualness": round(min(1, unusual), 3),
            "recency": round(recency, 3), "recognisability": round(recog, 3)}
    return {"type": kind, "key": key, "subject": subject, "text": text, "numbers": numbers, "dims": dims,
            "score": round(sum(W[k] * v for k, v in dims.items()), 3), "href": href, "prov": prov, "detail": detail}


def _pre(state, inn):
    """Who is involved next: from the pre_ball event if present, else the crease after the last ball."""
    pb = state.get("pre_ball")
    if pb and inn and pb["innings"] == inn["innings"]:
        return pb["striker"]["id"], pb["non_striker"]["id"], pb["bowler"]["id"]
    if inn:
        return inn.get("striker"), inn.get("non_striker"), inn.get("current_bowler")
    return None, None, None


# ------------------------------------------------------------------------------------------------ generators
def candidates(state: dict, base: dict) -> list[dict]:
    inn = _cur(state)
    if not inn or inn["super_over"]:
        return []                                   # Cricsheet: super overs do not count towards statistics
    out: list[dict] = []
    s, ns, bw = _pre(state, inn)
    names = {**{p: b["name"] for p, b in inn["batters"].items()}, **{p: b["name"] for p, b in inn["bowlers"].items()}}
    pb = state.get("pre_ball") or {}
    for side in ("striker", "non_striker", "bowler"):
        if pb.get(side):
            names[pb[side]["id"]] = pb[side]["name"]
    nm = lambda p: names.get(p, p)  # noqa: E731
    fmtname = f"{base['format']} {'men' if base['gender'] == 'male' else 'women'}"

    # 1. Current battle: striker v bowler history before this match. Unusual = how far SR and dismissals sit from the
    #    batter's own usual numbers (log SR ratio, and outs v expected).
    if s and bw:
        h = base["battles"].get(f"{s}|{bw}")
        usual = base["bat"].get(s, {}).get("all")
        if h and h["balls"] >= 12 and usual and usual["balls"] >= 120:
            usr, hsr = 100 * usual["runs"] / usual["balls"], 100 * h["runs"] / h["balls"]
            exp_out = h["balls"] * usual["outs"] / usual["balls"]
            un = max(abs(math.log(max(hsr, 1) / usr)) / math.log(1.6), abs(h["outs"] - exp_out) / max(1.5, math.sqrt(exp_out) * 2))
            out.append(_cand("battle", f"battle|{s}|{bw}", s,
                             f"{nm(s)} v {nm(bw)} before today: {h['runs']} off {h['balls']} (SR {round(hsr, 1)}, usual {round(usr, 1)}), "
                             f"out {h['outs']} time{'s' if h['outs'] != 1 else ''} where {round(exp_out, 1)} would be expected.",
                             [{"label": "balls", "value": h["balls"]}, {"label": "SR", "value": round(hsr, 1)}, {"label": "outs", "value": h["outs"]}],
                             1.0, h["balls"] / 60, un, _recency(h["last"], base["asof"]), _recog(base, s, bw),
                             f"/battle?bat={s}&bowl={bw}", detail={"matches": h["matches"], "first": h["first"], "last": h["last"]}))

    # 2. Batter at this stage of an innings v their usual at the same stage (needs 100 balls at that stage before today).
    for pid, rel in ((s, 0.9), (ns, 0.6)):
        b = inn["batters"].get(pid) if pid else None
        if not b or b["balls"] < 10:
            continue
        st = stage_of(b["balls"] - 1)
        hist = base["bat"].get(pid, {}).get("stage", {}).get(st)
        if not hist or hist["balls"] < 100:
            continue
        usual, now = sr(hist), round(100 * b["runs"] / b["balls"], 1)
        un = abs(math.log(max(now, 1) / max(usual, 1))) / math.log(1.8) * min(1, b["balls"] / 20)
        out.append(_cand("batter_stage", f"stage|{pid}|{st}|{'up' if now > usual else 'down'}", pid,
                         f"{nm(pid)} {b['runs']} ({b['balls']}): strike rate {now} against {usual} usually at balls {st} of a {base['format']} innings.",
                         [{"label": "SR now", "value": now}, {"label": f"usual, balls {st}", "value": usual}, {"label": "sample", "value": hist["balls"]}],
                         rel, hist["balls"] / 400, un, 1.0, _recog(base, pid), f"/players/{pid}?tab=states"))

    # 3. Bowler's current spell v their usual economy in this phase (needs 120 balls in the phase before today).
    if bw and bw in inn["bowlers"]:
        w = inn["bowlers"][bw]
        sp = w["spell"]
        ph = _phase(base["format"], inn["legal"])
        hist = base["bowl"].get(bw, {}).get("phase", {}).get(ph)
        if sp and sp["balls"] >= 12 and hist and hist["balls"] >= 120:
            usual, now = econ(hist), round(6 * sp["runs"] / sp["balls"], 2)
            un = abs(now - usual) / (3.0 if base["format"] == "T20" else 2.0) * min(1, sp["balls"] / 24)
            out.append(_cand("bowler_spell", f"spell|{bw}|{sp['number']}|{'tight' if now < usual else 'loose'}", bw,
                             f"{nm(bw)}'s spell: {sp['wickets']}/{sp['runs']} off {_ov(sp['balls'])}, economy {now} against {usual} usually in the {ph}.",
                             [{"label": "econ now", "value": now}, {"label": f"usual ({ph})", "value": usual}, {"label": "sample", "value": hist["balls"]}],
                             0.85, hist["balls"] / 480, un, 1.0, _recog(base, bw), f"/players/{bw}?tab=bowling"))

    # 4. Partnership v this pair's covered history (3+ previous stands).
    p = inn["partnership"]
    if p and p["balls"] >= 6:
        a, b2 = sorted([p["a"], p["b"]])
        h = base["pairs"].get(f"{a}|{b2}")
        if h and h["stands"] >= 3:
            avg = h["runs"] / h["stands"]
            un = max(0.0, (p["runs"] - avg) / max(avg, 10)) if p["runs"] > avg else 0.0
            bucket = "best" if p["runs"] > (h["best"] or 0) else "above_avg" if p["runs"] > avg else "below"
            out.append(_cand("partnership", f"pair|{a}|{b2}|{bucket}", f"{a}|{b2}",
                             f"{nm(a)} and {nm(b2)}: {p['runs']} together today; before today {h['stands']} stands, average {round(avg, 1)}, best {h['best']}.",
                             [{"label": "today", "value": p["runs"]}, {"label": "avg stand", "value": round(avg, 1)}, {"label": "best", "value": h["best"]}],
                             0.7, h["stands"] / 10, min(1, un) + (0.4 if bucket == "best" else 0), 1.0, _recog(base, a, b2),
                             f"/partnerships?p1={a}&p2={b2}&format={base['format']}"))

    # 5. Wickets down v how often innings in this format were this many down by now (before today). Unusual = rarity.
    lb = inn["legal"] - inn["legal"] % 6
    dist = base["ref"]["wickets_at"].get(str(lb))
    if dist and inn["wickets"] >= 2 and lb >= 6:
        tot = sum(dist.values())
        atleast = sum(v for k, v in dist.items() if int(k) >= inn["wickets"])
        share = atleast / tot if tot else None
        if share is not None and tot >= 200 and share <= 0.2:
            out.append(_cand("wickets_down", f"wk|{inn['innings']}|{inn['wickets']}", inn["batting_team"],
                             f"{inn['batting_team']} are {inn['runs']}/{inn['wickets']} after {_ov(inn['legal'])}: {round(100 * share, 1)}% of covered {fmtname} innings "
                             f"before today had lost {inn['wickets']}+ wickets by {lb // 6} overs.",
                             [{"label": "share of innings", "value": f"{round(100 * share, 1)}%"}, {"label": "innings compared", "value": tot}],
                             0.8, tot / 2000, 1 - share / 0.2, 1.0, 0.6, None))

    # 6. Score at this point v covered innings at the same point (before today).
    if lb >= 12 and inn["innings"] <= 2:
        ref = base["ref"]["score_at"].get(str(inn["innings"]), {}).get(str(lb))
        score_now = _score_at(inn, lb)
        if ref and ref["n"] >= 200 and score_now is not None:
            diff = score_now - ref["score"]
            un = abs(diff) / (25 if base["format"] == "T20" else 40)
            out.append(_cand("score_rate", f"rate|{inn['innings']}|{'above' if diff > 0 else 'below'}|{lb // 36}", inn["batting_team"],
                             f"{inn['batting_team']} had {score_now} after {lb // 6} overs; covered {fmtname} innings {inn['innings']} averaged {ref['score']} at that point before today.",
                             [{"label": "now", "value": score_now}, {"label": "average", "value": ref["score"]}, {"label": "innings", "value": ref["n"]}],
                             0.55, ref["n"] / 2000, un, 1.0, 0.6, None))

    # 7. Chase state: requirement crossing the current rate by a clear margin (factual; no win probability).
    if inn["target"] and inn["limit_balls"] and not inn["target_reached"]:
        need, left = inn["target"] - inn["runs"], inn["limit_balls"] - inn["legal"]
        if left > 0 and inn["legal"] >= 6:
            rrr, crr = 6 * need / left, 6 * inn["runs"] / inn["legal"]
            gap = rrr - crr
            if abs(gap) >= 1.5:
                band = int(gap // 2)
                out.append(_cand("chase", f"chase|{band}", inn["batting_team"],
                                 f"{inn['batting_team']} need {need} off {left}: required {round(rrr, 2)} an over, scoring at {round(crr, 2)} so far.",
                                 [{"label": "required", "value": round(rrr, 2)}, {"label": "current", "value": round(crr, 2)}],
                                 0.9 if left <= inn["limit_balls"] / 3 else 0.7, 1.0, min(1, abs(gap) / 6), 1.0, 0.6, None, prov="DERIVED"))

    # 8. Unusual sequences, defined against the 99th percentile of this format's covered innings before today.
    dq = base["ref"]["dot_streak_p99"]
    if dq and dq.get("v") and inn["dot_streak"] >= dq["v"]:
        out.append(_cand("dot_sequence", f"dots|{inn['innings']}|{inn['legal'] - inn['dot_streak']}", inn["batting_team"],
                         f"{inn['dot_streak']} dot balls in a row. Only 1% of covered {fmtname} innings before today contained a run of {dq['v']} or more.",
                         [{"label": "dots in a row", "value": inn["dot_streak"]}, {"label": "99th percentile", "value": dq["v"]}],
                         0.75, dq["n"] / 2000, 0.9, 1.0, 0.6, None))
    oq = base["ref"]["over_runs_p99"]
    last_over = inn["overs"][-1] if inn["overs"] else None
    if oq and oq.get("v") and last_over and last_over["runs"] >= oq["v"]:
        out.append(_cand("big_over", f"over|{inn['innings']}|{last_over['over']}", inn["batting_team"],
                         f"{last_over['runs']} runs from over {last_over['over'] + 1} (bowled by {last_over['bowler']}). 99% of covered {fmtname} overs before today went for fewer than {oq['v']}.",
                         [{"label": "runs in over", "value": last_over["runs"]}, {"label": "99th percentile", "value": oq["v"]}],
                         0.75, 1.0, 0.85, 1.0, 0.6, None))

    # 9. Wicket burst: the Phase 4 collapse definition (3+ wickets within 18 legal balls for ≤ 20 runs).
    fow = inn["fow"]
    if len(fow) >= 3:
        a, z = fow[-3], fow[-1]
        if z["legal"] - a["legal"] <= 18 and z["score"] - (a["score"] - 0) <= 20 and inn["legal"] - z["legal"] <= 6:
            out.append(_cand("wicket_burst", f"burst|{inn['innings']}|{a['wicket']}", inn["batting_team"],
                             f"{inn['batting_team']} lost 3 wickets in {z['legal'] - a['legal'] + 1} balls for {z['score'] - a['score']} runs ({a['label']}–{z['label']}).",
                             [{"label": "wickets", "value": 3}, {"label": "balls", "value": z["legal"] - a["legal"] + 1}],
                             0.85, 1.0, 0.8, 1.0, 0.6, None, prov="OBSERVED"))
    return out


def _phase(fmt: str, legal: int) -> str:
    ov = legal // 6
    if fmt == "T20":
        return "powerplay" if ov < 6 else "middle" if ov < 15 else "death"
    return "powerplay" if ov < 10 else "middle" if ov < 40 else "death"


def _score_at(inn: dict, lb: int) -> int | None:
    tot, legal = 0, 0
    for o in inn["overs"]:
        if legal >= lb:
            break
        tot += o["runs"]
        legal += 6
    return tot if legal == lb else None


def _ov(balls: int) -> str:
    return f"{balls // 6}.{balls % 6}"


def select(cands: list[dict]) -> list[dict]:
    """Threshold, then diversity (one per type, one per subject), then top TOP by score. Deterministic tie-breaks."""
    ok = [c for c in cands if c["score"] >= MIN_SCORE and c["dims"]["unusualness"] >= MIN_UNUSUAL]
    ok.sort(key=lambda c: (-c["score"], c["key"]))
    out, types, subjects = [], set(), set()
    for c in ok:
        if c["type"] in types or c["subject"] in subjects:
            continue
        out.append(c)
        types.add(c["type"])
        subjects.add(c["subject"])
        if len(out) == TOP:
            break
    return out


def right_now(state: dict, prev: dict | None, base: dict) -> dict:
    now = select(candidates(state, base))
    before = {c["key"] for c in select(candidates(prev, base))} if prev else set()
    for c in now:
        c["new"] = c["key"] not in before
    return {"items": now, "nothing_new": not any(c["new"] for c in now),
            "method": "Deterministic ranking: 0.35 relevance + 0.20 sample + 0.30 unusualness + 0.05 recency + 0.10 recognisability; "
                      f"shown only if score ≥ {MIN_SCORE} and unusualness ≥ {MIN_UNUSUAL}; one per type and per subject; "
                      "baselines use only covered matches before this one."}


# ------------------------------------------------------------------------------------------------ record watch
def record_watch(state: dict, base: dict, coverage: dict | None) -> list[dict]:
    inn = _cur(state)
    if not inn or inn["super_over"]:
        return []
    cref, out = base["comp"], []
    scope = f"covered {cref.get('name') or base['format']} data before this match"
    cov = (coverage or {}).get("status")
    note = "Within CRICINTEL's covered data, not an official record" + (f" (Cricsheet completeness for this competition: {cov.lower()})" if cov else "")
    for pid in [inn["striker"], inn["non_striker"]]:
        b = inn["batters"].get(pid) if pid else None
        if not b:
            continue
        for mark in (50, 100, 150, 200):
            if mark - 10 <= b["runs"] < mark:
                out.append({"kind": "milestone", "key": f"ms|{pid}|{mark}", "text": f"{b['name']} is {mark - b['runs']} short of {mark}.", "official": True,
                            "note": "A milestone, not a record."})
                break
        if cref.get("top_score") and cref["top_score"] - 25 <= b["runs"]:
            out.append({"kind": "record", "key": f"hs|{pid}", "text": f"{b['name']} {b['runs']}: the highest individual score in {scope} is {cref['top_score']}.",
                        "note": note})
        cr = (cref.get("squad_runs") or {}).get(pid)
        board = cref.get("runs_board") or []
        if cr is not None and board:
            mine = cr + b["runs"]
            above = [r for r in board if r["pid"] != pid and r["runs"] > cr]
            passed = [r for r in above if r["runs"] < mine]
            nxt = min((r for r in above if r["runs"] >= mine), key=lambda r: r["runs"], default=None)
            if passed:
                out.append({"kind": "leaderboard", "key": f"lb|{pid}|{len(passed)}", "pid": pid,
                            "text": f"{b['name']} has passed {len(passed)} player{'s' if len(passed) > 1 else ''} on the run-scoring list in {scope} today ({mine} in total).", "note": note})
            elif nxt and nxt["runs"] - mine <= 20:
                out.append({"kind": "leaderboard", "key": f"lbn|{pid}|{nxt['pid']}", "pid": pid, "other": nxt["pid"],
                            "text": f"{b['name']} is {nxt['runs'] - mine + 1} runs from moving up the run-scoring list in {scope}.", "note": note})
    p = inn["partnership"]
    if p and cref.get("top_part"):
        top = cref["top_part"].get(p["wicket"])
        if top and p["runs"] >= top - 25:
            out.append({"kind": "record", "key": f"pt|{p['wicket']}", "text": f"This stand is {p['runs']}; the best for wicket {p['wicket']} in {scope} is {top}.", "note": note})
    for w in inn["bowlers"].values():
        if w["wickets"] == 4:
            out.append({"kind": "milestone", "key": f"5w|{w['id']}", "text": f"{w['name']} has 4 wickets: one from a five-wicket haul.", "official": True, "note": "A milestone, not a record."})
        if cref.get("best_wkts") and w["wickets"] >= cref["best_wkts"] - 1 and w["wickets"] >= 3:
            out.append({"kind": "record", "key": f"bw|{w['id']}", "text": f"{w['name']} has {w['wickets']}; the most wickets in an innings in {scope} is {cref['best_wkts']}.", "note": note})
    if cref.get("top_total") and inn["runs"] >= cref["top_total"] - 30 and inn["innings"] <= 2:
        out.append({"kind": "record", "key": f"tt|{inn['innings']}", "text": f"{inn['batting_team']} {inn['runs']}: the highest total in {scope} is {cref['top_total']}.", "note": note})
    return out


# ------------------------------------------------------------------------------------------------ timeline
def timeline(state: dict, base: dict) -> list[dict]:
    """Factual events up to the cursor, newest first. Each links to its delivery; labels are descriptive, never editorial."""
    ev = []
    dq = (base["ref"].get("dot_streak_p99") or {}).get("v")
    oq = (base["ref"].get("over_runs_p99") or {}).get("v")
    for inn in state["innings"]:
        tag = f"{inn['batting_team']}{' (super over)' if inn['super_over'] else ''}"
        ev.append({"kind": "innings_start", "innings": inn["innings"], "order": (inn["innings"], -1),
                   "text": f"{tag} innings begins" + (f" · target {inn['target']}" if inn["target"] else "")})
        for f in inn["fow"]:
            ev.append({"kind": "wicket", "innings": inn["innings"], "order": (inn["innings"], f["legal"], 1), "label": f["label"], "event_id": f["event_id"],
                       "text": f"{f['player']} {f['runs']} ({f['balls']}) · {f['kind']} · {inn['batting_team']} {f['score']}/{f['wicket']}"})
        for e in inn["events"]:
            ev.append({**e, "innings": inn["innings"], "order": (inn["innings"], e.get("legal", 10 ** 6), 2)})
        for k, b in enumerate(inn["milestones"] if "milestones" in inn else []):
            ev.append({**b, "innings": inn["innings"], "order": (inn["innings"], b["legal"], 3)})
        if oq:
            for o in inn["overs"]:
                if o["runs"] >= oq:
                    ev.append({"kind": "big_over", "innings": inn["innings"], "order": (inn["innings"], (o["over"] + 1) * 6, 4),
                               "text": f"{o['runs']} runs from over {o['over'] + 1} ({o['bowler']}), at or above the 99th percentile ({oq}) of covered overs"})
        if dq and inn.get("max_dot_streak", 0) >= dq:
            ev.append({"kind": "dot_sequence", "innings": inn["innings"], "order": (inn["innings"], inn["max_dot_streak_at"], 4),
                       "text": f"{inn['max_dot_streak']} dot balls in a row, at or above the 99th percentile ({dq}) of covered innings"})
    ev.sort(key=lambda e: e["order"], reverse=True)
    for e in ev:
        e.pop("order", None)
    return ev
