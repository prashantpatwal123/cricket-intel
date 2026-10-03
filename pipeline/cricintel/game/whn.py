"""Historical "What Happens Next?" — moment selection, freezing state, reveal.

Moments are drawn only from matches ON/AFTER the model's training cutoff, so the model probabilities
shown at reveal never saw the match (no leakage). The public moment id is an HMAC of the delivery id,
so the API never leaks which delivery is being asked about before the reveal.

    python -m cricintel.game.whn --dataset synthetic --n 400
"""
from __future__ import annotations

import argparse
import re
import hashlib
import hmac
import json
import random
import secrets

from ..config import MODELS
from ..db import DB
from ..model import baseline
from ..model.baseline import CLASSES, FEATURE_SQL
from . import scoring

SCHEME = "capped rarity √, ×4 cap"  # chosen in docs/game-scoring.md


def _path(dataset):
    return MODELS / f"whn-moments-{dataset}.json"


def build(db: DB, n: int = 400, seed: int = 5) -> dict:
    model = baseline.load(db.manifest["dataset"])
    cutoff = model.art["training_window"]["to_exclusive"]
    rows = db.q(FEATURE_SQL + " AND b.start_date >= ?::DATE", [cutoff])
    ctx = {r["delivery_id"]: r for r in db.q("""SELECT delivery_id, over, score_before, wickets_before, chasing, runs_required,
              balls_remaining, batter_runs_before, batter_balls_before, phase, competition, team_type, batting_team, bowling_team
              FROM balls WHERE start_date >= ?::DATE""", [cutoff])}
    FULL = {"India", "Australia", "England", "South Africa", "New Zealand", "Pakistan", "Sri Lanka", "West Indies",
            "Bangladesh", "Zimbabwe", "Ireland", "Afghanistan"}

    def prestige(c):
        """Product heuristic for a recognisable game: big leagues, ICC events, full-member internationals."""
        comp = c["competition"] or ""
        major_icc = re.search(r"World Cup|Champions Trophy", comp) and not re.search(r"Qualifier|League|Region|Challenge|Play-?off", comp)
        if comp in ("Indian Premier League", "Women's Premier League") or major_icc:
            return 3.0
        if c["team_type"] == "international" and c["batting_team"] in FULL and c["bowling_team"] in FULL:
            return 2.0
        return 0.02
    rnd = random.Random(seed)

    def interest(r):
        c = ctx[r["delivery_id"]]
        s = 1.0
        if c["chasing"] and c["balls_remaining"] is not None and c["balls_remaining"] <= 30 and 0 < (c["runs_required"] or 0) <= 50:
            s += 4  # tight finish
        if c["phase"] == "death":
            s += 1.5
        if 40 <= c["batter_runs_before"] <= 49 or 90 <= c["batter_runs_before"] <= 99:
            s += 2  # milestone in sight
        return s * prestige(c)

    picked = rnd.choices(rows, weights=[interest(r) for r in rows], k=min(n * 3, len(rows)))
    seen, moments = set(), []
    key = secrets.token_hex(16)
    for r in picked:
        if r["delivery_id"] in seen:
            continue
        seen.add(r["delivery_id"])
        p = model.predict(r)
        moments.append({"moment_id": hmac.new(key.encode(), r["delivery_id"].encode(), hashlib.sha256).hexdigest()[:16],
                        "delivery_id": r["delivery_id"], "actual": r["y"], "probs": [round(x, 4) for x in p],
                        "drivers": model.drivers(r), "context_probs": [round(x, 4) for x in model.context_probs(r)]})
        if len(moments) >= n:
            break
    art = {"dataset": db.manifest["dataset"], "model_version": model.art["model_version"], "cutoff": cutoff,
           "scheme": SCHEME, "moments": moments}
    _path(db.manifest["dataset"]).write_text(json.dumps(art))
    return {"moments": len(moments), "cutoff": cutoff}


class Game:
    def __init__(self, db: DB):
        self.db = db
        self.art = json.loads(_path(db.manifest["dataset"]).read_text())
        self.by_id = {m["moment_id"]: m for m in self.art["moments"]}

    def random_moment(self, exclude: set[str]) -> dict:
        pool = [m for m in self.art["moments"] if m["moment_id"] not in exclude] or self.art["moments"]
        return self.state(random.choice(pool)["moment_id"])

    def _card(self, did):
        from ..analytics.player import delivery_cards
        return delivery_cards(self.db, [did])[0]

    def state(self, mid: str) -> dict:
        m = self.by_id[mid]
        b = self.db.q1("SELECT * FROM balls WHERE delivery_id = ?", [m["delivery_id"]])
        prev = self.db.q("""SELECT ball_label, runs_total, n_wickets, wides, noballs, is_four, is_six FROM balls
                            WHERE match_id = ? AND innings_no = ? AND seq < ? ORDER BY seq DESC LIMIT 6""",
                         [b["match_id"], b["innings_no"], b["seq"]])
        bowl = self.db.q1("""SELECT count(*) FILTER (WHERE legal) balls, sum(runs_batter + wides + noballs) runs,
                (SELECT count(*) FROM dismissals x WHERE x.match_id = ? AND x.innings_no = ? AND x.bowler_id = ? AND x.bowler_credited
                   AND x.delivery_id IN (SELECT delivery_id FROM balls WHERE match_id = ? AND innings_no = ? AND seq < ?)) wkts
                FROM balls WHERE match_id = ? AND innings_no = ? AND bowler_id = ? AND seq < ?""",
                              [b["match_id"], b["innings_no"], b["bowler_id"], b["match_id"], b["innings_no"], b["seq"],
                               b["match_id"], b["innings_no"], b["bowler_id"], b["seq"]])
        ns = self.db.q1("""SELECT sum(runs_batter) r, count(*) FILTER (WHERE faced) bf FROM balls
                           WHERE match_id = ? AND innings_no = ? AND batter_id = ? AND seq < ?""",
                        [b["match_id"], b["innings_no"], b["non_striker_id"], b["seq"]])
        return {
            "moment_id": mid, "competition": b["competition"], "format": b["format_group"], "gender": b["gender"],
            "date": b["start_date"], "season": b["season"], "batting_team": b["batting_team"], "bowling_team": b["bowling_team"],
            "innings_no": b["innings_no"], "score": f"{b['score_before']}/{b['wickets_before']}",
            "next_ball": b["ball_label"], "overs_completed": f"{b['legal_balls_before'] // 6}.{b['legal_balls_before'] % 6}",
            "phase": b["phase"],
            "batter": {"name": b["batter"], "runs": b["batter_runs_before"], "balls": b["batter_balls_before"], "hand": b["batter_hand"]},
            "non_striker": {"name": b["non_striker"], "runs": ns["r"] or 0, "balls": ns["bf"] or 0},
            "bowler": {"name": b["bowler"], "style": b["bowler_style"], "figures": f"{(bowl['balls'] or 0) // 6}.{(bowl['balls'] or 0) % 6}-{bowl['runs'] or 0}-{bowl['wkts'] or 0}"},
            "chase": {"target": b["target_runs"], "runs_required": b["runs_required"], "balls_remaining": b["balls_remaining"],
                      "required_rate": round(b["required_rate"], 2) if b["required_rate"] else None} if b["chasing"] else None,
            "recent": [_ball_glyph(x) for x in reversed(prev)],
            "options": CLASSES, "outcome_definition": "Runs off this delivery including extras (5 counts as 4, 7+ as 6). WICKET = any dismissal.",
        }

    def reveal(self, mid: str, pick: str | None) -> dict:
        m = self.by_id[mid]
        card = self._card(m["delivery_id"])
        b = self.db.q1("SELECT match_id, innings_no, seq FROM balls WHERE delivery_id = ?", [m["delivery_id"]])
        nxt = self.db.q("""SELECT ball_label, runs_total, n_wickets, wides, noballs, is_four, is_six FROM balls
                           WHERE match_id = ? AND innings_no = ? AND seq > ? ORDER BY seq LIMIT 6""", [b["match_id"], b["innings_no"], b["seq"]])
        ai = CLASSES.index(m["actual"])
        res = {"moment_id": mid, "actual": m["actual"], "delivery": card,
               "model": {"version": self.art["model_version"], "probs": [{"outcome": c, "p": p} for c, p in zip(CLASSES, m["probs"])], "drivers": m["drivers"],
                         "trained_before": self.art["cutoff"], "prov": "MODELLED"},
               "next_balls": [_ball_glyph(x) for x in nxt]}
        mi = max(range(len(CLASSES)), key=lambda j: m["probs"][j])
        res["model"]["pick"] = CLASSES[mi]
        res["model"]["correct"] = mi == ai
        res["model"]["points"] = scoring.capped_rarity(m["probs"], mi, ai)  # the model always picks its own favourite
        res["model"]["p_actual"] = m["probs"][ai]
        res["rarity"] = {"p_actual": round(m["probs"][ai], 4),
                         "label": "expected" if m["probs"][ai] >= 0.3 else "plausible" if m["probs"][ai] >= 0.1 else "rare" if m["probs"][ai] >= 0.03 else "very rare"}
        res["match_line"] = f"{card['competition']} · {card['date']} · {card['teams'][0]} v {card['teams'][1]}"
        if pick is not None:
            if pick not in CLASSES:
                raise ValueError("bad pick")
            pi = CLASSES.index(pick)
            res["pick"] = pick
            res["correct"] = pi == ai
            res["points"] = scoring.capped_rarity(m["probs"], pi, ai)
            res["points_if_correct"] = scoring.capped_rarity(m["probs"], pi, pi)
            res["scheme"] = self.art["scheme"]
        return res


def _ball_glyph(x) -> str:
    if x["n_wickets"]:
        return "W"
    if x["wides"]:
        return f"{x['runs_total']}wd"
    if x["noballs"]:
        return f"{x['runs_total']}nb"
    return "•" if x["runs_total"] == 0 else str(x["runs_total"])


def scoring_report(db: DB) -> str:
    """Simulate schemes on ALL held-out deliveries and write docs/game-scoring.md tables."""
    model = baseline.load(db.manifest["dataset"])
    cutoff = model.art["training_window"]["to_exclusive"]
    rows = db.q(FEATURE_SQL + " AND b.start_date >= ?::DATE", [cutoff])
    samples = [(model.predict(r), CLASSES.index(r["y"])) for r in rows]
    sim = scoring.simulate(samples)
    L = [f"_Simulated on {len(samples):,} held-out deliveries ({'SYNTHETIC' if db.manifest['synthetic'] else 'real'} dataset), model {model.art['model_version']}._", ""]
    for scheme, strat in sim.items():
        L += [f"### {scheme}", "", "| Strategy | Mean pts/pick | Hit rate | Max single pick | Share of pts from top 5% picks | 20-pick session CV |", "|---|---|---|---|---|---|"]
        for s, v in strat.items():
            L.append(f"| {s} | {v['mean']} | {v['hit_rate']:.1%} | {v['max_single']} | {v['top5pct_share']:.0%} | {v['session_cv']} |")
        L.append("")
    return "\n".join(L), sim


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", default="synthetic")
    ap.add_argument("--n", type=int, default=400)
    ap.add_argument("--report", action="store_true")
    a = ap.parse_args()
    db = DB(a.dataset)
    if a.report:
        md, sim = scoring_report(db)
        print(md)
    else:
        print(build(db, a.n))
