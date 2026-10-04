"""Phase 5 service tests on the synthetic dataset (engineering only): spoiler-safe responses, bounded reads, causal novelty,
Match Ask date bounds, reconciliation with recorded totals, notification design rules."""
import copy
import json
import re

import pytest

from cricintel.analytics import context as CX
from cricintel.live import notify as N
from cricintel.live import service as S
from cricintel.live.cricsheet_provider import HistoricalCricsheetProvider
from cricintel.live.engine import EventLog, replay
from cricintel.live.validate import run as reconcile


@pytest.fixture(scope="module")
def ldb(dataset):
    CX.build_context("synthetic")
    from cricintel.db import connect
    db = connect("synthetic")
    assert db.has_live
    return db


@pytest.fixture(scope="module")
def mid(ldb):
    return ldb.q1("""SELECT match_id FROM innings GROUP BY 1 HAVING count(*) = 2 AND sum(CASE WHEN target_runs IS NOT NULL THEN 1 ELSE 0 END) = 1
                     ORDER BY match_id LIMIT 1""")["match_id"]


def _blob(x):
    x = dict(x)
    x.pop("timing_ms", None)
    return json.dumps(x, sort_keys=True, default=str)


def test_engine_reconciles_with_recorded_innings_totals(ldb):
    r = reconcile(ldb, "format_group IN ('T20','ODI')", 40)
    assert r["matches"] > 0 and r["mismatches"] == 0, r["examples"]


def test_provider_never_reads_beyond_the_cursor(ldb, mid):
    p = HistoricalCricsheetProvider(ldb, mid)
    for n in (0, 1, 7, 30):
        list(p.events(n))
        assert len(p._rows) <= n


def test_response_at_n_contains_no_later_delivery_or_result(ldb, mid):
    r = S.Replay(ldb, mid)
    total = r.prov.total
    ids = [d["delivery_id"] for d in ldb.q("SELECT delivery_id FROM deliveries WHERE match_id = ? ORDER BY innings_no, seq", [mid])]
    result = r.at(total)["meta"]["result"]
    assert result
    for n in (0, 1, 12, total // 2, total - 1):
        body = _blob(S.Replay(ldb, mid).at(n))
        seen = set(re.findall(rf'"({mid}:\d+:\d+)"', body))
        assert seen <= set(ids[:n]), f"cursor {n} leaked {sorted(seen - set(ids[:n]))[:3]}"
        assert result not in body
        assert '"total"' not in body          # the length of the match is not disclosed


def test_fresh_replay_equals_long_running_replay_truncated(ldb, mid):
    long = S.Replay(ldb, mid)
    total = long.prov.total
    long.at(total)
    for n in (0, 1, total // 3, total // 2, total - 1, total):
        assert _blob(S.Replay(ldb, mid).at(n)) == _blob(long.at(n)), n


def test_novelty_memory_is_causal_and_deterministic(ldb, mid):
    a, b = S.Replay(ldb, mid), S.Replay(ldb, mid)
    total = a.prov.total
    a.at(total)                     # walks the whole match
    b.at(total // 2)                # walks only half
    for n in range(1, total // 2 + 1):
        assert a.new_at[n] == b.new_at[n]
    assert b.walk_pos == total // 2


def test_insights_are_not_announced_every_ball(ldb, mid):
    r = S.Replay(ldb, mid)
    r.at(r.prov.total)
    quiet = sum(1 for n in range(1, r.prov.total + 1) if not r.new_at.get(n))
    assert quiet / r.prov.total > 0.5


def test_match_ask_is_limited_to_before_the_match(ldb, mid):
    r = S.Replay(ldb, mid)
    n = r.prov.total // 2
    a = r.ask(n, "Who has dismissed this batter most?")
    assert any("only matches before this one" in c["label"] for c in a.get("interpretation", a.get("context_chips", [])))
    d = r.base["asof"]
    assert all(x < d for x in re.findall(r"\d{4}-\d{2}-\d{2}", json.dumps(a, default=str)) if x != d)


def test_score_pick_reveals_exactly_one_ball(ldb, mid):
    r = S.Replay(ldb, mid)
    x = r.score_pick(10, "DOT")
    assert x["cursor"] == 11 and x["state"]["replay"]["cursor"] == 11


def test_notification_plan_respects_budget_dedupe_and_never_fires_every_ball(ldb, mid):
    r = S.Replay(ldb, mid)
    tot = r.prov.total
    lg = r.log(tot)
    states = [copy.deepcopy(r._state(lg, n).state) for n in range(1, tot + 1)]
    sent = N.plan(states, r.base, set(N.PRIORITY))
    assert len({(s["type"], s["key"]) for s in sent}) == len(sent)
    for k in {s["innings"] for s in sent}:
        assert sum(1 for s in sent if s["innings"] == k and s["type"] != "wicket") <= N.PER_INNINGS
    assert len(sent) < tot / 5
    assert sent == N.plan(states, r.base, set(N.PRIORITY))
