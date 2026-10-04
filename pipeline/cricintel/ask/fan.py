"""Ask (Phase 7 additions): questions answered from the knowledge graph, the fan engines and the shared Filters.

New question kinds (all deterministic; the grammar stays narrow where an interpretation can't be validated):
  scored_fastest_against  "Who has Kohli scored fastest against?"        batter's strike rate by bowler, 60+ balls, shrunk value shown
  player_faced_change     "What changes after Kohli faces 30 balls?"      before/after split: SR, boundary %, dot %, dismissal rate
  similar                 "Which players are most similar to Rohit?"      the validated Similar Players index
  compare_players         "Compare Kohli and Rohit in chases"             two batters under the same filters, lead / tie per measure
  team_chases             "Show India's biggest successful T20 chases"   team_results, chasing side won
  battle_dismissals       "Which Kohli-Zampa dismissals happened in death overs?"  every dismissal of A by B under the filters
Every executor uses Filters.where, so any filter it is given is applied or the question is refused; nothing is dropped.
"""
from __future__ import annotations

import math

from ..analytics.filters import Filters, team_names
from ..analytics.entities import _nm, canon
from ..db import DB

KINDS = {"scored_fastest_against": "Scored fastest against", "player_faced_change": "Before / after N balls", "similar": "Similar players",
         "compare_players": "Compare two players", "team_chases": "Biggest successful chases", "battle_dismissals": "Dismissals in a battle"}
NO_FILTERS = {"similar": set(), "team_chases": {"format", "competition", "team_type", "year_from", "year_to", "before_date", "opposition"}}


def _items(rows, label, value, href, sub=None):
    return [{"label": label(r), "value": value(r), "href": href(r), "sub": sub(r) if sub else None} for r in rows]


def execute(db: DB, it, f: Filters, scope: str, base: dict) -> dict | None:
    k = it.kind
    if k not in KINDS:
        return None
    if k in NO_FILTERS:
        extra = set(it.filters) - NO_FILTERS[k]
        if extra:
            return {**base, "status": "needs_clarification",
                    "message": f"This kind of question can't yet be limited by {', '.join(sorted(extra))}; remove that condition or ask it another way."}
    try:
        return globals()["_" + k](db, it, f, scope, base)
    except Exception as e:  # noqa: BLE001 - an unsupported filter combination is refused, never answered wrongly
        return {**base, "status": "needs_clarification", "message": f"That combination of conditions isn't supported for this question ({type(e).__name__})."}


def _scored_fastest_against(db, it, f, scope, base):
    pid, name = it.subject["person_id"], it.subject["name"]
    w, p = f.where("batter")
    rows = db.q(f"""SELECT bowler_id, count(*) FILTER (WHERE faced) AS balls, sum(runs_batter) AS runs FROM balls
                    WHERE batter_id = ? AND {w} GROUP BY 1 HAVING count(*) FILTER (WHERE faced) >= ?""", [pid, *p, it.min_sample or 60])
    usual = db.q1(f"SELECT sum(runs_batter) * 1.0 / nullif(count(*) FILTER (WHERE faced), 0) AS rpb FROM balls WHERE batter_id = ? AND {w}", [pid, *p])["rpb"] or 0
    for r in rows:
        r["sr"] = 100 * r["runs"] / r["balls"]
        r["shrunk"] = 100 * (r["runs"] + 60 * usual) / (r["balls"] + 60)
        r["name"] = _nm(db, r["bowler_id"])
    rows.sort(key=lambda r: -r["shrunk"])
    rows = rows[:10]
    if not rows:
        return {**base, "status": "ok", "answer": f"No bowler has bowled {it.min_sample or 60}+ balls to {name} {scope}.", "numbers": []}
    r0 = rows[0]
    return {**base, "status": "ok",
            "answer": f"{name} has scored fastest against {r0['name']} {scope}: {r0['runs']} off {r0['balls']} balls (strike rate {r0['sr']:.0f}, "
                      f"against a usual {100 * usual:.0f}).", "numbers": [],
            "items": _items(rows, lambda r: r["name"], lambda r: f"{r['sr']:.0f}", lambda r: f"/battle?bat={pid}&bowl={r['bowler_id']}",
                            lambda r: f"{r['runs']} off {r['balls']} · shrunk estimate {r['shrunk']:.0f}"),
            "definition": f"Bowlers who have bowled at least {it.min_sample or 60} balls to {name}, ranked by strike rate shrunk toward {name}'s usual rate "
                          "with 60 pseudo-balls, so a short hot streak does not top the list.", "link": {"kind": "player", "id": pid}}


def _player_faced_change(db, it, f, scope, base):
    pid, name = it.subject["person_id"], it.subject["name"]
    n = next((x["after_balls"] for x in it.notes if "after_balls" in x), 30)
    fl = Filters.parse({k: v for k, v in it.filters.items() if k not in ("faced_from", "faced_to")})
    w, p = fl.where("batter", alias="b")
    rows = db.q(f"""SELECT (b.batter_balls_before >= ?) AS after, count(*) FILTER (WHERE b.faced) AS balls, sum(b.runs_batter) AS runs,
                    count(*) FILTER (WHERE b.faced AND (b.is_four OR b.is_six)) AS bnd, count(*) FILTER (WHERE b.faced AND b.runs_batter = 0) AS dots,
                    count(x.delivery_id) AS outs
                    FROM balls b LEFT JOIN dis x ON x.delivery_id = b.delivery_id AND x.player_out_id = b.batter_id AND x.counts_as_dismissal
                    WHERE b.batter_id = ? AND {w} GROUP BY 1""", [n, pid, *p])
    by = {r["after"]: r for r in rows}
    a, b = by.get(False), by.get(True)
    if not a or not b or not a["balls"] or not b["balls"]:
        return {**base, "status": "ok", "answer": f"Not enough balls either side of ball {n} for {name} {scope}.", "numbers": []}

    def m(r):
        return {"sr": 100 * r["runs"] / r["balls"], "bnd": 100 * r["bnd"] / r["balls"], "dot": 100 * r["dots"] / r["balls"], "out": 100 * r["outs"] / r["balls"]}
    A, B = m(a), m(b)
    nums = [{"label": f"Strike rate · first {n}", "value": f"{A['sr']:.0f}"}, {"label": f"Strike rate · after {n}", "value": f"{B['sr']:.0f}"},
            {"label": "Boundary %", "value": f"{A['bnd']:.1f} → {B['bnd']:.1f}"}, {"label": "Dot-ball %", "value": f"{A['dot']:.1f} → {B['dot']:.1f}"},
            {"label": "Outs / 100 balls", "value": f"{A['out']:.2f} → {B['out']:.2f}"}]
    return {**base, "status": "ok",
            "answer": f"{name} {scope}: strike rate {A['sr']:.0f} in the first {n} balls of an innings and {B['sr']:.0f} after them; boundaries "
                      f"{A['bnd']:.1f}% → {B['bnd']:.1f}% of balls, dots {A['dot']:.1f}% → {B['dot']:.1f}%, dismissals {A['out']:.2f} → {B['out']:.2f} per 100 balls.",
            "numbers": nums, "definition": f"All covered T20 and ODI balls unless a format is named. Balls the batter faced before and after they had already faced {n} in that innings ({a['balls']:,} and {b['balls']:,} balls). "
                                          "Whether a change is unusual compared with peers is on the player's 'What makes them different' section.",
            "link": {"kind": "player", "id": pid, "tab": "states"}}


def _similar(db, it, f, scope, base):
    from ..fan import similar as SM
    pid, name = it.subject["person_id"], it.subject["name"]
    s = SM.similar(db, pid, k=8)
    if not s.get("available"):
        return {**base, "status": "ok", "answer": f"No similar players shown for {name}: {s['reason']}.", "numbers": []}
    r0 = s["rows"][0]
    return {**base, "status": "ok",
            "answer": f"Most similar to {name} ({s['format']} {s['role']}, style not quality): {r0['name']}, then "
                      f"{', '.join(r['name'] for r in s['rows'][1:4])}.", "numbers": [],
            "items": _items(s["rows"], lambda r: r["name"], lambda r: f"{r['distance']:.2f}", lambda r: f"/compare?ids={pid},{r['pid']}",
                            lambda r: "alike: " + ", ".join(a["label"].lower() for a in r["alike"])),
            "definition": f"Nearest neighbours on fingerprint dimensions among {s['pool_size']} peers; validated on held-out halves of each player's "
                          f"matches (self-match in top 5: {round(100 * s['validation']['self_top5'])}% v {round(100 * s['validation']['chance_top5'], 1)}% by chance). "
                          "Value = distance (lower = more alike).", "link": {"kind": "player", "id": pid}}


def _compare_players(db, it, f, scope, base):
    a, b = it.subject, it.opponent
    w, p = f.where("batter", alias="b")
    out = []
    for pl in (a, b):
        r = db.q1(f"""SELECT count(*) FILTER (WHERE b.faced) AS n, sum(b.runs_batter) AS r, sum(b.runs_batter * b.runs_batter) AS r2,
                      count(*) FILTER (WHERE b.faced AND (b.is_four OR b.is_six)) AS bnd, count(x.delivery_id) AS outs
                      FROM balls b LEFT JOIN dis x ON x.delivery_id = b.delivery_id AND x.player_out_id = b.batter_id AND x.counts_as_dismissal
                      WHERE b.batter_id = ? AND {w}""", [pl["person_id"], *p])
        out.append(r)
    A, B = out
    if not A["n"] or not B["n"]:
        return {**base, "status": "ok", "answer": f"Both players need batting {scope} to compare.", "numbers": []}
    dims = []
    alpha = 0.05 / 3

    def verdict(va, sa, vb, sb, hb):
        z = (va - vb) / math.sqrt(sa * sa + sb * sb) if (sa or sb) else 0
        pv = math.erfc(abs(z) / math.sqrt(2))
        return "too close to call" if pv >= alpha else (a["name"] if (va > vb) == hb else b["name"]) + " leads"

    def sr(R):
        m = R["r"] / R["n"]; return 100 * m, 100 * math.sqrt(max(1e-9, R["r2"] / R["n"] - m * m) / R["n"])

    def prop(k, n):
        q = k / n; return 100 * q, 100 * math.sqrt(max(1e-9, q * (1 - q)) / n)
    for label, fa, fb, hb in (("Strike rate", sr(A), sr(B), True), ("Dismissals per 100 balls", prop(A["outs"], A["n"]), prop(B["outs"], B["n"]), False),
                              ("Boundary %", prop(A["bnd"], A["n"]), prop(B["bnd"], B["n"]), True)):
        dims.append({"label": label, "a": round(fa[0], 1), "b": round(fb[0], 1), "verdict": verdict(fa[0], fa[1], fb[0], fb[1], hb)})
    leads = [f"{d['label'].lower()}: {d['verdict']}" for d in dims]
    return {**base, "status": "ok",
            "answer": f"{a['name']} v {b['name']} {scope}: " + "; ".join(f"{d['label'].lower()} {d['a']:g} v {d['b']:g}" for d in dims) + ". " + "; ".join(leads) + ".",
            "numbers": [{"label": f"{d['label']}", "value": f"{d['a']:g} v {d['b']:g}"} for d in dims],
            "definition": f"{A['n']:,} v {B['n']:,} balls, all covered T20 and ODI balls unless a format is named. A lead needs a two-sided test at 0.05 ÷ 3 measures; otherwise 'too close to call'. No overall score.",
            "link": {"kind": "compare", "ids": [a["person_id"], b["person_id"]]},
            "items": [{"label": "Open the full comparison", "value": "→", "href": f"/compare?ids={a['person_id']},{b['person_id']}", "sub": "scoring, survival, match states, timeline, records"}]}


def _team_chases(db, it, f, scope, base):
    team = next((n["team"] for n in it.notes if "team" in n), None)
    if not team:
        return {**base, "status": "needs_clarification", "message": "Name a team, e.g. \"India's biggest successful T20 chases\"."}
    names = team_names(team)
    w, p = [f"i2_team IN ({','.join('?' * len(names))})", "winner = i2_team", "i2_runs IS NOT NULL"], list(names)
    fl = it.filters
    for key, col in (("format", "format_group"), ("competition", "competition"), ("team_type", "team_type")):
        if fl.get(key):
            w.append(f"{col} = ?"); p.append(fl[key])
    if it.gender:
        w.append("gender = ?"); p.append(it.gender)
    if fl.get("year_from"):
        w.append("year >= ?"); p.append(fl["year_from"])
    if fl.get("year_to"):
        w.append("year <= ?"); p.append(fl["year_to"])
    if fl.get("before_date"):
        w.append("start_date < ?::DATE"); p.append(str(fl["before_date"]))
    if fl.get("opposition"):
        on = team_names(fl["opposition"])
        w.append(f"i1_team IN ({','.join('?' * len(on))})"); p.extend(on)
    rows = db.q(f"""SELECT match_id, i1_team, i2_runs, i2_wkts, i1_runs, start_date, competition, method, gender, format_group FROM team_results
                    WHERE {' AND '.join(w)} ORDER BY i2_runs DESC LIMIT 10""", p)
    if not rows:
        return {**base, "status": "ok", "answer": f"No successful chases by {team} {scope}.", "numbers": []}
    r0 = rows[0]
    return {**base, "status": "ok",
            "answer": f"{team}'s biggest successful chase {scope}: {r0['i2_runs']}/{r0['i2_wkts']} against {r0['i1_team']} ({r0['start_date']}), chasing {r0['i1_runs'] + 1}.",
            "numbers": [], "items": _items(rows, lambda r: f"{r['i2_runs']}/{r['i2_wkts']} v {r['i1_team']}", lambda r: r["format_group"],
                                           lambda r: f"/match/{r['match_id']}", lambda r: f"{r['competition'] or ''} · {r['start_date']}" + (f" · {r['method']}" if r["method"] else "")),
            "definition": "Second-innings totals in matches the chasing side won. Rain-adjusted results are labelled with their method.",
            "link": {"kind": "record", "id": f"biggest-chases.{it.gender or rows[0]['gender']}.{it.filters.get('format') or rows[0]['format_group']}"}}


def _battle_dismissals(db, it, f, scope, base):
    a, b = it.subject, it.opponent
    w, p = f.where("batter")
    rows = db.q(f"""SELECT delivery_id, match_id, kind, route, start_date, phase, over, ball_label, batter_runs_before, batter_balls_before, competition
                    FROM dis WHERE player_out_id = ? AND bowler_id = ? AND bowler_credited AND {w} ORDER BY start_date""", [a["person_id"], b["person_id"], *p])
    total = db.q1("SELECT count(*) AS n FROM dis WHERE player_out_id = ? AND bowler_id = ? AND bowler_credited", [a["person_id"], b["person_id"]])["n"]
    if not rows:
        return {**base, "status": "ok", "answer": f"None of {b['name']}'s {total} dismissals of {a['name']} came {scope}.", "numbers": [],
                "link": {"kind": "battle", "bat": a["person_id"], "bowl": b["person_id"]}}
    return {**base, "status": "ok",
            "answer": f"{len(rows)} of {b['name']}'s {total} dismissals of {a['name']} came {scope}.", "numbers": [],
            "items": _items(rows, lambda r: f"{r['kind']} · over {r['ball_label']}", lambda r: f"{r['batter_runs_before']}({r['batter_balls_before']})",
                            lambda r: f"/delivery/{r['delivery_id']}", lambda r: f"{r['competition'] or ''} · {r['start_date']} · {r['phase']}"),
            "definition": "Bowler-credited dismissals of the batter by that bowler. Value = the batter's score (balls) before the wicket ball.",
            "link": {"kind": "battle", "bat": a["person_id"], "bowl": b["person_id"]}}
