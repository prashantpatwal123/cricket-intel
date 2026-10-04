"""Cricket Stories: deterministic sequences of evidence cards assembled from computed facts.

Rules: every sentence is a template filled with numbers computed here; every card links to its evidence; titles avoid causal
language ("What the X–Y battle shows", not "Why"), because our data shows what happened, not why.
"""
from __future__ import annotations

from ..db import DB
from . import battle as B
from . import replay as R
from .entities import _nm, match_page
from .filters import Filters


def _card(kind: str, title: str, text: str, facts: list, href: str | None = None, visual: dict | None = None) -> dict:
    return {"kind": kind, "title": title, "text": text, "facts": facts, "href": href, "visual": visual}


def _f(label, value, prov="DERIVED"):
    return {"label": label, "value": value, "prov": prov}


def innings_story(db: DB, mid: str, inn: int, pid: str) -> dict | None:
    s = R.innings_story(db, mid, inn, pid)
    bi = db.q1("SELECT * FROM bat_innings WHERE match_id = ? AND innings_no = ? AND batter_id = ?", [mid, inn, pid])
    if not s or not bi:
        return None
    nm, sm, m = s["batter"]["name"], s["summary"], s["match"]
    faced = [b for b in s["balls"] if b["on_strike"] and not b["symbol"].endswith("wd")]
    cards = []
    chase = bi["chasing"] and bi["req_at_arrival"] is not None
    cards.append(_card("situation", "The situation", (
        f"{nm} walked in at {sm['arrived']} in over {bi['arrived_over'] + 1}" +
        (f", with {bi['req_at_arrival']} needed off {bi['balls_left_at_arrival']} balls ({bi['rrr_at_arrival']:.2f} an over)." if chase else ", batting first.")),
        [_f("Score on arrival", sm["arrived"]), _f("Over", bi["arrived_over"] + 1)] +
        ([_f("Needed", f"{bi['req_at_arrival']} off {bi['balls_left_at_arrival']}"), _f("Required rate", f"{bi['rrr_at_arrival']:.2f}")] if chase else []),
        f"/delivery/{s['balls'][0]['delivery_id']}", {"type": "situation", "ball": s["balls"][0]["delivery_id"]}))
    first = faced[:10]
    if first:
        r10 = sum(b["runs"] for b in first)
        usual = db.q1("""SELECT 100.0 * sum(runs_batter) / count(*) AS sr, count(*) AS n FROM balls WHERE batter_id = ? AND format_group = ? AND wides = 0
                         AND batter_balls_before < 10 AND match_id <> ?""", [pid, bi["format_group"], mid])
        cards.append(_card("early", "The first ten balls", (
            f"{r10} runs off the first {len(first)} balls faced (strike rate {100 * r10 / len(first):.0f})" +
            (f", against {usual['sr']:.0f} in their other covered {bi['format_group']} innings at the same stage." if usual and usual["n"] else ".")),
            [_f("Runs", r10), _f("Balls", len(first)), _f("Usual SR, balls 1–10", f"{usual['sr']:.0f}" if usual and usual["n"] else "–")],
            None, {"type": "balls", "symbols": [b["symbol"] for b in first]}))
    if s["partnerships"]:
        p = max(s["partnerships"], key=lambda x: x["runs"])
        cards.append(_card("partnership", "The partnership", (
            f"The biggest stand was {p['runs']} off {p['balls']} balls with {p['partner']}; {nm} made {p['my_runs']} of them."),
            [_f("Stand", f"{p['runs']} ({p['balls']})"), _f(f"{nm}", p["my_runs"]), _f(p["partner"], p["partner_runs"])],
            f"/partnerships?p1={pid}&p2={p['partner_id']}", {"type": "split", "a": p["my_runs"], "b": p["partner_runs"]}))
    if chase:
        rr = [b for b in s["balls"] if b.get("required_rate") is not None]
        if rr:
            peak = max(rr, key=lambda b: b["required_rate"])
            last = rr[-1]
            cards.append(_card("rate", "The required rate", (
                f"The required rate went from {bi['rrr_at_arrival']:.2f} on arrival to a peak of {peak['required_rate']:.2f} at {peak['ball_label']} "
                f"({peak['runs_required']} needed off {peak['balls_left']}), and stood at {last['required_rate']:.2f} before the last ball {nm} saw."),
                [_f("On arrival", f"{bi['rrr_at_arrival']:.2f}"), _f("Peak", f"{peak['required_rate']:.2f}"), _f("At the end", f"{last['required_rate']:.2f}")],
                f"/delivery/{peak['delivery_id']}", {"type": "series", "values": [round(b["required_rate"], 2) for b in rr]}))
    if bi["b10"] == 10 and bi["balls"] >= 20:
        before = (bi["runs"] - bi["r10"]) / (bi["balls"] - 10)
        cards.append(_card("acceleration", "The finish", (
            f"{bi['r10']} runs off the last 10 balls faced (strike rate {10 * bi['r10']:.0f}), against {100 * before:.0f} before them."),
            [_f("Last 10 balls", bi["r10"]), _f("SR before", f"{100 * before:.0f}"), _f("SR last 10", f"{10 * bi['r10']:.0f}")],
            None, {"type": "balls", "symbols": [b["symbol"] for b in faced[-10:]]}))
    tail = s["balls"][-6:]
    cards.append(_card("final_balls", "The last deliveries", "The final six deliveries of the innings while they were at the crease.",
                       [_f(b["ball_label"], b["symbol"], "OBSERVED") for b in tail], f"/delivery/{tail[-1]['delivery_id']}",
                       {"type": "ball_links", "balls": [{"id": b["delivery_id"], "symbol": b["symbol"], "label": b["ball_label"]} for b in tail]}))
    cards.append(_card("result", "The result", (
        f"{nm} finished {sm['runs']}{'*' if sm['not_out'] else ''} off {sm['balls']} balls. {m['result_line']}."),
        [_f("Score", f"{sm['runs']}{'*' if sm['not_out'] else ''} ({sm['balls']})", "OBSERVED"), _f("Result", m["result_line"], "OBSERVED")],
        f"/match/{mid}"))
    return {"title": f"How {nm}'s {sm['runs']}{'*' if sm['not_out'] else ''} unfolded", "subtitle": f"{s['teams']['batting_team']} v {s['teams']['bowling_team']} · "
            f"{m['competition']} · {m['start_date']}", "cards": cards, "source": {"type": "innings", "href": f"/innings/{mid}/{inn}/{pid}"},
            "method": "Every sentence is a template filled with numbers computed from the ball-by-ball record. No language model."}


def battle_story(db: DB, bat: str, bowl: str) -> dict | None:
    b = B.battle(db, bat, bowl, Filters())
    if not b["met"]:
        return None
    t, e = b["total"], b["edge"]
    bn, wn = _nm(db, bat), _nm(db, bowl)
    cards = [_card("overview", "The record", (
        f"{bn} has faced {t['balls']} balls from {wn} in {t['matches']} covered matches between {t['first_date']} and {t['last_date']}, "
        f"scoring {t['runs']} runs (strike rate {t['strike_rate']}) and being dismissed {t['dismissals']} time{'s' if t['dismissals'] != 1 else ''}."),
        [_f("Balls", t["balls"], "OBSERVED"), _f("Runs", t["runs"], "OBSERVED"), _f("Dismissals", t["dismissals"], "OBSERVED"), _f("SR", t["strike_rate"])],
        f"/battle?bat={bat}&bowl={bowl}")]
    sr = e["strike_rate"]
    if sr.get("batter_usual") is not None:
        lo, hi = sr["matchup_interval_90"]
        rel = "within" if lo <= sr["batter_usual"] <= hi else ("below" if sr["batter_usual"] > hi else "above")
        cards.append(_card("scoring", "Scoring against usual", (
            f"The strike rate here is {sr['matchup']} (90% interval {lo:.0f}–{hi:.0f}). {bn}'s usual rate is {sr['batter_usual']}, "
            + ("inside that range." if rel == "within" else f"so in this battle {bn} scores {'more slowly' if rel == 'below' else 'faster'} than usual.")),
            [_f("Here", sr["matchup"]), _f("Batter usual", sr["batter_usual"]), _f("Bowler concedes", sr.get("bowler_usual_conceded"))], None,
            {"type": "numline", "here": sr["matchup"], "lo": lo, "hi": hi, "usual": sr["batter_usual"]}))
    d = e["dismissals"]
    if d.get("expected_from_batter_usual_rate") is not None:
        cards.append(_card("dismissals", "Dismissals against expectation", (
            f"{wn} has dismissed {bn} {d['observed']} times. At {bn}'s usual dismissal rate against all bowlers, {d['expected_from_batter_usual_rate']} "
            f"would be expected from {t['balls']} balls (90% interval for the observed count {d['observed_interval_90'][0]}–{d['observed_interval_90'][1]})."),
            [_f("Observed", d["observed"], "OBSERVED"), _f("Expected", d["expected_from_batter_usual_rate"], "MODELLED")], None))
    if b["dismissals_by_kind"]:
        kinds = [k for k in b["dismissals_by_kind"] if k["n"]]
        cards.append(_card("how", "How the dismissals happened", "; ".join(f"{k['label'].lower()}: {k['n']}" for k in kinds) + ".",
                           [_f(k["label"], k["n"], "OBSERVED" if k["route"] != "CAUGHT_KEEPER" else "DERIVED") for k in kinds],
                           f"/battle?bat={bat}&bowl={bowl}"))
    ph = b["by"]["phase"]["rows"]
    if ph:
        cards.append(_card("when", "When they met", "Balls, runs and dismissals by phase of the innings.",
                           [_f(r["bucket"], f"{r['runs']} off {r['balls']}, {r['dismissals']} out") for r in ph], None,
                           {"type": "bars", "rows": [{"k": r["bucket"], "balls": r["balls"], "sr": r["strike_rate"], "outs": r["dismissals"]} for r in ph]}))
    yr = b["by"]["year"]["rows"]
    if len(yr) >= 2:
        cards.append(_card("time", "Over time", "Strike rate and dismissals by year of meeting.",
                           [_f(str(r["bucket"]), f"SR {r['strike_rate']}, {r['dismissals']} out ({r['balls']} balls)") for r in yr], None,
                           {"type": "series", "values": [r["strike_rate"] for r in yr], "labels": [r["bucket"] for r in yr]}))
    cards.append(_card("caveat", "What this does not show", (
        "Cricsheet records outcomes, not line, length, pace or shot, so this battle can't say why it went this way. "
        f"{e['sample_note']}"), [], None))
    return {"title": f"What the {bn}–{wn} battle shows", "subtitle": f"{t['balls']} balls · {t['matches']} matches", "cards": cards,
            "source": {"type": "battle", "href": f"/battle?bat={bat}&bowl={bowl}"},
            "method": "Every sentence is a template filled with numbers computed from the ball-by-ball record. Titles avoid 'why': the data shows what happened, not causes."}


def match_story(db: DB, mid: str) -> dict | None:
    mp = match_page(db, mid)
    if not mp:
        return None
    m, inns = mp["match"], mp["innings"]
    cards = [_card("setting", "The match", (
        f"{m['team1']} v {m['team2']} in the {m['competition'] or 'series'}{', ' + m['event_stage'] if m['event_stage'] else ''} at {m['venue'] or 'an unrecorded venue'} "
        f"on {m['start_date']}." + (f" {m['toss_winner']} won the toss and chose to {m['toss_decision']}." if m.get("toss_winner") else "")),
        [_f("Competition", m["competition"] or "—", "OBSERVED"), _f("Venue", m["venue"] or "—", "OBSERVED")], f"/match/{mid}")]
    for i in inns:
        ph = i["phases"]
        top = max(i["batting"], key=lambda b: b["runs"]) if i["batting"] else None
        bb = i["bowling"][0] if i["bowling"] else None
        cards.append(_card("innings", f"{i['batting_team']}: {i['total_runs']}/{i['total_wickets']}", (
            f"{i['batting_team']} made {i['total_runs']}/{i['total_wickets']} in {i['overs']} overs. "
            + " ".join(f"{k.capitalize()}: {v['runs']}/{v['wkts']}." for k, v in sorted(ph.items(), key=lambda kv: ["powerplay", "middle", "death"].index(kv[0]) if kv[0] in ("powerplay", "middle", "death") else 9))
            + (f" Top score {top['name']} {top['runs']}{'*' if top['not_out'] else ''} ({top['balls']})." if top else "")
            + (f" Best bowling {bb['name']} {bb['wickets']}/{bb['runs']}." if bb else "")),
            [_f(k, f"{v['runs']}/{v['wkts']}") for k, v in ph.items()], None,
            {"type": "worm", "overs": [o["runs"] for o in i["overs_list"]], "wkts": [o["wkts"] for o in i["overs_list"]]}))
        for ev in [e for e in mp["events"] if e["innings_no"] == i["innings_no"] and e["kind"] in ("collapse",)]:
            cards.append(_card("event", "A cluster of wickets", ev["label"] + ".", [_f("Definition", ev["definition"])],
                               f"/delivery/{ev['delivery_id']}" if ev.get("delivery_id") else None))
    if mp["partnerships"]:
        p = mp["partnerships"][0]
        cards.append(_card("partnership", "The biggest partnership", f"{p['p1_name']} and {p['p2_name']} added {p['runs']} off {p['balls']} balls.",
                           [_f("Stand", f"{p['runs']} ({p['balls']})")], f"/innings/{mid}/{p['innings_no']}/{p['p1']}"))
    cards.append(_card("result", "The result", f"{m['result_line']}.", [_f("Result", m["result_line"], "OBSERVED")], f"/match/{mid}"))
    return {"title": f"How {m['team1']} v {m['team2']} unfolded", "subtitle": f"{m['competition'] or ''} · {m['start_date']}", "cards": cards,
            "source": {"type": "match", "href": f"/match/{mid}"}, "method": "Assembled from computed match facts; no turning points are claimed."}
