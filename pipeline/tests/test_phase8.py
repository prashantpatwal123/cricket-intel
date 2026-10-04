"""Phase 8 on the synthetic dataset (engineering only): battle meetings + earlier/later split, role-adaptive layouts
(including the neutral layout for small samples), Home examples that drop rather than fake missing entities,
deterministic Ask follow-ups, and plain-language findings (no "percentile" in headlines)."""
import pytest

from cricintel.analytics import context as CX
from cricintel.ask.v1 import followups
from cricintel.fan import battle as FB, home as FH, player as FPL


@pytest.fixture(scope="module")
def fdb(dataset):
    CX.build_context("synthetic")
    from cricintel.db import connect
    return connect("synthetic")


def test_meetings_one_row_per_match_and_halves_add_up(fdb):
    pair = fdb.q1("SELECT batter_id, bowler_id, balls, runs FROM battles ORDER BY balls DESC LIMIT 1")
    m = FB.meetings(fdb, pair["batter_id"], pair["bowler_id"])
    ids = [r["match_id"] for r in m["rows"]]
    assert len(ids) == len(set(ids)) == m["count"] > 0
    assert [r["date"] for r in m["rows"]] == sorted(r["date"] for r in m["rows"])
    total_balls = sum(r["balls"] for r in m["rows"])
    if m["change"]:
        e, l = m["change"]["earlier"], m["change"]["later"]
        assert e["balls"] + l["balls"] == total_balls
        assert e["meetings"] + l["meetings"] == m["count"]
        assert "forecast" in m["change"]["note"] or "noise" in m["change"]["note"]  # descriptive, never a prediction
        for h in (e, l):
            if h["out_rate_interval_90"]:
                lo, hi = h["out_rate_interval_90"]
                assert 0 <= lo <= hi <= 100
    for r in m["rows"]:
        assert r["href"].startswith("/innings/") and (r["how"] is None) == (not r["out"])


def test_layouts_are_role_adaptive_and_neutral_for_small_samples(fdb):
    big = fdb.q1("SELECT batter_id AS p FROM balls GROUP BY 1 ORDER BY count(*) DESC LIMIT 1")["p"]
    small = fdb.q1("""SELECT person_id AS p FROM player_profile pp WHERE person_id NOT LIKE 'unres:%'
                      AND (SELECT count(*) FROM balls WHERE batter_id = pp.person_id OR bowler_id = pp.person_id) BETWEEN 1 AND 60 LIMIT 1""")
    h = FPL.hero(fdb, big)
    assert h["layout"] in {"batter", "bowler", "allrounder", "keeper"}
    if small:
        hs = FPL.hero(fdb, small["p"])
        assert hs["layout"] == "neutral" and hs["kind"] == "player"


def test_home_examples_never_fake_missing_entities(fdb):
    FH._examples.cache_clear()
    ex = FH._examples(fdb)
    heroes = [e["hero"] for e in ex]
    assert "play" in heroes and len(heroes) == len(set(heroes))
    for e in ex:  # synthetic data has no Kohli / MCG: those examples must be dropped, not invented
        if e["hero"] in ("player", "battle", "ask"):
            assert fdb.q1("SELECT 1 AS x FROM player_profile WHERE person_id = ?", [FH.KOHLI])


def test_followups_are_deterministic_and_bounded():
    res = {"status": "ok", "question": "Who dismisses A most?",
           "intent": {"kind": "dismissed_by", "subject": {"person_id": "a1", "name": "Alpha Batter"}, "opponent": None},
           "numbers": [{"label": "Beta Bowler", "value": 5, "link": {"kind": "battle", "bat": "a1", "bowl": "b1"}}]}
    f1, f2 = followups(res), followups(dict(res))
    assert f1 == f2 and 1 <= len(f1) <= 2
    assert f1[0]["q"] == "Alpha Batter v Beta Bowler" and f1[1]["href"] == "/how-out/a1"
    assert followups({"status": "needs_clarification"}) == []
    # a follow-up never repeats the question just asked
    same = {**res, "intent": {"kind": "matchup", "subject": {"person_id": "a1", "name": "Alpha Batter"}, "opponent": {"person_id": "b1", "name": "Beta Bowler"}},
            "question": "Who dismisses Alpha Batter most?"}
    assert all(f.get("q") != same["question"] for f in followups(same))


def test_findings_use_plain_language_not_percentile():
    dim = {"key": "sr", "label": "Scoring rate", "description": "Runs per 100 balls", "unit": "SR", "value": 150.0, "peer_median": 125.0,
           "percentile": 97, "enough_sample": True, "n": 900, "n_unit": "balls", "min_sample": 300, "evidence": {}}
    fp = {"dimensions": [dim, {**dim, "key": "out_rate", "label": "Dismissal frequency", "percentile": 0}],
          "peer_pool": {"size": 300, "definition": "peers"}, "pid": "x", "available": True}
    items = FPL._extreme_dims(fp, "Alpha", "batting")
    assert len(items) == 2
    for it in items:
        assert "percentile" not in it["headline"].lower()
    heads = " | ".join(it["headline"] for it in items)
    assert "only 3% of them have a higher figure" in heads and "none of them has a lower figure" in heads
    assert any("97" in it["why"]["percentile"] for it in items)  # the exact figure stays one tap away


def test_tied_dismissers_read_as_a_list():
    from cricintel.ask.intents import and_list
    assert and_list(["A"]) == "A"
    assert and_list(["A", "B"]) == "A and B"
    assert and_list(["Dale Steyn", "Chris Woakes", "Umesh Yadav", "Morne Morkel"]) == "Dale Steyn, Chris Woakes, Umesh Yadav and Morne Morkel"
