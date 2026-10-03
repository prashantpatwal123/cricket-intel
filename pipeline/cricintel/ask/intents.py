"""Ask Cricket v0: deterministic, query-backed answers. NO language model, NO generated numbers.

question -> intent template (regex) -> entity resolution (player names from the dataset) -> analytics
query -> templated answer + the numbers + how it was computed + a drill-down handle.

The same structured `intent` objects are what a future LLM parser will emit; this module is the
executor/validator, so swapping the parser later doesn't change how answers are computed.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from ..analytics import player as P
from ..analytics.filters import Filters
from ..db import DB

ROUTE_WORDS = {
    "run out": ["RUN_OUT"], "bowled": ["BOWLED"], "lbw": ["LBW"], "leg before": ["LBW"], "stumped": ["STUMPED"],
    "caught behind": ["CAUGHT_KEEPER"], "caught by the keeper": ["CAUGHT_KEEPER"], "caught by the wicketkeeper": ["CAUGHT_KEEPER"],
    "caught and bowled": ["CAUGHT_BOWLER"], "caught & bowled": ["CAUGHT_BOWLER"], "hit wicket": ["HIT_WICKET"],
    "caught": ["CAUGHT_KEEPER", "CAUGHT_BOWLER", "CAUGHT_FIELDER", "CAUGHT_KEEPER_STATUS_UNKNOWN", "CAUGHT_UNKNOWN_FIELDER"],
}
FORMAT_WORDS = {r"\bt20i?s?\b": "T20", r"\bodis?\b": "ODI", r"\bone[- ]day\b": "ODI"}
PHASE_WORDS = {r"\bdeath( overs)?\b": "death", r"\bpowerplay\b": "powerplay", r"\bmiddle overs\b": "middle"}

EXAMPLES = [
    "How many times has {p} been run out?",
    "How many times has {p} been bowled?",
    "How many times has {p} been caught behind?",
    "Who has dismissed {p} the most?",
    "How many runs has {p} scored against {b}?",
    "What is {p}'s strike rate against {b}?",
    "How does {p} perform while chasing?",
    "Which over does {p} get dismissed in most often?",
    "How does {p} do against spin?",
    "How many sixes has {p} hit in T20s?",
]


STOP = set("""how many times has have been was were the and against with does did while chasing perform runs run out
bowled caught behind stumped strike rate what which who most over overs sixes fours hit scored score get gets dismissed
dismiss spin pace record versus internationals since during when innings match matches player players bowler batter
keeper wicketkeeper team teams in of on at to for by is are it his her their our data covered""".split())


@dataclass
class Resolved:
    person_id: str
    name: str
    matches: int
    assumed_over: list | None = None


class Resolver:
    """Find player mentions using every known alias (Register names, names.csv, match-file names).
    Surname-only matches require >= 4 letters and not an English/cricket stopword."""
    def __init__(self, db: DB):
        rows = db.q("SELECT person_id, name, matches, teams, aliases FROM player_profile WHERE person_id NOT LIKE 'unres:%'")
        self.by_pid = {r["person_id"]: r for r in rows}
        self.full: dict[str, set] = {}
        self.sur: dict[str, set] = {}
        for r in rows:
            for a in set((r["aliases"] or []) + [r["name"]]):
                a = re.sub(r"\s*\(\d+\)$", "", a).strip().lower()
                if len(a) >= 5 and " " in a:
                    self.full.setdefault(a, set()).add(r["person_id"])
                last = a.split()[-1] if a.split() else ""
                if len(last) >= 4 and last not in STOP and last.isalpha():
                    self.sur.setdefault(last, set()).add(r["person_id"])

    def find(self, text: str) -> list[tuple[int, int, list]]:
        """n-gram dictionary lookup (longest first, non-overlapping): O(words), not O(aliases)."""
        t = text.lower()
        toks = [(m.start(), m.end(), m.group(0)) for m in re.finditer(r"[a-z0-9'.-]+", t)]
        hits, used = [], set()
        for size in (5, 4, 3, 2):
            for i in range(len(toks) - size + 1):
                if any(j in used for j in range(i, i + size)):
                    continue
                phrase = " ".join(x[2] for x in toks[i:i + size])
                phrase = re.sub(r"'s$", "", phrase)
                if phrase in self.full:
                    used.update(range(i, i + size))
                    hits.append((toks[i][0], toks[i + size - 1][1], self.full[phrase]))
        for i, (a, b, w) in enumerate(toks):
            if i in used:
                continue
            w2 = re.sub(r"'s$", "", w)
            if w2 in self.sur:
                used.add(i)
                hits.append((a, b, self.sur[w2]))
        return [(a, b, [self.by_pid[p] for p in pids]) for a, b, pids in sorted(hits)]

    @staticmethod
    def pick(ps: list) -> tuple[dict | None, list]:
        """One candidate -> it. Several -> the clear favourite (>= 3x the matches of the next) or None (ambiguous)."""
        ps = sorted(ps, key=lambda p: -p["matches"])
        if len(ps) == 1:
            return ps[0], []
        if ps[0]["matches"] >= 3 * ps[1]["matches"]:
            return ps[0], ps[1:]
        return None, ps


def _filters(q: str) -> Filters:
    f = {}
    for pat, v in FORMAT_WORDS.items():
        if re.search(pat, q):
            f["format"] = v
    for pat, v in PHASE_WORDS.items():
        if re.search(pat, q):
            f["phase"] = v
    if re.search(r"\binternationals?\b", q):
        f["team_type"] = "international"
    m = re.search(r"\bsince (\d{4})\b", q)
    if m:
        f["year_from"] = int(m.group(1))
    return Filters.parse(f)


def answer(db: DB, question: str) -> dict:
    r = _answer(db, question)
    if r.get("status") == "ok" and r.get("_assumptions"):
        r["assumptions"] = r.pop("_assumptions")
    r.pop("_assumptions", None)
    return r


_ASSUME: list = []


def _answer(db: DB, question: str) -> dict:
    q = question.lower().strip()
    hits = Resolver(db).find(q)
    ents = []
    assumptions = []
    for a, b, ps in hits:
        best, others = Resolver.pick(ps)
        if best is None:
            return {"status": "ambiguous", "question": question,
                    "message": f"'{question[a:b]}' matches several players. Which one did you mean?",
                    "candidates": [{"person_id": p["person_id"], "name": p["name"], "matches": p["matches"],
                                    "teams": (p["teams"] or [])[:3]} for p in others]}
        if others:
            assumptions.append(f"'{question[a:b]}' taken to mean {best['name']} ({best['matches']} matches); "
                               f"also matches {', '.join(o['name'] for o in others[:3])}.")
        ents.append(Resolved(best["person_id"], best["name"], best["matches"]))
    _ASSUME[:] = assumptions
    if not ents:
        return {"status": "no_entity", "question": question,
                "message": "I couldn't find a player from our dataset in that question. Ask Cricket v0 supports these question types:",
                "examples": [e.format(p="<player>", b="<bowler>") for e in EXAMPLES], "examples_are_templates": True}
    f = _filters(q)
    p1 = ents[0]
    p2 = ents[1] if len(ents) > 1 else None
    scope = _scope_text(f)

    # --- intent: how many times dismissed by <route>
    m = re.search(r"how (?:many times|often) (?:has|have|did|does)?.*?(?:been |get |got |gets )?(run out|bowled|lbw|leg before|stumped|caught behind|caught by the (?:wicket)?keeper|caught (?:and|&) bowled|hit wicket|caught)", q)
    if m and not p2:
        word = m.group(1)
        routes = ROUTE_WORDS[word]
        d = P.dismissals(db, p1.person_id, f)
        n = sum(r["n"] for r in d["routes"] if r["route"] in routes)
        prov = "DERIVED" if any(r in ("CAUGHT_KEEPER", "CAUGHT_FIELDER") for r in routes) else "OBSERVED"
        caveat = ("Counts catches taken by the fielding side's wicketkeeper. Keeper identity is inferred (DERIVED), and catches "
                  "where it couldn't be established are excluded rather than guessed. The data does not record edges.") if "CAUGHT_KEEPER" in routes else None
        # Never imply an edge: a catch by the keeper is reported as exactly that.
        said = "caught by the wicketkeeper" if routes == ["CAUGHT_KEEPER"] else word
        return _ok(question, "dismissal_count", [p1], f,
                   f"{p1.name} has been {said} {n} time{'s' if n != 1 else ''}{scope}: {n} of {d['total']} dismissals.",
                   [{"label": f"{said.capitalize()} dismissals", "value": n, "prov": prov},
                    {"label": "All dismissals", "value": d["total"], "prov": "OBSERVED"},
                    {"label": "Balls faced", "value": d["balls_faced"], "prov": "OBSERVED"}],
                   drill={"player": p1.person_id, "route": routes[0] if len(routes) == 1 else None},
                   method=f"dismissals of person {p1.person_id} where route ∈ {routes}" + (f"; filters {f.active()}" if f.active() else ""),
                   caveat=caveat, viz="howout")

    # --- intent: who dismissed X most
    if re.search(r"(who|which bowler)\b.*\bdismiss(ed|es)?\b.*\bmost\b|\bmost\b.*\bdismiss", q) and not p2:
        d = P.dismissals(db, p1.person_id, f)
        tb = d["top_bowlers"]
        if not tb:
            return _ok(question, "top_dismisser", [p1], f, f"No bowler has dismissed {p1.name}{scope} in our data.", [], method="", viz=None)
        lead = [b for b in tb if b["n"] == tb[0]["n"]]
        names = " and ".join(b["bowler"] for b in lead)
        return _ok(question, "top_dismisser", [p1], f,
                   f"{names} {'have' if len(lead) > 1 else 'has'} dismissed {p1.name} most often{scope}: {tb[0]['n']} time{'s' if tb[0]['n'] != 1 else ''}.",
                   [{"label": b["bowler"], "value": b["n"], "prov": "OBSERVED", "drill": {"player": p1.person_id, "bowler_id": b["bowler_id"]}} for b in tb],
                   method=f"bowler-credited dismissals of {p1.person_id}, grouped by bowler" + (f"; filters {f.active()}" if f.active() else ""),
                   caveat="Counts only wickets credited to the bowler (run-outs excluded).", viz="table")

    # --- intent: X against bowler Y (runs / strike rate / record)
    if p2 and re.search(r"\b(against|vs\.?|versus|v)\b", q):
        m = P.matchups(db, p1.person_id, Filters(**{**f.active(), "bowler_id": p2.person_id}), by="bowler")
        r = m["rows"][0] if m["rows"] else None
        if not r:
            return _ok(question, "matchup", [p1, p2], f, f"{p1.name} hasn't faced {p2.name}{scope} in our data.", [], method="", viz=None)
        wants_sr = "strike rate" in q
        lead = (f"{p1.name}'s strike rate against {p2.name} is {r['strike_rate']}{scope}: {r['runs']} runs off {r['balls']} balls."
                if wants_sr else
                f"{p1.name} has scored {r['runs']} runs off {r['balls']} balls against {p2.name}{scope} (SR {r['strike_rate']}), dismissed {r['dismissals']} time{'s' if r['dismissals'] != 1 else ''}.")
        small = r["balls"] < 30
        return _ok(question, "matchup", [p1, p2], f, lead,
                   [{"label": k, "value": r[v], "prov": "OBSERVED"} for k, v in
                    (("Balls", "balls"), ("Runs", "runs"), ("Strike rate", "strike_rate"), ("Dismissals", "dismissals"),
                     ("Dot %", "dot_pct"), ("Boundary %", "boundary_pct"), ("4s", "fours"), ("6s", "sixes"))],
                   drill={"player": p1.person_id, "bowler_id": p2.person_id},
                   method=f"balls where batter={p1.person_id} and bowler={p2.person_id}" + (f"; filters {f.active()}" if f.active() else ""),
                   caveat=f"Small sample ({r['balls']} balls). Treat with caution." if small else None, viz="matchup")

    # --- intent: vs pace / spin
    m = re.search(r"\b(against|vs\.?|versus)\s+(pace|spin|seam|fast bowl\w*|spinners?)\b", q)
    if m and not p2:
        fam = "spin" if m.group(2).startswith("spin") else "pace"
        mu = P.matchups(db, p1.person_id, f, by="bowler_family")
        rows = {r["k"]: r for r in mu["rows"]}
        r = rows.get(fam)
        unk = rows.get(None)
        if not r:
            return _ok(question, "vs_family", [p1], f, f"No balls against {fam} recorded for {p1.name}{scope}.", [], method="", viz=None)
        base = mu["baseline"]
        lead = (f"Against {fam}, {p1.name} scores at a strike rate of {r['strike_rate']} and is dismissed every "
                f"{r['balls_per_dismissal'] or '–'} balls{scope}, against {base['strike_rate']} and every {base['balls_per_dismissal'] or '–'} balls overall.")
        return _ok(question, "vs_family", [p1], f, lead,
                   [{"label": f"Balls v {fam}", "value": r["balls"], "prov": "DERIVED"},
                    {"label": f"SR v {fam}", "value": r["strike_rate"], "prov": "DERIVED"},
                    {"label": f"Dismissals v {fam}", "value": r["dismissals"], "prov": "DERIVED"},
                    {"label": "SR overall", "value": base["strike_rate"], "prov": "OBSERVED"}],
                   drill={"player": p1.person_id, "bowler_family": fam},
                   method="balls grouped by the bowler's bowling family from player metadata",
                   caveat=(f"{unk['balls']} balls were against bowlers whose type is unknown. They are excluded, not guessed." if unk else None),
                   viz="matchup")

    # --- intent: chasing
    if re.search(r"\bchas(e|es|ing)\b", q) and not p2:
        ch = P.matchups(db, p1.person_id, Filters(**{**f.active(), "chasing": True}), by="bowler")["baseline"]
        se = P.matchups(db, p1.person_id, Filters(**{**f.active(), "chasing": False}), by="bowler")["baseline"]
        lead = (f"Chasing, {p1.name} strikes at {ch['strike_rate']} and is out every {ch['balls_per_dismissal'] or '–'} balls; "
                f"batting first (or with no target) it's {se['strike_rate']} and every {se['balls_per_dismissal'] or '–'} balls{scope}.")
        return _ok(question, "chasing", [p1], f, lead,
                   [{"label": "Balls (chasing)", "value": ch["balls"], "prov": "DERIVED"}, {"label": "SR (chasing)", "value": ch["strike_rate"], "prov": "DERIVED"},
                    {"label": "Outs (chasing)", "value": ch["dismissals"], "prov": "DERIVED"}, {"label": "Balls (setting)", "value": se["balls"], "prov": "DERIVED"},
                    {"label": "SR (setting)", "value": se["strike_rate"], "prov": "DERIVED"}, {"label": "Outs (setting)", "value": se["dismissals"], "prov": "DERIVED"}],
                   drill={"player": p1.person_id, "chasing": True},
                   method="limited-overs balls split by whether a target existed (second innings)",
                   caveat="Dismissals count wickets credited to bowlers. 'Chasing' applies only to limited-overs second innings.", viz="situations")

    # --- intent: which over dismissed most
    if re.search(r"which over", q) and re.search(r"dismiss|out\b", q) and not p2:
        s = P.situations(db, p1.person_id, f)["by_over"]
        if not s or not any(r["dismissals"] for r in s):
            return _ok(question, "dismissal_over", [p1], f, f"No dismissals for {p1.name}{scope}.", [], method="", viz=None)
        top = max(s, key=lambda r: (r["dismissals"], -r["bucket"]))
        rate_top = max((r for r in s if r["balls"] >= 30), key=lambda r: r["dismissal_rate"] or 0, default=None)
        lead = f"{p1.name} has been dismissed most often in over {top['bucket']}{scope}: {top['dismissals']} times in {top['balls']} balls faced."
        if rate_top and rate_top["bucket"] != top["bucket"]:
            lead += f" Per ball faced, though, the highest dismissal rate (min 30 balls) is in over {rate_top['bucket']}: {rate_top['dismissal_rate']} per 100 balls."
        return _ok(question, "dismissal_over", [p1], f, lead,
                   [{"label": f"Over {r['bucket']}", "value": r["dismissals"], "n": r["balls"], "prov": "OBSERVED"}
                    for r in sorted(s, key=lambda r: -r["dismissals"])[:5]],
                   drill={"player": p1.person_id, "over": top["bucket"]},
                   method="dismissals grouped by over number (1-based); rate = dismissals per 100 balls faced",
                   caveat="Raw counts favour overs where the player bats more often, so compare rates too.", viz="situations")

    # --- intent: sixes / fours
    m = re.search(r"how many (sixes|6s|fours|4s)", q)
    if m and not p2:
        six = m.group(1) in ("sixes", "6s")
        mu = P.matchups(db, p1.person_id, f, by="bowler")["baseline"]
        n = mu["sixes"] if six else mu["fours"]
        return _ok(question, "boundaries", [p1], f, f"{p1.name} has hit {n} {'sixes' if six else 'fours'}{scope}, in {mu['balls']} balls faced.",
                   [{"label": "Sixes" if six else "Fours", "value": n, "prov": "OBSERVED"}, {"label": "Balls faced", "value": mu["balls"], "prov": "OBSERVED"}],
                   drill={"player": p1.person_id}, method="balls with runs off the bat = 6 (or 4) that were boundaries", viz=None)

    return {"status": "unsupported", "question": question, "entities": [e.__dict__ for e in ents],
            "message": "I can't answer that type of question yet. Ask Cricket v0 supports these templates:",
            "examples": [e.format(p=p1.name, b="<bowler>") for e in EXAMPLES]}


def _scope_text(f: Filters) -> str:
    a = f.active()
    parts = []
    if "format" in a:
        parts.append({"T20": "in T20 matches (T20Is, IPL, WPL)", "ODI": "in ODIs"}.get(a["format"], f"in {a['format']}s"))
    if "phase" in a:
        parts.append(f"in the {a['phase']} overs" if a["phase"] != "powerplay" else "in the powerplay")
    if "team_type" in a:
        parts.append("in internationals")
    if "year_from" in a:
        parts.append(f"since {a['year_from']}")
    return (" " + " ".join(parts) + " (in our covered data)") if parts else " in our covered data"


def _ok(question, intent, ents, f, text, numbers, method, drill=None, caveat=None, viz=None):
    return {"status": "ok", "question": question, "intent": intent, "entities": [e.__dict__ for e in ents],
            "filters": f.active(), "answer": text, "numbers": numbers, "drill": drill, "caveat": caveat, "viz": viz,
            "how_computed": method, "generated_by": "template (no language model)", "prov": "OBSERVED/DERIVED aggregates from the dataset",
            "_assumptions": list(_ASSUME)}
