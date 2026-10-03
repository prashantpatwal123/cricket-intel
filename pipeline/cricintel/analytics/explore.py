"""Explore feed: real-data discoveries, computed once per dataset build and cached to disk."""
from __future__ import annotations

import json

from ..db import DB
from . import battle as BT
from . import insights as INS
from . import records as REC
from .filters import Filters


def feed(db: DB, n_players: int = 24) -> dict:
    path = db.dataset_dir / "derived" / "explore_cache.json"
    if path.exists():
        cached = json.loads(path.read_text())
        if cached.get("built_at") == db.manifest["built_at"]:
            return cached
    players = db.q("""SELECT b.batter_id AS pid, pp.name, pp.genders[1] AS gender, b.format_group AS fmt, count(*) AS n
                      FROM balls b JOIN player_profile pp ON pp.person_id = b.batter_id WHERE b.faced
                      GROUP BY 1, 2, 3, 4 QUALIFY row_number() OVER (PARTITION BY pp.genders[1] ORDER BY count(*) DESC) <= ?""", [n_players // 2])
    cards = []
    for p in players:
        r = INS.insights(db, p["pid"], p["fmt"], name=p["name"])
        for c in r["cards"][:2]:
            if c["stable"]:
                cards.append({**c, "player": p["name"], "person_id": p["pid"], "gender": p["gender"], "format": p["fmt"]})
    cards.sort(key=lambda c: c["p"])
    # keep variety: at most one card per player, alternate genders
    seen, picked = set(), []
    for c in cards:
        if c["person_id"] not in seen:
            seen.add(c["person_id"]); picked.append(c)
    by_g = {"male": [c for c in picked if c["gender"] == "male"], "female": [c for c in picked if c["gender"] == "female"]}
    mixed = [x for pair in zip(by_g["male"], by_g["female"]) for x in pair][:10]
    battles = BT.notable_battles(db, None, 8)
    recs = []
    for pr in REC.PRESETS[:6]:
        for g in ("male", "female"):
            lb = REC.leaderboard(db, pr["metric"], Filters.parse(pr["filters"]), pr.get("min"), 3, g)
            if lb["rows"]:
                recs.append({"preset": pr, "gender": g, "label": lb["label"], "definition": lb["definition"],
                             "min_sample": lb["min_sample"], "sample_unit": lb["sample_unit"], "top": lb["rows"][:3]})
    out = {"built_at": db.manifest["built_at"], "insights": mixed, "battles": battles, "records": recs}
    path.write_text(json.dumps(out, default=str))
    return out
