"""Cross-checks: the same quantity computed by different paths must agree."""
from cricintel import scene
from cricintel.analytics import player as P
from cricintel.analytics.filters import Filters


def _players(db, n=8):
    return [r["person_id"] for r in db.q(
        "SELECT batter_id AS person_id FROM balls GROUP BY 1 ORDER BY count(*) DESC LIMIT ?", [n])]


def test_dismissal_totals_agree(dataset):
    for pid in _players(dataset):
        prof = P.profile(dataset, pid, Filters())
        dis = P.dismissals(dataset, pid, Filters())
        assert prof["batting"]["outs"] == dis["total"], pid
        assert sum(r["n"] for r in dis["routes"]) == dis["total"]


def test_matchup_baseline_matches_profile(dataset):
    for pid in _players(dataset):
        prof = P.profile(dataset, pid, Filters())
        m = P.matchups(dataset, pid, Filters(), by="bowler", limit=10_000)
        assert m["baseline"]["balls"] == prof["batting"]["balls"]
        assert m["baseline"]["runs"] == prof["batting"]["runs"]
        assert sum(r["balls"] for r in m["rows"]) == m["baseline"]["balls"]
        assert sum(r["dismissals"] for r in m["rows"]) == m["baseline"]["dismissals"]


def test_family_groups_partition_balls(dataset):
    pid = _players(dataset, 1)[0]
    m = P.matchups(dataset, pid, Filters(), by="bowler_family")
    assert sum(r["balls"] for r in m["rows"]) == m["baseline"]["balls"]  # unknown group kept, not dropped


def test_drilldown_count_equals_aggregate(dataset):
    for pid in _players(dataset, 4):
        dis = P.dismissals(dataset, pid, Filters(format="T20"))
        for r in dis["routes"]:
            dq = P.delivery_query(dataset, Filters(format="T20"), out_id=pid, route=r["route"], limit=1)
            assert dq["total"] == r["n"], (pid, r["route"])


def test_filters_reject_unknown_keys():
    import pytest
    with pytest.raises(ValueError):
        Filters.parse({"formatt": "T20"})


def test_scene_never_invents_positions(dataset):
    ids = [r["delivery_id"] for r in dataset.q("SELECT delivery_id FROM dismissals ORDER BY delivery_id LIMIT 400")]
    for card in P.delivery_cards(dataset, ids):
        sc = scene.build(card)
        for e in sc["elements"]:
            assert e["kind"] not in ("fielder_position", "pitch_point", "trajectory"), e  # no tracking -> never drawn
        for f in card["wickets"][0]["fielders"] or []:
            assert f["position"] is None
        if card["wickets"][0]["route"] in ("CAUGHT_FIELDER", "CAUGHT_KEEPER_STATUS_UNKNOWN"):
            assert any(u["key"] == "fielder_position" for u in sc["unknowns"])
        if any(e["kind"] == "path" for e in sc["elements"]):
            assert sc["overall_prov"] == "RECONSTRUCTED"


def test_keeper_route_requires_inference(dataset):
    bad = dataset.q("""SELECT count(*) n FROM dismissals WHERE route = 'CAUGHT_KEEPER'
                       AND (keeper_id IS NULL OR fielder_id <> keeper_id)""")[0]["n"]
    assert bad == 0
