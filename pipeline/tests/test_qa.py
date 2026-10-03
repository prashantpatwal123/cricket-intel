"""QA must pass on a clean build and must CATCH injected corruption."""
import json

from cricintel import build, qa


def _status(rep, cid):
    return next(c for c in rep["checks"] if c["id"] == cid)


def test_clean_dataset_has_no_errors(dataset):
    rep = qa.run("synthetic")
    assert rep["errors"] == 0, [c for c in rep["checks"] if c["status"] == "ERROR"]


def test_injected_corruption_is_detected(dataset, raw_dir):
    files = sorted(raw_dir.glob("*.json"))
    doc = json.loads(files[0].read_text())
    bad = json.loads(json.dumps(doc))
    dl = bad["innings"][0]["overs"][0]["deliveries"]
    dl[0]["runs"]["total"] = dl[0]["runs"]["batter"] + dl[0]["runs"]["extras"] + 3      # runs.total mismatch
    dl[1]["extras"] = {"wides": 1}; dl[1]["runs"]["extras"] = 2; dl[1]["runs"]["total"] = dl[1]["runs"]["batter"] + 2  # extras mismatch
    dl[2]["bowler"] = bad["info"]["players"][bad["innings"][0]["team"]][0]          # bowler from batting side
    dl[3]["wickets"] = [{"player_out": "Nobody Atall", "kind": "bowled"}]            # player out not on the ball
    dup = files[0].with_name("8999999.json")
    dup.write_text(json.dumps(doc))                                                   # duplicate fingerprint
    corrupt = files[1].with_name("8999998.json")
    corrupt.write_text(json.dumps(bad))
    try:
        build.build("synthetic")
        rep = qa.run("synthetic")
        for cid in ("runs_total_sum", "extras_sum", "bowler_not_in_xi", "player_out_on_ball"):
            assert _status(rep, cid)["violations"] > 0, cid
        assert _status(rep, "dup_match_fingerprint")["violations"] > 0
    finally:
        dup.unlink(); corrupt.unlink()
        build.build("synthetic")
