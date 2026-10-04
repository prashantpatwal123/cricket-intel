"""Visual Cricket Engine V2 (Phase 6): layered, provenance-carrying objects for the graphical components.

Layers (progressive enhancement; a visual must work with Layer 0 alone):
  L0 event      batter, bowler, non-striker, runs, extras, boundary flag, dismissal (kind, fielders)    Cricsheet: present
  L1 metadata   batting hand, bowling arm/style (career-level), keeper status (derived)              partial
  L2 geometry   line, length, pitch point, speed                                                     absent
  L3 shot       shot type, direction                                                                 absent
  L4 contact    edge / contact location                                                              absent
  L5 tracking   trajectory, movement, player positions                                               absent
Absent layers carry `available: false`, why, and what would unlock them. Nothing is ever filled in to make a visual
render: components are written to render a sparse truthful state.
"""
from __future__ import annotations

from ..db import DB
from ..enrich.provenance import derived, observed

LAYERS = [
    ("L0", "Event", "Who faced whom, what happened, how a wicket fell"),
    ("L1", "Player metadata", "Batting hand, bowling arm and style"),
    ("L2", "Delivery geometry", "Line, length, pitch point, speed"),
    ("L3", "Shot", "Shot type and direction"),
    ("L4", "Contact", "Edge and contact location"),
    ("L5", "Tracking", "Trajectory, movement, player positions"),
]
ABSENT = {
    "L2": ("Cricsheet records no line, length, pitch point or speed (none of these keys exists in any of its 10,247 files).",
           "A licensed feed with coded or ball-tracking line/length/speed."),
    "L3": ("No shot type or direction is recorded in Cricsheet.", "A licensed coded feed with shot labels and wagon-wheel angles."),
    "L4": ("No edge or bat-contact data exists in any source available to CRICINTEL.",
           "Validated edge flags from a licensed feed, or tracking/sensor data. Commentary text is not accepted as ground truth."),
    "L5": ("No tracking data is available.", "Multi-camera ball and player tracking licensed for this use."),
}
CS = "cricsheet"


def _meta(db: DB, pid: str) -> dict:
    """Usable (licence-cleared) player metadata with provenance; unusable or missing values are reported, not filled."""
    out = {}
    for r in db.q("SELECT field, value, prov, source_id, method, confidence FROM player_metadata WHERE person_id = ? AND NOT is_override", [pid]):
        if r["field"] in ("bowling_style", "bowling_arm", "bowling_family", "batting_hand", "wicketkeeper", "role"):
            cur = out.get(r["field"])
            if cur is None or (r["source_id"] == "wikidata" and cur["source"] != "wikidata"):
                prop = {"bowling_style": "P2545 bowling style", "bowling_arm": "P2545 bowling style", "bowling_family": "P2545 bowling style",
                        "role": "P413 position played", "batting_hand": "P552 handedness", "wicketkeeper": "P413 position played"}[r["field"]]
                p = (observed("wikidata", prop, confidence=r["confidence"], licence="CC0 1.0", method=r["method"])
                     if r["prov"] == "OBSERVED" else derived(r["method"], confidence=r["confidence"], source="cricsheet events"))
                out[r["field"]] = {"value": r["value"], "source": r["source_id"], "provenance": p.as_dict()}
    return out


def delivery_layers(db: DB, did: str) -> dict | None:
    b = db.q1("""SELECT delivery_id, match_id, innings_no, ball_label, batter_id, batter, bowler_id, bowler, non_striker_id, non_striker,
                        runs_batter, runs_total, wides, noballs, byes, legbyes, is_four, is_six, batting_team, bowling_team, start_date, competition,
                        format_group, phase FROM balls WHERE delivery_id = ?""", [did])
    if not b:
        return None
    b["start_date"] = str(b["start_date"])
    from .entities import names
    nm = names(db)
    for k in ("batter", "bowler", "non_striker"):
        b[k] = nm.get(b[f"{k}_id"], b[k])
    dis = db.q("""SELECT kind, player_out_id, player_out, fielder_id, fielder, substitute, fielders, keeper_id, keeper_method, keeper_conf,
                         route, route_prov, route_confidence, route_method, bowler_credited FROM dis WHERE delivery_id = ?""", [did])
    ev = observed(CS, "deliveries[]", did, licence="Cricsheet match data (licence unresolved; internal preview)")
    L0 = {"batter": {"id": b["batter_id"], "name": b["batter"]}, "bowler": {"id": b["bowler_id"], "name": b["bowler"]},
          "non_striker": {"id": b["non_striker_id"], "name": b["non_striker"]},
          "runs": {"batter": b["runs_batter"], "total": b["runs_total"], "wides": b["wides"], "noballs": b["noballs"], "byes": b["byes"], "legbyes": b["legbyes"]},
          "boundary": 6 if b["is_six"] else 4 if b["is_four"] else None, "label": b["ball_label"],
          "dismissal": [{"kind": d["kind"], "player_out": {"id": d["player_out_id"], "name": nm.get(d["player_out_id"], d["player_out"])},
                         "fielders": [{"id": d["fielder_id"], "name": nm.get(d["fielder_id"], d["fielder"]), "substitute": bool(d["substitute"])}] if d["fielder"] else [],
                         "bowler_credited": d["bowler_credited"],
                         "keeper": {"is_keeper_catch": d["route"] == "CAUGHT_KEEPER", "status_unknown": d["route"] == "CAUGHT_KEEPER_STATUS_UNKNOWN",
                                    "provenance": derived(d["keeper_method"] or "keeper_inference", confidence=d["keeper_conf"],
                                                          source="cricsheet events").as_dict() if d["keeper_id"] else None},
                         "route": d["route"], "provenance": observed(CS, "wickets[].kind", did).as_dict()} for d in dis]}
    meta = {"batter": _meta(db, b["batter_id"]), "bowler": _meta(db, b["bowler_id"])}
    l1_avail = any(meta[s].get(k) for s, ks in (("batter", ("batting_hand",)), ("bowler", ("bowling_style", "bowling_arm", "bowling_family"))) for k in ks)
    layers = [{"layer": "L0", "name": LAYERS[0][1], "available": True, "data": L0, "provenance": ev.as_dict()},
              {"layer": "L1", "name": LAYERS[1][1], "available": l1_avail, "partial": True, "data": meta,
               "missing": [f"{s} {k}" for s, ks in (("batter", ("batting_hand",)), ("bowler", ("bowling_style",))) for k in ks if not meta[s].get(k)],
               "why_missing": "Batting hand is in no licence-cleared source; bowling style is in CC0 Wikidata for about 6% of players only.",
               "unlock": "Licence-cleared player metadata (see docs/data/metadata-pilot.md)."}]
    for code, name, desc in LAYERS[2:]:
        why, unlock = ABSENT[code]
        layers.append({"layer": code, "name": name, "available": False, "describes": desc, "why_missing": why, "unlock": unlock})
    return {"delivery_id": did, "match": {k: b[k] for k in ("match_id", "innings_no", "batting_team", "bowling_team", "start_date", "competition", "format_group", "phase")},
            "layers": layers, "fidelity": max(int(x["layer"][1]) for x in layers if x["available"]),
            "text": describe(L0)}


def describe(L0: dict) -> str:
    """Accessible text equivalent built only from Layer 0 facts."""
    s = f"{L0['label']}: {L0['bowler']['name']} to {L0['batter']['name']}, "
    if L0["dismissal"]:
        d = L0["dismissal"][0]
        how = d["kind"]
        if d["kind"] == "caught" and d["fielders"]:
            who = d["fielders"][0]["name"]
            how = f"caught by {who}" + (" (the wicketkeeper, derived)" if d["keeper"]["is_keeper_catch"] else "")
        return s + f"{d['player_out']['name']} out, {how}. Where the ball pitched, the shot played and any edge are not recorded."
    r = L0["runs"]
    return s + (f"{L0['boundary']} runs (boundary)" if L0["boundary"] else f"{r['total']} run{'s' if r['total'] != 1 else ''}") + ". Line, length and shot are not recorded."


# ------------------------------------------------------------------ Dismissal DNA V2
ROUTE_LABEL = {"BOWLED": "Bowled", "LBW": "LBW", "CAUGHT_KEEPER": "Caught by wicketkeeper", "CAUGHT_KEEPER_STATUS_UNKNOWN": "Caught (keeper status unknown)",
               "CAUGHT_FIELDER": "Caught by a fielder", "CAUGHT_BOWLER": "Caught & bowled", "STUMPED": "Stumped", "RUN_OUT": "Run out",
               "HIT_WICKET": "Hit wicket", "RETIRED_NOT_OUT": "Retired", "OTHER": "Other (rare)", "CAUGHT_UNKNOWN_FIELDER": "Caught (fielder not recorded)"}
DIMS = {"route": "route", "bowler": "bowler_id", "format": "format_group", "phase": "phase", "style": "coalesce(bowler_family, 'unknown')"}


def dismissal_dna(db: DB, pid: str, route: str | None = None, bowler: str | None = None, fmt: str | None = None, phase: str | None = None,
                  style: str | None = None) -> dict:
    w, p = ["player_out_id = ?", "counts_as_dismissal"], [pid]
    for v, col in ((route, "route"), (bowler, "bowler_id"), (fmt, "format_group"), (phase, "phase")):
        if v:
            w.append(f"{col} = ?"); p.append(v)
    if style:
        w.append("coalesce(bowler_family, 'unknown') = ?"); p.append(style)
    where = " AND ".join(w)
    from .entities import names
    nm = names(db)
    total = db.q1(f"SELECT count(*) AS n FROM dis WHERE {where}", p)["n"]
    tree = {}
    for dim, col in DIMS.items():
        rows = db.q(f"SELECT {col} AS k, any_value(bowler) AS bname, count(*) AS n FROM dis WHERE {where} GROUP BY 1 ORDER BY n DESC LIMIT 12", p)
        tree[dim] = [{"key": r["k"], "label": ROUTE_LABEL.get(r["k"], r["k"]) if dim == "route" else (nm.get(r["k"], r["bname"]) if dim == "bowler" else r["k"]),
                      "n": r["n"]} for r in rows]
    known_style = sum(x["n"] for x in tree["style"] if x["key"] != "unknown")
    style_ok = total > 0 and known_style / total >= 0.5     # a split where most bowlers are unknown would mislead
    items = db.q(f"""SELECT delivery_id, match_id, start_date, competition, format_group, phase, bowler_id, bowler, kind, route, route_confidence,
                            fielder, batter_runs_before, batter_balls_before, ball_label, bowling_team FROM dis WHERE {where}
                     ORDER BY start_date DESC LIMIT 60""", p)
    for r in items:
        r["start_date"] = str(r["start_date"])
        r["route_label"] = ROUTE_LABEL.get(r["route"], r["route"])
        r["bowler"] = nm.get(r["bowler_id"], r["bowler"])
    keeper_unknown = db.q1(f"SELECT count(*) AS n FROM dis WHERE {where} AND route = 'CAUGHT_KEEPER_STATUS_UNKNOWN'", p)["n"]
    return {"pid": pid, "filters": {"route": route, "bowler": bowler, "format": fmt, "phase": phase, "style": style}, "total": total, "tree": tree,
            "style_coverage": {"known": known_style, "total": total, "offered": style_ok,
                               "note_offered": f"Bowling family known for {known_style} of {total} dismissals; split offered only at 50%+ coverage.", "note": "Bowling family (pace/spin) from CC0 Wikidata where available; the rest is unknown and shown as such."},
            "keeper_unknown": keeper_unknown,
            "keeper_note": "Caught by wicketkeeper is DERIVED (keeper inferred per match, 0.90–0.97 confidence); it is not the same as 'caught behind' or an edge, which are not recorded.",
            "available_filters": ["route", "bowler", "format", "phase", "bowling family (partial)"],
            "unavailable_filters": [{"filter": "line / length", "why": ABSENT["L2"][0]}, {"filter": "shot", "why": ABSENT["L3"][0]},
                                    {"filter": "edge (outside / inside / top)", "why": ABSENT["L4"][0]}],
            "items": items}


# ------------------------------------------------------------------ what we know about a battle
def battle_knowledge(db: DB, bat: str, bowl: str) -> dict:
    t = db.q1("""SELECT count(*) FILTER (WHERE faced) AS balls, sum(runs_batter) AS runs, count(DISTINCT match_id) AS matches FROM balls
                 WHERE batter_id = ? AND bowler_id = ?""", [bat, bowl])
    outs = db.q("SELECT route, count(*) AS n FROM dis WHERE player_out_id = ? AND bowler_id = ? AND bowler_credited GROUP BY 1 ORDER BY 2 DESC", [bat, bowl])
    mb, mw = _meta(db, bat), _meta(db, bowl)
    names = {r["person_id"]: r["name"] for r in db.q("SELECT person_id, name FROM player_profile WHERE person_id IN (?, ?)", [bat, bowl])}
    known = [{"item": f"{t['balls']} balls, {t['runs']} runs across {t['matches']} matches", "prov": "OBSERVED"},
             {"item": "Dismissals by kind: " + (", ".join(f"{ROUTE_LABEL.get(o['route'], o['route']).lower()} {o['n']}" for o in outs) or "none"), "prov": "OBSERVED"}]
    der = [{"item": "Strike rate, dismissal rate and their comparison with each player's usual numbers (battle page)", "prov": "DERIVED"},
           {"item": "Whether a catch was taken by the wicketkeeper (keeper inferred per match)", "prov": "DERIVED"},
           {"item": "Phase and match-situation splits", "prov": "DERIVED"}]
    meta_rows = []
    for who, pid, m, fld in (("batter", bat, mb, "batting_hand"), ("bowler", bowl, mw, "bowling_style")):
        v = m.get(fld)
        meta_rows.append({"who": names.get(pid, pid), "field": fld, "value": v["value"] if v else None,
                          "status": "known (CC0)" if v else "not in a licence-cleared source", "provenance": v["provenance"] if v else None})
    unavailable = [{"item": "Where the deliveries pitched (line and length)", "why": ABSENT["L2"][0]},
                   {"item": "Which shots were played", "why": ABSENT["L3"][0]},
                   {"item": "Whether any dismissal was an edge", "why": ABSENT["L4"][0]},
                   {"item": "Pace, turn, drift or bounce", "why": ABSENT["L5"][0]}]
    return {"batter": {"id": bat, "name": names.get(bat)}, "bowler": {"id": bowl, "name": names.get(bowl)}, "known": known, "derived": der,
            "metadata": meta_rows, "unavailable": unavailable,
            "cannot_say": "We cannot say why this matchup behaves as it does in terms of line, length, shot or spin: none of that is recorded. "
                          "We can say what happened, how often, and how that compares with each player's usual outcomes."}
