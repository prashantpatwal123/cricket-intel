"""Ask Cricket v0 answers must equal analytics results; WHN must not leak outcomes or training data."""
import json
import re

from cricintel.analytics import player as P
from cricintel.analytics.filters import Filters
from cricintel.ask.intents import answer


def _top(db):
    return db.q1("""SELECT pp.person_id, pp.name FROM balls b JOIN player_profile pp ON pp.person_id = b.batter_id
                    WHERE pp.person_id NOT LIKE 'unres:%' GROUP BY ALL ORDER BY count(*) DESC LIMIT 1""")


def test_dismissal_count_matches_analytics(dataset):
    p = _top(dataset)
    d = P.dismissals(dataset, p["person_id"], Filters())
    for word, route in (("run out", "RUN_OUT"), ("bowled", "BOWLED"), ("stumped", "STUMPED")):
        r = answer(dataset, f"How many times has {p['name']} been {word}?")
        exp = next(x["n"] for x in d["routes"] if x["route"] == route)
        assert r["status"] == "ok" and r["numbers"][0]["value"] == exp
        assert re.search(rf"\b{exp}\b", r["answer"])


def test_numbers_in_text_come_from_payload(dataset):
    p = _top(dataset)
    b = dataset.q1("SELECT bowler AS name FROM balls WHERE batter_id = ? GROUP BY 1 ORDER BY count(*) DESC LIMIT 1", [p["person_id"]])
    for q in (f"How many runs has {p['name']} scored against {b['name']}?", f"Who has dismissed {p['name']} the most?",
              f"How does {p['name']} perform while chasing?"):
        r = answer(dataset, q)
        assert r["status"] == "ok", r
        payload = json.dumps(r["numbers"])
        for num in re.findall(r"\d+(?:\.\d+)?", r["answer"]):
            assert num in payload or num in json.dumps(r), (q, num)


def test_unknown_player_and_unsupported(dataset):
    assert answer(dataset, "How many times has Zzyzx Nobody been bowled?")["status"] == "no_entity"
    p = _top(dataset)
    assert answer(dataset, f"Is {p['name']} the greatest ever?")["status"] == "unsupported"


def test_whn_no_leakage(dataset):
    from cricintel.game.whn import Game, build
    from cricintel.model import baseline
    baseline.train(dataset, "2024-01-01")
    build(dataset, n=50)
    g = Game(dataset)
    for m in g.art["moments"][:30]:
        s = g.state(m["moment_id"])
        blob = json.dumps(s, default=str)
        assert m["delivery_id"] not in blob and "actual" not in s
        d = dataset.q1("SELECT start_date FROM balls WHERE delivery_id = ?", [m["delivery_id"]])
        assert str(d["start_date"]) >= g.art["cutoff"]  # model never saw this match
        r = g.reveal(m["moment_id"], "DOT")
        assert r["actual"] == m["actual"] and (r["points"] > 0) == (m["actual"] == "DOT")
        assert 10 <= r["points_if_correct"] <= 40
