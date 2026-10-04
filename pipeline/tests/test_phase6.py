"""Phase 6: provenance model, taxonomies, source versioning, live-feed compatibility of enriched deliveries, Visual Engine V2
and the capability audit (synthetic dataset and hand-built events for engineering only)."""
import json

import pytest

from cricintel.analytics import context as CX
from cricintel.enrich import provenance as PV
from cricintel.enrich.capability import audit
from cricintel.enrich.taxonomy import map_shot, normalize_batting_hand, normalize_bowling, shot_node
from cricintel.enrich.versioning import Store
from cricintel.live.contract import Event
from cricintel.live.engine import EventLog, replay


# ---------------------------------------------------------------- provenance
def test_provenance_requirements_and_illustrative_guard():
    with pytest.raises(ValueError):
        PV.Provenance("OBSERVED", source="cricsheet")                         # needs source_field
    with pytest.raises(ValueError):
        PV.Provenance("MODELLED", method="m", confidence=0.5)                 # needs model_version
    with pytest.raises(ValueError):
        PV.Provenance("ILLUSTRATIVE", method="demo", source_event_id="1:1:1") # cannot attach to a real delivery
    with pytest.raises(ValueError):
        PV.Provenance("ILLUSTRATIVE", method="demo", subject_ids=("ba607b88",))
    with pytest.raises(ValueError):
        PV.Provenance("BELIEVED", method="x")
    p = PV.observed("cricsheet", "wickets[].kind", "1:1:1").as_dict()
    assert p["provenance_type"] == "OBSERVED" and "Recorded directly" in p["why"]
    assert "does not show anything that actually happened" in PV.illustrative("demo/v1").explain()


# ---------------------------------------------------------------- taxonomy
@pytest.mark.parametrize("label,code,arm,family", [
    ("Right-arm [[Fast bowling|medium]]", "RM", "right", "pace"), ("Slow left-arm orthodox", "LO", "left", "spin"),
    ("Right-arm [[Leg-spin|Leg-Break]]", "RLB", "right", "spin"), ("left-arm unorthodox spin", "LWS", "left", "spin"),
    ("fast bowling", "PACE_FAST", None, "pace"), ("seam bowling", "PACE", None, "pace"), ("right arm", "R_UNKNOWN", "right", None),
    ("Right-arm off break", "ROB", "right", "spin")])
def test_bowling_labels_map_only_as_far_as_they_say(label, code, arm, family):
    n = normalize_bowling(label, "test")
    assert (n["canonical"], n["arm"], n["family"]) == (code, arm, family)
    assert n["original"] == label


def test_unmapped_labels_stay_unknown_and_source_notes_are_kept():
    assert normalize_bowling("medium pace swing", "x")["canonical"] is None
    n = normalize_bowling("Right-arm fast{{efn|name=s|Some sources list him as fast-medium.}}", "x")
    assert n["canonical"] == "RF" and "fast-medium" in n["note"]
    assert normalize_batting_hand("Left-handed", "x")["canonical"] == "left"
    assert normalize_batting_hand("ambidextrous", "x")["canonical"] is None


def test_shot_labels_map_to_the_level_the_source_supports():
    m = {"drive": "drive", "cover drive": "cover_drive"}
    assert map_shot("Drive", m, "v")["level"] == "family"
    assert map_shot("Cover Drive", m, "v")["canonical"] == "cover_drive"
    assert map_shot("Paddle-ish", m, "v")["mapped"] is False
    assert shot_node("reverse_sweep")["family"] == "sweep"


# ---------------------------------------------------------------- source versioning
def test_store_never_overwrites_and_resolves_by_licence_policy(tmp_path):
    st = Store(tmp_path / "obs.jsonl")
    st.add("p1", "bowling_style", "wikipedia", "Right-arm leg-break", "RLB", 0.9, "2026-10-04", "Page", "rev1")
    r = st.resolve("p1", "bowling_style")
    assert r["value"] is None and r["status"] == "blocked_by_licence"          # CC BY-SA is not product-usable yet
    st.add("p1", "bowling_style", "wikidata", "leg break", "RLB", 0.9, "2026-10-03", "Q1", "run1")
    r = st.resolve("p1", "bowling_style")
    assert (r["value"], r["used_source"], r["source_version"]) == ("RLB", "wikidata", "run1")
    assert st.add("p1", "bowling_style", "wikidata", "leg break", "RLB", 0.9, "2026-10-03", "Q1", "run1") is None   # idempotent
    st.add("p1", "bowling_style", "wikidata", "leg spin", "RLB", 0.8, "2026-10-05", "Q1", "run2")
    r = st.resolve("p1", "bowling_style")
    assert r["source_changed_since_first_seen"]["wikidata"] is True and r["history_length"] == 3
    st.add("p1", "bowling_style", "wikipedia", "Right-arm off break", "ROB", 0.95, "2026-10-06", "Page", "rev2")
    assert st.resolve("p1", "bowling_style")["sources_disagree"] is True
    reloaded = Store(tmp_path / "obs.jsonl")
    assert len(reloaded.rows) == len(st.rows)                                  # append-only file


# ---------------------------------------------------------------- live compatibility
M = "E1"
A, B, X = {"id": "a", "name": "A"}, {"id": "b", "name": "B"}, {"id": "x", "name": "X"}


def _ball(eid, idx, enrichment=None, rb=1):
    p = {"innings": 1, "over": 0, "index": idx, "batter": A, "non_striker": B, "bowler": X,
         "runs": {"batter": rb, "wides": 0, "noballs": 0, "byes": 0, "legbyes": 0, "penalty": 0}, "boundary": None, "wickets": []}
    if enrichment:
        p["enrichment"] = enrichment
    return Event(eid, M, "delivery", p)


def _prov():
    return PV.observed("licensed-feed-x", "ball.coordinates", "e1").as_dict()


def test_enriched_deliveries_flow_through_the_unchanged_engine():
    base = [Event(f"{M}:m", M, "match_meta", {"teams": ["H", "A"], "competition": "c", "format": "T20", "gender": "male", "venue": "v",
                                                 "date": "2020-01-01", "scheduled_overs": 20}),
            Event(f"{M}:s", M, "innings_start", {"innings": 1, "batting_team": "H", "bowling_team": "A", "super_over": False})]
    rich = {"L2": {"line": "outside_off", "length": "good_length", "speed_kph": 138.4, "provenance": _prov()},
            "L3": {"shot": "cover_drive", "direction_deg": 62.0, "provenance": _prov()}}
    plain_log, rich_log = EventLog(), EventLog()
    for e in base + [_ball("e1", 1), _ball("e2", 2)]:
        plain_log.add(e)
    for e in base + [_ball("e1", 1, rich), _ball("e2", 2)]:
        rich_log.add(e)
    p, r = replay(plain_log).state, replay(rich_log).state
    assert p["innings"][0]["runs"] == r["innings"][0]["runs"] and p["innings"][0]["batters"] == r["innings"][0]["batters"]
    assert r["capabilities"] == {"L2": 1, "L3": 1} and "capabilities" not in p
    assert r["innings"][0]["recent"][0]["layers"] == ["L2", "L3"]


@pytest.mark.parametrize("bad", [
    {"L2": {"line": "outside_off"}},                                                         # no provenance
    {"L2": {"line": "fourth_stump", "provenance": PV.observed("f", "x", "e").as_dict()}},    # not a canonical line
    {"L3": {"shot": "helicopter", "provenance": PV.observed("f", "x", "e").as_dict()}},      # not a canonical shot
    {"L9": {"x": 1, "provenance": PV.observed("f", "x", "e").as_dict()}},                   # unknown layer
    {"L2": {"line": "middle", "provenance": PV.illustrative("demo").as_dict()}},            # illustrative on a real ball
])
def test_bad_enrichment_is_rejected(bad):
    with pytest.raises(ValueError):
        _ball("e9", 1, bad)


# ---------------------------------------------------------------- Visual Engine V2 and audit on the synthetic dataset
@pytest.fixture(scope="module")
def vdb(dataset):
    CX.build_context("synthetic")
    from cricintel.db import connect
    return connect("synthetic")


def test_delivery_layers_never_invent_geometry(vdb):
    from cricintel.analytics.visual import delivery_layers
    did = vdb.q1("SELECT delivery_id FROM dis WHERE kind = 'caught' LIMIT 1")["delivery_id"]
    d = delivery_layers(vdb, did)
    by = {x["layer"]: x for x in d["layers"]}
    assert by["L0"]["available"] and all(not by[k]["available"] and by[k]["why_missing"] and by[k]["unlock"] for k in ("L2", "L3", "L4", "L5"))
    blob = json.dumps(d)
    for k in ('"pitch_x"', '"speed_kph"', '"trajectory"', '"direction_deg"', '"line":', '"length":'):
        assert k not in blob
    assert "not recorded" in d["text"]


def test_dismissal_dna_counts_add_up(vdb):
    from cricintel.analytics.visual import dismissal_dna
    pid = vdb.q1("SELECT player_out_id AS p FROM dis WHERE counts_as_dismissal GROUP BY 1 ORDER BY count(*) DESC LIMIT 1")["p"]
    d = dismissal_dna(vdb, pid)
    assert sum(x["n"] for x in d["tree"]["route"]) == d["total"] > 0
    sub = dismissal_dna(vdb, pid, route=d["tree"]["route"][0]["key"])
    assert sub["total"] == d["tree"]["route"][0]["n"]
    assert {x["filter"] for x in d["unavailable_filters"]} >= {"line / length", "shot"}


def test_capability_audit_marks_geometry_unavailable(vdb):
    a = audit(vdb)
    f = {r["field"]: r for r in a["fields"]}
    for k in ("line", "length", "shot_type", "edge", "ball_trajectory", "fielder_position", "delivery_speed"):
        assert f[k]["status"] == "unavailable" and f[k]["usable_now"] is False
    assert f["ball_outcome"]["status"] == "available"
    assert len(a["fields"]) >= 33
