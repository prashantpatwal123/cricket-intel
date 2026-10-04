"""On This Day: matches, innings, spells and partnerships from covered data on today's calendar date.

Anniversary rule: an item is called "N years ago today" only when the match was played on a single day (end date equal to
start date, or no end date recorded and a limited-overs match). Matches that ran over more than one day (reserve days)
are listed separately as "began on this day". Dates are Cricsheet's recorded match dates; nothing is inferred.
"""
from __future__ import annotations

from datetime import date

from ..db import DB
from ..analytics.entities import names
from . import kg


def on_this_day(db: DB, day: str | None = None, k: int = 12) -> dict:
    d = date.fromisoformat(day) if day else date.today()
    md = (d.month, d.day)
    nm = names(db)
    ms = db.q("""SELECT m.match_id, m.start_date, m.end_date, m.n_days, m.team1, m.team2, m.winner, m.competition, m.event_stage, m.gender, m.format_group,
                        m.win_by_runs, m.win_by_wickets, m.result
                 FROM matches m WHERE month(m.start_date) = ? AND day(m.start_date) = ? AND m.format_group IN ('T20', 'ODI')
                 AND year(m.start_date) < ?""", [md[0], md[1], d.year])
    single = {m["match_id"] for m in ms if (m["end_date"] in (None, m["start_date"])) and (m["n_days"] in (None, 1))}
    meta = {m["match_id"]: m for m in ms}
    ids = list(meta)
    items = []
    if ids:
        ph = ",".join("?" * len(ids))
        for r in db.q(f"""SELECT match_id, innings_no, batter_id, runs, balls, not_out, team, opponent FROM bat_innings WHERE match_id IN ({ph})
                          AND (runs >= 90 OR (runs >= 50 AND balls > 0 AND runs * 1.0 / balls >= 2)) ORDER BY runs DESC LIMIT 20""", ids):
            m = meta[r["match_id"]]
            items.append(dict(kind="innings", title=f"{nm.get(r['batter_id'], r['batter_id'])} {r['runs']}{'*' if r['not_out'] else ''} ({r['balls']})",
                              detail=f"{r['team']} v {r['opponent']}" + (f" · {m['competition']}" if m["competition"] else ""),
                              href=f"/innings/{r['match_id']}/{r['innings_no']}/{r['batter_id']}", match_id=r["match_id"],
                              weight=r["runs"] / 100 + kg.recog(db, r["batter_id"]) + kg.comp_recog(m["competition"]) * 0.5))
        for r in db.q(f"""SELECT match_id, innings_no, bowler_id, wickets, runs, team, opponent FROM bowl_innings WHERE match_id IN ({ph})
                          AND wickets >= 4 ORDER BY wickets DESC, runs LIMIT 12""", ids):
            m = meta[r["match_id"]]
            items.append(dict(kind="spell", title=f"{nm.get(r['bowler_id'], r['bowler_id'])} {r['wickets']}/{r['runs']}",
                              detail=f"{r['team']} v {r['opponent']}" + (f" · {m['competition']}" if m["competition"] else ""),
                              href=f"/spell/{r['match_id']}/{r['innings_no']}/{r['bowler_id']}", match_id=r["match_id"],
                              weight=r["wickets"] / 4 + kg.recog(db, r["bowler_id"]) + kg.comp_recog(m["competition"]) * 0.5))
        for r in db.q(f"""SELECT match_id, p1, p2, runs, balls, wicket_no FROM partnerships WHERE match_id IN ({ph}) AND runs >= 120
                          ORDER BY runs DESC LIMIT 6""", ids):
            m = meta[r["match_id"]]
            items.append(dict(kind="partnership", title=f"{nm.get(r['p1'], r['p1'])} & {nm.get(r['p2'], r['p2'])}: {r['runs']} ({r['balls']})",
                              detail=f"for wicket {r['wicket_no'] + 1} · {m['team1']} v {m['team2']}", href=f"/match/{r['match_id']}", match_id=r["match_id"],
                              weight=r["runs"] / 150 + kg.recog(db, r["p1"], r["p2"]) + kg.comp_recog(m["competition"]) * 0.5))
        for m in ms:
            if m["event_stage"] == "Final" or m["result"] == "tie" or (m["win_by_wickets"] == 1) or (m["win_by_runs"] is not None and m["win_by_runs"] <= 2):
                why = ("a final" if m["event_stage"] == "Final" else "a tie" if m["result"] == "tie" else
                       "won by 1 wicket" if m["win_by_wickets"] == 1 else f"won by {m['win_by_runs']} run{'s' if m['win_by_runs'] != 1 else ''}")
                items.append(dict(kind="match", title=f"{m['team1']} v {m['team2']}", detail=f"{why}" + (f" · {m['competition']}" if m["competition"] else ""),
                                  href=f"/match/{m['match_id']}", match_id=m["match_id"], weight=1.5 + kg.comp_recog(m["competition"])))
    for it in items:
        m = meta[it["match_id"]]
        y = m["start_date"].year
        it["year"] = y
        it["date"] = str(m["start_date"])
        it["exact_day"] = it["match_id"] in single
        it["when"] = f"{d.year - y} year{'s' if d.year - y != 1 else ''} ago today ({y})" if it["exact_day"] else f"began on this day in {y} (match spanned more than one day)"
        it["gender"], it["format"] = m["gender"], m["format_group"]
    items.sort(key=lambda x: -x["weight"])
    out, per_match = [], {}
    for it in items:
        if per_match.get(it["match_id"], 0) >= 2:
            continue
        per_match[it["match_id"]] = per_match.get(it["match_id"], 0) + 1
        it.pop("weight")
        out.append(it)
        if len(out) >= k:
            break
    return {"date": d.isoformat(), "label": d.strftime("%-d %B"), "matches_on_this_day": len(ms), "items": out,
            "rule": __doc__.strip().split("\n\n")[1]}
