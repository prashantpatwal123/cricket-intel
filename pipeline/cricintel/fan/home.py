"""Home (Phase 8): the first 60 seconds. Five real examples, one per hero experience, each with a fact computed from
covered data, plus today's single finding, battle and Play challenge (from the daily discovery selection)."""
from __future__ import annotations

from datetime import date
from functools import lru_cache

from ..db import DB
from ..analytics.entities import names
from . import daily

KOHLI, ZAMPA, MCG = "ba607b88", "14f96089", "1298150"


@lru_cache(maxsize=4)
def _examples(db: DB) -> list[dict]:
    """The five launch examples. Each is built only if its entities exist in the loaded dataset (an example whose
    player or match is missing is dropped, never faked)."""
    nm = names(db)
    out: list[dict] = []
    k = db.q1("SELECT sum(runs) AS r, count(*) AS i FROM bat_innings WHERE batter_id = ?", [KOHLI])
    if k and k["i"] and KOHLI in nm:
        out.append({"hero": "player", "title": f"Understand {nm[KOHLI]}", "fact": f"{k['r']:,} runs in {k['i']} covered innings. Scoring, dismissals, nemeses",
                    "href": f"/players/{KOHLI}"})
    b = db.q1("SELECT sum(balls) AS balls, sum(runs) AS runs, sum(outs) AS outs FROM battles WHERE batter_id = ? AND bowler_id = ?", [KOHLI, ZAMPA])
    if b and b["balls"] and KOHLI in nm and ZAMPA in nm:
        out.append({"hero": "battle", "title": f"{nm[KOHLI].split()[-1]} v {nm[ZAMPA].split()[-1]}", "fact": f"{b['runs']} runs off {b['balls']} balls, out {b['outs']} times",
                    "href": f"/battle?bat={KOHLI}&bowl={ZAMPA}"})
    m = db.q1("SELECT i1_runs, i2_team FROM team_results WHERE match_id = ?", [MCG])
    first = db.q1("SELECT count(*) AS n FROM live_deliveries WHERE match_id = ? AND innings_no = 1", [MCG])
    if m and m["i2_team"] and first and first["n"]:
        out.append({"hero": "match", "title": "Replay the MCG 2022 chase", "fact": f"{m['i2_team']} chasing {m['i1_runs'] + 1}, ball by ball. Historical replay, not live",
                    "href": f"/live-lab/{MCG}?n={first['n']}"})
    out.append({"hero": "play", "title": "Can you predict the next ball?", "fact": "Real moments from covered matches. Beat the model", "href": "/play"})
    tops = db.q("""SELECT bowler_id, count(*) AS n FROM dis WHERE player_out_id = ? AND bowler_credited GROUP BY 1 ORDER BY n DESC LIMIT 3""", [KOHLI])
    if tops:
        lead = [t for t in tops if t["n"] == tops[0]["n"]]
        who = " and ".join(sorted(nm.get(t["bowler_id"], t["bowler_id"]) for t in lead))
        out.append({"hero": "ask", "title": "Ask: Who dismisses Kohli most?", "fact": f"{who}: {tops[0]['n']} times{' each' if len(lead) > 1 else ''}. Then ask your own",
                    "href": "/ask?q=" + "Who%20dismisses%20Kohli%20most%3F"})
    return out


def home(db: DB, day: str | None = None, seen: set[str] | None = None) -> dict:
    d = daily.explore(db, day or date.today().isoformat(), seen)
    return {"examples": _examples(db), "finding": (d["worth_knowing"] or [None])[0], "battle": (d["battles"] or [None])[0],
            "play": (d["play"] or [None])[0], "on_this_day": (d["on_this_day"]["items"] or [None])[0], "on_this_day_label": d["on_this_day"]["label"],
            "record": (d["record_book"] or [None])[0], "rabbit_start": d["rabbit_hole"]["start"], "date": d["date"]}
