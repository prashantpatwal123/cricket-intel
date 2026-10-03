"""Ask Cricket v1: QUESTION -> PARSED INTENT -> VALIDATED QUERY -> DATABASE RESULT -> RESPONSE.

`parse()` turns text into a structured Intent (deterministic here; this is the ONLY place a language model
could ever plug in, and its output would go through the same `validate()`). `execute()` runs the intent through
the same engines as the rest of the product (records leaderboard, battle, dismissal story), so Ask can never
compute a number differently from the pages. Response text is templated from the result; no generated numbers.
"""
from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field

from ..analytics import battle as B
from ..analytics.filters import Filters
from ..analytics.player import ROUTE_META
from ..analytics.records import METRICS, leaderboard
from ..db import DB
from .intents import Resolver

METRIC_WORDS = [  # (regex, metric key, perspective)
    (r"\bsix(es)?\b|\b6s\b", "sixes", "batter"), (r"\bfours?\b|\b4s\b", "fours", "batter"),
    (r"strike[- ]?rate|\bsr\b", "strike_rate", "batter"), (r"dot[- ]?ball|dots?\b", "dot_pct", "batter"),
    (r"boundar(y|ies) (%|percent|rate)|boundary percentage", "boundary_pct", "batter"),
    (r"\baverage\b", "average", "batter"), (r"balls faced", "balls_faced", "batter"),
    (r"\beconomy\b", "economy", "bowler"), (r"\bwickets?\b", "wickets", "bowler"),
    (r"keeper catches|catches as (wicket)?keeper|caught behind|caught by the (wicket)?keeper", "keeper_catches", "fielder"),
    (r"stumpings", "stumpings", "fielder"), (r"\bcatches\b", "catches", "fielder"),
    (r"\bruns\b", "runs", "batter"),
]
DISMISSAL_WORDS = [(r"run ?outs?|been run out", "RUN_OUT", "run out"), (r"\bbowled\b", "BOWLED", "bowled"), (r"\blbw\b|leg before", "LBW", "lbw"),
                   (r"\bstumped\b", "STUMPED", "stumped"), (r"caught behind|caught by the (wicket)?keeper", "CAUGHT_KEEPER", "caught by the wicketkeeper"),
                   (r"caught (and|&) bowled", "CAUGHT_BOWLER", "caught and bowled"), (r"\bhit wicket\b", "HIT_WICKET", "hit wicket")]
COMPETITIONS = {r"\bipl\b|indian premier league": "Indian Premier League", r"\bwpl\b|women'?s premier league": "Women's Premier League"}


_RES: dict = {}


def _resolver(db: DB) -> Resolver:
    if _RES.get("db") is not db:
        _RES["db"], _RES["r"] = db, Resolver(db)
    return _RES["r"]


@dataclass
class Intent:
    kind: str = "unknown"            # player_stat | dismissal_count | leaderboard | matchup | dismissed_by
    subject: dict | None = None      # {person_id, name}
    opponent: dict | None = None
    metric: str | None = None
    dismissal: str | None = None
    filters: dict = field(default_factory=dict)
    gender: str | None = None
    min_sample: int | None = None
    notes: list = field(default_factory=list)


def parse(db: DB, question: str) -> Intent:
    q = " " + question.lower().strip().rstrip("?") + " "
    it = Intent()
    res = _resolver(db)
    players = []
    for a, b, ps in res.find(q):
        best, others = Resolver.pick(ps)
        if best is None:
            it.notes.append({"ambiguous": question[max(0, a - 1):b], "candidates": [{"person_id": o["person_id"], "name": o["name"],
                                                                                       "matches": o["matches"]} for o in others[:5]]})
            continue
        players.append({"person_id": best["person_id"], "name": best["name"], "genders": best.get("teams") and None})
        if others:
            it.notes.append({"assumed": f"'{question[max(0, a - 1):b].strip()}' → {best['name']} ({best['matches']} matches); "
                                        f"also matches {', '.join(o['name'] for o in others[:3])}"})
    f: dict = {}
    for pat, comp in COMPETITIONS.items():
        if re.search(pat, q):
            f["competition"] = comp
    if re.search(r"\bt20is?\b|t20 internationals?", q):
        f["format"], f["team_type"] = "T20", "international"
    elif re.search(r"\bt20s?\b", q):
        f["format"] = "T20"
    if re.search(r"\bodis?\b|one[- ]day", q):
        f["format"] = "ODI"
    if re.search(r"\binternationals?\b", q) and "team_type" not in f:
        f["team_type"] = "international"
    for pat, ph in ((r"death( overs)?", "death"), (r"power ?play", "powerplay"), (r"middle overs", "middle")):
        if re.search(pat, q):
            f["phase"] = ph
    if re.search(r"\bchas(e|es|ing)\b|batting second|second innings", q):
        f["chasing"] = True
    elif re.search(r"batting first|setting( a)? target|first innings", q):
        f["chasing"] = False
    m = re.search(r"between (\d{4}) and (\d{4})|from (\d{4}) to (\d{4})", q)
    if m:
        y1, y2 = [int(x) for x in m.groups() if x][:2]
        f["year_from"], f["year_to"] = y1, y2
    elif (m := re.search(r"since (\d{4})", q)):
        f["year_from"] = int(m.group(1))
    elif (m := re.search(r"\bin (\d{4})\b", q)):
        f["year_from"] = f["year_to"] = int(m.group(1))
    elif (m := re.search(r"before (\d{4})", q)):
        f["year_to"] = int(m.group(1)) - 1
    if (m := re.search(r"after (\d+) balls", q)):
        f["faced_from"] = int(m.group(1))
    if (m := re.search(r"(first|opening) (\d+) balls", q)):
        f["faced_to"] = int(m.group(2)) - 1
    if re.search(r"full members?|test nations", q):
        f["full_members"] = True
    if f.get("competition") == "Women's Premier League":
        it.gender = "female"
    elif f.get("competition") == "Indian Premier League":
        it.gender = "male"
    if re.search(r"\bwomen'?s?\b|\bfemale\b|\bwomen\b", q):
        it.gender = "female"
    elif re.search(r"\bmen'?s?\b|\bmale\b", q):
        it.gender = "male"
    # opposition team ("against Australia") only if no second player took that slot
    if "teams" not in _RES or _RES.get("teams_db") is not db:
        _RES["teams"] = sorted({r["t"] for r in db.q("SELECT DISTINCT team1 AS t FROM matches UNION SELECT DISTINCT team2 FROM matches")},
                               key=len, reverse=True)
        _RES["teams_db"] = db
    for t in _RES["teams"]:
        if re.search(r"\b(against|vs\.?|versus|v)\s+" + re.escape(t.lower()) + r"\b", q):
            f["opposition"] = t
            break
    if (m := re.search(r"min(imum)? (\d+) balls", q)):
        it.min_sample = int(m.group(2))
    for pat, key, persp in METRIC_WORDS:
        if re.search(pat, q):
            it.metric = key
            break
    for pat, route, word in DISMISSAL_WORDS:
        if re.search(pat, q):
            it.dismissal = route
            break
    ranking = (re.search(r"^\s*(who|which)\b", q) and re.search(r"\b(most|highest|lowest|best|fewest|least|top)\b", q)) or \
        re.search(r"^\s*(most|highest|lowest|best|fewest|top|leaders?)\b", q)
    if len(players) >= 2 and re.search(r"\b(against|vs\.?|versus|v|facing)\b", q):
        a, b = players[0], players[1]
        n_ab = db.q1("SELECT count(*) AS n FROM balls WHERE batter_id = ? AND bowler_id = ?", [a["person_id"], b["person_id"]])["n"]
        n_ba = db.q1("SELECT count(*) AS n FROM balls WHERE batter_id = ? AND bowler_id = ?", [b["person_id"], a["person_id"]])["n"]
        if n_ba > n_ab:  # "Bumrah v Warner": the data says which one batted
            a, b = b, a
            it.notes.append({"assumed": f"{a['name']} as batter, {b['name']} as bowler ({n_ba} balls that way round, {n_ab} the other)"})
        it.kind, it.subject, it.opponent = "matchup", a, b
    elif players and re.search(r"(who|which bowler).*dismiss|dismissed .* (the )?most", q):
        it.kind, it.subject = "dismissed_by", players[0]
    elif ranking:
        it.kind = "leaderboard"
        if it.dismissal and not it.metric:
            it.metric = {"RUN_OUT": "times_run_out", "BOWLED": "times_bowled", "CAUGHT_KEEPER": "keeper_catches",
                         "STUMPED": "stumpings"}.get(it.dismissal)
        rate = it.metric in METRICS and METRICS[it.metric][5] > 0
        if rate and not ({"team_type", "competition", "opposition", "full_members"} & set(f)):
            # Rate leaderboards over all teams are dominated by small associate samples; default to the main game, visibly.
            f["full_members"] = True
            it.notes.append({"assumed": "rate leaderboard limited to matches between ICC full members plus leagues; remove that condition to include all teams"})
    elif players and it.dismissal and re.search(r"how (many times|often)|times", q):
        it.kind, it.subject = "dismissal_count", players[0]
    elif players and it.metric:
        it.kind, it.subject = "player_stat", players[0]
    elif players:
        it.kind, it.subject, it.metric = "player_stat", players[0], "strike_rate"
        it.notes.append({"assumed": "no statistic named; showing strike rate and core numbers"})
    it.filters = f
    return it


def validate(db: DB, it: Intent) -> list[str]:
    errs = []
    if it.kind == "unknown":
        errs.append("I couldn't tell what you want to know. Try naming a player, a statistic, or a 'who has the most…' question.")
    if it.metric and it.metric not in METRICS and it.metric != "average":
        errs.append(f"unsupported statistic {it.metric}")
    try:
        Filters.parse(it.filters)
    except ValueError as e:
        errs.append(str(e))
    if it.kind == "leaderboard" and not it.metric:
        errs.append("Which statistic should I rank by? (e.g. sixes, strike rate, wickets, economy)")
    return errs


def interpretation(it: Intent) -> list[dict]:
    chips = []
    names = {"player_stat": "Player statistic", "dismissal_count": "Dismissal count", "leaderboard": "Leaderboard",
             "matchup": "Batter v bowler", "dismissed_by": "Bowlers who dismissed"}
    chips.append({"key": "kind", "label": names.get(it.kind, it.kind), "removable": False})
    if it.subject:
        chips.append({"key": "subject", "label": it.subject["name"], "removable": False})
    if it.opponent:
        chips.append({"key": "opponent", "label": "v " + it.opponent["name"], "removable": False})
    if it.metric:
        chips.append({"key": "metric", "label": METRICS.get(it.metric, ("Average",))[0], "removable": False})
    if it.dismissal:
        chips.append({"key": "dismissal", "label": ROUTE_META.get(it.dismissal, {}).get("label", it.dismissal), "removable": False})
    labels = {"format": lambda v: v, "team_type": lambda v: "Internationals" if v == "international" else "Leagues",
              "competition": lambda v: v, "phase": lambda v: f"{v} overs", "chasing": lambda v: "Chasing" if v else "Batting first",
              "year_from": lambda v: f"from {v}", "year_to": lambda v: f"to {v}", "opposition": lambda v: f"against {v}",
              "faced_from": lambda v: f"after {v} balls", "faced_to": lambda v: f"first {v + 1} balls", "full_members": lambda v: "Full members & leagues"}
    for k, v in it.filters.items():
        chips.append({"key": f"filters.{k}", "label": labels.get(k, lambda v: f"{k}={v}")(v), "removable": True})
    if it.gender:
        chips.append({"key": "gender", "label": "Women" if it.gender == "female" else "Men", "removable": True})
    return chips


def _scope(f: dict, gender=None) -> str:
    bits = []
    if f.get("competition"):
        bits.append(f"in the {f['competition']}")
    elif f.get("format"):
        bits.append({"T20": "in T20Is" if f.get("team_type") == "international" else "in T20s (T20Is, IPL, WPL)", "ODI": "in ODIs"}[f["format"]])
    if f.get("phase"):
        bits.append({"death": "in death overs", "powerplay": "in the powerplay", "middle": "in the middle overs"}[f["phase"]])
    if "chasing" in f:
        bits.append("while chasing" if f["chasing"] else "when batting first")
    if f.get("opposition"):
        bits.append(f"against {f['opposition']}")
    if f.get("year_from") and f.get("year_to") and f["year_from"] == f["year_to"]:
        bits.append(f"in {f['year_from']}")
    else:
        if f.get("year_from"):
            bits.append(f"since {f['year_from']}")
        if f.get("year_to"):
            bits.append(f"up to {f['year_to']}")
    if f.get("faced_from"):
        bits.append(f"after facing {f['faced_from']} balls")
    return (" ".join(bits) + " " if bits else "") + "in our covered data"


def execute(db: DB, it: Intent) -> dict:
    errs = validate(db, it)
    base = {"intent": asdict(it), "interpretation": interpretation(it), "notes": it.notes,
            "pipeline": ["question", "parsed intent", "validated query", "database result", "templated response"],
            "generated_by": "deterministic parser + shared analytics engines (no language model)"}
    if errs:
        return {**base, "status": "needs_clarification", "message": errs[0],
                "ambiguous": [n for n in it.notes if "ambiguous" in n]}
    f = Filters.parse(it.filters)
    scope = _scope(it.filters, it.gender)
    if it.kind == "matchup":
        r = B.battle(db, it.subject["person_id"], it.opponent["person_id"], f)
        t = r["total"]
        if not r["met"]:
            return {**base, "status": "ok", "answer": f"{it.subject['name']} hasn't faced {it.opponent['name']} {scope}.", "numbers": []}
        return {**base, "status": "ok",
                "answer": f"{it.subject['name']} v {it.opponent['name']} {scope}: {t['runs']} runs off {t['balls']} balls "
                          f"(SR {t['strike_rate']}), {t['dismissals']} dismissal{'s' if t['dismissals'] != 1 else ''}.",
                "numbers": [{"label": k, "value": t[v]} for k, v in (("Balls", "balls"), ("Runs", "runs"), ("Strike rate", "strike_rate"),
                            ("Dismissals", "dismissals"), ("Dot %", "dot_pct"), ("4s", "fours"), ("6s", "sixes"))],
                "link": {"kind": "battle", "bat": it.subject["person_id"], "bowl": it.opponent["person_id"]},
                "caveat": r["edge"]["sample_note"]}
    if it.kind == "dismissed_by":
        lb = leaderboard(db, "pair_dismissals", Filters.parse({**it.filters, "batter_id": it.subject["person_id"]}), 0, 5, it.gender)
        rows = lb["rows"]
        if not rows:
            return {**base, "status": "ok", "answer": f"No bowler-credited dismissals of {it.subject['name']} {scope}.", "numbers": []}
        top = [r for r in rows if r["value"] == rows[0]["value"]]
        return {**base, "status": "ok",
                "answer": f"{' and '.join(r['names'][1] for r in top)} {'have' if len(top) > 1 else 'has'} dismissed {it.subject['name']} most often "
                          f"{scope}: {int(rows[0]['value'])} times.",
                "numbers": [{"label": r["names"][1], "value": int(r["value"]), "n": r["sample"], "link": {"kind": "battle", "bat": r["ids"][0], "bowl": r["ids"][1]}}
                            for r in rows],
                "definition": lb["definition"], "caveat": "Wickets credited to the bowler only (run-outs excluded)."}
    if it.kind == "dismissal_count":
        st = B.dismissal_story(db, it.subject["person_id"], it.dismissal, f)
        word = ROUTE_META[it.dismissal]["label"].lower()
        return {**base, "status": "ok",
                "answer": f"{it.subject['name']} has been {word} {st['n']} time{'s' if st['n'] != 1 else ''} {scope}: {st['n']} of {st['of_total']} dismissals.",
                "numbers": [{"label": ROUTE_META[it.dismissal]["label"], "value": st["n"]}, {"label": "All dismissals", "value": st["of_total"]}],
                "link": {"kind": "player", "id": it.subject["person_id"], "route": it.dismissal},
                "caveat": st.get("terminology")}
    if it.kind == "player_stat" and not it.filters.get("format") and not it.filters.get("competition"):
        fmts = [r["format_group"] for r in db.q("SELECT DISTINCT format_group FROM balls WHERE batter_id = ? OR bowler_id = ? ORDER BY 1",
                                                [it.subject["person_id"]] * 2)]
        parts = [execute(db, Intent(**{**asdict(it), "filters": {**it.filters, "format": fm}})) for fm in fmts]
        parts = [p_ for p_ in parts if p_.get("status") == "ok" and p_.get("numbers")]
        if len(parts) > 1:
            return {**base, "status": "ok", "answer": " ".join(p_["answer"] for p_ in parts),
                    "numbers": [{**n, "label": f"{n['label']} ({p_['intent']['filters']['format']})"} for p_ in parts for n in p_["numbers"][:2]],
                    "link": parts[0].get("link"), "definition": parts[0].get("definition"),
                    "caveat": "No format was specified, so T20 and ODI are reported separately rather than mixed."}
        if parts:
            return {**parts[0], "interpretation": base["interpretation"]}
    if it.kind == "player_stat":
        pid = it.subject["person_id"]
        persp = {"bowler_wk": "bowler"}.get(METRICS.get(it.metric, ("", "batter"))[1], METRICS.get(it.metric, ("", "batter"))[1])
        if it.metric == "average":
            runs = leaderboard(db, "runs", Filters.parse({**it.filters, "batter_id": pid}), 0, 1)["rows"]
            outs = db.q1(f"SELECT count(*) AS n FROM dis WHERE player_out_id = ? AND counts_as_dismissal AND {f.where('batter')[0]}",
                         [pid, *f.where('batter')[1]])["n"]
            r_ = runs[0]["value"] if runs else 0
            avg = round(r_ / outs, 2) if outs else None
            return {**base, "status": "ok", "answer": f"{it.subject['name']} averages {avg if avg else '–'} {scope} ({int(r_)} runs, {outs} dismissals).",
                    "numbers": [{"label": "Average", "value": avg}, {"label": "Runs", "value": int(r_)}, {"label": "Dismissals", "value": outs}],
                    "link": {"kind": "player", "id": pid}}
        key = {"batter": "batter_id", "bowler": "bowler_id"}.get(persp)
        if key is None:
            return {**base, "status": "needs_clarification", "message": "That statistic is a leaderboard; try 'who has the most …'."}
        lb = leaderboard(db, it.metric, Filters.parse({**it.filters, key: pid}), 0, 1)
        if not lb["rows"]:
            return {**base, "status": "ok", "answer": f"No qualifying data for {it.subject['name']} {scope}.", "numbers": []}
        r = lb["rows"][0]
        return {**base, "status": "ok",
                "answer": f"{it.subject['name']}: {lb['label'].lower()} {r['value_fmt']} {scope}"
                          + (f" (from {r['sample']} {lb['sample_unit']})." if lb["sample_unit"] in ("balls", "legal balls") else f" ({r['matches']} matches)."),
                "numbers": [{"label": lb["label"], "value": r["value_fmt"]}, {"label": lb["sample_unit"].capitalize(), "value": r["sample"]},
                            {"label": "Matches", "value": r["matches"]}],
                "definition": lb["definition"], "link": {"kind": "player", "id": pid}}
    if it.kind == "leaderboard" and it.gender is None:
        parts = []
        for g in ("male", "female"):
            sub = execute(db, Intent(**{**asdict(it), "gender": g}))
            if sub.get("leaderboard"):
                parts.append(sub)
        if parts:
            return {**base, "status": "ok", "answer": " ".join(("Men: " if p_["intent"]["gender"] == "male" else "Women: ") + p_["answer"] for p_ in parts),
                    "leaderboards": [p_["leaderboard"] for p_ in parts], "numbers": [], "link": parts[0]["link"],
                    "caveat": "Men's and women's cricket are ranked separately. " + parts[0].get("caveat", "")}
    if it.kind == "leaderboard":
        lb = leaderboard(db, it.metric, f, it.min_sample, 10, it.gender)
        if not lb["rows"]:
            return {**base, "status": "ok", "answer": f"No one qualifies {scope} (minimum {lb['min_sample']} {lb['sample_unit']}).", "numbers": []}
        top = lb["rows"][0]
        mins = f" (min {lb['min_sample']} {lb['sample_unit']})" if lb["min_sample"] else ""
        who = " v ".join(top["names"])
        return {**base, "status": "ok",
                "answer": f"{who} ranks first for {lb['label'].lower()} {scope}: {top['value_fmt']}{mins}.",
                "leaderboard": lb, "numbers": [], "link": {"kind": "records", "metric": it.metric, "filters": it.filters},
                "caveat": lb["coverage"]}
    return {**base, "status": "needs_clarification", "message": "I couldn't map that to an analysis yet."}


def ask(db: DB, question: str) -> dict:
    it = parse(db, question)
    out = execute(db, it)
    out["question"] = question
    return out


def run_intent(db: DB, intent: dict) -> dict:
    allowed = {k: intent.get(k) for k in Intent.__dataclass_fields__ if k in intent}
    return execute(db, Intent(**allowed))
