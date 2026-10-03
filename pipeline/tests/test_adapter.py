"""Cricsheet adapter: edge cases from the documented format."""
import copy

import pytest

from cricintel.sources.cricsheet import Quarantine, parse_match

BASE = {
    "meta": {"data_version": "1.1.0", "created": "2024-01-01", "revision": 1},
    "info": {
        "balls_per_over": 6, "dates": ["2024-01-01"], "gender": "female", "match_type": "T20", "overs": 20,
        "teams": ["A", "B"], "team_type": "international",
        "players": {"A": ["a1", "a2", "a3"], "B": ["b1", "b2", "b3"]},
        "registry": {"people": {"a1": "pa1", "a2": "pa2", "a3": "pa3", "b1": "pb1", "b2": "pb2", "b3": "pb3"}},
        "outcome": {"winner": "B", "by": {"wickets": 2}},
    },
    "innings": [
        {"team": "A", "overs": [{"over": 0, "deliveries": [
            {"batter": "a1", "bowler": "b1", "non_striker": "a2", "runs": {"batter": 0, "extras": 1, "total": 1}, "extras": {"wides": 1}},
            {"batter": "a1", "bowler": "b1", "non_striker": "a2", "runs": {"batter": 4, "extras": 0, "total": 4}},
            {"batter": "a1", "bowler": "b1", "non_striker": "a2", "runs": {"batter": 0, "extras": 0, "total": 0},
             "wickets": [{"player_out": "a1", "kind": "caught", "fielders": [{"name": "b2"}]}]},
            {"batter": "a3", "bowler": "b1", "non_striker": "a2", "runs": {"batter": 1, "extras": 1, "total": 2}, "extras": {"noballs": 1}},
            {"batter": "a2", "bowler": "b1", "non_striker": "a3", "runs": {"batter": 0, "extras": 0, "total": 0},
             "wickets": [{"player_out": "a3", "kind": "run out", "fielders": [{"name": "b3"}, {"name": "sub1", "substitute": True}]}]},
        ]}]},
        {"team": "B", "target": {"runs": 8, "overs": 20}, "overs": [{"over": 0, "deliveries": [
            {"batter": "b1", "bowler": "a1", "non_striker": "b2", "runs": {"batter": 6, "extras": 0, "total": 6}},
            {"batter": "b1", "bowler": "a1", "non_striker": "b2", "runs": {"batter": 2, "extras": 0, "total": 2}},
        ]}]},
    ],
}


def parse(doc=None):
    return parse_match(copy.deepcopy(doc or BASE), "m1", "cricsheet", "test", "sha")


def test_counts_and_legal_balls():
    out = parse()
    d = out["deliveries"]
    assert len(d) == 7
    assert [x["legal"] for x in d[:5]] == [False, True, True, False, True]
    assert d[0]["ball_label"] == "0.1" and d[1]["ball_label"] == "0.1" and d[2]["ball_label"] == "0.2"


def test_context_derivation():
    d = parse()["deliveries"]
    assert d[2]["score_before"] == 5 and d[2]["wickets_before"] == 0
    assert d[3]["wickets_before"] == 1
    assert d[3]["batter_balls_before"] == 0  # new batter
    chase = [x for x in d if x["innings_no"] == 2]
    assert chase[0]["chasing"] and chase[0]["target_runs"] == 8 and chase[0]["runs_required"] == 8
    assert chase[0]["balls_remaining"] == 120 and abs(chase[0]["required_rate"] - 0.4) < 1e-9
    assert chase[1]["runs_required"] == 2


def test_balls_faced_excludes_wides_only():
    d = parse()["deliveries"]
    # a1 faced: wide (not faced), 4, wicket  -> 2 balls before nothing; a3's no-ball counts as faced
    assert d[2]["batter_balls_before"] == 1 and d[2]["batter_runs_before"] == 4


def test_wickets_and_fielders():
    out = parse()
    w = out["wickets"]
    assert [x["kind"] for x in w] == ["caught", "run out"]
    assert w[0]["bowler_credited"] and not w[1]["bowler_credited"]
    assert w[1]["striker_out"] is False  # a3 was non-striker
    f = out["wicket_fielders"]
    assert [(x["fielder"], x["substitute"]) for x in f] == [("b2", False), ("b3", False), ("sub1", True)]


def test_gender_never_defaulted():
    doc = copy.deepcopy(BASE)
    del doc["info"]["gender"]
    with pytest.raises(Quarantine):
        parse(doc)


def test_unknown_keys_recorded_as_drift():
    from collections import Counter
    doc = copy.deepcopy(BASE)
    doc["info"]["new_field"] = 1
    doc["innings"][0]["overs"][0]["deliveries"][0]["mystery"] = True
    drift = Counter()
    parse_match(doc, "m1", "cricsheet", "t", "s", drift)
    assert drift["info.new_field"] == 1 and drift["delivery.mystery"] == 1


def test_missing_registry_uses_flagged_fallback():
    doc = copy.deepcopy(BASE)
    del doc["info"]["registry"]["people"]["a3"]
    out = parse(doc)
    p = [x for x in out["players_in_match"] if x["name"] == "a3"][0]
    assert p["person_id"].startswith("unres:") and p["identity_resolved"] is False


def test_derived_target_when_absent():
    doc = copy.deepcopy(BASE)
    del doc["innings"][1]["target"]
    out = parse(doc)
    inn2 = out["innings"][1]
    assert inn2["target_runs"] == 8 and inn2["target_prov"] == "DERIVED"
