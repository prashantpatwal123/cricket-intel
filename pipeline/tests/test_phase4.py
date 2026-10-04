"""Phase 4: knowledge-graph tables, search, libraries, similar battles, related links, stories, feed, Ask V3 parsing."""
import re

import pytest

from cricintel.analytics import context as CX
from cricintel.analytics import entities as E
from cricintel.analytics import feed as F
from cricintel.analytics import libraries as L
from cricintel.analytics import related as R
from cricintel.analytics import search as S
from cricintel.analytics import stories as ST
from cricintel.analytics.graph import TEAM_CANON, canon_sql
from cricintel.ask import v1 as ask


@pytest.fixture(scope="module")
def gdb(dataset):
    CX.build_context("synthetic")
    from cricintel.db import connect
    db = connect("synthetic")
    assert db.has_context
    return db


@pytest.fixture(scope="module")
def top(gdb):
    """The highest covered innings in the synthetic data: a known entity every test can navigate from."""
    return gdb.q1("SELECT match_id, innings_no, batter_id, runs FROM bat_innings ORDER BY runs DESC, match_id LIMIT 1")


# ---------------------------------------------------------------- graph tables
def test_bat_innings_runs_equal_ball_sums(gdb):
    bad = gdb.q1("""SELECT count(*) AS n FROM bat_innings bi JOIN (
                      SELECT match_id, innings_no, batter_id, sum(runs_batter) AS r FROM balls GROUP BY 1, 2, 3) b USING (match_id, innings_no, batter_id)
                    WHERE bi.runs <> b.r""")["n"]
    assert bad == 0


def test_bowl_innings_wickets_equal_credited_dismissals(gdb):
    bad = gdb.q1("""SELECT count(*) AS n FROM bowl_innings bi JOIN (
                      SELECT b.match_id, b.innings_no, b.bowler_id, count(d.delivery_id) AS w FROM balls b
                      LEFT JOIN dis d ON d.delivery_id = b.delivery_id AND d.bowler_credited GROUP BY 1, 2, 3) x USING (match_id, innings_no, bowler_id)
                    WHERE bi.wickets <> x.w""")["n"]
    assert bad == 0


def test_battles_respect_minimum_balls(gdb):
    assert gdb.q1("SELECT count(*) FILTER (WHERE balls < 12) AS n FROM battles")["n"] == 0


def test_team_results_are_canonical(gdb):
    olds = list(TEAM_CANON)
    n = gdb.q1(f"SELECT count(*) AS n FROM team_results WHERE ta IN ({','.join('?' * len(olds))}) OR tb IN ({','.join('?' * len(olds))})", olds + olds)["n"]
    assert n == 0
    assert "Delhi Capitals" in canon_sql("x") and "Punjab Kings" in canon_sql("x")


# ---------------------------------------------------------------- search
def test_search_finds_a_player_by_prefix(gdb, top):
    idx = S.Index(S.build_index(gdb))
    name = E._nm(gdb, top["batter_id"])
    res = idx.search(name.split()[-1][:4])
    hits = [it for g in res["groups"] for it in g["items"]]
    assert any(top["batter_id"] in it["href"] for it in hits)


def test_search_empty_and_stopword_queries_return_nothing(gdb):
    idx = S.Index(S.build_index(gdb))
    assert idx.search("")["groups"] == [] and idx.search("the of")["groups"] == []


# ---------------------------------------------------------------- libraries & battles
@pytest.mark.parametrize("cat", list(L.INNINGS_CATS))
def test_innings_library_categories_run_and_define_themselves(gdb, cat):
    r = L.innings_library(gdb, cat, full_members=False)
    assert r["definition"]
    for row in r["rows"]:
        assert row["runs"] >= 0 and row["balls"] > 0


@pytest.mark.parametrize("cat", list(L.SPELL_CATS))
def test_spell_library_categories_run(gdb, cat):
    r = L.spell_library(gdb, cat, full_members=False)
    assert r["definition"]


def test_similar_battles_never_return_the_battle_itself(gdb):
    b = gdb.q1("SELECT batter_id, bowler_id FROM battles ORDER BY balls DESC LIMIT 1")
    r = L.similar_battles(gdb, b["batter_id"], b["bowler_id"])
    assert all((x["bat"], x["bowl"]) != (b["batter_id"], b["bowler_id"]) for x in r.get("rows", []))


# ---------------------------------------------------------------- rabbit hole
def test_related_links_are_deterministic_unique_and_reasoned(gdb, top):
    a = R.related(gdb, "player", top["batter_id"])
    assert len(a) >= 3
    assert a == R.related(gdb, "player", top["batter_id"])
    assert len({x["href"] for x in a}) == len(a)
    assert all(x.get("reason") for x in a)


def test_related_match_offers_at_least_three_hops(gdb, top):
    assert len(R.related(gdb, "match", top["match_id"])) >= 3


# ---------------------------------------------------------------- stories
CAUSAL = re.compile(r"\b(why|because|caused|thanks to|due to)\b", re.I)


def test_stories_have_no_causal_titles_and_carry_evidence(gdb, top):
    s = ST.innings_story(gdb, top["match_id"], top["innings_no"], top["batter_id"])
    assert s and not CAUSAL.search(s["title"])
    assert all(c.get("evidence") or c.get("href") or c.get("facts") for c in s["cards"])
    m = ST.match_story(gdb, top["match_id"])
    assert m and not CAUSAL.search(m["title"])


def test_match_events_are_chronological_and_defined(gdb, top):
    page = E.match_page(gdb, top["match_id"])
    ev = page["events"]
    keys = [(e["innings_no"], e["pos"]) for e in ev]
    assert keys == sorted(keys)
    assert all(e["definition"] for e in ev)


# ---------------------------------------------------------------- feed
def test_feed_is_deterministic_by_day_and_explains_itself(gdb):
    a, b = F.daily(gdb, "2026-01-01"), F.daily(gdb, "2026-01-01")
    assert [c["href"] for c in a["cards"]] == [c["href"] for c in b["cards"]]
    assert all(c["reason"] for c in a["cards"])
    assert len({c["href"] for c in a["cards"]}) == len(a["cards"])


# ---------------------------------------------------------------- Ask V3 parsing
def test_ask_v3_routes(gdb, top):
    name = E._nm(gdb, top["batter_id"])
    cases = {f"Show {name}'s best innings while chasing": "innings_list",
             f"Who partners {name} best?": "partners",
             f"Which bowlers have troubled {name} most?": "troubled_by",
             f"Compare {name} before and after 2020": "period_compare"}
    for q, kind in cases.items():
        assert ask.parse(gdb, q).kind == kind, q


def test_find_teams_understands_franchise_abbreviations():
    assert set(ask.find_teams("RCB v CSK")) == {"Royal Challengers Bengaluru", "Chennai Super Kings"}
