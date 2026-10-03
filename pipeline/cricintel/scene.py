"""SceneSpec builder: renderer-agnostic description of a delivery, with provenance per element.

Coordinate frame (metres): x = lateral (+ = off side for a right-hander), y = along the pitch from
the batter's stumps (y = 0) to the bowler's stumps (y = 20.12). The frontend draws whatever it gets.
When tracking/shot/fielding enrichment rows exist (delivery_tracking etc.) they are rendered as
OBSERVED geometry. Without them, the builder emits only law-implied facts plus explicitly
RECONSTRUCTED schematic paths and UNKNOWN markers. It never fabricates a pitch point, line, length,
speed, shot or fielding position.
"""
from __future__ import annotations

PITCH_LEN = 20.12
RANK = {"OBSERVED": 0, "DERIVED": 1, "RECONSTRUCTED": 2, "MODELLED": 3, "ILLUSTRATIVE": 4}

UNKNOWN_LABELS = {
    "line": "Line", "length": "Length", "speed": "Speed", "trajectory": "Ball path",
    "pitch_point": "Pitch point", "shot": "Shot played", "direction": "Ball direction after contact",
    "fielder_position": "Fielder position", "contact": "Bat contact", "run_out_end": "End at which the run-out happened",
}


def el(kind: str, prov: str, note: str | None = None, **attrs) -> dict:
    return {"kind": kind, "prov": prov, "note": note, **attrs}


def build(card: dict, tracking: dict | None = None, shot: dict | None = None,
          fielding: list[dict] | None = None) -> dict:
    hand = (card["batter"].get("hand") or "unknown")
    E: list[dict] = [
        el("pitch", "ILLUSTRATIVE", "Standard pitch geometry (not this ground's measurements)", length=PITCH_LEN),
        el("stumps", "ILLUSTRATIVE", None, end="batter", y=0),
        el("stumps", "ILLUSTRATIVE", None, end="bowler", y=PITCH_LEN),
        el("batter", "OBSERVED" if hand != "unknown" else "ILLUSTRATIVE",
           "Generic figure. Batting hand " + ("from player metadata" if hand != "unknown" else "unknown, so drawn as a neutral icon"),
           name=card["batter"]["name"], hand=hand, y=0.6),
        el("bowler", "OBSERVED", "Bowler identity observed; run-up and release point are schematic",
           name=card["bowler"]["name"], style=card["bowler"].get("style"), y=PITCH_LEN + 1.5),
    ]
    unknown: set[str] = {"line", "length", "speed", "trajectory", "pitch_point", "shot", "direction", "contact"}
    facts = []

    if tracking:  # future: OBSERVED geometry from a licensed tracking source
        if tracking.get("pitch_x_m") is not None:
            E.append(el("pitch_point", tracking["prov"], f"source {tracking['prov_source_id']}",
                        x=tracking["pitch_x_m"], y=tracking["pitch_y_m"]))
            unknown -= {"pitch_point", "line", "length"}
        if tracking.get("speed_release_kph") is not None:
            facts.append({"label": "Speed", "value": f"{tracking['speed_release_kph']:.0f} km/h", "prov": tracking["prov"]})
            unknown.discard("speed")
        if tracking.get("trajectory_ref"):
            E.append(el("trajectory", tracking["prov"], None, ref=tracking["trajectory_ref"]))
            unknown.discard("trajectory")
    if shot and shot.get("shot_type"):
        facts.append({"label": "Shot", "value": shot["shot_type"], "prov": shot["prov"]})
        unknown.discard("shot")

    wk = card["wickets"][0] if card["wickets"] else None
    route = wk["route"] if wk else None
    schematic = "Schematic path: shows which players were involved, not the real ball flight"
    keeper_needed = route in ("CAUGHT_KEEPER", "STUMPED")
    if keeper_needed:
        kf = next((f for f in wk["fielders"] if f["role"] == "wicketkeeper"), None) if wk else None
        E.append(el("keeper", "DERIVED" if route == "CAUGHT_KEEPER" else "OBSERVED",
                    "Keeper identity " + ("inferred" if route == "CAUGHT_KEEPER" else "implied by the stumping"),
                    name=(kf or (wk["fielders"][0] if wk and wk["fielders"] else {})).get("name"), y=-1.4))

    path_to_batter = el("path", "RECONSTRUCTED", schematic, frm="bowler", to="batter")
    if route == "BOWLED":
        E += [el("path", "RECONSTRUCTED", schematic, frm="bowler", to="stumps_batter"),
              el("impact", "OBSERVED", "The ball hit the stumps (implied by the dismissal)", at="stumps_batter")]
        facts.append({"label": "Outcome", "value": "Bowled: the ball hit the stumps", "prov": "OBSERVED"})
    elif route == "LBW":
        E += [path_to_batter, el("impact", "OBSERVED", "Ball struck the batter (umpire's LBW decision)", at="batter_pad"),
              el("projection", "DERIVED", "Under the Laws, the ball must have been judged to be going on to hit the stumps",
                 frm="batter_pad", to="stumps_batter"),
              el("constraint", "DERIVED", "Under the Laws, an LBW ball cannot pitch outside leg stump", zone="outside_leg_excluded",
                 hand=hand)]
        facts.append({"label": "Law constraint", "value": "Did not pitch outside leg stump", "prov": "DERIVED"})
    elif route == "CAUGHT_KEEPER":
        E += [path_to_batter, el("path", "RECONSTRUCTED", schematic + ". The edge or contact type is unknown", frm="batter", to="keeper"),
              el("catch", "DERIVED", "Caught by the wicketkeeper", at="keeper")]
    elif route == "STUMPED":
        E += [path_to_batter, el("path", "RECONSTRUCTED", schematic, frm="batter", to="keeper"),
              el("impact", "OBSERVED", "Keeper broke the wicket with the batter out of the crease (implied by the stumping)",
                 at="stumps_batter"),
              el("batter_out_of_crease", "OBSERVED", "Out of the crease (implied by the stumping)")]
    elif route == "CAUGHT_BOWLER":
        E += [path_to_batter, el("path", "RECONSTRUCTED", schematic, frm="batter", to="bowler"),
              el("catch", "OBSERVED", "Caught by the bowler", at="bowler")]
    elif route in ("CAUGHT_FIELDER", "CAUGHT_KEEPER_STATUS_UNKNOWN", "CAUGHT_UNKNOWN_FIELDER"):
        names = ", ".join(f["name"] for f in (wk["fielders"] or []) if f.get("name")) or "unrecorded fielder"
        E += [path_to_batter,
              el("unknown_zone", "UNKNOWN", f"Caught by {names}. The fielding position is not in the data", zone="field_ring"),
              el("catch", "OBSERVED", f"Caught by {names}", at="field_ring")]
        unknown.add("fielder_position")
    elif route == "RUN_OUT":
        names = ", ".join(f["name"] for f in (wk["fielders"] or []) if f.get("name"))
        E += [el("run_out", "OBSERVED", f"Run out: {wk['player_out']}" + (f" (fielders: {names})" if names else ""),
                 striker=wk["striker_out"]),
              el("unknown_zone", "UNKNOWN", "The end at which the wicket was broken is not recorded", zone="both_ends")]
        unknown |= {"run_out_end", "fielder_position"}
    elif route == "HIT_WICKET":
        E += [path_to_batter, el("impact", "OBSERVED", "Batter broke their own wicket", at="stumps_batter")]
    elif route is None:
        r = card["runs"]
        E.append(path_to_batter)
        if r["six"] or r["four"]:
            E.append(el("unknown_zone", "UNKNOWN", f"{'Six' if r['six'] else 'Four'}: the direction is not recorded", zone="boundary"))
            unknown.add("direction")
        elif r["wides"]:
            E.append(el("label", "OBSERVED", "Wide called"))
        facts.append({"label": "Outcome", "value": _outcome_text(card), "prov": "OBSERVED"})
    else:
        E.append(path_to_batter)

    if wk:
        facts.insert(0, {"label": "Dismissal", "value": wk["route_label"], "prov": wk["route_prov"]})
    facts.append({"label": "Over", "value": card["over_ball"], "prov": "OBSERVED"})
    data_els = [e for e in E if e["kind"] not in ("pitch", "stumps", "batter", "bowler")]
    overall = max((e["prov"] for e in data_els if e["prov"] in RANK), key=lambda p: RANK[p], default="OBSERVED")
    banner = {
        "RECONSTRUCTED": "RECONSTRUCTED FROM EVENT DATA: not ball-tracking. The paths are schematic.",
        "OBSERVED": "Built from observed event data.",
        "DERIVED": "Built from observed and derived event data.",
    }.get(overall, overall)
    return {"version": "scene/v0", "frame": {"pitch_length_m": PITCH_LEN, "x": "lateral (+off side for RHB)", "y": "batter→bowler"},
            "overall_prov": overall, "banner": banner, "elements": E, "facts": facts,
            "unknowns": [{"key": k, "label": UNKNOWN_LABELS[k]} for k in sorted(unknown)],
            "has_tracking": bool(tracking), "has_shot": bool(shot and shot.get("shot_type"))}


def _outcome_text(card: dict) -> str:
    r = card["runs"]
    if r["six"]:
        return "Six"
    if r["four"]:
        return "Four"
    if r["wides"]:
        return f"Wide (+{r['extras']})"
    if r["noballs"]:
        return f"No-ball, {r['batter']} off the bat"
    if r["byes"] or r["legbyes"]:
        return f"{r['extras']} {'bye' if r['byes'] else 'leg-bye'}{'s' if r['extras'] > 1 else ''}"
    return "Dot ball" if r["total"] == 0 else f"{r['batter']} run{'s' if r['batter'] != 1 else ''}"
