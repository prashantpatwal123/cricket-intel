"""Phase 7 fan layer on the synthetic dataset (engineering only): knowledge graph, Rabbit-Hole ranking and session
penalties, Records V2, validated similarity, BH-protected "didn't know" facts, Player Stories language, matchup rules,
Compare V2 (no single score), On This Day anniversary rule, spoiler-safe Play moments and the new Ask kinds."""
import re
from collections import Counter

import pytest

from cricintel.analytics import context as CX
from cricintel.fan import compare as CMP, didnt_know as DK, kg, moments as MO, onthisday as OTD, player as FPL, rabbit as RB, records2 as R2, similar as SM

CAUSAL = re.compile(r"\b(because|handles? pressure|clutch|loses concentration|nerves|choke|mental)\b", re.I)


@pytest.fixture(scope="module")
def fdb(dataset):
    CX.build_context("synthetic")
    from cricintel.db import connect
    db = connect("synthetic")
    R2.build(db); R2.load.cache_clear()
    SM.build(db); SM.load.cache_clear()
    return db


@pytest.fixture(scope="module")
def ids(fdb):
    bat = fdb.q1("SELECT batter_id AS p FROM balls GROUP BY 1 ORDER BY count(*) DESC LIMIT 1")["p"]
    bowl = fdb.q1("SELECT bowler_id AS p FROM balls GROUP BY 1 ORDER BY count(*) DESC LIMIT 1")["p"]
    pair = fdb.q1("SELECT batter_id, bowler_id FROM battles ORDER BY balls DESC LIMIT 1")
    inn = fdb.q1("SELECT match_id, innings_no, batter_id FROM bat_innings ORDER BY runs DESC LIMIT 1")
    sp = fdb.q1("SELECT match_id, innings_no, bowler_id FROM bowl_innings ORDER BY wickets DESC, runs LIMIT 1")
    mid = fdb.q1("SELECT match_id FROM team_results WHERE i2_runs IS NOT NULL ORDER BY match_id LIMIT 1")["match_id"]
    return {"bat": bat, "bowl": bowl, "battle": f"{pair['batter_id']}|{pair['bowler_id']}", "innings": f"{inn['match_id']}|{inn['innings_no']}|{inn['batter_id']}",
            "spell": f"{sp['match_id']}|{sp['innings_no']}|{sp['bowler_id']}", "match": mid}


# ---------------------------------------------------------------- knowledge graph
def test_every_major_entity_type_has_real_next_steps(fdb, ids):
    for typ, key in (("player", ids["bat"]), ("player", ids["bowl"]), ("battle", ids["battle"]), ("innings", ids["innings"]),
                     ("spell", ids["spell"]), ("match", ids["match"])):
        edges = kg.neighbours(fdb, typ, key)
        assert len(edges) >= 3, (typ, key, edges)
        for e in edges:
            assert e["id"] != kg.node(typ, key), "an entity must not link to itself"
            assert e["href"].startswith("/") and e["type"] in kg.NODE_TYPES
            assert e["relation"] in kg.RELATION_PRIOR, e["relation"]
            assert all(0 <= v <= 1 for v in e["f"].values()), e["f"]
            assert e["reason"]


def test_battle_edges_are_real_meetings(fdb, ids):
    for e in kg.neighbours(fdb, "player", ids["bat"]):
        if e["type"] == "battle" and e["relation"] in ("dismissed_by", "dominated"):
            bat, bowl = e["id"].split(":", 1)[1].split("|")
            n = fdb.q1("SELECT count(*) AS n FROM balls WHERE batter_id = ? AND bowler_id = ?", [bat, bowl])["n"]
            assert n > 0 and bat == ids["bat"]


# ---------------------------------------------------------------- Rabbit-Hole engine
def test_rabbit_is_deterministic_and_never_repeats_an_entity(fdb, ids):
    a = RB.explore_next(fdb, "player", ids["bat"])
    b = RB.explore_next(fdb, "player", ids["bat"])
    assert [x["id"] for x in a["items"]] == [x["id"] for x in b["items"]]
    assert len({x["id"] for x in a["items"]}) == len(a["items"])
    assert len(a["items"]) <= 6


def test_rabbit_diversifies_relations():
    def e(i, rel, typ="battle"):
        return {"id": f"{typ}:{i}", "href": f"/x/{i}", "type": typ, "relation": rel, "label": i, "reason": "r",
                "f": {"sample": 1, "strength": 1, "unusual": 1, "recency": 1, "recog": 1, "prior": 1}}
    edges = [e(str(i), "dismissed_by") for i in range(8)] + [e("p", "partner", "partnership"), e("m", "latest_match", "match")]
    out = RB.rank(edges, k=4)
    assert Counter(x["relation"] for x in out)["dismissed_by"] < 4, "one relation must not fill the list"


def test_session_memory_pushes_visited_destinations_down(fdb, ids):
    first = RB.explore_next(fdb, "player", ids["bat"])["items"]
    top = first[0]
    again = RB.explore_next(fdb, "player", ids["bat"], seen=[top["id"]])["items"]
    pos = next((i for i, x in enumerate(again) if x["id"] == top["id"]), 99)
    assert pos > 0, "a visited destination must not stay first"
    assert next(x for x in again if x["id"] == top["id"])["why"]["seen_this_session"] if pos < 99 else True


def test_chain_never_revisits(fdb, ids):
    path = RB.chain(fdb, "player", ids["bat"], 6)
    assert len({p["id"] for p in path}) == len(path)
    assert kg.node("player", ids["bat"]) not in {p["id"] for p in path}


# ---------------------------------------------------------------- Records V2
def test_records_have_definition_sample_coverage_and_evidence(fdb):
    d = R2.load(fdb)
    assert d["records"]
    for r in d["records"]:
        assert r["title"] and r["definition"] and r["coverage"] and r["filters"]
        for row in r["rows"]:
            assert row["href"].startswith("/") and row["rank"] >= 1
        ranks = [row["rank"] for row in r["rows"]]
        assert ranks == sorted(ranks)
    cat = R2.catalog(fdb)
    assert all(c["category"] in R2.CATEGORIES for c in cat["categories"])


def test_record_titles_are_human_readable():
    for d in R2.DEFS:
        assert not re.search(r"_|\bsr\b|pct", d["title"]), d["title"]


# ---------------------------------------------------------------- Similar Players
def test_similarity_reports_holdout_validation_and_hides_failing_pools(fdb, ids):
    s = SM.load(fdb)
    assert s and s["pools"]
    for p in s["pools"].values():
        v = p["validation"]
        assert "status" in v
    r = SM.similar(fdb, ids["bat"])
    if r["available"]:
        assert r["validation"]["status"] == "pass"
        assert "not similar quality" in r["note"]
        assert all(x["pid"] != ids["bat"] for x in r["rows"])
    else:
        assert r["reason"]


# ---------------------------------------------------------------- "You probably didn't know"
def test_benjamini_hochberg():
    # m = 5, q = 0.05: thresholds 0.01, 0.02, 0.03, 0.04, 0.05
    assert [x["p"] for x in DK.bh([{"p": p} for p in (0.0001, 0.002, 0.03, 0.04, 0.5)], q=0.05)] == [0.0001, 0.002, 0.03, 0.04]
    assert [x["p"] for x in DK.bh([{"p": p} for p in (0.0001, 0.002, 0.035, 0.045, 0.5)], q=0.05)] == [0.0001, 0.002]
    assert DK.bh([{"p": 0.9}], q=0.05) == []


def test_didnt_know_pool_obeys_sample_and_language_rules(fdb):
    for f in DK.pool(fdb):
        assert f["n"] >= DK.MIN_N[f["type"]]
        assert not CAUSAL.search(f["headline"] + f["statement"])
        assert f["href"].startswith("/")


# ---------------------------------------------------------------- Player Stories / home
def test_player_home_language_is_descriptive_not_causal(fdb, ids):
    for pid in (ids["bat"], ids["bowl"]):
        h = FPL.hero(fdb, pid)
        assert h and h["role"]["primary"] in ("batter", "bowler")
        for c in FPL.stories(fdb, pid)["cards"]:
            assert not CAUSAL.search(" ".join(str(c.get(k, "")) for k in ("title", "headline", "evidence", "comparison")))
            assert c.get("link") and c.get("prov")
        for it in FPL.different(fdb, pid)["items"]:
            assert not CAUSAL.search(it["headline"] + it["body"])
            assert it.get("why")


def test_bowler_home_leads_with_bowling(fdb, ids):
    r = kg.role(fdb, ids["bowl"])
    if r["primary"] == "bowler" and not r["allrounder"]:
        assert list(FPL.matchups(fdb, ids["bowl"])["views"]) in ([], ["as_bowler"])


def test_matchup_rivalry_label_needs_sample(fdb, ids):
    for view in FPL.matchups(fdb, ids["bat"])["views"].values():
        for rows in view.values():
            for r in rows:
                if r["label"] == "rivalry":
                    assert r["balls"] >= FPL.RIVALRY_MIN_BALLS and r["matches"] >= FPL.RIVALRY_MIN_MATCHES
                assert r["balls"] >= FPL.TINY_BALLS


# ---------------------------------------------------------------- Compare V2
def test_compare_has_per_dimension_verdicts_and_no_overall_score(fdb):
    a, b = [r["batter_id"] for r in fdb.q("SELECT batter_id FROM balls GROUP BY 1 ORDER BY count(*) DESC LIMIT 2")]
    c = CMP.compare(fdb, a, b)
    assert c["available"]
    assert not any(k in c for k in ("score", "overall", "winner"))
    assert c["alpha"] == pytest.approx(0.05 / len(c["dimensions"]), abs=1e-4)
    for d in c["dimensions"]:
        assert d["verdict"] in ("A leads", "B leads", "too close to call", "not comparable")
    assert set(c["leads"]) == {"A", "B", "tied"}


# ---------------------------------------------------------------- On This Day
def test_on_this_day_only_claims_anniversaries_for_single_day_matches(fdb):
    d = fdb.q1("SELECT start_date FROM matches WHERE format_group IN ('T20','ODI') ORDER BY start_date LIMIT 1")["start_date"]
    day = d.replace(year=d.year + 3).isoformat()
    r = OTD.on_this_day(fdb, day)
    for it in r["items"]:
        m = fdb.q1("SELECT start_date, end_date, n_days FROM matches WHERE match_id = ?", [it["match_id"]])
        assert (m["start_date"].month, m["start_date"].day) == (d.month, d.day)
        if "ago today" in it["when"]:
            assert m["end_date"] in (None, m["start_date"]) and m["n_days"] in (None, 1)


# ---------------------------------------------------------------- Play moments
def test_moment_is_pre_ball_and_cursor_points_at_that_ball(fdb, ids):
    mid, inn, pid = ids["innings"].split("|")
    m = MO.for_innings(fdb, mid, int(inn), pid)
    if not m:
        pytest.skip("innings too short for a moment")
    rows = fdb.q("SELECT delivery_id, batter_runs_before, batter_balls_before FROM live_deliveries WHERE match_id = ? ORDER BY innings_no, seq", [mid])
    nxt = rows[m["cursor"]]
    assert m["pre_ball"]["batter_runs"] == nxt["batter_runs_before"] and m["pre_ball"]["batter_balls"] == nxt["batter_balls_before"]
    assert m["href"].endswith(f"?n={m['cursor']}&game=1") and m["spoiler_safe"]
    assert "What happened next?" in m["title"]


# ---------------------------------------------------------------- Ask additions
def test_new_ask_kinds_parse_and_answer(fdb, ids):
    from cricintel.ask import v1
    name = fdb.q1("SELECT name FROM player_profile WHERE person_id = ?", [ids["bat"]])["name"]
    for q, kind in ((f"Who has {name} scored fastest against?", "scored_fastest_against"),
                    (f"What changes after {name} faces 30 balls?", "player_faced_change"),
                    (f"Which players are most similar to {name}?", "similar")):
        r = v1.ask(fdb, q)
        assert r["intent"]["kind"] == kind, (q, r["intent"]["kind"])
        assert r["interpretation"][0]["key"] == "kind"
        assert r["status"] in ("ok", "needs_clarification")
