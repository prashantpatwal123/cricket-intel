"""Discovery Engine v1: deterministic candidate findings, ranked. No language model writes or invents a finding.

Every candidate comes from a generator that runs a named statistical comparison over covered data and returns:
headline (templated), statement ("In our covered … data"), the numbers, WHY (comparison, calculation, test, sample),
a link to the evidence, and its ranking components. Ranking = unusualness × sample strength × recency ×
recognisability, then a diversity pass (one finding per player, rotate types and genders).
"""
from __future__ import annotations

import json
import math
from collections import defaultdict

from ..db import DB
from .filters import FULL_MEMBERS
from .player import ROUTE_META

VERSION = "discovery-1.1"
FM = ",".join("'" + t + "'" for t in FULL_MEMBERS)
SCOPE = f"(team_type = 'club' OR (batting_team IN ({FM}) AND bowling_team IN ({FM})))"
GL = {"male": "men's", "female": "women's"}
TYPE_LABEL = {"matchup": "Surprising matchup", "dismissal": "Unusual dismissal pattern", "partnership": "Exceptional partnership",
              "state": "When they change", "trend": "Career trend", "record": "Record in reach", "comeback": "Comeback chase",
              "pattern": "Strength / weakness"}


def _pois_upper(k: int, lam: float) -> float:
    """P(X >= k) for Poisson(lam)."""
    if k <= 0:
        return 1.0
    term, cdf = math.exp(-lam), 0.0
    for i in range(k):
        cdf += term
        term *= lam / (i + 1)
    return max(1e-300, 1 - cdf)


def _binom_upper(k: int, n: int, p: float) -> float:
    tot = 0.0
    for i in range(k, n + 1):
        tot += math.exp(math.lgamma(n + 1) - math.lgamma(i + 1) - math.lgamma(n - i + 1) + i * math.log(p) + (n - i) * math.log(1 - p))
    return max(1e-300, min(1.0, tot))


def _norm_p(z: float) -> float:
    return max(1e-300, math.erfc(abs(z) / math.sqrt(2)))


def _matches(db: DB) -> dict:
    return {r["person_id"]: r["matches"] for r in db.q("SELECT person_id, matches FROM player_profile")}


def gen_matchups(db: DB) -> list[dict]:
    out = []
    rows = db.q(f"""
      WITH bat AS (SELECT batter_id, format_group, gender, count(*) FILTER (WHERE wides = 0) AS n,
                          sum(runs_batter) AS r, sum(runs_batter * runs_batter) AS rr FROM balls WHERE {SCOPE} GROUP BY ALL),
           bo AS (SELECT batter_id, format_group, count(*) AS outs FROM dis WHERE bowler_credited GROUP BY ALL),
           pair AS (SELECT b.batter_id, b.bowler_id, b.format_group, b.gender, any_value(b.batter) AS batter, any_value(b.bowler) AS bowler,
                           count(*) FILTER (WHERE b.wides = 0) AS n, sum(b.runs_batter) AS r, sum(b.runs_batter * b.runs_batter) AS rr,
                           max(b.start_date) AS last_date, count(DISTINCT b.match_id) AS matches
                    FROM balls b WHERE {SCOPE} GROUP BY 1, 2, 3, 4 HAVING count(*) FILTER (WHERE b.wides = 0) >= 60),
           po AS (SELECT batter_id, bowler_id, format_group, count(*) AS outs FROM dis WHERE bowler_credited GROUP BY ALL)
      SELECT pair.*, coalesce(po.outs, 0) AS outs, bat.n AS bn, bat.r AS br, bat.rr AS brr, coalesce(bo.outs, 0) AS bouts
      FROM pair JOIN bat USING (batter_id, format_group, gender)
      LEFT JOIN po USING (batter_id, bowler_id, format_group) LEFT JOIN bo USING (batter_id, format_group)""")
    names = {x["person_id"]: x["name"] for x in db.q("SELECT person_id, name FROM player_profile")}
    for r in rows:
        if not r["bn"] or r["bn"] < 500:
            continue
        r["batter"], r["bowler"] = names.get(r["batter_id"], r["batter"]), names.get(r["bowler_id"], r["bowler"])
        rate = r["bouts"] / r["bn"]
        lam = r["n"] * rate
        if r["outs"] >= 4 and r["outs"] >= 2.2 * lam:
            p = _pois_upper(r["outs"], lam)
            out.append({"type": "matchup", "gender": r["gender"], "format": r["format_group"], "p": p, "n": r["n"], "last_date": str(r["last_date"]),
                        "entities": [r["batter_id"], r["bowler_id"]], "people": [r["batter"], r["bowler"]],
                        "headline": f"{r['bowler']} has dismissed {r['batter']} {r['outs']} times in {r['n']} balls",
                        "statement": f"In our covered {GL[r['gender']]} {r['format_group']} data, {r['bowler']} has dismissed {r['batter']} "
                                     f"{r['outs']} times. At {r['batter']}'s usual dismissal rate we'd expect {lam:.1f}.",
                        "numbers": [{"label": "Dismissals", "value": r["outs"]}, {"label": "Expected", "value": round(lam, 1)}, {"label": "Balls", "value": r["n"]}],
                        "why": {"comparison": f"{r['batter']}'s dismissals by this bowler v their dismissal rate against all bowlers "
                                              f"({100 * rate:.2f} per 100 balls)",
                                "calculation": f"expected = {r['n']} balls × {rate:.4f} = {lam:.2f}; observed {r['outs']}",
                                "test": f"Poisson upper tail p = {p:.2g}", "sample": f"{r['n']} balls over {r['matches']} matches"},
                        "href": f"/battle?bat={r['batter_id']}&bowl={r['bowler_id']}"})
        m0, n0 = r["br"] / r["bn"], r["bn"]
        m1 = r["r"] / r["n"]
        v1 = max(1e-9, (r["rr"] - r["n"] * m1 * m1) / (r["n"] - 1))
        v0 = max(1e-9, (r["brr"] - n0 * m0 * m0) / (n0 - 1))
        z = (m1 - m0) / math.sqrt(v1 / r["n"] + v0 / n0)
        if z > 3 and r["outs"] <= max(1, lam * 0.5) and r["n"] >= 90:
            out.append({"type": "matchup", "gender": r["gender"], "format": r["format_group"], "p": _norm_p(z), "n": r["n"],
                        "last_date": str(r["last_date"]), "entities": [r["batter_id"], r["bowler_id"]], "people": [r["batter"], r["bowler"]],
                        "headline": f"{r['batter']} scores at {100 * m1:.0f} against {r['bowler']}, out {r['outs']} time{'s' if r['outs'] != 1 else ''}",
                        "statement": f"In our covered {GL[r['gender']]} {r['format_group']} data, {r['batter']} has {r['r']} runs off {r['n']} balls "
                                     f"from {r['bowler']} (strike rate {100 * m1:.0f}, against {100 * m0:.0f} overall) and has been dismissed by "
                                     f"them {r['outs']} time{'s' if r['outs'] != 1 else ''}.",
                        "numbers": [{"label": "SR v this bowler", "value": round(100 * m1)}, {"label": "SR overall", "value": round(100 * m0)},
                                    {"label": "Outs", "value": r["outs"]}],
                        "why": {"comparison": f"{r['batter']} against this bowler v against all bowlers", "calculation":
                                f"{100 * m1:.1f} − {100 * m0:.1f} = {100 * (m1 - m0):+.1f} strike-rate points", "test": f"Welch z = {z:.1f}",
                                "sample": f"{r['n']} balls, {r['matches']} matches"},
                        "href": f"/battle?bat={r['batter_id']}&bowl={r['bowler_id']}"})
    return out


def gen_dismissals(db: DB) -> list[dict]:
    routes = ("BOWLED", "LBW", "CAUGHT_KEEPER", "STUMPED", "RUN_OUT", "CAUGHT_BOWLER")
    lg = {(r["format_group"], r["gender"], r["route"]): r["share"] for r in db.q(f"""
        SELECT format_group, gender, route, count(*) * 1.0 / sum(count(*)) OVER (PARTITION BY format_group, gender) AS share
        FROM dis WHERE counts_as_dismissal AND {SCOPE} AND batter_position <= 7 GROUP BY format_group, gender, route""")}
    rows = db.q(f"""SELECT player_out_id AS pid, any_value(player_out) AS name, format_group, gender, route, count(*) AS k,
                           sum(count(*)) OVER (PARTITION BY player_out_id, format_group) AS n, max(max(start_date)) OVER (PARTITION BY player_out_id) AS last_date
                    FROM dis WHERE counts_as_dismissal AND {SCOPE} GROUP BY player_out_id, format_group, gender, route""")
    out = []
    names = {x["person_id"]: x["name"] for x in db.q("SELECT person_id, name FROM player_profile")}
    for r in rows:
        if r["route"] not in routes or r["n"] < 30:
            continue
        r["name"] = names.get(r["pid"], r["name"])
        p0 = lg.get((r["format_group"], r["gender"], r["route"]))
        if not p0 or r["k"] / r["n"] < 1.8 * p0 or r["k"] < 6:
            continue
        p = _binom_upper(r["k"], r["n"], p0)
        label = ROUTE_META.get(r["route"], {}).get("label", r["route"]).lower()
        out.append({"type": "dismissal", "gender": r["gender"], "format": r["format_group"], "p": p, "n": r["n"], "last_date": str(r["last_date"]),
                    "entities": [r["pid"]], "people": [r["name"]],
                    "headline": f"{r['name']}: {100 * r['k'] / r['n']:.0f}% of dismissals {label}, against {100 * p0:.0f}% typically",
                    "statement": f"In our covered {GL[r['gender']]} {r['format_group']} data, {r['k']} of {r['name']}'s {r['n']} dismissals were "
                                 f"{label}. For top- and middle-order batters the share is {100 * p0:.1f}%.",
                    "numbers": [{"label": label.capitalize(), "value": r["k"]}, {"label": "Dismissals", "value": r["n"]},
                                {"label": "Typical share", "value": f"{100 * p0:.0f}%"}],
                    "why": {"comparison": f"share of dismissals {label} v batters at positions 1–7 in the same format and gender",
                            "calculation": f"{r['k']}/{r['n']} = {100 * r['k'] / r['n']:.1f}% v {100 * p0:.1f}%", "test": f"binomial upper tail p = {p:.2g}",
                            "sample": f"{r['n']} dismissals"},
                    "href": f"/players/{r['pid']}?tab=dismissals&format={r['format_group']}&route={r['route']}"})
    return out


def gen_partnerships(db: DB) -> list[dict]:
    lg = {(r["format_group"], r["gender"]): r for r in db.q(f"""SELECT format_group, gender, sum(runs) * 6.0 / sum(balls) AS rr,
                  sum(runs) * 1.0 / count(*) FILTER (WHERE ended = 'wicket') AS avg FROM partnerships WHERE {SCOPE} GROUP BY ALL""")}
    rows = db.q(f"""SELECT p1, p2, format_group, gender, count(*) AS inns, sum(runs) AS runs, sum(balls) AS balls,
                           count(*) FILTER (WHERE ended = 'wicket') AS w, max(start_date) AS last_date, max(runs) AS best
                    FROM partnerships WHERE {SCOPE} GROUP BY ALL HAVING count(*) >= 15 AND sum(balls) >= 500""")
    names = {r["person_id"]: r["name"] for r in db.q("SELECT person_id, name FROM player_profile")}
    out = []
    for r in rows:
        L = lg[(r["format_group"], r["gender"])]
        avg = r["runs"] / max(1, r["w"])
        ratio = avg / L["avg"]
        if ratio < 1.8:
            continue
        # partnership totals are roughly exponential: the mean of n exponentials has sd = mean / sqrt(n)
        z = (avg - L["avg"]) / (L["avg"] / math.sqrt(max(1, r["w"])))
        a, b = names.get(r["p1"], r["p1"]), names.get(r["p2"], r["p2"])
        out.append({"type": "partnership", "gender": r["gender"], "format": r["format_group"], "p": _norm_p(z), "n": r["balls"],
                    "last_date": str(r["last_date"]), "entities": [r["p1"], r["p2"]], "people": [a, b],
                    "headline": f"{a} and {b} average {avg:.0f} per partnership, {ratio:.1f}× the norm",
                    "statement": f"In our covered {GL[r['gender']]} {r['format_group']} data, {a} and {b} have batted together {r['inns']} times, "
                                 f"adding {r['runs']} runs at {6 * r['runs'] / r['balls']:.2f} an over. Typical: {L['avg']:.0f} per partnership, "
                                 f"{L['rr']:.2f} an over.",
                    "numbers": [{"label": "Avg stand", "value": round(avg)}, {"label": "Typical", "value": round(L["avg"])},
                                {"label": "Stands", "value": r["inns"]}],
                    "why": {"comparison": "runs per partnership ended by a wicket v all partnerships in the same format and gender",
                            "calculation": f"{r['runs']} runs ÷ {r['w']} dismissals = {avg:.1f} v {L['avg']:.1f}", "test": f"z = {z:.1f} (exponential approximation)",
                            "sample": f"{r['inns']} partnerships, {r['balls']} balls"},
                    "href": f"/partnerships?p1={r['p1']}&p2={r['p2']}&format={r['format_group']}"})
    return out


def gen_states(db: DB, n_per: int = 12) -> list[dict]:
    from . import states as ST
    top = db.q("""SELECT batter_id AS pid, format_group, gender, any_value(batter) AS nm, count(*) AS n, max(start_date) AS last_date FROM balls
                  WHERE wides = 0 AND format_group IN ('T20', 'ODI') GROUP BY batter_id, format_group, gender
                  QUALIFY row_number() OVER (PARTITION BY format_group, gender ORDER BY count(*) DESC) <= ?""", [n_per])
    names = {r["person_id"]: r["name"] for r in db.q("SELECT person_id, name FROM player_profile")}
    out = []
    for t in top:
        s = ST.states(db, t["pid"], "batting", t["format_group"])
        for c in s.get("biggest_changes", [])[:1]:
            g = next(g for g in s["groups"] if g["label"] == c["group"])
            row = next(x for x in g["rows"] if x["bucket"] == c["bucket"])
            m, e = row["player"]["strike_rate"], row["expected_if_typical"]
            iv = row["player"]["sr_interval"]
            se = (iv[1] - iv[0]) / (2 * 1.645)
            z = (m - e) / se if se else 0
            nm = names.get(t["pid"], t["nm"])
            word = "faster" if c["relative"] > 0 else "slower"
            ph = c["phrase"]
            out.append({"type": "state", "gender": t["gender"], "format": t["format_group"], "p": _norm_p(z), "n": row["player"]["balls"],
                        "last_date": str(t["last_date"]), "entities": [t["pid"]], "people": [nm],
                        "headline": f"{nm} scores {abs(c['relative']):.0f} strike-rate points {word} than expected {ph}",
                        "statement": f"In our covered {GL[t['gender']]} {t['format_group']} data, {nm}'s strike rate {ph} is {m}. "
                                     f"If they changed like similar batters do, we'd expect {e}.",
                        "numbers": [{"label": "Strike rate", "value": m}, {"label": "Expected", "value": e}, {"label": "Balls", "value": row["player"]["balls"]}],
                        "why": {"comparison": s["peer_definition"], "calculation": s["method"], "test": f"z = {z:.1f}; 99% interval excludes expected",
                                "sample": f"{row['player']['balls']} balls"},
                        "href": f"/players/{t['pid']}?tab=states&format={t['format_group']}"})
    return out


def gen_trends(db: DB) -> list[dict]:
    rows = db.q(f"""SELECT batter_id AS pid, any_value(batter) AS nm, format_group, gender, year, count(*) AS n, sum(runs_batter) AS r,
                           sum(runs_batter * runs_batter) AS rr FROM balls WHERE wides = 0 AND {SCOPE} AND year >= 2021 GROUP BY ALL""")
    by = defaultdict(dict)
    for r in rows:
        by[(r["pid"], r["format_group"], r["gender"], r["nm"])][r["year"]] = r
    names = {r["person_id"]: r["name"] for r in db.q("SELECT person_id, name FROM player_profile")}
    latest = max(r["year"] for r in rows)
    out = []
    for (pid, fmt, g, nm), ys in by.items():
        cur = ys.get(latest) if ys.get(latest, {}).get("n", 0) >= 150 else ys.get(latest - 1)
        if not cur or cur["n"] < 150:
            continue
        prev = [v for y, v in ys.items() if cur["year"] - 3 <= y < cur["year"]]
        n0 = sum(v["n"] for v in prev)
        if n0 < 400:
            continue
        r0, rr0 = sum(v["r"] for v in prev), sum(v["rr"] for v in prev)
        m1, m0 = cur["r"] / cur["n"], r0 / n0
        v1 = max(1e-9, (cur["rr"] - cur["n"] * m1 * m1) / (cur["n"] - 1)); v0 = max(1e-9, (rr0 - n0 * m0 * m0) / (n0 - 1))
        z = (m1 - m0) / math.sqrt(v1 / cur["n"] + v0 / n0)
        if abs(z) < 2.5 or abs(m1 - m0) < 0.12:
            continue
        nm2 = names.get(pid, nm)
        word = "up" if m1 > m0 else "down"
        out.append({"type": "trend", "gender": g, "format": fmt, "p": _norm_p(z), "n": cur["n"], "last_date": f"{cur['year']}-12-31",
                    "entities": [pid], "people": [nm2],
                    "headline": f"{nm2}'s {fmt} strike rate is {word}: {100 * m1:.0f} in {cur['year']} v {100 * m0:.0f} the three years before",
                    "statement": f"In our covered {GL[g]} {fmt} data, {nm2} scored at {100 * m1:.1f} in {cur['year']} ({cur['n']} balls) against "
                                 f"{100 * m0:.1f} over the previous three years ({n0} balls).",
                    "numbers": [{"label": str(cur["year"]), "value": round(100 * m1)}, {"label": "Prior 3 yrs", "value": round(100 * m0)},
                                {"label": "Balls", "value": cur["n"]}],
                    "why": {"comparison": "latest covered year v the three years before", "calculation": f"{100 * m1:.1f} − {100 * m0:.1f}",
                            "test": f"Welch z = {z:.1f}", "sample": f"{cur['n']} v {n0} balls"},
                    "href": f"/players/{pid}?tab=timeline&format={fmt}"})
    return out


def gen_records(db: DB) -> list[dict]:
    """Only for competitions Cricsheet covers completely (IPL, WPL), so 'record' means something."""
    out = []
    latest = {r["competition"]: r["y"] for r in db.q("""SELECT competition, max(year) AS y FROM balls
              WHERE competition IN ('Indian Premier League', 'Women''s Premier League') GROUP BY 1""")}
    for comp, metric, label, expr, col in (("Indian Premier League", "sixes", "sixes", "count(*) FILTER (WHERE is_six)", "batter_id"),
                                          ("Indian Premier League", "runs", "runs", "sum(runs_batter)", "batter_id"),
                                          ("Women's Premier League", "runs", "runs", "sum(runs_batter)", "batter_id"),
                                          ("Women's Premier League", "sixes", "sixes", "count(*) FILTER (WHERE is_six)", "batter_id")):
        rows = db.q(f"""SELECT {col} AS pid, any_value(batter) AS nm, {expr} AS v, max(year) AS last_year, any_value(gender) AS g
                        FROM balls WHERE competition = ? GROUP BY 1 ORDER BY v DESC LIMIT 10""", [comp])
        if len(rows) < 2:
            continue
        lead = rows[0]
        for r in rows[1:6]:
            gap = lead["v"] - r["v"]
            if r["last_year"] == latest[comp] and gap <= 0.08 * lead["v"] and gap > 0:
                nm = db.q1("SELECT name FROM player_profile WHERE person_id = ?", [r["pid"]])["name"]
                lnm = db.q1("SELECT name FROM player_profile WHERE person_id = ?", [lead["pid"]])["name"]
                out.append({"type": "record", "gender": r["g"], "format": "T20", "p": 1e-3, "n": r["v"], "last_date": f"{latest[comp]}-12-31",
                            "entities": [r["pid"], lead["pid"]], "people": [nm, lnm],
                            "headline": f"{nm} is {gap} {label} behind {lnm}'s {comp} record",
                            "statement": f"In our {comp} data (Cricsheet covers every match), {lnm} leads with {lead['v']} {label}. "
                                         f"{nm}, active in {latest[comp]}, has {r['v']}.",
                            "numbers": [{"label": nm, "value": r["v"]}, {"label": lnm, "value": lead["v"]}, {"label": "Gap", "value": gap}],
                            "why": {"comparison": f"career {label} in {comp}", "calculation": f"{lead['v']} − {r['v']} = {gap}",
                                    "test": "within 8% of the leader and active in the latest season", "sample": "complete competition coverage"},
                            "href": f"/records?metric={metric}&competition={comp}&gender={r['g']}"})
    return out


def gen_comebacks(db: DB, sdx_available: bool) -> list[dict]:
    if not sdx_available:
        return []
    rows = db.q(f"""SELECT b.match_id, any_value(b.batting_team) AS team, any_value(b.bowling_team) AS opp, any_value(b.start_date) AS d,
                           any_value(b.competition) AS comp, any_value(b.format_group) AS fmt, any_value(b.gender) AS g, max(s.sdx) AS peak,
                           arg_max(b.delivery_id, s.sdx) AS peak_delivery, arg_max(b.score_before || '/' || b.wickets_before, s.sdx) AS peak_score,
                           arg_max(b.runs_required, s.sdx) AS rr, arg_max(b.balls_left, s.sdx) AS bl
                    FROM balls b JOIN situation s USING (delivery_id)
                    WHERE b.winner = b.batting_team AND b.innings_no = 2 AND b.method IS NULL AND {SCOPE.replace('team_type', 'b.team_type').replace('batting_team', 'b.batting_team').replace('bowling_team', 'b.bowling_team')}
                    GROUP BY b.match_id HAVING max(s.sdx) >= 92""")
    out = []
    for r in rows:
        top = db.q1("""SELECT b.batter_id, coalesce(any_value(pp.name), any_value(b.batter)) AS nm, sum(b.runs_batter) AS runs
                       FROM balls b LEFT JOIN player_profile pp ON pp.person_id = b.batter_id WHERE b.match_id = ? AND b.innings_no = 2
                       GROUP BY 1 ORDER BY runs DESC LIMIT 1""", [r["match_id"]])
        out.append({"type": "comeback", "gender": r["g"], "format": r["fmt"], "p": max(1e-6, (100 - r["peak"]) / 100), "n": 1, "last_date": str(r["d"]),
                    "entities": [top["batter_id"]], "people": [r["team"]], "experimental": True,
                    "headline": f"{r['team']} won from {r['peak_score']}, needing {r['rr']} off {r['bl']}",
                    "statement": f"In {r['comp']} ({r['d']}), {r['team']} needed {r['rr']} off {r['bl']} balls at {r['peak_score']} against {r['opp']}, "
                                 f"a point where {r['peak']:.0f}% of similar chases historically failed, and won. Top scorer: {top['nm']} ({top['runs']}).",
                    "numbers": [{"label": "Peak difficulty", "value": f"{r['peak']:.0f}"}, {"label": "Needed", "value": r["rr"]}, {"label": "Balls", "value": r["bl"]}],
                    "why": {"comparison": "Situation Difficulty — Experimental (SDX v0.1)", "calculation": "100 × historical failure rate at the same demand",
                            "test": "chase won after SDX ≥ 92", "sample": "one match"},
                    "href": f"/innings/{r['match_id']}/2/{top['batter_id']}"})
    return out


def rank(cands: list[dict], matches: dict, limit: int = 40) -> list[dict]:
    for c in cands:
        unusual = min(10.0, -math.log10(c["p"]))
        sample = min(1.0, math.log10(max(10, c["n"])) / 3)
        y = int(c["last_date"][:4])
        recency = 1.5 if y >= 2025 else 1.25 if y >= 2023 else 1.0
        recog = min(1.0, math.log10(1 + max(matches.get(e, 0) for e in c["entities"])) / math.log10(400))
        c["score"] = round(unusual * (0.5 + 0.5 * recog) * recency * (0.6 + 0.4 * sample), 3)
        c["score_parts"] = {"unusualness": round(unusual, 2), "sample": round(sample, 2), "recency": recency, "recognisability": round(recog, 2)}
        c["type_label"] = TYPE_LABEL[c["type"]]
        c["id"] = f"{c['type']}:{':'.join(c['entities'])}:{c['format']}"
    cands.sort(key=lambda c: -c["score"])
    # diversity: one finding per lead entity; round-robin across types; alternate genders where possible
    seen, buckets = set(), defaultdict(list)
    for c in cands:
        if c["entities"][0] in seen:
            continue
        seen.add(c["entities"][0])
        buckets[c["type"]].append(c)
    picked, gi = [], 0
    while len(picked) < limit and any(buckets.values()):
        for t in list(buckets):
            if not buckets[t]:
                del buckets[t]; continue
            want = ("male", "female")[gi % 2]
            idx = next((i for i, c in enumerate(buckets[t][:4]) if c["gender"] == want), 0)
            picked.append(buckets[t].pop(idx)); gi += 1
            if len(picked) >= limit:
                break
    return picked


def discover(db: DB, sdx_available: bool = False) -> dict:
    path = db.dataset_dir / "derived" / f"discovery_cache{'_exp' if sdx_available else ''}.json"
    if path.exists():
        cached = json.loads(path.read_text())
        if cached.get("built_at") == db.manifest["built_at"] and cached.get("version") == VERSION:
            return cached
    import time
    t0 = time.time()
    counts, cands = {}, []
    for name, fn in (("matchup", lambda: gen_matchups(db)), ("dismissal", lambda: gen_dismissals(db)), ("partnership", lambda: gen_partnerships(db)),
                     ("state", lambda: gen_states(db)), ("trend", lambda: gen_trends(db)), ("record", lambda: gen_records(db)),
                     ("comeback", lambda: gen_comebacks(db, sdx_available))):
        c = fn()
        counts[name] = len(c)
        cands += c
    items = rank(cands, _matches(db))
    out = {"version": VERSION, "built_at": db.manifest["built_at"], "items": items, "candidates": counts, "seconds": round(time.time() - t0, 1),
           "method": "Deterministic generators run named tests over covered data; each candidate is ranked by unusualness (−log10 p, capped), "
                     "sample strength, recency and how recognisable the players are, then diversified (one per player, rotating types and "
                     "genders). Text is templated from the computed numbers; no language model is involved."}
    path.write_text(json.dumps(out, default=str))
    return out
