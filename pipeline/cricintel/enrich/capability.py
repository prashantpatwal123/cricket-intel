"""Field-level data capability audit (Phase 6). The single source of truth for /data and docs/data/capability-audit.*.

Static facts (source, licence, access …) are written down per field; coverage is MEASURED from the dataset where the
field exists at all. UNKNOWN means UNKNOWN: no field below is marked available on assumption.
Status: "available" (✓), "partial" (△), "unavailable" (✕).

Evidence for "not in Cricsheet": docs/data/cricsheet-schema-observed.json lists every key present in all 10,247
files (per-delivery keys: batter, bowler, non_striker, runs, extras, wickets{kind, player_out, fielders{name, substitute}},
review, replacements). There is no line, length, speed, coordinates, shot, direction, contact or position key.
"""
from __future__ import annotations

from ..db import DB

CS = "Cricsheet ball-by-ball (match data)"
CS_LIC = "UNRESOLVED: no licence statement found for match data; site footer 'All rights reserved'. Internal preview only."
WD = "Wikidata (CC0), joined via the Cricsheet Register's ESPNcricinfo id (P2697)"
NONE = "No source available to CRICINTEL"


def _f(field, group, status, source, authority, licence, commercial, coverage, depth, live, granularity, confidence, cost, access,
       redistribution, usable, notes="", unlock=""):
    return dict(field=field, group=group, status=status, source=source, source_authority=authority, licence=licence,
                commercial_use=commercial, coverage=coverage, historical_depth=depth, live_availability=live, granularity=granularity,
                confidence=confidence, cost=cost, access=access, redistribution=redistribution, usable_now=usable, notes=notes, unlock=unlock)


def _pct(a, b):
    return round(100.0 * a / b, 1) if b else 0.0


def measure(db: DB) -> dict:
    m = {}
    q1 = db.q1
    m["deliveries"] = q1("SELECT count(*) AS n FROM balls")["n"]
    r = q1("""SELECT count(*) FILTER (WHERE bowler_family IS NOT NULL) AS fam, count(*) FILTER (WHERE bowler_style IS NOT NULL) AS sty,
                     count(*) FILTER (WHERE bowler_arm IS NOT NULL) AS arm, count(*) FILTER (WHERE batter_hand IS NOT NULL) AS hand FROM balls""")
    m.update({k: _pct(v, m["deliveries"]) for k, v in r.items()})
    players = q1("SELECT count(*) AS n FROM player_profile")["n"]
    for fld in ("bowling_style", "bowling_arm", "batting_hand", "role", "wicketkeeper"):
        n = q1("SELECT count(DISTINCT person_id) AS n FROM player_metadata WHERE field = ?", [fld])["n"]
        m[f"players_{fld}"] = _pct(n, players)
    m["players"] = players
    tm = q1("SELECT count(*) * 2 AS n FROM matches")["n"]
    m["keeper_team_matches"] = _pct(q1("SELECT count(DISTINCT match_id || team) AS n FROM keeper_inference")["n"], tm)
    c = q1("""SELECT count(*) FILTER (WHERE route = 'CAUGHT_KEEPER') AS k, count(*) FILTER (WHERE route = 'CAUGHT_KEEPER_STATUS_UNKNOWN') AS u,
                     count(*) FILTER (WHERE route IN ('CAUGHT_FIELDER', 'CAUGHT_KEEPER', 'CAUGHT_KEEPER_STATUS_UNKNOWN', 'CAUGHT_UNKNOWN_FIELDER')) AS c FROM dis""")
    m["caught_keeper_status_known"] = _pct(c["c"] - c["u"], c["c"])
    f = q1("""SELECT count(*) AS n, count(*) FILTER (WHERE EXISTS (SELECT 1 FROM wicket_fielders x WHERE x.delivery_id = w.delivery_id AND x.wicket_idx = w.wicket_idx)) AS w
              FROM wickets w WHERE kind IN ('caught', 'run out', 'stumped')""")
    m["fielder_named"] = _pct(f["w"], f["n"])
    m["batting_position"] = _pct(q1("SELECT count(*) FILTER (WHERE batter_position IS NOT NULL) AS n FROM balls")["n"], m["deliveries"])
    m["reviews"] = q1("SELECT count(*) AS n FROM reviews")["n"]
    return m


def audit(db: DB) -> dict:
    m = measure(db)
    rows = [
        # ---- player metadata
        _f("batting_handedness", "player", "unavailable", f"{WD}; Wikipedia infobox (CC BY-SA, comparison only)", "community-edited encyclopaedic",
           "CC0 (Wikidata); CC BY-SA 4.0 (Wikipedia)", "CC0: yes. CC BY-SA: attribution + share-alike; legal review required",
           f"{m['hand']}% of deliveries. Wikidata P552 is generic handedness on 29 of 31,699 cricketer items, not batting hand.",
           "career-level", "n/a (static)", "player", "Wikidata: none usable; Wikipedia: high for pilot players, licence blocks use",
           "free", "SPARQL / MediaWiki API via GitHub runner", "Wikipedia: share-alike", False,
           "Pilot: 8/8 players have batting hand in Wikipedia infoboxes, 0/8 in Wikidata.",
           "Licence review of Wikipedia-derived facts, or a licensed player feed"),
        _f("bowling_handedness", "player", "partial", WD, "community-edited", "CC0", "yes",
           f"{m['arm']}% of deliveries; {m['players_bowling_arm']}% of players", "career", "n/a", "player",
           "medium: Wikidata labels are coarse ('fast bowling' carries no arm)", "free", "SPARQL via GitHub runner", "none (CC0)", True,
           "Only where the Wikidata label states the arm (e.g. 'left-arm orthodox spin')."),
        _f("bowling_style", "player", "partial", WD, "community-edited", "CC0", "yes",
           f"{m['sty']}% of deliveries; {m['players_bowling_style']}% of players (family known on {m['fam']}% of deliveries)", "career", "n/a",
           "player (career style, not per delivery)", "medium; mapping confidence recorded per value", "free", "SPARQL via GitHub runner", "none (CC0)", True,
           "Pilot: 0/8 pilot players have P2545 in Wikidata; Wikipedia has 8/8 (licence review pending).",
           "More CC0 values, licence-cleared Wikipedia extraction, or a licensed player feed"),
        _f("wicketkeeper_identity", "player", "partial", f"{CS} (derived)", "derived from observed stumpings and career usage", CS_LIC, "UNKNOWN (match-data licence unresolved)",
           f"keeper identified in {m['keeper_team_matches']}% of team-matches; keeper status known for {m['caught_keeper_status_known']}% of catches",
           "all covered matches", "derivable from events in a replay", "team-match", "0.90–0.97 per inference method (measured)", "free", "download",
           "as match data", True, "Cricsheet does not mark the keeper. DERIVED, never assumed; ambiguous cases stay 'unknown'."),
        _f("player_role", "player", "partial", f"{CS} (derived) + {WD}", "derived from usage", f"{CS_LIC}; CC0", "UNKNOWN for derived values",
           f"{m['players_role']}% of players", "career", "n/a", "player", "0.95 (derived rule)", "free", "download", "as match data", True),
        _f("batting_position", "event", "available", CS, "official scorers' order as published by Cricsheet", CS_LIC, "UNKNOWN",
           f"{m['batting_position']}% of deliveries", "all covered matches", "yes (order of arrival)", "innings", "high (observed order)", "free", "download",
           "as match data", True, "DERIVED from the order batters appear."),
        _f("bowling_spell", "event", "available", f"{CS} (derived)", "derived", CS_LIC, "UNKNOWN", "100% of deliveries", "all covered matches", "yes",
           "over", "rule-based (overs with at most one over between them)", "free", "download", "as match data", True, "Ends are not recorded."),
        # ---- delivery geometry
        *[_f(fld, grp, "unavailable", NONE, "—", "—", "—", "0%", "—", "—", "—", "—", "QUOTE REQUIRED (commercial)", "—", "—", False,
             "Not a key in any of the 10,247 Cricsheet files (observed schema).", unlock)
          for fld, grp, unlock in [
              ("delivery_speed", "geometry", "Licensed ball-tracking-derived feed"),
              ("release_speed", "geometry", "Licensed ball-tracking feed"),
              ("line", "geometry", "Licensed feed with coded or tracked line"),
              ("length", "geometry", "Licensed feed with coded or tracked length"),
              ("pitch_coordinates", "geometry", "Tracking-derived feed"),
              ("bounce", "geometry", "Tracking"), ("swing", "geometry", "Tracking"), ("seam_movement", "geometry", "Tracking"),
              ("spin", "geometry", "Tracking (revolutions/deviation)"), ("delivery_variation", "geometry", "Coded feed or tracking"),
              ("ball_trajectory", "geometry", "Multi-camera tracking (e.g. Hawk-Eye-class)"),
              ("landing_point", "geometry", "Tracking"),
              # shot
              ("shot_type", "shot", "Licensed coded feed (shot labels)"), ("shot_direction", "shot", "Licensed coded feed (wagon-wheel angle)"),
              ("attacking_defensive_shot", "shot", "Licensed coded feed"), ("control_false_shot", "shot", "Licensed coded feed"),
              ("boundary_destination", "shot", "Coded feed with landing zone"),
              # contact
              ("edge", "contact", "Licensed feed with edge flags (validated); commentary text is not ground truth"),
              ("bat_contact_location", "contact", "Tracking or sensor bat data"),
              ("foot_movement", "contact", "Tracking or coded video"), ("batter_position_at_contact", "contact", "Tracking"),
              # fielding
              ("fielder_position", "fielding", "Coded feed or tracking"), ("field_configuration", "fielding", "Coded feed (field settings)"),
              ("catch_position", "fielding", "Coded feed or tracking"), ("run_out_location", "fielding", "Coded feed (end) or tracking"),
          ]],
        _f("fielder_identity", "fielding", "partial", CS, "official scorecards via Cricsheet", CS_LIC, "UNKNOWN",
           f"named on {m['fielder_named']}% of caught / run-out / stumped dismissals; never for non-dismissal balls",
           "all covered matches", "yes (with the wicket)", "dismissal", "high (observed); substitutes flagged", "free", "download", "as match data", True,
           "Who caught it, never where."),
        _f("dismissal_kind", "event", "available", CS, "official scorers", CS_LIC, "UNKNOWN", "100% of dismissals", "all covered matches", "yes",
           "dismissal", "high", "free", "download", "as match data", True),
        _f("ball_outcome", "event", "available", CS, "official scorers", CS_LIC, "UNKNOWN", f"100% of {m['deliveries']:,} deliveries", "all covered matches",
           "yes", "delivery", "high", "free", "download", "as match data", True, "Runs, extras by type, boundary flag (four/six), wickets."),
        _f("drs_review", "event", "partial", CS, "official", CS_LIC, "UNKNOWN", f"{m['reviews']:,} reviews recorded (where Cricsheet records them)",
           "recent internationals mainly", "yes", "delivery", "high where present", "free", "download", "as match data", True,
           "Who reviewed and the decision; not ball-tracking output."),
    ]
    counts = {s: sum(1 for r in rows if r["status"] == s) for s in ("available", "partial", "unavailable")}
    return {"fields": rows, "counts": counts, "measured": m,
            "evidence": "docs/data/cricsheet-schema-observed.json (every key in all 10,247 files); coverage measured from the working DB",
            "legend": {"available": "✓", "partial": "△", "unavailable": "✕"}}


if __name__ == "__main__":
    import argparse
    import json
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", default="cricsheet")
    a = ap.parse_args()
    print(json.dumps(audit(DB(a.dataset)), indent=1, default=str))
