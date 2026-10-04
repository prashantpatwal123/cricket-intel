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
from .intents import Resolver, and_list

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
    for a, b, ps in res.find(re.sub(r"(?<=[a-z])-(?=[a-z])", " ", q)):   # "Kohli-Zampa" names two players
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
    if (m := re.search(r"after (?:facing )?(\d+) balls|(?:after|once) .{0,30}?(?:faces?|facing|faced|has faced) (\d+) balls", q)):
        f["faced_from"] = int(next(x for x in m.groups() if x))
    if (m := re.search(r"(first|opening) (\d+) balls", q)):
        f["faced_to"] = int(m.group(2)) - 1
    if (m := re.search(r"between balls (\d+) and (\d+)|\bballs (\d+) ?(?:-|–|to) ?(\d+)", q)):
        a_, b_ = [int(x) for x in m.groups() if x][:2]
        f["faced_from"], f["faced_to"] = a_ - 1, b_ - 1  # "ball 20" = the batter had already faced 19
    if (m := re.search(r"\bovers? (\d+) ?(?:-|–|to|and) ?(\d+)", q)):
        f["over_from"], f["over_to"] = int(m.group(1)), int(m.group(2))
    elif (m := re.search(r"\b(?:last|final) (\d+) overs", q)) and f.get("format"):
        n_ = int(m.group(1)); tot = 20 if f["format"] == "T20" else 50
        f["over_from"], f["over_to"] = tot - n_ + 1, tot
    if (m := re.search(r"(\d+(?:\.\d+)?) ?\+? (?:an|per|a) over|required (?:run )?rate (?:of |above |over )?(\d+(?:\.\d+)?)", q)):
        f["rrr_from"] = float(next(x for x in m.groups() if x))
        f["chasing"] = True
    if re.search(r"behind (the )?(required )?rate", q):
        f["chase_state"] = "behind"
    elif re.search(r"ahead of (the )?(required )?rate", q):
        f["chase_state"] = "ahead"
    if re.search(r"\bnew batters?\b|\bfirst 10 balls\b", q) and "faced_to" not in f:
        f["batter_stage"] = "new"
    elif re.search(r"\bset batters?\b", q):
        f["batter_stage"] = "set"
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
    mentioned = find_teams(q)
    for t in _RES["teams"]:
        if re.search(r"\b(against|vs\.?|versus|v)\s+" + re.escape(t.lower()) + r"\b", q) and len(mentioned) < 2:
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
    if players and re.search(r"\bsimilar\b|plays? like|most like", q):
        it.kind, it.subject = "similar", players[0]
    elif players and re.search(r"fastest against|scored (the )?fastest|quickest against|highest strike rate against", q):
        it.kind, it.subject = "scored_fastest_against", players[0]
    elif len(players) == 1 and "faced_from" in f and re.search(r"\bchange|\bdiffer|what happens|how does .+ (score|bat)", q):
        it.kind, it.subject = "player_faced_change", players[0]
        it.notes.append({"after_balls": f.pop("faced_from")})
    elif len(players) >= 2 and re.search(r"\bcompare\b|\bcomparison\b", q):
        it.kind, it.subject, it.opponent = "compare_players", players[0], players[1]
    elif len(players) >= 2 and re.search(r"\bdismissals?\b", q) and not re.search(r"how many", q):
        a, b = players[0], players[1]
        n_ab = db.q1("SELECT count(*) AS n FROM balls WHERE batter_id = ? AND bowler_id = ?", [a["person_id"], b["person_id"]])["n"]
        n_ba = db.q1("SELECT count(*) AS n FROM balls WHERE batter_id = ? AND bowler_id = ?", [b["person_id"], a["person_id"]])["n"]
        if n_ba > n_ab:
            a, b = b, a
        it.kind, it.subject, it.opponent = "battle_dismissals", a, b
    elif not players and len(mentioned) >= 1 and re.search(r"\bchas(e|es)\b", q) and re.search(r"biggest|highest|largest|successful|best", q):
        it.kind = "team_chases"
        it.notes.append({"team": mentioned[0]})
        f.pop("chasing", None); f.pop("opposition", None)
        if len(mentioned) >= 2:
            f["opposition"] = mentioned[1]
    elif players and re.search(r"how (does|do|did|has) .+ (get|got|been|gets) (out|dismissed)|how (is|was) .+ dismissed|how .+ gets? out", q):
        it.kind, it.subject = "how_out", players[0]
    elif players and re.search(r"\b(innings|knocks?|scores)\b", q) and re.search(r"\b(best|top|highest|biggest)\b", q):
        it.kind, it.subject = "innings_list", players[0]
    elif players and re.search(r"\bspells?\b|bowling figures|\bfigures\b", q):
        it.kind, it.subject = "spells_list", players[0]
    elif re.search(r"what happened|\bscorecard\b|\bthe match\b", q) and len(mentioned) >= 2:
        it.kind = "match_lookup"
        it.notes.append({"teams": mentioned[:2]})
        team_words = {w for t in mentioned for w in t.lower().split()}
        places = [w for w in re.findall(r"\bin ([a-z]+)", q) if w not in team_words and w not in ("the", "a", "an")]
        if places:
            it.notes.append({"place": places[0]})
        f.pop("opposition", None)
    elif players and re.search(r"partners?\b|partnerships?", q) and re.search(r"\bbest\b|who (bats|partners)|with whom", q):
        it.kind, it.subject = "partners", players[0]
    elif players and re.search(r"troubled|struggled against|struggles against|problems|toughest|hardest", q):
        it.kind, it.subject = "troubled_by", players[0]
    elif players and re.search(r"\bcompare\b.*\bbefore\b.*\bafter\b|\bbefore and after\b", q) and (m_ := re.search(r"(?:before and after|after) (\d{4})", q)):
        it.kind, it.subject = "period_compare", players[0]
        it.notes.append({"split_year": int(m_.group(1))})
        f.pop("year_from", None); f.pop("year_to", None)
    elif re.search(r"improve[sd]?|gain(?:s|ed)?|increase[sd]?", q) and "faced_from" in f and not players:
        it.kind, it.metric = "faced_change", "strike_rate"
        it.notes.append({"after_balls": f.pop("faced_from")})
        if not ({"team_type", "competition", "opposition", "full_members"} & set(f)):
            f["full_members"] = True
            it.notes.append({"assumed": "limited to matches between ICC full members plus leagues; remove that condition to include all teams"})
    elif len(mentioned) >= 2 and re.search(r"battles?|match-?ups?", q):
        it.kind = "rivalry_battles"
        it.notes.append({"teams": mentioned[:2]})
        f.pop("opposition", None)
    elif re.search(r"partnerships?|\bpairs?\b|batting pairs?", q) and not players:
        it.kind = "partnership_leaderboard"
        it.metric = "run_rate" if re.search(r"fastest|quickest|run rate|scoring rate", q) else ("average" if re.search(r"average", q) else "runs")
    elif re.search(r"improves?|improvement|biggest (jump|rise)|accelerat", q) and re.search(r"middle", q) and re.search(r"death", q) and not players:
        it.kind, it.metric = "phase_change", "strike_rate"
        f.pop("phase", None)
        if not ({"team_type", "competition", "opposition", "full_members"} & set(f)):
            f["full_members"] = True
            it.notes.append({"assumed": "limited to matches between ICC full members plus leagues; remove that condition to include all teams"})
        if "format" not in f:
            f["format"] = "T20"
            it.notes.append({"assumed": "T20 (middle-to-death change is defined per format); remove to switch"})
    elif players and re.search(r"\b(show|list)\b.*dismissals|dismissals (between|after|in|when)", q):
        it.kind, it.subject = "dismissal_list", players[0]
    elif len(players) >= 2 and re.search(r"\b(against|vs\.?|versus|v|facing)\b", q):
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
        if not it.metric and re.search(r"\bbest\b", q) and re.search(r"\bbowl(ers?|ing)\b", q):
            it.metric = "economy"
            it.notes.append({"assumed": "'best' bowlers read as lowest economy; name a statistic (wickets, dot balls) to change it"})
        if not it.metric and re.search(r"\bbest\b", q):
            it.metric = "strike_rate"
            it.notes.append({"assumed": "'best' read as highest strike rate; name a statistic to change it"})
        if it.dismissal and not it.metric:
            it.metric = {"RUN_OUT": "times_run_out", "BOWLED": "times_bowled", "CAUGHT_KEEPER": "keeper_catches",
                         "STUMPED": "stumpings"}.get(it.dismissal)
        rate = it.metric in METRICS and METRICS[it.metric][5] > 0
        if rate and f.get("phase") and not it.min_sample:
            # one phase is a small slice of a career: "best in the death" needs a bigger sample than the all-balls default
            it.min_sample = 300
            it.notes.append({"assumed": "minimum 300 balls in that phase; add 'min N balls' to change it"})
        if rate and not ({"team_type", "competition", "opposition", "full_members"} & set(f)):
            # Rate leaderboards over all teams are dominated by small associate samples; default to the main game, visibly.
            f["full_members"] = True
            it.notes.append({"assumed": "rate leaderboard limited to matches between ICC full members plus leagues; remove that condition to include all teams"})
    elif players and it.dismissal and re.search(r"how (many times|often)|times", q):
        it.kind, it.subject = "dismissal_count", players[0]
    elif players and it.metric:
        it.kind, it.subject = "player_stat", players[0]
    elif players:
        pid_ = players[0]["person_id"]
        r_ = db.q1("""SELECT count(*) FILTER (WHERE batter_id = ?) AS bat, count(*) FILTER (WHERE bowler_id = ?) AS bowl
                      FROM balls WHERE batter_id = ? OR bowler_id = ?""", [pid_] * 4)
        if r_ and r_["bowl"] > 1.3 * r_["bat"]:
            it.kind, it.subject = "bowler_summary", players[0]
            it.notes.append({"assumed": f"{players[0]['name']} mostly bowls in our data, so this shows bowling"})
        else:
            it.kind, it.subject, it.metric = "player_stat", players[0], "strike_rate"
            it.notes.append({"assumed": "no statistic named; showing strike rate and core numbers"})
    it.filters = f
    return it


def find_teams(q: str) -> list[str]:
    """Teams mentioned in the question, longest names first, including franchise abbreviations (RCB, CSK)."""
    from ..analytics.graph import TEAM_ABBR
    found = []
    ql = " " + q.lower() + " "
    for t in _RES.get("teams", []):
        if re.search(r"(?<![a-z])" + re.escape(t.lower()) + r"(?![a-z])", ql) and not any(t.lower() in f.lower() for f in found):
            found.append(t)
    for full, abbrs in TEAM_ABBR.items():
        for a in abbrs:
            if re.search(r"(?<![a-z])" + a + r"(?![a-z])", ql) and full not in found:
                found.append(full)
    return found


def validate(db: DB, it: Intent) -> list[str]:
    errs = []
    if it.kind == "unknown":
        errs.append("I couldn't tell what you want to know. Try naming a player, a statistic, or a 'who has the most…' question.")
    if it.kind not in ("partnership_leaderboard", "faced_change") and it.metric and it.metric not in METRICS and it.metric != "average":
        errs.append(f"unsupported statistic {it.metric}")
    try:
        Filters.parse(it.filters)
    except ValueError as e:
        errs.append(str(e))
    if it.kind in ("dismissal_list",) and ({"chase_state", "batter_stage", "non_striker_id"} & set(it.filters)):
        errs.append("Dismissal lists can't yet be filtered by chase state, batter stage or partner.")
    amb = [n for n in it.notes if "ambiguous" in n]
    if amb and (it.kind in ("unknown", "leaderboard") and re.search(r"dismiss|against|\bv\b", " ".join(n["ambiguous"] for n in amb) + " ") or it.kind == "unknown"):
        errs.insert(0, f"Which player did you mean by \"{amb[0]['ambiguous'].strip()}\"?")
    if it.kind == "leaderboard" and not it.metric:
        errs.append("Which statistic should I rank by? (e.g. sixes, strike rate, wickets, economy)")
    return errs


def interpretation(it: Intent) -> list[dict]:
    chips = []
    names = {"player_stat": "Player statistic", "dismissal_count": "Dismissal count", "leaderboard": "Leaderboard",
             "matchup": "Batter v bowler", "dismissed_by": "Bowlers who dismissed", "partnership_leaderboard": "Partnerships",
             "phase_change": "Middle → death change", "dismissal_list": "List of dismissals", "bowler_summary": "Bowling summary",
             "innings_list": "Best innings", "spells_list": "Best spells", "match_lookup": "Find a match", "partners": "Best partners",
             "troubled_by": "Bowlers who troubled", "period_compare": "Before / after", "faced_change": "Change after N balls",
             "rivalry_battles": "Unusual battles in a rivalry", "how_out": "How they get out",
             "scored_fastest_against": "Scored fastest against", "player_faced_change": "Before / after N balls", "similar": "Similar players",
             "compare_players": "Compare two players", "team_chases": "Biggest successful chases", "battle_dismissals": "Dismissals in a battle"}
    chips.append({"key": "kind", "label": names.get(it.kind, it.kind), "removable": False})
    if it.subject:
        chips.append({"key": "subject", "label": it.subject["name"], "removable": False})
    if it.opponent:
        chips.append({"key": "opponent", "label": "v " + it.opponent["name"], "removable": False})
    if it.metric:
        chips.append({"key": "metric", "label": {"run_rate": "Run rate", "average": "Average"}.get(it.metric, METRICS.get(it.metric, ("Average",))[0]),
                      "removable": False})
    if it.dismissal:
        chips.append({"key": "dismissal", "label": ROUTE_META.get(it.dismissal, {}).get("label", it.dismissal), "removable": False})
    labels = {"format": lambda v: v, "team_type": lambda v: "Internationals" if v == "international" else "Leagues",
              "competition": lambda v: v, "phase": lambda v: f"{v} overs", "chasing": lambda v: "Chasing" if v else "Batting first",
              "year_from": lambda v: f"from {v}", "year_to": lambda v: f"to {v}", "opposition": lambda v: f"against {v}",
              "faced_from": lambda v: f"from ball {v + 1}", "faced_to": lambda v: f"up to ball {v + 1}", "full_members": lambda v: "Full members & leagues",
              "over_from": lambda v: f"from over {v}", "over_to": lambda v: f"to over {v}", "rrr_from": lambda v: f"required rate ≥ {v:g}",
              "chase_state": lambda v: "behind the required rate" if v == "behind" else f"{v} of the required rate", "batter_stage": lambda v: f"{v} batters",
              "before_date": lambda v: f"before {v}"}
    for k, v in it.filters.items():
        chips.append({"key": f"filters.{k}", "label": labels.get(k, lambda v: f"{k}={v}")(v), "removable": True})
    if it.gender:
        chips.append({"key": "gender", "label": "Women" if it.gender == "female" else "Men", "removable": True})
    for n in it.notes:
        if "teams" in n:
            chips.append({"key": "teams", "label": " v ".join(n["teams"]), "removable": False})
        if "place" in n:
            chips.append({"key": "place", "label": f"in {n['place'].title()}", "removable": False})
        if "split_year" in n:
            chips.append({"key": "split", "label": f"before / from {n['split_year']}", "removable": False})
        if "team" in n:
            chips.append({"key": "team", "label": n["team"], "removable": False})
        if "after_balls" in n:
            chips.append({"key": "after", "label": f"before v after ball {n['after_balls']}", "removable": False})
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
    if f.get("faced_from") is not None and f.get("faced_to") is not None:
        bits.append(f"on balls {f['faced_from'] + 1}–{f['faced_to'] + 1} of their innings")
    elif f.get("faced_from"):
        bits.append(f"after facing {f['faced_from']} balls")
    elif f.get("faced_to") is not None:
        bits.append(f"in their first {f['faced_to'] + 1} balls")
    if f.get("over_from") or f.get("over_to"):
        bits.append(f"in overs {f.get('over_from', 1)}–{f.get('over_to', '')}".rstrip("–"))
    if f.get("rrr_from"):
        bits.append(f"with a required rate of {f['rrr_from']:g}+ an over")
    if f.get("chase_state"):
        bits.append("when behind the required rate" if f["chase_state"] == "behind" else f"when {f['chase_state']} of the required rate")
    if f.get("batter_stage"):
        bits.append({"new": "against new batters (0–9 balls faced)", "set": "against set batters (30+ balls)", "settling": "against batters on 10–29 balls"}[f["batter_stage"]])
    if f.get("before_date"):
        bits.append(f"before {f['before_date']}")
    return (" ".join(bits) + " " if bits else "") + "in covered matches"


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
    from . import fan as FAN
    v4 = FAN.execute(db, it, f, scope, base)
    if v4 is not None:
        return v4
    v3 = _execute_v3(db, it, f, scope, base)
    if v3 is not None:
        return v3
    if it.kind == "partnership_leaderboard":
        from ..analytics import partnerships as PT
        parts = []
        for g in ([it.gender] if it.gender else ["male", "female"]):
            ph = it.filters.get("phase")
            r = PT.best_pairs(db, g, it.filters.get("format"), it.filters.get("team_type"), it.metric, phase=ph,
                              min_innings=8, min_balls=120 if ph else 240, limit=10)
            if r["rows"]:
                parts.append((g, r))
        if not parts:
            return {**base, "status": "ok", "answer": f"No partnership qualifies {scope}.", "numbers": []}
        unit = {"run_rate": "run rate", "average": "average", "runs": "runs together"}[it.metric]
        ans = " ".join(f"{'Men' if g == 'male' else 'Women'}: {r['rows'][0]['p1_name']} & {r['rows'][0]['p2_name']} lead for {unit} {scope} "
                       f"({r['rows'][0][it.metric]})." for g, r in parts)
        return {**base, "status": "ok", "answer": ans, "numbers": [],
                "pairs": [{"gender": g, "rows": r["rows"][:8], "thresholds": r["thresholds"], "sort": it.metric} for g, r in parts],
                "definition": parts[0][1]["definition"], "caveat": parts[0][1]["thresholds"] + ". Men's and women's pairs are ranked separately.",
                "link": {"kind": "partnerships", "sort": it.metric, "phase": it.filters.get("phase"), "format": it.filters.get("format")}}
    if it.kind == "phase_change":
        fmt = it.filters.get("format", "T20")
        mins = {"T20": (300, 150), "ODI": (600, 200)}[fmt]
        out_lb = []
        for g in ([it.gender] if it.gender else ["male", "female"]):
            w, p_ = Filters.parse({**{k: v for k, v in it.filters.items() if k != "format"}, "format": fmt, "gender": g}).where("batter")
            rows = db.q(f"""SELECT batter_id, count(*) FILTER (WHERE phase = 'middle') AS mb, sum(runs_batter) FILTER (WHERE phase = 'middle') AS mr,
                                   count(*) FILTER (WHERE phase = 'death') AS db_, sum(runs_batter) FILTER (WHERE phase = 'death') AS dr
                            FROM balls WHERE {w} AND wides = 0 GROUP BY 1
                            HAVING count(*) FILTER (WHERE phase = 'middle') >= ? AND count(*) FILTER (WHERE phase = 'death') >= ?""", [*p_, *mins])
            if not rows:
                continue
            lm = sum(r["mr"] for r in rows) / sum(r["mb"] for r in rows); ld = sum(r["dr"] for r in rows) / sum(r["db_"] for r in rows)
            K_ = 60
            for r in rows:
                d_sh = (r["dr"] + K_ * ld) / (r["db_"] + K_)  # shrink the smaller death sample toward the league death rate
                r["middle_sr"], r["death_sr"] = round(100 * r["mr"] / r["mb"], 1), round(100 * r["dr"] / r["db_"], 1)
                r["change"] = round(100 * (d_sh - r["mr"] / r["mb"]), 1)
                r["vs_typical"] = round(r["change"] - 100 * (ld - lm), 1)
            rows.sort(key=lambda r: -r["change"])
            names = {x["person_id"]: x["name"] for x in db.q(f"SELECT person_id, name FROM player_profile WHERE person_id IN ({','.join('?' * len(rows[:10]))})",
                                                               [r["batter_id"] for r in rows[:10]])}
            out_lb.append({"gender": g, "typical_change": round(100 * (ld - lm), 1), "rows": [
                {"rank": i + 1, "person_id": r["batter_id"], "name": names.get(r["batter_id"], r["batter_id"]), "middle_sr": r["middle_sr"],
                 "death_sr": r["death_sr"], "change": r["change"], "vs_typical": r["vs_typical"], "middle_balls": r["mb"], "death_balls": r["db_"]}
                for i, r in enumerate(rows[:10])]})
        if not out_lb:
            return {**base, "status": "ok", "answer": f"No batter qualifies {scope}.", "numbers": []}
        ans = " ".join(f"{'Men' if x['gender'] == 'male' else 'Women'}: {x['rows'][0]['name']} gains most, {x['rows'][0]['middle_sr']} → "
                       f"{x['rows'][0]['death_sr']} (typical change {x['typical_change']:+}). " for x in out_lb)
        return {**base, "status": "ok", "answer": ans.strip() + f" ({fmt}, {scope}.)", "numbers": [], "changes": out_lb,
                "definition": f"Strike rate in death overs minus strike rate in middle overs, {fmt}. Death strike rate shrunk 60 balls toward "
                              f"the league death rate. Minimum {mins[0]} middle-overs and {mins[1]} death-overs balls.",
                "caveat": "Batters who rarely reach the death overs are excluded by the minimums."}
    if it.kind == "dismissal_list":
        pid = it.subject["person_id"]
        w, p_ = f.where("batter")
        rows = db.q(f"""SELECT route, count(*) AS n FROM dis WHERE player_out_id = ? AND counts_as_dismissal AND {w} GROUP BY 1 ORDER BY n DESC""", [pid, *p_])
        tot = sum(r["n"] for r in rows)
        q_ = {"out_id": pid, **{k: v for k, v in it.filters.items()}}
        return {**base, "status": "ok",
                "answer": f"{it.subject['name']} was dismissed {tot} time{'s' if tot != 1 else ''} {scope}."
                          + (f" Most often {ROUTE_META.get(rows[0]['route'], {}).get('label', rows[0]['route']).lower()} ({rows[0]['n']})." if rows else ""),
                "numbers": [{"label": ROUTE_META.get(r["route"], {}).get("label", r["route"]), "value": r["n"]} for r in rows[:4]],
                "deliveries_query": q_, "link": {"kind": "player", "id": pid, "tab": "dismissals"}}
    if it.kind == "bowler_summary":
        pid = it.subject["person_id"]
        fmts = [it.filters["format"]] if it.filters.get("format") else [r["format_group"] for r in db.q(
            "SELECT format_group, count(*) AS n FROM balls WHERE bowler_id = ? GROUP BY 1 ORDER BY n DESC", [pid])]
        nums, ans = [], []
        for fm in fmts:
            ff = Filters.parse({**it.filters, "format": fm, "bowler_id": pid})
            vals = {m: leaderboard(db, m, ff, 0, 1)["rows"] for m in ("economy", "wickets", "bowl_dot_pct")}
            if not vals["economy"]:
                continue
            e, wk, d = vals["economy"][0], (vals["wickets"][0]["value"] if vals["wickets"] else 0), vals["bowl_dot_pct"][0]
            ans.append(f"{fm}: {int(wk)} wicket{'s' if int(wk) != 1 else ''}, economy {e['value_fmt']}, dot balls {d['value_fmt']}% from {e['sample']} legal balls")
            nums += [{"label": f"Economy ({fm})", "value": e["value_fmt"]}, {"label": f"Wickets ({fm})", "value": int(wk)}]
        if not ans:
            return {**base, "status": "ok", "answer": f"No bowling for {it.subject['name']} {scope}.", "numbers": []}
        return {**base, "status": "ok", "answer": f"{it.subject['name']} {scope}: " + "; ".join(ans) + ".", "numbers": nums,
                "definition": "Economy = runs conceded (incl. wides and no-balls) per 6 legal balls; wickets credited to the bowler.",
                "link": {"kind": "player", "id": pid, "tab": "bowling"}}
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
                "answer": f"{and_list([r['names'][1] for r in top])} {'have' if len(top) > 1 else 'has'} dismissed {it.subject['name']} most often "
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
    out["followups"] = followups(out)
    return out


def followups(res: dict) -> list[dict]:
    """One or two deterministic next questions/destinations for an answered question (Phase 8). Built from the
    intent kind and the answer's own linked entities; no language model. Each is {label, q} (re-asked) or {label, href}."""
    if res.get("status") != "ok":
        return []
    it = res.get("intent") or {}
    k, sub, opp = it.get("kind"), it.get("subject") or {}, it.get("opponent") or {}
    S = sub.get("name")
    out: list[dict] = []
    top_battle = next((n["link"] for n in res.get("numbers") or [] if (n.get("link") or {}).get("kind") == "battle"), None)
    link = res.get("link") or {}
    if k in ("dismissed_by", "troubled_by") and top_battle:
        bowler = next(n["label"] for n in res["numbers"] if n.get("link") == top_battle)
        out = [{"label": f"How has {S} scored against {bowler}?", "q": f"{S} v {bowler}"},
               {"label": f"Show every dismissal of {S}", "href": f"/how-out/{sub['person_id']}"}]
    elif k in ("matchup", "battle_dismissals") and sub and opp:
        out = [{"label": "Compare this battle with similar battles", "href": f"/battle?bat={sub['person_id']}&bowl={opp['person_id']}#battle-similar"},
               {"label": f"Who dismisses {S} most?", "q": f"Who dismisses {S} most?"}]
    elif k == "compare_players" and link.get("kind") == "compare":
        out = [{"label": "Open the full comparison", "href": f"/compare?ids={','.join(link['ids'])}"}]
    elif k == "match_lookup" and link.get("kind") == "match":
        out = [{"label": "Replay this match ball by ball", "href": f"/live-lab/{link['id']}"},
               {"label": "Read the match story", "href": f"/match/{link['id']}"}]
    elif sub and S:
        if k not in ("how_out", "dismissal_list", "dismissal_count"):
            out.append({"label": f"Who dismisses {S} most?", "q": f"Who dismisses {S} most?"})
        else:
            out.append({"label": f"Who has {S} scored fastest against?", "q": f"Who has {S} scored fastest against?"})
        if k in ("bowler_summary", "spells_list"):
            out.append({"label": f"Open {S}'s page", "href": f"/players/{sub['person_id']}"})
        elif k != "innings_list":
            out.append({"label": f"Show {S}'s best covered innings", "q": f"Show {S}'s best covered innings"})
        else:
            out.append({"label": f"Who partners {S} best?", "q": f"Who partners {S} best?"})
    elif k == "leaderboard" and (res.get("leaderboard") or (res.get("leaderboards") or [None])[0] or {}).get("rows"):
        lb = res.get("leaderboard") or res["leaderboards"][0]
        r0 = lb["rows"][0]
        if lb.get("entity") == "pair":
            out = [{"label": f"Open {' v '.join(r0['names'])}", "href": f"/battle?bat={r0['ids'][0]}&bowl={r0['ids'][1]}"}]
        else:
            q1 = f"What is {r0['names'][0]}'s best spell?" if lb.get("entity") == "bowler" else f"Who dismisses {r0['names'][0]} most?"
            out = [{"label": q1, "q": q1},
                   {"label": f"Open {r0['names'][0]}'s page", "href": f"/players/{r0['ids'][0]}"}]
    elif k == "partnership_leaderboard" and res.get("pairs"):
        g = res["pairs"][0]["rows"]
        if g:
            out = [{"label": f"Who partners {g[0]['p1_name']} best?", "q": f"Who partners {g[0]['p1_name']} best?"}]
    elif res.get("items"):
        out = [{"label": f"Open {res['items'][0]['label']}", "href": res["items"][0]["href"]}]
    q = (res.get("question") or "").strip().lower()
    return [f for f in out if f.get("q", "").lower() != q][:2]


def run_intent(db: DB, intent: dict) -> dict:
    allowed = {k: intent.get(k) for k in Intent.__dataclass_fields__ if k in intent}
    return execute(db, Intent(**allowed))


def _items(rows, label, value, href, sub=None):
    return [{"label": label(r), "value": value(r), "href": href(r), "sub": sub(r) if sub else None} for r in rows]


# Filters each knowledge-graph question type can honour. Anything else is refused, never silently dropped.
V3_SUPPORTED = {
    "innings_list": {"format", "competition", "team_type", "opposition", "year_from", "year_to", "before_date", "chasing"},
    "spells_list": {"format", "competition", "team_type", "opposition", "year_from", "year_to", "before_date", "chasing", "phase"},
    "match_lookup": {"year_from", "year_to", "before_date"},
    "how_out": {"format"},
    "partners": {"format"},
    "troubled_by": None,          # None = any Filters key (computed from balls when filtered)
    "period_compare": set(),
    "rivalry_battles": set(),
}


def _graph_where(fl: dict, gender: str | None, chasing_col: str, invert_chasing: bool = False) -> tuple[list, list]:
    """WHERE clauses for bat_innings / bowl_innings from Ask filters (columns shared by both tables)."""
    from ..analytics.filters import team_names
    w, p = [], []
    for key, col in (("format", "format_group"), ("competition", "competition"), ("team_type", "team_type")):
        if fl.get(key):
            w.append(f"{col} = ?"); p.append(fl[key])
    if gender:
        w.append("gender = ?"); p.append(gender)
    if fl.get("opposition"):
        names = team_names(fl["opposition"])
        w.append(f"opponent IN ({','.join('?' * len(names))})"); p.extend(names)
    if fl.get("year_from"):
        w.append("year >= ?"); p.append(fl["year_from"])
    if fl.get("year_to"):
        w.append("year <= ?"); p.append(fl["year_to"])
    if fl.get("before_date"):
        w.append("start_date < ?::DATE"); p.append(str(fl["before_date"]))
    if "chasing" in fl:
        w.append(f"coalesce({chasing_col}, false) = ?"); p.append((not fl["chasing"]) if invert_chasing else bool(fl["chasing"]))
    return w, p


def _execute_v3(db: DB, it: Intent, f: Filters, scope: str, base: dict) -> dict | None:
    """Ask v3: questions that resolve to objects in the knowledge graph (innings, spells, matches, partners, battles)."""
    from ..analytics import partnerships as PT
    from ..analytics.entities import _nm, canon
    k = it.kind
    if k in V3_SUPPORTED and V3_SUPPORTED[k] is not None:
        extra = set(it.filters) - V3_SUPPORTED[k]
        if extra:
            return {**base, "status": "needs_clarification",
                    "message": f"This kind of question can't yet be limited by {', '.join(sorted(extra))}; remove that condition or ask it another way."}
    if k == "how_out":
        from ..analytics.visual import dismissal_dna
        pid = it.subject["person_id"]
        d = dismissal_dna(db, pid, fmt=it.filters.get("format"))
        if not d["total"]:
            return {**base, "status": "ok", "answer": f"No dismissals of {it.subject['name']} {scope}.", "numbers": []}
        top = d["tree"]["route"][:4]
        ans = (f"{it.subject['name']} has been dismissed {d['total']} times {scope}: " + ", ".join(f"{x['label'].lower()} {x['n']}" for x in top) + ". "
               + (f"{d['keeper_unknown']} catches have keeper status unknown. " if d["keeper_unknown"] else "")
               + "Where the ball pitched, the shot and any edge are not recorded.")
        return {**base, "status": "ok", "answer": ans, "numbers": [],
                "items": _items(d["tree"]["route"], lambda r: r["label"], lambda r: str(r["n"]), lambda r: f"/how-out/{pid}?route={r['key']}"),
                "definition": d["keeper_note"], "link": {"kind": "how_out", "id": pid}}
    if k == "innings_list":
        pid = it.subject["person_id"]
        w, p = _graph_where(it.filters, it.gender, "chasing")
        w, p = ["batter_id = ?"] + w, [pid] + p
        rows = db.q(f"""SELECT match_id, innings_no, runs, balls, not_out, opponent, competition, start_date, won, format_group FROM bat_innings
                        WHERE {' AND '.join(w)} ORDER BY runs DESC, balls LIMIT 10""", p)
        if not rows:
            return {**base, "status": "ok", "answer": f"No innings for {it.subject['name']} {scope}.", "numbers": []}
        r0 = rows[0]
        return {**base, "status": "ok", "answer": f"{it.subject['name']}'s best covered innings {scope}: {r0['runs']}{'*' if r0['not_out'] else ''} off {r0['balls']} "
                f"v {r0['opponent']} ({r0['start_date']}){', a win' if r0['won'] else ''}.", "numbers": [],
                "items": _items(rows, lambda r: f"{r['runs']}{'*' if r['not_out'] else ''} ({r['balls']}) v {r['opponent']}", lambda r: r["format_group"],
                                lambda r: f"/innings/{r['match_id']}/{r['innings_no']}/{pid}", lambda r: f"{r['competition']} · {r['start_date']} · {'won' if r['won'] else 'not won'}"),
                "definition": "Ranked by runs, then fewer balls. Opens the ball-by-ball Innings Story.", "link": {"kind": "player", "id": pid, "tab": "innings"}}
    if k == "spells_list":
        pid = it.subject["person_id"]
        w, p = _graph_where(it.filters, it.gender, "defending", invert_chasing=True)   # bowler side: chasing batters = defending
        w, p = ["bowler_id = ?"] + w, [pid] + p
        if it.filters.get("phase") not in (None, "death"):
            return {**base, "status": "needs_clarification", "message": "Spell lists support death overs only as a phase."}
        death = it.filters.get("phase") == "death"
        order = "death_wkts DESC, death_runs * 1.0 / death_balls ASC" if death else "wickets DESC, runs ASC"
        if death:
            w.append("death_balls >= 12")
        rows = db.q(f"""SELECT match_id, innings_no, wickets, runs, balls, death_wkts, death_runs, death_balls, opponent, competition, start_date
                        FROM bowl_innings WHERE {' AND '.join(w)} ORDER BY {order} LIMIT 10""", p)
        if not rows:
            return {**base, "status": "ok", "answer": f"No qualifying spells for {it.subject['name']} {scope}.", "numbers": []}
        r0 = rows[0]
        ans = (f"{it.subject['name']}'s best death-overs spell: {r0['death_wkts']}/{r0['death_runs']} off {r0['death_balls']} death balls v {r0['opponent']} ({r0['start_date']})."
               if death else f"{it.subject['name']}'s best covered figures {scope}: {r0['wickets']}/{r0['runs']} v {r0['opponent']} ({r0['start_date']}).")
        return {**base, "status": "ok", "answer": ans, "numbers": [],
                "items": _items(rows, lambda r: (f"{r['death_wkts']}/{r['death_runs']} at the death" if death else f"{r['wickets']}/{r['runs']}") + f" v {r['opponent']}",
                                lambda r: f"{r['balls'] // 6}.{r['balls'] % 6} ov", lambda r: f"/spell/{r['match_id']}/{r['innings_no']}/{pid}",
                                lambda r: f"{r['competition']} · {r['start_date']}"),
                "definition": ("Death overs: T20 16–20, ODI 41–50; at least 12 death balls; most death wickets then lowest death economy." if death
                               else "Ranked by wickets, then fewest runs, for the whole innings."), "link": {"kind": "player", "id": pid, "tab": "bowling"}}
    if k == "match_lookup":
        teams = next(n["teams"] for n in it.notes if "teams" in n)
        place = next((n["place"] for n in it.notes if "place" in n), None)
        a, b = sorted([canon(teams[0]), canon(teams[1])])
        w, p = ["ta = ? AND tb = ?"], [a, b]
        if it.filters.get("year_from"):
            w.append("year >= ?"); p.append(it.filters["year_from"])
        if it.filters.get("year_to"):
            w.append("year <= ?"); p.append(it.filters["year_to"])
        if it.filters.get("before_date"):
            w.append("start_date < ?::DATE"); p.append(str(it.filters["before_date"]))
        if place:
            w.append("(lower(city) LIKE ? OR lower(venue) LIKE ?)"); p += [f"%{place}%", f"%{place}%"]
        if it.gender:
            w.append("gender = ?"); p.append(it.gender)
        rows = db.q(f"SELECT * FROM team_results WHERE {' AND '.join(w)} ORDER BY start_date DESC LIMIT 8", p)
        if not rows:
            return {**base, "status": "ok", "answer": f"No covered match between {a} and {b} matches that description.", "numbers": []}
        from ..analytics.replay import _result_line
        m0 = rows[0]
        meta = db.q1("SELECT * FROM matches WHERE match_id = ?", [m0["match_id"]])
        top = db.q1("SELECT batter_id, runs, not_out, balls FROM bat_innings WHERE match_id = ? ORDER BY runs DESC LIMIT 1", [m0["match_id"]])
        best = db.q1("SELECT bowler_id, wickets, runs FROM bowl_innings WHERE match_id = ? ORDER BY wickets DESC, runs LIMIT 1", [m0["match_id"]])
        ans = (f"{m0['team1']} v {m0['team2']}, {m0['competition'] or 'match'}, {m0['city'] or m0['venue']}, {m0['start_date']}: "
               f"{m0['i1_team']} {m0['i1_runs']}/{m0['i1_wkts']}, {m0['i2_team']} {m0['i2_runs']}/{m0['i2_wkts']}. {_result_line(meta)}. "
               f"Top score {_nm(db, top['batter_id'])} {top['runs']}{'*' if top['not_out'] else ''} ({top['balls']}); best bowling {_nm(db, best['bowler_id'])} "
               f"{best['wickets']}/{best['runs']}.")
        return {**base, "status": "ok", "answer": ans + (f" {len(rows) - 1} other covered match{'es' if len(rows) > 2 else ''} also fit." if len(rows) > 1 else ""),
                "numbers": [], "link": {"kind": "match", "id": m0["match_id"]},
                "items": _items(rows, lambda r: f"{r['team1']} v {r['team2']}", lambda r: str(r["start_date"]), lambda r: f"/match/{r['match_id']}",
                                lambda r: f"{r['competition'] or ''} · {r['city'] or r['venue'] or ''}"),
                "story": f"/story/match/{m0['match_id']}"}
    if k == "partners":
        pid = it.subject["person_id"]
        r = PT.player_partners(db, pid, it.filters.get("format"))
        if not r.get("available"):
            return {**base, "status": "ok", "answer": f"No partnerships for {it.subject['name']} {scope}.", "numbers": []}
        best = r["brings_out_best"]
        most = r["partners"][:5]
        ans = (f"Most runs together ({r['format']}): {most[0]['partner_name']}, {most[0]['runs']} in {most[0]['innings']} stands. "
               + (f"{it.subject['name']} scores fastest, relative to expectation, with {best[0]['partner_name']} ({best[0]['my_sr']} v {best[0]['phase_adjusted_expected_sr']} expected)."
                  if best else "No partner clears the evidence bar for changing their own scoring."))
        return {**base, "status": "ok", "answer": ans, "numbers": [],
                "items": _items(most, lambda x: x["partner_name"], lambda x: f"{x['runs']} runs", lambda x: f"/partnerships?p1={pid}&p2={x['partner']}",
                                lambda x: f"{x['innings']} stands · {x['run_rate']} an over · best {x['best']}"),
                "definition": r["method"], "link": {"kind": "player", "id": pid, "tab": "partners"}}
    if k == "troubled_by":
        pid = it.subject["person_id"]
        if it.filters:   # filtered (e.g. before a replayed match): recompute battles and the batter's usual rates under the same filters
            fw, fp = Filters.parse(it.filters).where("batter", "b")
            u = db.q1(f"""SELECT count(*) FILTER (WHERE b.faced) AS balls, sum(b.runs_batter) AS runs, count(x.delivery_id) AS outs
                          FROM balls b LEFT JOIN dis x ON x.delivery_id = b.delivery_id AND x.player_out_id = b.batter_id AND x.bowler_credited
                          WHERE b.batter_id = ? AND {fw}""", [pid] + fp)
            rows = db.q(f"""SELECT b.bowler_id, count(*) FILTER (WHERE b.faced) AS balls, sum(b.runs_batter) AS runs, count(x.delivery_id) AS outs
                            FROM balls b LEFT JOIN dis x ON x.delivery_id = b.delivery_id AND x.player_out_id = b.batter_id AND x.bowler_credited
                            WHERE b.batter_id = ? AND {fw} GROUP BY 1 HAVING count(*) FILTER (WHERE b.faced) >= 30""", [pid] + fp) if u["balls"] else []
            for r in rows:
                r["batter_rpb"], r["batter_out_rate"] = (u["runs"] or 0) / u["balls"], (u["outs"] or 0) / u["balls"]
        else:
            rows = db.q("""SELECT bowler_id, balls, runs, outs, batter_rpb, batter_out_rate FROM battles WHERE batter_id = ? AND balls >= 30""", [pid])
        for r in rows:
            r["exp"] = r["balls"] * (r["batter_out_rate"] or 0)
            r["sr"] = round(100 * r["runs"] / r["balls"], 1)
            # rank: dismissals above expectation first, then strike rate below usual
            r["score"] = (r["outs"] - r["exp"]) / max(1.0, r["exp"]) ** 0.5 + (100 * (r["batter_rpb"] or 0) - r["sr"]) / 40
        rows.sort(key=lambda r: -r["score"])
        rows = rows[:8]
        if not rows:
            return {**base, "status": "ok", "answer": f"No bowler has bowled 30+ balls to {it.subject['name']} in covered data.", "numbers": []}
        r0 = rows[0]
        return {**base, "status": "ok", "answer": f"{_nm(db, r0['bowler_id'])} stands out: {it.subject['name']} scores at {r0['sr']} against them "
                f"(usual {100 * r0['batter_rpb']:.0f}) and has been dismissed {r0['outs']} times where {r0['exp']:.1f} would be expected.", "numbers": [],
                "items": _items(rows, lambda x: _nm(db, x["bowler_id"]), lambda x: f"SR {x['sr']}", lambda x: f"/battle?bat={pid}&bowl={x['bowler_id']}",
                                lambda x: f"{x['balls']} balls · {x['outs']} out (expected {x['exp']:.1f})"),
                "definition": "Bowlers with 30+ balls to this batter, ranked by dismissals above expectation (scaled) plus strike-rate suppression versus the "
                              "batter's usual. 'Troubled' describes outcomes only, not why.", "link": {"kind": "player", "id": pid, "tab": "matchups"}}
    if k == "period_compare":
        pid = it.subject["person_id"]
        y = next(n["split_year"] for n in it.notes if "split_year" in n)
        rows = db.q("""SELECT format_group, CASE WHEN year < ? THEN 'before' ELSE 'after' END AS period, sum(runs) AS runs, sum(balls) AS balls,
                              count(*) AS inns, count(*) FILTER (WHERE NOT not_out) AS outs FROM bat_innings WHERE batter_id = ? GROUP BY 1, 2 ORDER BY 1, 2 DESC""", [y, pid])
        if not rows:
            return {**base, "status": "ok", "answer": f"No covered batting for {it.subject['name']}.", "numbers": []}
        nums, parts = [], []
        for fm in sorted({r["format_group"] for r in rows}):
            d = {r["period"]: r for r in rows if r["format_group"] == fm}
            if "before" in d and "after" in d:
                b0, a0 = d["before"], d["after"]
                sb, sa = 100 * b0["runs"] / b0["balls"], 100 * a0["runs"] / a0["balls"]
                ab = b0["runs"] / b0["outs"] if b0["outs"] else None
                aa = a0["runs"] / a0["outs"] if a0["outs"] else None
                parts.append(f"{fm}: SR {sb:.1f} → {sa:.1f}, average {ab:.1f} → {aa:.1f} ({b0['balls']} v {a0['balls']} balls)" if ab and aa else f"{fm}: SR {sb:.1f} → {sa:.1f}")
                nums += [{"label": f"{fm} SR before {y}", "value": f"{sb:.1f}"}, {"label": f"{fm} SR from {y}", "value": f"{sa:.1f}"}]
        return {**base, "status": "ok", "answer": f"{it.subject['name']} before {y} v from {y}, covered data: " + "; ".join(parts) + ".", "numbers": nums,
                "definition": "Strike rate = runs per 100 balls faced; average = runs per dismissal. Covered data only; coverage can differ between periods.",
                "link": {"kind": "player", "id": pid, "tab": "career"}}
    if k == "faced_change":
        n_ = next(n["after_balls"] for n in it.notes if "after_balls" in n)
        out_lb = []
        for g in ([it.gender] if it.gender else ["male", "female"]):
            w, p = Filters.parse({**it.filters, "gender": g}).where("batter")
            rows = db.q(f"""SELECT batter_id, count(*) FILTER (WHERE batter_balls_before < ?) AS b0, sum(runs_batter) FILTER (WHERE batter_balls_before < ?) AS r0,
                                   count(*) FILTER (WHERE batter_balls_before >= ?) AS b1, sum(runs_batter) FILTER (WHERE batter_balls_before >= ?) AS r1
                            FROM balls WHERE {w} AND wides = 0 GROUP BY 1 HAVING count(*) FILTER (WHERE batter_balls_before >= ?) >= 300
                               AND count(*) FILTER (WHERE batter_balls_before < ?) >= 300""", [n_, n_, n_, n_, *p, n_, n_])
            if not rows:
                continue
            lb0 = sum(r["r0"] for r in rows) / sum(r["b0"] for r in rows); lb1 = sum(r["r1"] for r in rows) / sum(r["b1"] for r in rows)
            for r in rows:
                r1s = (r["r1"] + 60 * lb1) / (r["b1"] + 60)
                r["sr0"], r["sr1"], r["change"] = round(100 * r["r0"] / r["b0"], 1), round(100 * r["r1"] / r["b1"], 1), round(100 * (r1s - r["r0"] / r["b0"]), 1)
            rows.sort(key=lambda r: -r["change"])
            out_lb.append({"gender": g, "typical_change": round(100 * (lb1 - lb0), 1), "rows": [
                {"rank": i + 1, "person_id": r["batter_id"], "name": _nm(db, r["batter_id"]), "middle_sr": r["sr0"], "death_sr": r["sr1"], "change": r["change"],
                 "vs_typical": round(r["change"] - 100 * (lb1 - lb0), 1), "middle_balls": r["b0"], "death_balls": r["b1"]} for i, r in enumerate(rows[:10])]})
        if not out_lb:
            return {**base, "status": "ok", "answer": f"No batter qualifies {scope}.", "numbers": []}
        ans = " ".join(f"{'Men' if x['gender'] == 'male' else 'Women'}: {x['rows'][0]['name']} gains most, {x['rows'][0]['middle_sr']} → {x['rows'][0]['death_sr']} "
                       f"(typical change {x['typical_change']:+})." for x in out_lb)
        return {**base, "status": "ok", "answer": ans, "numbers": [], "changes": out_lb, "change_labels": [f"first {n_} balls", f"after {n_} balls"],
                "definition": f"Strike rate on balls faced after the first {n_} of an innings minus strike rate on the first {n_}; later rate shrunk 60 balls "
                              f"toward the league. Minimum 300 balls on each side."}
    if k == "rivalry_battles":
        teams = next(n["teams"] for n in it.notes if "teams" in n)
        from ..analytics.filters import team_names
        A, B_ = team_names(teams[0]), team_names(teams[1])
        qa, qb = ",".join("?" * len(A)), ",".join("?" * len(B_))
        g = it.gender or "male"
        rows = db.q(f"""SELECT b.batter_id, b.bowler_id, count(*) FILTER (WHERE b.wides = 0) AS balls, sum(b.runs_batter) AS runs,
                               count(*) FILTER (WHERE d.delivery_id IS NOT NULL) AS outs, any_value(t.batter_out_rate) AS bo, any_value(t.batter_rpb) AS brpb
                        FROM balls b LEFT JOIN dis d ON d.delivery_id = b.delivery_id AND d.player_out_id = b.batter_id AND d.bowler_credited
                        LEFT JOIN battles t ON t.batter_id = b.batter_id AND t.bowler_id = b.bowler_id AND t.gender = b.gender
                        WHERE b.gender = ? AND ((b.batting_team IN ({qa}) AND b.bowling_team IN ({qb})) OR (b.batting_team IN ({qb}) AND b.bowling_team IN ({qa})))
                        GROUP BY 1, 2 HAVING count(*) FILTER (WHERE b.wides = 0) >= 48""", [g, *A, *B_, *B_, *A])
        import math
        for r in rows:
            lam = r["balls"] * (r["bo"] or 0)
            term, cdf = math.exp(-lam), 0.0
            for i in range(r["outs"]):
                cdf += term; term *= lam / (i + 1)
            p_out = max(1e-12, 1 - cdf)
            sr, usual = 100 * r["runs"] / r["balls"], 100 * (r["brpb"] or 0)
            r.update(exp=lam, sr=round(sr, 1), usual=round(usual, 1), p=p_out, why="dismissed often" if r["outs"] > lam * 1.8 else "")
        rows = [r for r in rows if r["why"] or abs(r["sr"] - r["usual"]) >= 35]
        rows.sort(key=lambda r: (r["p"], -abs(r["sr"] - r["usual"])))
        rows = rows[:8]
        if not rows:
            return {**base, "status": "ok", "answer": f"No battle between {teams[0]} and {teams[1]} players stands out in covered data.", "numbers": []}
        r0 = rows[0]
        return {**base, "status": "ok", "answer": f"Most unusual: {_nm(db, r0['batter_id'])} v {_nm(db, r0['bowler_id'])}: {r0['runs']} off {r0['balls']} "
                f"(SR {r0['sr']}, usual {r0['usual']}), {r0['outs']} out where {r0['exp']:.1f} would be expected.", "numbers": [],
                "items": _items(rows, lambda x: f"{_nm(db, x['batter_id'])} v {_nm(db, x['bowler_id'])}", lambda x: f"{x['outs']} out",
                                lambda x: f"/battle?bat={x['batter_id']}&bowl={x['bowler_id']}", lambda x: f"{x['balls']} balls · SR {x['sr']} (usual {x['usual']}) · expected outs {x['exp']:.1f}"),
                "definition": "Battles in matches between these teams with 48+ balls; 'unusual' = dismissals at least 1.8× the batter's usual rate (ranked by Poisson tail) "
                              "or strike rate 35+ points away from the batter's usual.", "link": {"kind": "rivalry", "a": teams[0], "b": teams[1], "gender": g}}
    return None
