"""Phase 5 engine tests on hand-built event streams (synthetic events for engineering edge cases only, never user-facing)."""
import itertools
import random

import pytest

from cricintel.live.contract import Event
from cricintel.live.engine import EventLog, recompute, replay

M = "T1"
A = {"id": "a", "name": "A Opener"}
B = {"id": "b", "name": "B Opener"}
C = {"id": "c", "name": "C Three"}
D = {"id": "d", "name": "D Four"}
X = {"id": "x", "name": "X Bowler"}
Y = {"id": "y", "name": "Y Bowler"}


def meta(overs=20):
    return Event(f"{M}:meta", M, "match_meta", {"teams": ["Home", "Away"], "competition": "Test Cup", "format": "T20", "gender": "male",
                                                "venue": "V", "date": "2020-01-01", "scheduled_overs": overs})


def start(k, bat="Home", bowl="Away", **kw):
    return Event(f"{M}:start:{k}", M, "innings_start", {"innings": k, "batting_team": bat, "bowling_team": bowl, "super_over": False, **kw})


def ball(eid, inn, over, idx, bat, ns, bowl, rb=0, wd=0, nb=0, by=0, lb=0, pen=0, boundary=None, wickets=()):
    return Event(eid, M, "delivery", {"innings": inn, "over": over, "index": idx, "batter": bat, "non_striker": ns, "bowler": bowl,
                                      "runs": {"batter": rb, "wides": wd, "noballs": nb, "byes": by, "legbyes": lb, "penalty": pen},
                                      "boundary": boundary, "wickets": list(wickets)})


def wk(p, kind, fielders=()):
    return {"player_out": p, "kind": kind, "fielders": list(fielders)}


def build(events):
    log = EventLog()
    for e in events:
        log.add(e)
    return log


def over0():
    """One over with every kind of extra, a boundary, a run out of the non-striker and a stumping."""
    return [meta(), start(1),
            ball("d1", 1, 0, 1, A, B, X, rb=4, boundary=4),
            ball("d2", 1, 0, 2, A, B, X, wd=1),                       # wide: no ball faced, charged to bowler
            ball("d3", 1, 0, 3, A, B, X, nb=1, rb=1),                 # no-ball + 1: faced, not legal
            ball("d4", 1, 0, 4, B, A, X, by=2),                       # byes: team runs, not bowler's
            ball("d5", 1, 0, 5, B, A, X, lb=1),                       # leg-bye
            ball("d6", 1, 0, 6, A, B, X, rb=1, wickets=[wk(B, "run out", ["F"])]),   # non-striker run out
            ball("d7", 1, 0, 7, A, C, X, wickets=[wk(A, "stumped", ["K"])]),
            ball("d8", 1, 0, 8, D, C, X, rb=6, boundary=6)]


def test_extras_and_dismissals_are_accounted_correctly():
    st = replay(build(over0())).state
    inn = st["innings"][0]
    assert inn["runs"] == 4 + 1 + 2 + 2 + 1 + 1 + 0 + 6 == 17
    assert inn["legal"] == 6 and inn["wickets"] == 2
    assert inn["extras"] == {"wides": 1, "noballs": 1, "byes": 2, "legbyes": 1, "penalty": 0}
    x = inn["bowlers"]["x"]
    assert x["runs"] == 4 + 1 + 2 + 0 + 0 + 1 + 0 + 6 == 14       # byes/leg-byes not charged
    assert x["balls"] == 6 and x["wickets"] == 1                   # stumping credited, run out not
    a = inn["batters"]["a"]
    assert (a["runs"], a["balls"], a["fours"]) == (6, 4, 1)        # wide not faced, no-ball faced
    assert inn["batters"]["b"]["out"] and inn["batters"]["b"]["how"] == "run out"
    assert [f["player"] for f in inn["fow"]] == ["B Opener", "A Opener"]
    assert inn["batters"]["d"]["sixes"] == 1
    assert inn["recent"][-1]["g"] == "6" and inn["recent"][1]["g"] == "wd"


def test_partnerships_partition_team_runs():
    inn = replay(build(over0())).state["innings"][0]
    parts = inn["partnerships"] + [inn["partnership"]]
    assert sum(p["runs"] for p in parts) == inn["runs"]
    assert [p["wicket"] for p in parts] == [1, 2, 3]


def test_retired_hurt_is_not_a_wicket_and_batter_can_return():
    ev = [meta(), start(1), ball("r1", 1, 0, 1, A, B, X, rb=1),
          ball("r2", 1, 0, 2, B, A, X, wickets=[wk(B, "retired hurt")]),
          ball("r3", 1, 0, 3, C, A, X, rb=2),
          ball("r4", 1, 0, 4, B, C, X, rb=1)]                     # B comes back
    inn = replay(build(ev)).state["innings"][0]
    assert inn["wickets"] == 0 and not inn["batters"]["b"]["out"]
    assert any(e["kind"] == "retired" for e in inn["events"])


def chase(target=8, overs=1, extra=()):
    ev = [meta(overs), start(1), ball("i1", 1, 0, 1, A, B, X, rb=6, boundary=6), ball("i2", 1, 0, 2, A, B, X, rb=1),
          Event(f"{M}:end1", M, "innings_end", {"innings": 1, "reason": "overs complete"}),
          start(2, "Away", "Home", target_runs=target, target_overs=overs),
          ball("c1", 2, 0, 1, C, D, Y, rb=4, boundary=4), ball("c2", 2, 0, 2, C, D, Y, rb=4, boundary=4), *extra]
    return ev


def test_chase_completion_and_innings_transition():
    st = replay(build(chase())).state
    i1, i2 = st["innings"]
    assert i1["closed"] and i1["close_reason"] == "overs complete"
    assert i2["target"] == 8 and i2["runs"] == 8 and i2["target_reached"]


def test_innings_break_shows_next_innings_and_target_before_any_ball():
    ev = chase()[:5] + [chase()[5]]
    st = replay(build(ev)).state
    assert [i["innings"] for i in st["innings"]] == [1, 2]
    assert st["innings"][1]["n"] == 0 and st["innings"][1]["target"] == 8


def test_revised_target_applies_from_its_position():
    ev = chase(target=20, overs=2) + [Event(f"{M}:rev", M, "target_revision",
                                            {"innings": 2, "target_runs": 9, "target_overs": 1, "after_event_id": "c1"})]
    i2 = replay(build(ev)).state["innings"][1]
    assert i2["target"] == 9 and i2["limit_balls"] == 6
    assert any(e["kind"] == "target_revision" for e in i2["events"])


def test_tie_and_super_over():
    ev = chase(target=8) [:-1] + [ball("c2", 2, 0, 2, C, D, Y, rb=3),
                                   Event(f"{M}:end2", M, "innings_end", {"innings": 2, "reason": "overs complete"}),
                                   Event(f"{M}:so3", M, "innings_start", {"innings": 3, "batting_team": "Away", "bowling_team": "Home", "super_over": True}),
                                   ball("s1", 3, 0, 1, C, D, X, rb=6, boundary=6),
                                   ball("s2", 3, 0, 2, C, D, X, wickets=[wk(C, "bowled")]),
                                   ball("s3", 3, 0, 3, A, D, X, wickets=[wk(D, "run out")])]
    st = replay(build(ev)).state
    i2, so = st["innings"][1], st["innings"][2]
    assert i2["runs"] == 7 and not i2["target_reached"]              # tie: one short of the target
    assert so["super_over"] and so["limit_balls"] == 6 and so["max_wickets"] == 2 and so["wickets"] == 2


# ---------------------------------------------------------------- look-ahead leakage
def long_innings(n=40, seed=3):
    rng = random.Random(seed)
    ev = [meta(), start(1)]
    bats, nxt = [A, B], iter([C, D, {"id": "e", "name": "E"}, {"id": "f", "name": "F"}])
    for i in range(n):
        over, idx = divmod(i, 6)
        bowler = X if over % 2 == 0 else Y
        r = rng.choice([0, 0, 1, 1, 2, 4, 6, "w"])
        if r == "w":
            out = bats[0]
            ev.append(ball(f"L{i}", 1, over, idx + 1, bats[0], bats[1], bowler, wickets=[wk(out, "bowled")]))
            bats[0] = next(nxt, {"id": f"z{i}", "name": f"Z{i}"})
        else:
            ev.append(ball(f"L{i}", 1, over, idx + 1, bats[0], bats[1], bowler, rb=r, boundary=r if r in (4, 6) else None))
            if r % 2:
                bats.reverse()
    return ev


def test_state_at_n_is_identical_whatever_happens_later():
    ev = long_innings()
    base = build(ev)
    for n in (1, 7, 18, 33):
        ref = replay(base, upto=n).hash()
        # mutate every later delivery's outcome; state at n must not move
        mutated = ev[:2 + n] + [Event(e.event_id, M, "delivery", {**e.payload, "runs": {"batter": 6, "wides": 0, "noballs": 0, "byes": 0, "legbyes": 0, "penalty": 0},
                                                                  "boundary": 6, "wickets": []}) for e in ev[2 + n:]]
        assert replay(build(mutated), upto=n).hash() == ref
        # and must equal a log that never contained the later deliveries at all, only the live-style announcement of
        # who faces and bowls next (identities, no outcome)
        nx = ev[2 + n].payload
        pre = Event(f"pre{n}", M, "pre_ball", {"innings": nx["innings"], "striker": nx["batter"], "non_striker": nx["non_striker"], "bowler": nx["bowler"]})
        assert replay(build(ev[:2 + n] + [pre])).hash() == ref


def test_pre_ball_event_cannot_carry_outcomes():
    with pytest.raises(ValueError):
        Event("p", M, "pre_ball", {"innings": 1, "striker": A, "non_striker": B, "bowler": X, "runs": {"batter": 4}})


# ---------------------------------------------------------------- arrival order, duplicates, corrections
def test_out_of_order_and_duplicate_arrival_gives_identical_state():
    ev = long_innings()
    ref = replay(build(ev)).hash()
    head, tail = ev[:2], ev[2:]
    for seed in range(5):
        shuffled = tail[:]
        random.Random(seed).shuffle(shuffled)
        dupes = shuffled + random.Random(seed + 9).sample(shuffled, 8)
        assert replay(build(head + dupes)).hash() == ref


def test_conflicting_duplicate_keeps_first_and_records_anomaly():
    ev = long_innings(10)
    bad = Event(ev[5].event_id, M, "delivery", {**ev[5].payload, "runs": {**ev[5].payload["runs"], "batter": 3}})
    log = build(ev + [bad])
    assert log.anomalies and replay(log).hash() == replay(build(ev)).hash()


def corr(eid, op, target, **kw):
    return Event(eid, M, "correction", {"op": op, "target_event_id": target, **kw})


def test_update_correction_matches_a_log_that_was_right_first_time():
    ev = long_innings()
    fixed_payload = {**ev[12].payload, "runs": {"batter": 2, "wides": 0, "noballs": 0, "byes": 0, "legbyes": 0, "penalty": 0}, "boundary": None, "wickets": []}
    right = ev[:12] + [Event(ev[12].event_id, M, "delivery", fixed_payload)] + ev[13:]
    corrected = build(ev + [corr("u1", "update", ev[12].event_id, delivery={"runs": fixed_payload["runs"], "boundary": None, "wickets": []})])
    assert replay(corrected).hash() == replay(build(right)).hash()


def test_changed_dismissal_attribution():
    ev = long_innings()
    i = next(k for k, e in enumerate(ev) if e.kind == "delivery" and e.payload["wickets"])
    p = ev[i].payload
    log = build(ev + [corr("u2", "update", ev[i].event_id, delivery={"wickets": [wk(p["batter"], "caught", ["Sub"])]})])
    st = replay(log).state["innings"][0]
    assert st["batters"][p["batter"]["id"]]["how"] == "caught"


def test_retract_and_insert():
    ev = long_innings()
    # retract ball 10, then insert it back after ball 9: must equal the original
    log = build(ev + [corr("r", "retract", ev[11].event_id)])
    assert replay(log).state["n"] == 39
    log.add(corr("i", "insert", ev[10].event_id, new_event_id=ev[11].event_id + "-again", delivery={k: v for k, v in ev[11].payload.items()}))
    a, b = replay(log).state, replay(build(ev)).state
    assert a["innings"][0]["runs"] == b["innings"][0]["runs"] and a["innings"][0]["wickets"] == b["innings"][0]["wickets"]


def test_recompute_from_checkpoint_equals_full_replay():
    ev = long_innings(60)
    log = build(ev[:40])
    eng = replay(log)
    for e in ev[40:]:                      # new balls arrive
        log.add(e)
    eng, reapplied = recompute(log, eng)
    assert eng.hash() == replay(log).hash() and reapplied < 60
    log.add(corr("late", "update", ev[50].event_id, delivery={"runs": {"batter": 3, "wides": 0, "noballs": 0, "byes": 0, "legbyes": 0, "penalty": 0}, "boundary": None, "wickets": []}))
    eng2, reapplied2 = recompute(log, eng)
    assert eng2.hash() == replay(log).hash()
    assert reapplied2 <= 60 - 42          # resumed from the checkpoint at or before ball 49, not from ball 1


def test_same_log_same_hash_every_time():
    ev = long_innings()
    assert len({replay(build(ev)).hash() for _ in range(3)}) == 1


def test_bad_events_are_rejected():
    with pytest.raises(ValueError):
        Event("x", M, "delivery", {"innings": 1, "over": 0, "index": 1, "batter": A, "non_striker": B, "bowler": X, "runs": {"batter": -1}})
    with pytest.raises(ValueError):
        Event("x", M, "nonsense", {})
    st = replay(build([meta(), ball("orphan", 1, 0, 1, A, B, X)])).state   # delivery before its innings_start arrived
    assert st["anomalies"] and st["innings"][0]["batting_team"] == "?"
