"""Universal search: FIND things (players, teams, competitions, editions, matches, innings, spells, battles, partnerships,
rivalries, records). Search does not answer statistical questions; that is Ask.

Index: one entry per entity with normalised tokens, built once from the knowledge-graph tables and cached to
derived/search_index.json. Query: tokens are matched exactly or by prefix through an inverted index; an entity must
match (almost) every meaningful query token. Patterns steer ranking: "A v B" → battles, rivalries, matches;
"6/19" → spells; "82*" → innings; a year → matches and editions; "partnerships" → pairs; metric words → records.
"""
from __future__ import annotations

import json
import math
import re
from collections import defaultdict

from ..db import DB
from .graph import TEAM_ABBR, TEAM_CANON
from .records import METRICS

VERSION = "search-1.0"
STOP = {"the", "of", "in", "and", "a", "an", "at", "for", "to", "vs", "v", "versus", "against", "men", "mens", "men's", "women", "womens",
        "women's", "match", "matches", "show", "me", "best", "by", "on", "with"}
TYPE_LABEL = {"player": "Players", "team": "Teams", "competition": "Competitions", "edition": "Editions", "match": "Matches",
              "innings": "Innings", "spell": "Spells", "battle": "Battles", "pair": "Partnerships", "rivalry": "Rivalries", "record": "Records"}
METRIC_WORDS = {"sixes": "sixes", "six": "sixes", "fours": "fours", "runs": "runs", "economy": "economy", "wickets": "wickets",
                "strike": "strike_rate", "dot": "dot_pct", "dots": "dot_pct", "boundary": "boundary_pct", "boundaries": "boundary_pct",
                "stumpings": "stumpings", "catches": "catches", "run-outs": "times_run_out"}
PHASE_WORDS = {"death": "death", "powerplay": "powerplay", "middle": "middle"}


def norm(s: str | None) -> list[str]:
    if not s:
        return []
    s = s.lower().replace("’", "'")
    return [t for t in re.findall(r"[a-z0-9'*/.-]+", s) if t]


def team_toks(name: str | None) -> set[str]:
    """Team name tokens plus franchise abbreviations (RCB, CSK…) and the canonical name of renamed franchises."""
    if not name:
        return set()
    c = TEAM_CANON.get(name, name)
    return set(norm(name)) | set(norm(c)) | set(TEAM_ABBR.get(c, []))


LOW_PRESTIGE = re.compile(r"qualifier|region|league 2|challenge league|play-?off|sub regional", re.I)


def _slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def build_index(db: DB) -> dict:
    E: list[dict] = []
    add = lambda **k: E.append(k)  # noqa: E731
    names = {}
    for r in db.q("SELECT person_id, name, aliases, matches, role, teams, genders FROM player_profile WHERE person_id NOT LIKE 'unres:%' AND matches > 0"):
        names[r["person_id"]] = r["name"]
        toks = set(norm(r["name"]))
        for a in (r["aliases"] or []):
            toks |= set(norm(re.sub(r"\s*\(\d+\)$", "", a)))
        add(type="player", key=r["person_id"], label=r["name"], sub=f"{(r['role'] or 'role unknown')} · {', '.join((r['teams'] or [])[:2])} · {r['matches']} matches",
            toks=sorted(toks), w=math.log10(1 + r["matches"]), href=f"/players/{r['person_id']}", g=(r["genders"] or [None])[0])
    teams = db.q("""SELECT t AS team, gender, count(*) AS n FROM (SELECT team1 AS t, gender FROM team_results UNION ALL SELECT team2, gender FROM team_results)
                    GROUP BY 1, 2""")
    for t in teams:
        add(type="team", key=f"{t['team']}|{t['gender']}", label=t["team"], sub=f"{'Women' if t['gender'] == 'female' else 'Men'} · {t['n']} covered matches",
            toks=sorted(team_toks(t["team"])), w=math.log10(1 + t["n"]), href=f"/rivalry?a={t['team']}&gender={t['gender']}", g=t["gender"])
    for c in db.q("""SELECT competition, gender, any_value(format_group) AS f, count(*) AS n, min(year) AS y0, max(year) AS y1 FROM team_results WHERE competition IS NOT NULL GROUP BY 1, 2"""):
        add(type="competition", key=f"{c['competition']}|{c['gender']}", label=c["competition"], sub=f"{c['f']} · {c['n']} matches · {c['y0']}–{c['y1']}",
            toks=sorted(set(norm(c["competition"])) | {"competition", "tournament"}), w=math.log10(1 + c["n"]) + 0.4 - (1.2 if LOW_PRESTIGE.search(c["competition"]) else 0),
            href=f"/competition?name={c['competition']}&gender={c['gender']}", g=c["gender"])
    for c in db.q("""SELECT competition, season, gender, count(*) AS n, min(start_date) AS d0 FROM team_results WHERE competition IS NOT NULL AND season IS NOT NULL GROUP BY 1, 2, 3 HAVING count(*) >= 3"""):
        yrs = {str(c["d0"])[:4], *re.findall(r"\d{4}", c["season"] or "")}
        add(type="edition", key=f"{c['competition']}|{c['season']}|{c['gender']}", label=f"{c['competition']} {c['season']}", sub=f"{c['n']} matches",
            toks=sorted(set(norm(c["competition"])) | yrs | {c["season"].lower()}), w=math.log10(1 + c["n"]) + 0.2 - (1.2 if LOW_PRESTIGE.search(c["competition"]) else 0),
            href=f"/competition?name={c['competition']}&gender={c['gender']}&season={c['season']}", g=c["gender"])
    for m in db.q("SELECT match_id, team1, team2, competition, start_date, venue, city, gender, winner, event_stage FROM team_results"):
        toks = team_toks(m["team1"]) | team_toks(m["team2"]) | set(norm(m["competition"])) | {str(m["start_date"])[:4]} | set(norm(m["city"] or "")) \
            | set(norm((m["venue"] or "").split(",")[0]))
        add(type="match", key=m["match_id"], label=f"{m['team1']} v {m['team2']}",
            sub=f"{m['competition'] or 'Match'}{' · ' + m['event_stage'] if m['event_stage'] else ''} · {m['city'] or m['venue'] or ''} · {m['start_date']}",
            toks=sorted(toks), w=0.6 + (0.4 if m["event_stage"] in ("Final", "Semi Final") else 0) + 0.05 * (int(str(m["start_date"])[:4]) - 2000) / 10
            + (0.5 if re.search(r"world cup|premier league|asia cup", m["competition"] or "", re.I) else 0) - (0.8 if LOW_PRESTIGE.search(m["competition"] or "") else 0),
            href=f"/match/{m['match_id']}", g=m["gender"], teams=[m["team1"], m["team2"]], year=int(str(m["start_date"])[:4]))
    for r in db.q("""SELECT match_id, innings_no, batter_id, runs, balls, not_out, opponent, competition, start_date FROM bat_innings
                     QUALIFY runs >= 50 OR row_number() OVER (PARTITION BY batter_id ORDER BY runs DESC) <= 3"""):
        nm = names.get(r["batter_id"])
        if not nm:
            continue
        sc = f"{r['runs']}{'*' if r['not_out'] else ''}"
        add(type="innings", key=f"{r['match_id']}|{r['innings_no']}|{r['batter_id']}", label=f"{nm} {sc} v {r['opponent']}",
            sub=f"{r['balls']} balls · {r['competition'] or ''} · {r['start_date']}",
            toks=sorted(set(norm(nm)) | {str(r["runs"]), sc} | set(norm(r["opponent"])) | {str(r["start_date"])[:4], "innings"}),
            w=0.3 + r["runs"] / 150, href=f"/innings/{r['match_id']}/{r['innings_no']}/{r['batter_id']}", pid=r["batter_id"], year=int(str(r["start_date"])[:4]))
    for r in db.q("""SELECT match_id, innings_no, bowler_id, wickets, runs, balls, opponent, competition, start_date FROM bowl_innings
                     QUALIFY wickets >= 3 OR row_number() OVER (PARTITION BY bowler_id ORDER BY wickets DESC, runs) <= 2"""):
        nm = names.get(r["bowler_id"])
        if not nm:
            continue
        fig = f"{r['wickets']}/{r['runs']}"
        add(type="spell", key=f"{r['match_id']}|{r['innings_no']}|{r['bowler_id']}", label=f"{nm} {fig} v {r['opponent']}",
            sub=f"{r['balls'] // 6}.{r['balls'] % 6} overs · {r['competition']} · {r['start_date']}",
            toks=sorted(set(norm(nm)) | {fig, f"{r['wickets']}-{r['runs']}", "spell", "figures"} | set(norm(r["opponent"])) | {str(r["start_date"])[:4]}),
            w=0.3 + r["wickets"] / 5 - r["runs"] / 200, href=f"/spell/{r['match_id']}/{r['innings_no']}/{r['bowler_id']}", pid=r["bowler_id"],
            year=int(str(r["start_date"])[:4]))
    for r in db.q("SELECT batter_id, bowler_id, gender, balls, runs, outs FROM battles WHERE balls >= 48"):
        a, b = names.get(r["batter_id"]), names.get(r["bowler_id"])
        if not a or not b:
            continue
        add(type="battle", key=f"{r['batter_id']}|{r['bowler_id']}", label=f"{a} v {b}", sub=f"{r['balls']} balls · {r['runs']} runs · {r['outs']} out",
            toks=sorted(set(norm(a)) | set(norm(b)) | {"battle"}), w=math.log10(r["balls"]), href=f"/battle?bat={r['batter_id']}&bowl={r['bowler_id']}",
            sides=[sorted(set(norm(a))), sorted(set(norm(b)))])
    for r in db.q("""SELECT p1, p2, count(*) AS n, sum(runs) AS runs FROM partnerships GROUP BY 1, 2 HAVING count(*) >= 6"""):
        a, b = names.get(r["p1"]), names.get(r["p2"])
        if not a or not b:
            continue
        add(type="pair", key=f"{r['p1']}|{r['p2']}", label=f"{a} & {b}", sub=f"{r['n']} partnerships · {r['runs']} runs",
            toks=sorted(set(norm(a)) | set(norm(b)) | {"partnership", "partnerships", "pair"}), w=math.log10(r["runs"]),
            href=f"/partnerships?p1={r['p1']}&p2={r['p2']}")
    for r in db.q("""SELECT pid, count(*) AS n FROM (SELECT p1 AS pid FROM partnerships UNION ALL SELECT p2 FROM partnerships) GROUP BY 1 HAVING count(*) >= 20"""):
        nm = names.get(r["pid"])
        if nm:
            add(type="pair", key=f"hub|{r['pid']}", label=f"{nm}'s partnerships", sub=f"{r['n']} partnerships · who they bat best with",
                toks=sorted(set(norm(nm)) | {"partnership", "partnerships", "partners"}), w=math.log10(r["n"]) + 0.5,
                href=f"/players/{r['pid']}?tab=partners")
    for r in db.q("""SELECT ta, tb, gender, count(*) AS n FROM team_results GROUP BY 1, 2, 3 HAVING count(*) >= 4"""):
        add(type="rivalry", key=f"{r['ta']}|{r['tb']}|{r['gender']}", label=f"{r['ta']} v {r['tb']}",
            sub=f"{'Women' if r['gender'] == 'female' else 'Men'} · {r['n']} covered matches",
            toks=sorted(team_toks(r["ta"]) | team_toks(r["tb"]) | {"rivalry", "head-to-head"}), w=math.log10(r["n"]) + 0.3,
            href=f"/rivalry?a={r['ta']}&b={r['tb']}&gender={r['gender']}", sides=[sorted(set(norm(r["ta"]))), sorted(set(norm(r["tb"])))], g=r["gender"])
    for k, v in METRICS.items():
        add(type="record", key=k, label=f"{v[0]} leaderboard", sub=v[8], toks=sorted(set(norm(v[0])) | set(norm(k.replace("_", " "))) | {"record", "records", "most"}),
            w=1.0, href=f"/records?metric={k}")
    return {"version": VERSION, "built_at": db.manifest["built_at"], "entities": E}


class Index:
    def __init__(self, data: dict):
        self.E = data["entities"]
        self.inv: dict[str, list[int]] = defaultdict(list)
        for i, e in enumerate(self.E):
            for t in e["toks"]:
                self.inv[t].append(i)
        self.vocab = sorted(self.inv)

    def _match(self, tok: str) -> dict[int, float]:
        out = {i: 1.0 for i in self.inv.get(tok, [])}
        if len(tok) >= 3:  # prefix match ("kohl" → kohli), weaker than exact
            import bisect
            j = bisect.bisect_left(self.vocab, tok)
            while j < len(self.vocab) and self.vocab[j].startswith(tok):
                if self.vocab[j] != tok:
                    for i in self.inv[self.vocab[j]]:
                        out.setdefault(i, 0.75)
                j += 1
        return out

    def search(self, q: str, limit_per_type: int = 6) -> dict:
        raw = norm(q)
        vs = bool(re.search(r"\b(v|vs|versus|against)\b", q.lower()))
        fig = next((t for t in raw if re.fullmatch(r"\d{1,2}[/-]\d{1,3}", t)), None)
        score_tok = next((t for t in raw if re.fullmatch(r"\d{1,3}\*", t)), None)
        year = next((int(t) for t in raw if re.fullmatch(r"(19|20)\d{2}", t)), None)
        metric = next((METRIC_WORDS[t] for t in raw if t in METRIC_WORDS), None)
        phase = next((PHASE_WORDS[t] for t in raw if t in PHASE_WORDS), None)
        toks = [t for t in raw if t not in STOP and t not in ("overs", "over")]
        if not toks:
            return {"query": q, "groups": [], "intent": {}}
        scores: dict[int, float] = defaultdict(float)
        hits: dict[int, int] = defaultdict(int)
        for t in toks:
            for i, s in self._match(t).items():
                scores[i] += s; hits[i] += 1
        need = len(toks) if len(toks) <= 2 else len(toks) - 1  # tolerate one unmatched word in longer queries
        res = []
        for i, s in scores.items():
            if hits[i] < need:
                continue
            e = self.E[i]
            sc = s / len(toks) * 3 + e["w"] * 0.6 + (1.5 if hits[i] == len(toks) else 0)  # every word matched
            if vs and e["type"] in ("battle", "rivalry", "match"):
                sc += 1.5
            if fig and e["type"] == "spell":
                sc += 2.5
            if score_tok and e["type"] == "innings":
                sc += 2.5
            if year and e.get("year") == year:
                sc += 1.0
            if year and e["type"] == "match":
                sc += 0.5
            if year and e["type"] == "edition":
                sc += 1.6
            if "partnership" in q.lower() or "partnerships" in q.lower():
                sc += 1.5 if e["type"] == "pair" else 0
            if e["type"] == "player" and len(toks) <= 2 and not (vs or fig or score_tok or year):
                sc += 1.0
            res.append((sc, i))
        res.sort(reverse=True)
        groups: dict[str, list] = {}
        best: dict[str, float] = {}
        for sc, i in res:
            e = self.E[i]
            g = groups.setdefault(e["type"], [])
            if len(g) < limit_per_type:
                g.append({"type": e["type"], "label": e["label"], "sub": e["sub"], "href": e["href"], "score": round(sc, 2)})
                best[e["type"]] = max(best.get(e["type"], 0), sc)
        # Synthesised record result: "death overs economy" → a ready-made leaderboard
        if metric:
            lab = METRICS[metric][0]
            href = f"/records?metric={metric}" + (f"&phase={phase}" if phase else "")
            groups.setdefault("record", []).insert(0, {"type": "record", "label": f"{lab}{' in ' + phase + ' overs' if phase else ''}",
                                                       "sub": "Open this leaderboard in Records (men's and women's ranked separately)", "href": href, "score": 9})
            best["record"] = max(best.get("record", 0), 9 if not vs else 2)
        order = sorted(groups, key=lambda t: -best.get(t, 0))
        return {"query": q, "intent": {"versus": vs, "figures": fig, "score": score_tok, "year": year, "metric": metric, "phase": phase},
                "groups": [{"type": t, "label": TYPE_LABEL[t], "items": groups[t]} for t in order],
                "note": "Search finds players, matches and other things. To ask a statistical question, use Ask."}


def load(db: DB) -> Index:
    p = db.dataset_dir / "derived" / "search_index.json"
    if p.exists():
        d = json.loads(p.read_text())
        if d.get("built_at") == db.manifest["built_at"] and d.get("version") == VERSION:
            return Index(d)
    d = build_index(db)
    p.write_text(json.dumps(d, default=str))
    return Index(d)
