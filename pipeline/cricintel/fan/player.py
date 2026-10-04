"""Fan player home (Phase 7): what kind of cricketer is this, what makes them unusual, where to go next.

Sections, all deterministic and inspectable:
  hero            role (from covered balls), teams, formats, covered career span, key numbers
  different       3–5 evidence-backed findings, plain words, method behind WHY (strength/weakness engine + fingerprint extremes)
  stories         Player Stories cards ("Kohli after 30 balls", "Bumrah at the death"): headline, evidence, sample, comparison,
                  a deliveries link and provenance. Templated; never causal ("because", "handles pressure" are not used).
  matchups        biggest battles, dismissed most by, dominated, most balanced, unusual (and the bowler equivalents),
                  with sample shown and the "rivalry" label withheld below 120 balls / 5 matches
The fingerprint, dismissal DNA, partnerships, records and career sections reuse the existing endpoints.
"""
from __future__ import annotations

import math
import re
from functools import lru_cache

from ..db import DB
from ..analytics import fingerprint as FP
from ..analytics import insights as INS
from ..analytics.entities import names
from ..analytics.stats import wilson
from . import kg

CAUSAL = re.compile(r"\b(because|handles? pressure|clutch|loses concentration|nerves|choke|mental|bottle)\b", re.I)
RIVALRY_MIN_BALLS, RIVALRY_MIN_MATCHES = 120, 5
TINY_BALLS = 30


def _nm(db, pid):
    return names(db).get(pid, pid)


def ordinal(n: int) -> str:
    n = int(round(n))
    return f"{n}{'th' if 10 <= n % 100 <= 20 else {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')}"


# ------------------------------------------------------------------------------------------------ hero
@lru_cache(maxsize=4096)
def hero(db: DB, pid: str) -> dict | None:
    p = db.q1("SELECT * FROM player_profile WHERE person_id = ?", [pid])
    if not p:
        return None
    r = kg.role(db, pid)
    fm = db.q("""SELECT format_group AS f, count(DISTINCT match_id) AS m, min(start_date) AS a, max(start_date) AS b FROM balls
                 WHERE (batter_id = ? OR bowler_id = ?) AND format_group IN ('T20', 'ODI') GROUP BY 1 ORDER BY m DESC""", [pid, pid])
    bat = db.q1("""SELECT sum(runs) AS runs, sum(balls) AS balls, count(*) FILTER (WHERE NOT not_out) AS outs, count(*) AS inns, max(runs) AS hs
                   FROM bat_innings WHERE batter_id = ?""", [pid])
    bowl = db.q1("""SELECT sum(wickets) AS w, sum(balls) AS balls, sum(runs) AS runs, count(*) AS inns, max(wickets) AS best FROM bowl_innings
                    WHERE bowler_id = ?""", [pid])
    # role only where the covered balls make it defensible; otherwise a neutral presentation (no role-specific claims)
    neutral = (r["balls_faced"] + r["balls_bowled"]) < 300
    kind = ("player" if neutral else "all-rounder" if r["allrounder"] else "bowler" if r["primary"] == "bowler" else
            "wicketkeeper-batter" if p["wicketkeeper"] else "batter")
    layout = "neutral" if neutral else "allrounder" if r["allrounder"] else ("bowler" if r["primary"] == "bowler" else
             "keeper" if p["wicketkeeper"] else "batter")
    nums = []
    if r["primary"] == "batter" or r["allrounder"]:
        if bat and bat["balls"]:
            nums += [{"v": f"{bat['runs']:,}", "l": "runs"}, {"v": f"{100 * bat['runs'] / bat['balls']:.1f}", "l": "strike rate"},
                     {"v": f"{bat['runs'] / bat['outs']:.1f}" if bat["outs"] else "–", "l": "average"}]
    if r["primary"] == "bowler" or r["allrounder"]:
        if bowl and bowl["balls"]:
            nums += [{"v": f"{bowl['w']:,}", "l": "wickets"}, {"v": f"{6 * bowl['runs'] / bowl['balls']:.2f}", "l": "economy"}]
            if not r["allrounder"]:
                nums.append({"v": f"{bowl['balls'] / bowl['w']:.1f}" if bowl["w"] else "–", "l": "balls per wicket"})
    span = (min(x["a"] for x in fm), max(x["b"] for x in fm)) if fm else (None, None)
    keeping = None
    if layout == "keeper":
        keeping = db.q1("""SELECT count(*) FILTER (WHERE route = 'CAUGHT_KEEPER' AND fielder_id = ?) AS ct, count(*) FILTER (WHERE kind = 'stumped' AND fielder_id = ?) AS st
                           FROM dis WHERE fielder_id = ?""", [pid, pid, pid])
    return {"pid": pid, "name": p["name"], "kind": kind, "layout": layout, "keeping": keeping, "role": r, "gender": p["genders"][0], "teams": p["teams"][:4], "more_teams": max(0, len(p["teams"]) - 4),
            "formats": [{"format": x["f"], "matches": x["m"]} for x in fm], "matches": p["matches"],
            "span": {"from": str(span[0]) if span[0] else None, "to": str(span[1]) if span[1] else None}, "numbers": nums[:4],
            "coverage_note": "Covered Cricsheet matches only: these are not official career totals.",
            "metadata_known": {"batting_hand": p["batting_hand"], "bowling_style": p["bowling_style"]}}


# ------------------------------------------------------------------------------------------------ what makes them different
UNIT = {"sr": "", "bnd_rate": "%", "out_rate": " per 100 balls", "dot_rate": "%"}


def _plain_insight(c: dict, name: str) -> dict | None:
    pl = c.get("plain")
    if not pl:
        return None
    ph = pl["phrase"]
    # the engine tests the CHANGE in a situation relative to the typical change, so the headline describes the change
    pc, tc = pl["player_in"] - pl["player_out"], pl["typical_in"] - pl["typical_out"]
    typ = f"a typical {pl['band']} batter's"
    if pc > 0 and tc <= 0:
        move = f"rises, where {typ} falls"
    elif pc < 0 and tc >= 0:
        move = f"falls, where {typ} rises"
    elif pc > 0:
        move = f"rises {'more' if pl['direction'] == 'higher' else 'less'} than {typ}"
    else:
        move = f"falls {'more' if pl['direction'] == 'lower' else 'less'} than {typ}"
    head = f"{ph[0].upper() + ph[1:]}, {name}'s {pl['metric_label']} {move}"
    u = UNIT[pl["metric"]]
    body = (f"{name}'s {pl['metric_label']} {ph}: {pl['player_in']:g}{u} (otherwise {pl['player_out']:g}{u}). "
            f"A typical {pl['band']} batter: {pl['typical_in']:g}{u} {ph} (otherwise {pl['typical_out']:g}{u}).")
    return {"id": f"ins:{c['id']}", "source": "strengths engine", "kind": c["kind"], "headline": head, "body": body,
            "sample": f"{c['sample']['inside_balls']:,} balls in this situation", "stable": c["stable"], "why": c["why"],
            "evidence": {"query": c["evidence_query"], "label": f"{name} {ph}"}, "prov": "MODELLED comparison of OBSERVED balls"}


# plain words for the two ends of a dimension (low end, high end)
PLAIN = {"econ": ("most economical", "most expensive"), "pp_econ": ("most economical", "most expensive"), "mid_econ": ("most economical", "most expensive"),
         "death_econ": ("most economical", "most expensive"), "def_econ": ("most economical", "most expensive"), "set_econ": ("most economical", "most expensive"),
         "out_rate": ("hardest to dismiss", "easiest to dismiss"), "after30_out": ("hardest to dismiss once set", "easiest to dismiss once set"),
         "early_out": ("hardest to dismiss early", "easiest to dismiss early"), "dot_pct": ("fewest dot balls", "most dot balls"),
         "bnd_pct": ("fewest boundaries conceded", "most boundaries conceded"), "extras_pct": ("fewest wides and no-balls", "most wides and no-balls"),
         "wkt_rate": ("least frequent wicket-takers", "most frequent wicket-takers"), "new_wkt": ("least threatening to new batters", "most threatening to new batters")}


def _extreme_dims(fp: dict, name: str, role: str, lo_cut: float = 12, hi_cut: float = 88) -> list[dict]:
    if not fp.get("available"):
        return []
    def _share(p: int, word: str) -> str:  # plain-language percentile (Phase 8 terminology pass)
        return f"none of them has a {word} figure" if p <= 0 else f"only {p}% of them have a {word} figure"

    lower_better = {"dot_pct", "out_rate", "after30_out", "early_out", "econ", "bnd_pct", "extras_pct", "pp_econ", "mid_econ", "death_econ",
                    "def_econ", "set_econ"}
    out = []
    for d in fp["dimensions"]:
        if not d["enough_sample"] or d["percentile"] is None or d["key"] in ("bowler_conc", "route_conc"):
            continue
        pc = round(d["percentile"])
        if lo_cut < pc < hi_cut:
            continue
        hi = pc >= hi_cut
        style = "higher" if hi else "lower"
        strong = pc >= 88 or pc <= 12
        lo_w, hi_w = PLAIN.get(d["key"], ("lowest", "highest"))
        word = (f"among the {hi_w}" if strong else f"{hi_w.replace('most ', 'more ').replace('highest', 'higher')} than most") if hi else \
               (f"among the {lo_w}" if strong else f"{lo_w.replace('most ', 'more ').replace('lowest', 'lower').replace('fewest', 'fewer')} than most")
        head = f"{d['label']}: {name} is {word} of {fp['peer_pool']['size']} peers ({_share(100 - pc, 'higher') if hi else _share(pc, 'lower')})"
        unit = d["unit"]
        body = (f"{d['description']}: {d['value']:.4g} {unit} against a peer median of {d['peer_median']:.4g}. "
                f"Peers: {fp['peer_pool']['definition']}. A percentile describes style, not quality"
                + (" (lower is usually better here)." if d["key"] in lower_better else "."))
        out.append({"id": f"fp:{role}:{d['key']}", "source": "fingerprint", "kind": "style", "headline": head, "body": body,
                    "sample": f"{d['n']:,} {d['n_unit']}", "stable": None, "unusual": abs(pc - 50),
                    "why": {"definition": d["description"], "peer_pool": fp["peer_pool"]["definition"], "minimum": f"{d['min_sample']} {d['n_unit']}",
                            "percentile": f"{pc} (share of peers with a lower value)"},
                    "evidence": {"query": {("batter_id" if role == "batting" else "bowler_id"): fp.get("pid"), **d["evidence"]},
                                 "label": f"{name}: {d['label'].lower()}"}, "prov": "OBSERVED aggregate, percentile DERIVED"})
    out.sort(key=lambda x: -x["unusual"])
    return out


def different(db: DB, pid: str, k: int = 5) -> dict:
    h = hero(db, pid)
    if not h:
        return {"items": []}
    name = h["name"]
    items: list[dict] = []
    R = h["role"]
    roles = ["bowling"] if R["primary"] == "bowler" else ["batting"]
    if R["allrounder"]:
        roles = ["batting", "bowling"] if R["primary"] == "batter" else ["bowling", "batting"]
    for role in roles:
        if role == "batting" and h["role"]["balls_faced"] >= 300:
            fp = FP.fingerprint(db, pid, major=True)
            if fp.get("available"):
                fp["pid"] = pid
                ins = INS.insights(db, pid, fp["format"], None, name)
                seen_split = set()
                for c in ins.get("cards", []):
                    if c["split"] in seen_split or not c["stable"]:
                        continue                     # one finding per situation, and only those stable across both halves
                    seen_split.add(c["split"])
                    p = _plain_insight(c, name)
                    if p:
                        items.append(p)
                items += _extreme_dims(fp, name, "batting")[:3]
        if role == "bowling" and h["role"]["balls_bowled"] >= 300:
            fp = FP.bowling_fingerprint(db, pid, major=True)
            if fp.get("available"):
                fp["pid"] = pid
                items += _extreme_dims(fp, name, "bowling")[:4]
                if len(items) < 3:
                    items += _extreme_dims(fp, name, "bowling", 20, 80)[:3]
    # other evidence-backed distinctions: records they top, and findings that survived the discovery tests
    from . import records2, didnt_know
    for rec_ in records2.held_by(db, pid):
        if rec_["rank"] <= 3:
            items.append({"id": f"rec:{rec_['id']}", "source": "record book", "kind": "record", "headline": f"#{rec_['rank']} in {rec_['title']}: {rec_['value_fmt']}",
                          "body": "From the CRICINTEL record book (covered matches only, not official records).", "sample": f"{rec_['sample']:,}",
                          "stable": None, "why": {"definition": "See the record page for its definition, minimum sample and coverage."},
                          "evidence": {"href": f"/records/{rec_['id']}", "label": "Open the record"}, "prov": "OBSERVED"})
    for f in didnt_know.for_player(db, pid, 2):
        items.append({"id": f"find:{f['id']}", "source": "discovery engine", "kind": "finding", "headline": f["headline"], "body": f["statement"],
                      "sample": f"{f['n']:,}", "stable": None, "why": f["why"], "evidence": {"href": f["href"], "label": "See the evidence"}, "prov": "DERIVED"})
    # interleave sources so one engine does not fill the list: strengths engine, record book, fingerprint, discovery
    order = {"strengths engine": 0, "record book": 1, "fingerprint": 2, "discovery engine": 3}
    seen_n: dict = {}
    for it in items:
        seen_n[it["source"]] = seen_n.get(it["source"], 0) + 1
        it["_k"] = (seen_n[it["source"]], order.get(it["source"], 9))
    items.sort(key=lambda x: x["_k"])
    out, subj = [], set()
    for it in items:
        it.pop("_k", None)
        key = it["headline"].split(",")[0][:40]
        if key in subj or CAUSAL.search(it["headline"] + it["body"]):
            continue
        subj.add(key)
        out.append(it)
        if len(out) >= k:
            break
    return {"items": out, "note": "Each line compares this player with peers in covered data. Tap WHY for the test, sample and peer pool."}


# ------------------------------------------------------------------------------------------------ Player Stories
def _dim(fp, key):
    return next((d for d in fp.get("dimensions", []) if d["key"] == key), None)


def stories(db: DB, pid: str) -> dict:
    h = hero(db, pid)
    if not h:
        return {"cards": []}
    name = h["name"]
    cards = []
    R = h["role"]
    if R["balls_faced"] >= 300 and (R["primary"] == "batter" or R["allrounder"]):
        fp = FP.fingerprint(db, pid, major=True)
        if fp.get("available"):
            f = fp["format"]
            pool = fp["peer_pool"]["definition"]
            a30, sr = _dim(fp, "after30_sr"), _dim(fp, "sr")
            if a30 and a30["enough_sample"]:
                r = db.q1(f"""SELECT sum(runs_batter) FILTER (WHERE batter_balls_before < 30) AS r1, count(*) FILTER (WHERE faced AND batter_balls_before < 30) AS b1,
                               sum(runs_batter) FILTER (WHERE batter_balls_before >= 30) AS r2, count(*) FILTER (WHERE faced AND batter_balls_before >= 30) AS b2
                               FROM balls WHERE batter_id = ? AND format_group = ? {FP.MAJOR}""", [pid, f])
                if r["b1"] and r["b2"]:
                    s1, s2 = 100 * r["r1"] / r["b1"], 100 * r["r2"] / r["b2"]
                    cards.append(_card("after30", f"{name} after 30 balls", f"{f} strike rate {s1:.0f} in the first 30 balls of an innings, {s2:.0f} after them.",
                                       f"{r['b2']:,} balls after the 30th", f"Once set, faster than {round(a30['percentile'])}% of peers (peer median {a30['peer_median']:.0f}).",
                                       {"batter_id": pid, "format": f, "faced_from": 30}, f"{name} after facing 30 balls ({f})", a30, pool))
            for key, title, q in (("death_sr", "at the death", {"phase": "death"}), ("chase_sr", "when chasing", {"chasing": True}),
                                  ("pp_sr", "in the powerplay", {"phase": "powerplay"}), ("pressure_sr", "when the asking rate is high", {"chasing": True, "rrr_from": FP.PRESSURE_RRR[f]})):
                d = _dim(fp, key)
                if not d or not d["enough_sample"]:
                    continue
                other = f" (overall {sr['value']:.0f})" if sr else ""
                extra = f" (required rate {FP.PRESSURE_RRR[f]:g}+ an over)" if key == "pressure_sr" else ""
                cards.append(_card(key, f"{name} {title}", f"{f} strike rate {d['value']:.0f} {title}{extra}{other}.", f"{d['n']:,} balls",
                                   f"Faster than {round(d['percentile'])}% of peers (peer median {d['peer_median']:.0f}).", {"batter_id": pid, "format": f, **q},
                                   f"{name} {title} ({f})", d, pool))
            orate = _dim(fp, "out_rate")
            if orate and orate["enough_sample"] and orate["value"]:
                bpd = 100 / orate["value"]
                lo, hi = wilson(fp["outs"], fp["balls"])
                cards.append(_card("survival", f"How long {name} lasts", f"One dismissal every {bpd:.0f} balls faced in {f} ({fp['outs']} in {fp['balls']:,}).",
                                   f"{fp['balls']:,} balls", f"Dismissed less often than {round(100 - orate['percentile'])}% of peers. 90% interval: one every "
                                   f"{100 / (100 * hi):.0f}–{100 / (100 * lo):.0f} balls." if lo else "",
                                   {"batter_id": pid, "format": f}, f"{name}'s {f} balls", orate, pool, flip=True))
    if R["balls_bowled"] >= 300 and (R["primary"] == "bowler" or R["allrounder"]):
        fp = FP.bowling_fingerprint(db, pid, major=True)
        if fp.get("available"):
            f = fp["format"]
            pool = fp["peer_pool"]["definition"]
            for key, title, q in (("death_econ", "at the death", {"phase": "death"}), ("pp_econ", "in the powerplay", {"phase": "powerplay"}),
                                  ("set_econ", "against set batters", {"batter_stage": "set"})):
                d = _dim(fp, key)
                if not d or not d["enough_sample"]:
                    continue
                cards.append(_card(key, f"{name} {title}", f"{f} economy {d['value']:.2f} an over {title}.", f"{d['n']:,} legal balls",
                                   f"Cheaper than {round(100 - d['percentile'])}% of peers (peer median {d['peer_median']:.2f}).", {"bowler_id": pid, "format": f, **q},
                                   f"{name} bowling {title} ({f})", d, pool, flip=True))
            nw = _dim(fp, "new_wkt")
            if nw and nw["enough_sample"]:
                cards.append(_card("new_wkt", f"{name} against new batters", f"{nw['value']:.1f} wickets per 100 balls to batters on 0–9 balls faced ({f}).",
                                   f"{nw['n']:,} legal balls", f"More often than {round(nw['percentile'])}% of peers (peer median {nw['peer_median']:.1f}).",
                                   {"bowler_id": pid, "format": f, "batter_stage": "new"}, f"{name} to new batters ({f})", nw, pool))
    # batter v bowler: their longest battle
    from . import index
    ix = index.get(db)
    allb = ix["battles_bat"].get(pid, []) + ix["battles_bowl"].get(pid, [])
    b = max(allb, key=lambda x: x["balls"], default=None)
    if b:
        b = {**b, "m": b["matches"]}
    if b and b["balls"] >= 60:
        sr = 100 * b["runs"] / b["balls"]
        cards.append({"id": "battle", "title": f"{_nm(db, b['batter_id'])} v {_nm(db, b['bowler_id'])}", "headline": f"{b['runs']} runs off {b['balls']} balls, out {b['outs']} times",
                      "evidence": f"Strike rate {sr:.0f}, one dismissal every {b['balls'] / b['outs']:.0f} balls." if b["outs"] else f"Strike rate {sr:.0f}, never dismissed by this bowler.",
                      "sample": f"{b['balls']} balls in about {b['m']} matches", "comparison": "Their longest batter-v-bowler battle in covered data.",
                      "link": {"href": f"/battle?bat={b['batter_id']}&bowl={b['bowler_id']}", "label": "Every ball of this battle"},
                      "unusual": 30, "prov": "OBSERVED", "why": {"definition": "All balls this batter faced from this bowler, all covered formats."}})
    # everyone gets their best day, even with too few balls for a percentile story
    best = ((ix["best_innings"].get(pid) or [None])[0] if R["primary"] == "batter" or R["allrounder"] else None)
    if best:
        cards.append({"id": "best_innings", "title": f"{name}'s best day", "headline": f"{best['runs']}{'*' if best['not_out'] else ''} off {best['balls']} v {best['opponent']}",
                      "evidence": f"Highest covered score, {best['start_date']}.", "sample": "one innings", "comparison": "Highest score in covered matches.",
                      "link": {"href": f"/innings/{best['match_id']}/{best['innings_no']}/{pid}", "label": "Ball by ball"}, "unusual": 20, "prov": "OBSERVED",
                      "why": {"definition": "Runs off the bat in one innings, covered matches only."}})
    spell = (db.q1("""SELECT match_id, innings_no, wickets, runs, opponent, start_date FROM bowl_innings WHERE bowler_id = ? AND wickets > 0
                      ORDER BY wickets DESC, runs LIMIT 1""", [pid]) if R["primary"] == "bowler" or R["allrounder"] else None)
    if spell:
        cards.append({"id": "best_spell", "title": f"{name}'s best spell", "headline": f"{spell['wickets']}/{spell['runs']} v {spell['opponent']}",
                      "evidence": f"Best covered figures, {spell['start_date']}.", "sample": "one innings", "comparison": "Best figures in covered matches.",
                      "link": {"href": f"/spell/{spell['match_id']}/{spell['innings_no']}/{pid}", "label": "Ball by ball"}, "unusual": 20, "prov": "OBSERVED",
                      "why": {"definition": "Most bowler-credited wickets in one innings, then fewest runs."}})
    cards.sort(key=lambda c: -c["unusual"])
    for c in cards:
        assert not CAUSAL.search(" ".join(str(c.get(k, "")) for k in ("title", "headline", "evidence", "comparison"))), c
    return {"cards": cards[:6], "note": "Story cards describe what happened in covered data; they do not explain why."}


def _card(cid, title, headline, sample, comparison, query, label, d, pool, flip=False):
    pc = round(d["percentile"])
    return {"id": cid, "title": title, "headline": headline, "evidence": comparison, "sample": sample, "comparison": comparison,
            "link": {"query": query, "label": label}, "unusual": abs(pc - 50), "percentile": pc, "prov": "OBSERVED aggregate, percentile DERIVED",
            "why": {"definition": d["description"], "peer_pool": pool, "minimum": f"{d['min_sample']} {d['n_unit']}",
                    "note": "Percentile = share of peers with a lower value" + ("; for this measure lower is usually better." if flip else ".")}}


# ------------------------------------------------------------------------------------------------ matchup discovery
def _battle_rows(db: DB, pid: str, as_bowler: bool) -> list[dict]:
    me, other = ("bowler_id", "batter_id") if as_bowler else ("batter_id", "bowler_id")
    rows = db.q(f"""SELECT {other} AS other, sum(balls) AS balls, sum(runs) AS runs, sum(outs) AS outs, sum(matches) AS matches,
                    max(last_date) AS last, any_value(batter_rpb) AS bat_rpb, any_value(batter_out_rate) AS bat_or,
                    any_value(bowler_rpb) AS bowl_rpb, any_value(bowler_wkt_rate) AS bowl_wr
                    FROM battles WHERE {me} = ? GROUP BY 1 HAVING sum(balls) >= {TINY_BALLS}""", [pid])
    for r in rows:
        r["name"] = _nm(db, r["other"])
        r["sr"] = 100 * r["runs"] / r["balls"]
        # expected from the batter's usual rates (batter view) / bowler's usual rates (bowler view)
        rpb, orate = (r["bat_rpb"], r["bat_or"]) if not as_bowler else (r["bat_rpb"], r["bat_or"])
        r["usual_sr"] = 100 * (rpb or 0)
        r["exp_outs"] = r["balls"] * (orate or 0)
        lo, hi = wilson(r["outs"], r["balls"])
        r["out_interval"] = [round(r["balls"] * lo, 1), round(r["balls"] * hi, 1)] if lo is not None else None
        r["rivalry"] = r["balls"] >= RIVALRY_MIN_BALLS and r["matches"] >= RIVALRY_MIN_MATCHES
        r["href"] = f"/battle?bat={r['other']}&bowl={pid}" if as_bowler else f"/battle?bat={pid}&bowl={r['other']}"
        # Poisson-style surprise on dismissals (two-sided, normal approximation)
        r["z_outs"] = (r["outs"] - r["exp_outs"]) / math.sqrt(r["exp_outs"]) if r["exp_outs"] > 0 else 0
        # shrunk SR difference (60 pseudo-balls at the batter's usual rate)
        r["sr_shrunk"] = 100 * (r["runs"] + 60 * (rpb or 0)) / (r["balls"] + 60)
        r["sr_diff"] = r["sr_shrunk"] - r["usual_sr"]
    return rows


def _row(r: dict, why: str) -> dict:
    return {"pid": r["other"], "name": r["name"], "balls": r["balls"], "runs": r["runs"], "outs": r["outs"], "matches": r["matches"],
            "sr": round(r["sr"], 1), "usual_sr": round(r["usual_sr"], 1), "expected_outs": round(r["exp_outs"], 1), "out_interval_90": r["out_interval"],
            "label": "rivalry" if r["rivalry"] else ("small sample" if r["balls"] < 60 else "meeting"), "why": why, "href": r["href"], "last": str(r["last"])}


def matchups(db: DB, pid: str) -> dict:
    out = {}
    R = kg.role(db, pid)
    views = [False, True] if R["allrounder"] else ([True] if R["primary"] == "bowler" else [False])
    for as_bowler in views:
        rows = _battle_rows(db, pid, as_bowler)
        if not rows:
            continue
        view = {}
        view["biggest"] = [_row(r, f"{r['balls']} balls across {r['matches']} matches") for r in sorted(rows, key=lambda r: -r["balls"])[:5]]
        dis = [r for r in rows if r["outs"] >= 2]
        view["dismissed_most" if not as_bowler else "dismissed_most_often"] = [
            _row(r, f"{r['outs']} dismissals; about {r['exp_outs']:.1f} expected at the batter's usual rate") for r in
            sorted(dis, key=lambda r: (-r["outs"], r["balls"]))[:5]]
        big = [r for r in rows if r["balls"] >= 60]
        if not as_bowler:
            view["dominated"] = [_row(r, f"Strike rate {r['sr']:.0f} against a usual {r['usual_sr']:.0f} (shrunk estimate {r['sr_shrunk']:.0f})")
                                 for r in sorted(big, key=lambda r: -r["sr_diff"])[:5] if r["sr_diff"] > 5]
        else:
            view["took_apart"] = [_row(r, f"They scored at {r['sr']:.0f} against a usual {r['usual_sr']:.0f} (shrunk estimate {r['sr_shrunk']:.0f})")
                                  for r in sorted(big, key=lambda r: -r["sr_diff"])[:5] if r["sr_diff"] > 5]
            view["kept_quiet"] = [_row(r, f"They scored at {r['sr']:.0f} against a usual {r['usual_sr']:.0f} (shrunk estimate {r['sr_shrunk']:.0f})")
                                  for r in sorted(big, key=lambda r: r["sr_diff"])[:5] if r["sr_diff"] < -5]
        bal = [r for r in rows if r["balls"] >= RIVALRY_MIN_BALLS]
        view["balanced"] = [_row(r, f"Scoring within {abs(r['sr_diff']):.0f} of usual and {r['outs']} dismissals v {r['exp_outs']:.1f} expected")
                            for r in sorted(bal, key=lambda r: abs(r["sr_diff"]) / 10 + abs(r["z_outs"]))[:4]]
        unusual = [r for r in rows if r["balls"] >= 60 and abs(r["z_outs"]) >= 2.0]
        view["unusual"] = [_row(r, f"{r['outs']} dismissals where about {r['exp_outs']:.1f} would be usual ({'more' if r['z_outs'] > 0 else 'fewer'} than expected; "
                                f"90% range for this sample {r['out_interval'][0]:g}–{r['out_interval'][1]:g})") for r in
                           sorted(unusual, key=lambda r: -abs(r["z_outs"]))[:4]]
        out["as_bowler" if as_bowler else "as_batter"] = view
    return {"views": out, "rules": {"rivalry": f"called a rivalry only with {RIVALRY_MIN_BALLS}+ balls across {RIVALRY_MIN_MATCHES}+ matches",
                                    "minimum": f"meetings under {TINY_BALLS} balls are not listed; under 60 balls are marked small sample",
                                    "unusual": "dismissal count at least 2 standard deviations from expectation (Poisson approximation), 60+ balls",
                                    "shrinkage": "strike-rate differences are shrunk toward the batter's usual rate with 60 pseudo-balls"}}


# ------------------------------------------------------------------------------------------------ smaller home sections
def career(db: DB, pid: str) -> dict:
    """Year by year in covered data, for the primary role, per format. Gaps are years with no covered matches."""
    r = kg.role(db, pid)
    if r["primary"] == "bowler":
        rows = db.q("""SELECT year, format_group AS f, sum(wickets) AS v, sum(balls) AS balls, sum(runs) AS runs, count(*) AS inns FROM bowl_innings
                       WHERE bowler_id = ? GROUP BY 1, 2 ORDER BY 1""", [pid])
        pts = [{"year": x["year"], "format": x["f"], "value": x["v"], "rate": round(6 * x["runs"] / x["balls"], 2) if x["balls"] else None, "inns": x["inns"]} for x in rows]
        return {"metric": "wickets", "rate": "economy", "points": pts}
    rows = db.q("""SELECT year, format_group AS f, sum(runs) AS v, sum(balls) AS balls, count(*) AS inns FROM bat_innings
                   WHERE batter_id = ? GROUP BY 1, 2 ORDER BY 1""", [pid])
    pts = [{"year": x["year"], "format": x["f"], "value": x["v"], "rate": round(100 * x["v"] / x["balls"], 1) if x["balls"] else None, "inns": x["inns"]} for x in rows]
    return {"metric": "runs", "rate": "strike rate", "points": pts}


def wickets(db: DB, pid: str) -> dict:
    """How a bowler takes wickets: route of each bowler-credited wicket, the phase, and the batters dismissed most."""
    from ..analytics.visual import ROUTE_LABEL
    routes = db.q("""SELECT route, count(*) AS n FROM dis WHERE bowler_id = ? AND bowler_credited GROUP BY 1 ORDER BY n DESC""", [pid])
    total = sum(x["n"] for x in routes)
    phases = db.q("""SELECT phase, count(*) AS n FROM dis WHERE bowler_id = ? AND bowler_credited GROUP BY 1 ORDER BY n DESC""", [pid])
    stage = db.q1("""SELECT count(*) FILTER (WHERE batter_balls_before < 10) AS new, count(*) FILTER (WHERE batter_balls_before >= 30) AS set,
                     count(*) AS n FROM dis WHERE bowler_id = ? AND bowler_credited""", [pid])
    return {"total": total, "routes": [{"route": x["route"], "label": ROUTE_LABEL.get(x["route"], x["route"]), "n": x["n"],
                                        "pct": round(100 * x["n"] / total, 1) if total else None} for x in routes],
            "phases": [{"phase": x["phase"], "n": x["n"]} for x in phases], "stage": stage,
            "note": "Keeper catches use the DERIVED keeper identity; where keeper status is unknown the catch is counted separately. "
                    "Where the ball pitched or what shot was played is not recorded."}


def partners(db: DB, pid: str, k: int = 4) -> list[dict]:
    rows = db.q("""SELECT CASE WHEN p1 = ? THEN p2 ELSE p1 END AS partner, sum(runs) AS runs, count(*) AS n, max(runs) AS best,
                   sum(balls) AS balls FROM partnerships WHERE p1 = ? OR p2 = ? GROUP BY 1 ORDER BY runs DESC LIMIT ?""", [pid, pid, pid, k])
    return [{"pid": r["partner"], "name": _nm(db, r["partner"]), "runs": r["runs"], "stands": r["n"], "best": r["best"],
             "avg": round(r["runs"] / r["n"], 1), "href": f"/partnerships?p1={min(pid, r['partner'])}&p2={max(pid, r['partner'])}"} for r in rows]
