"""Phase 3: context engine, partnerships, spells, replay/stories, state analysis, Situation Difficulty, Ask v2 parsing."""
import pytest

from cricintel.analytics import context as CX
from cricintel.model import situation as S


@pytest.fixture(scope="module")
def cdb(dataset):
    CX.build_context("synthetic")
    from cricintel.db import connect
    db = connect("synthetic")
    assert db.has_context
    return db


def test_context_rows_cover_every_limited_overs_delivery(cdb):
    n_ctx = cdb.q1("SELECT count(*) AS n FROM delivery_context")["n"]
    n_del = cdb.q1("""SELECT count(*) AS n FROM deliveries d JOIN matches m USING (match_id) JOIN innings i USING (match_id, innings_no)
                      WHERE NOT i.super_over AND m.format_group IN ('T20', 'ODI')""")["n"]
    assert n_ctx == n_del


def test_context_invariants(cdb):
    bad = cdb.q1("""SELECT count(*) FILTER (WHERE team_dot_streak < 0 OR batter_dot_streak < 0 OR team_balls_since_boundary < 0
                                        OR batter_balls_since_boundary < 0 OR recent_wickets < 0) AS neg,
                           count(*) FILTER (WHERE balls_left <> innings_balls_limit - legal_balls_before) AS left_mismatch,
                           count(*) FILTER (WHERE wickets_in_hand <> 10 - wickets_before) AS wih,
                           count(*) FILTER (WHERE batter_stage = 'new' AND batter_balls_before >= 10) AS stage,
                           count(*) FILTER (WHERE team_dot_streak > legal_balls_before) AS streak
                    FROM balls WHERE format_group IN ('T20', 'ODI')""")
    assert all(v == 0 for v in bad.values()), bad


def test_recent_window_is_format_specific(cdb):
    rows = {r["format_group"]: r["w"] for r in cdb.q("SELECT format_group, any_value(recent_window) AS w FROM balls GROUP BY 1")}
    assert rows.get("T20", 12) == 12 and rows.get("ODI", 30) == 30


def test_partnerships_partition_innings_runs(cdb):
    # every run in an innings belongs to exactly one partnership
    bad = cdb.q("""SELECT p.match_id, p.innings_no, sum(p.runs) AS pr, any_value(t.r) AS tr FROM partnerships p
                   JOIN (SELECT match_id, innings_no, sum(runs_total) AS r FROM balls GROUP BY 1, 2) t USING (match_id, innings_no)
                   GROUP BY 1, 2 HAVING sum(p.runs) <> any_value(t.r)""")
    assert not bad


def test_spells_partition_bowler_overs(cdb):
    bad = cdb.q("""SELECT s.match_id FROM spells s JOIN (SELECT match_id, innings_no, bowler_id, count(DISTINCT over) AS n FROM balls GROUP BY 1, 2, 3) b
                   USING (match_id, innings_no, bowler_id) GROUP BY s.match_id, s.innings_no, s.bowler_id HAVING count(*) <> any_value(b.n)""")
    assert not bad


def test_innings_story_matches_scorecard(cdb):
    from cricintel.analytics import replay as R
    rows = cdb.q("""SELECT match_id, innings_no, batter_id, sum(runs_batter) AS r, count(*) FILTER (WHERE wides = 0) AS b
                    FROM balls GROUP BY 1, 2, 3 ORDER BY r DESC LIMIT 5""")
    for r in rows:
        s = R.innings_story(cdb, r["match_id"], r["innings_no"], r["batter_id"])
        assert s["summary"]["runs"] == r["r"] and s["summary"]["balls"] == r["b"]
        assert s["balls"][-1]["cum_runs"] == r["r"]


def test_replay_prev_next_walk(cdb):
    from cricintel.analytics import replay as R
    did = cdb.q1("SELECT delivery_id FROM balls WHERE seq = 5 LIMIT 1")["delivery_id"]
    r = R.delivery_replay(cdb, did)
    assert r["prev_id"] and r["next_id"]
    assert R.delivery_replay(cdb, r["next_id"])["prev_id"] == did
    assert "ball path" in r["not_recorded"]


def test_state_buckets_partition_balls(cdb):
    from cricintel.analytics import states as ST
    pid = cdb.q1("SELECT batter_id FROM balls GROUP BY 1 ORDER BY count(*) DESC LIMIT 1")["batter_id"]
    r = ST.states(cdb, pid, "batting")
    g = next(x for x in r["groups"] if x["key"] == "balls_faced")
    assert sum(x["player"]["balls"] for x in g["rows"] if x["player"]) == r["baseline"]["balls"]


def _toy_model():
    res = {"format": "T20", "gender": "male", "max_overs": 20,
           "table": [[0.0] * 11] + [[round(9 * ol * (1 - w / 10.5), 2) if w < 10 else 0.0 for w in range(11)] for ol in range(1, 21)]}
    curve = {"bins": S.D_BINS, "p_fail": [min(0.99, max(0.0, (b - 0.5) / 1.2)) for b in S.D_BINS[:-1]], "n": []}
    return S.SDX({"version": "test", "models": {"T20|male": {"resources": res, "curve": curve}}})


def test_sdx_bounded_and_monotone():
    m = _toy_model()
    for b in range(1, 121, 7):
        for w in range(0, 10):
            for rr in range(1, 200, 9):
                s = m.score("T20", "male", rr, b, w)["sdx"]
                assert 0 <= s <= 100
                assert m.score("T20", "male", rr, b, w + 1)["sdx"] >= s      # a wicket never makes it easier
                assert m.score("T20", "male", rr + 1, b, w)["sdx"] >= s      # more runs needed never easier
                assert m.score("T20", "male", rr, b - 1, w)["sdx"] >= s      # a dot ball never easier
    assert m.score("T20", "male", 0, 10, 2)["sdx"] == 0.0


def test_pav_is_monotone():
    out = S._pav([1, 2, 3, 4], [0.5, 0.2, 0.6, 0.4], [1, 1, 1, 1])
    assert all(a <= b + 1e-12 for a, b in zip(out, out[1:]))


def test_ask_v2_context_parsing(cdb):
    from cricintel.ask import v1
    it = v1.parse(cdb, "Who has the highest boundary rate after 30 balls?")
    assert it.kind == "leaderboard" and it.metric == "boundary_pct" and it.filters["faced_from"] == 30
    it = v1.parse(cdb, "Who is best while chasing 10+ an over?")
    assert it.filters["rrr_from"] == 10 and it.filters["chasing"] is True and it.metric == "strike_rate"
    it = v1.parse(cdb, "Which partnerships score fastest in the death overs?")
    assert it.kind == "partnership_leaderboard" and it.metric == "run_rate" and it.filters["phase"] == "death"
    it = v1.parse(cdb, "Who improves most from middle overs to death overs?")
    assert it.kind == "phase_change" and "phase" not in it.filters
    r = v1.execute(cdb, it)
    assert r["status"] == "ok"
