"""Strength & Weakness engine: statistical comparisons, never editorial opinion.

For a batter and a format, each candidate split S (e.g. "death overs", "balls 20–29 of the innings",
"chasing with required rate >= 10", "v Australia") is compared with the SAME player's balls outside S:

  metrics  : dismissal rate (outs/ball), boundary rate, dot rate (binomial) and runs per ball (mean)
  shrinkage: the inside-S estimate is shrunk toward the player's overall rate with K pseudo-balls
  interval : 90% (log-ratio Katz for rates, Welch-style for runs per ball)
  testing  : Benjamini–Hochberg FDR at q = 0.10 across all splits x metrics tested for the player
  gates    : min balls inside and outside; min effect size; interval must exclude "no difference"
  stability: the direction is re-checked separately in the earlier and later halves of the player's
             covered balls (by date)

Statements are templated from the numbers ("In our covered ODI data, X's dismissal rate … is 1.6x …").
Each card carries its WHY: the counts, baseline, interval, p/q values and a delivery query.
"""
from __future__ import annotations

import math

from ..db import DB
from .stats import benjamini_hochberg, mean_diff, rate_ratio, shrink_rate

K_SHRINK = 60.0
MIN_IN = {"T20": 90, "ODI": 150}
MIN_OUT = {"T20": 150, "ODI": 250}
MIN_RATE_EFFECT = 0.25          # |ratio - 1| >= 25%
MIN_SR_EFFECT = {"T20": 15.0, "ODI": 10.0}
PRESSURE = {"T20": 10.0, "ODI": 7.0}

BALLS_SQL = """
SELECT b.delivery_id, b.start_date, b.phase, b.over, b.chasing, b.required_rate, b.wickets_before,
       b.batter_balls_before AS bb, b.bowling_team, b.team_type, b.competition, b.innings_no,
       b.runs_batter AS r, b.faced, b.is_four, b.is_six, b.batter_position,
       EXISTS (SELECT 1 FROM wickets w WHERE w.delivery_id = b.delivery_id AND w.player_out_id = ? AND w.counts_as_dismissal) AS out
FROM balls b WHERE b.batter_id = ? AND b.format_group = ? {extra}
"""


def _splits(fmt: str, rows: list[dict]) -> list[tuple]:
    """(key, phrase, evidence filters, SQL condition on balls, python predicate on player rows)."""
    pr = PRESSURE[fmt]
    s = [
        ("phase:powerplay", "in powerplay overs", {"phase": "powerplay"}, "phase = 'powerplay'", lambda r: r["phase"] == "powerplay"),
        ("phase:middle", "in the middle overs", {"phase": "middle"}, "phase = 'middle'", lambda r: r["phase"] == "middle"),
        ("phase:death", "in death overs", {"phase": "death"}, "phase = 'death'", lambda r: r["phase"] == "death"),
        ("chasing", "while chasing", {"chasing": True}, "coalesce(chasing, false)", lambda r: bool(r["chasing"])),
        ("stage:0-9", "in the first 10 balls of an innings", {"faced_to": 9}, "batter_balls_before < 10", lambda r: r["bb"] < 10),
        ("stage:10-19", "between balls 10 and 19 of an innings", {"faced_from": 10, "faced_to": 19},
         "batter_balls_before BETWEEN 10 AND 19", lambda r: 10 <= r["bb"] < 20),
        ("stage:20-29", "between balls 20 and 29 of an innings", {"faced_from": 20, "faced_to": 29},
         "batter_balls_before BETWEEN 20 AND 29", lambda r: 20 <= r["bb"] < 30),
        ("stage:30+", "after facing 30 balls", {"faced_from": 30}, "batter_balls_before >= 30", lambda r: r["bb"] >= 30),
        ("wk:0-2", "with 0–2 wickets down", {"wk_to": 2}, "wickets_before <= 2", lambda r: r["wickets_before"] <= 2),
        ("wk:3-5", "with 3–5 wickets down", {"wk_from": 3, "wk_to": 5}, "wickets_before BETWEEN 3 AND 5",
         lambda r: 3 <= r["wickets_before"] <= 5),
        ("pressure", f"when chasing at a required rate of {pr:g}+", {"chasing": True, "rrr_from": pr},
         f"coalesce(chasing, false) AND required_rate >= {pr}", lambda r: bool(r["chasing"]) and (r["required_rate"] or 0) >= pr),
    ]
    # opposition teams with enough balls
    cnt: dict[str, int] = {}
    for r in rows:
        if r["faced"]:
            cnt[r["bowling_team"]] = cnt.get(r["bowling_team"], 0) + 1
    for team, n in sorted(cnt.items(), key=lambda x: -x[1])[:8]:
        if n >= MIN_IN[fmt]:
            s.append((f"opp:{team}", f"against {team}", {"opposition": team}, "bowling_team = " + "'" + team.replace("'", "''") + "'",
                      (lambda t: lambda r: r["bowling_team"] == t)(team)))
    return s


_LEAGUE: dict = {}
FIELDS = ("n", "runs", "ss", "bnd", "dots", "outs")


POS_BANDS = {"top": (1, 3, "top-order (1–3)"), "middle": (4, 7, "middle-order (4–7)"), "lower": (8, 11, "lower-order (8–11)")}


def _band(pos):
    return "top" if pos <= 3 else ("middle" if pos <= 7 else "lower")


def _league(db: DB, fmt: str, gender: str, team_type: str | None, splits: list[tuple], band: str = "top") -> dict:
    """Pooled per-ball baseline for every split (inside vs outside) across all batters of the same gender/format/level.
    Fixed splits are computed once per scope; opposition splits come from one GROUP BY bowling_team query."""
    key = (id(db), fmt, gender, team_type, band)
    if key not in _LEAGUE:
        lo_, hi_, _ = POS_BANDS[band]
        extra = (f"AND team_type = '{team_type}'" if team_type else "") + f" AND batter_position BETWEEN {lo_} AND {hi_}"
        base = f"""WITH w AS (SELECT delivery_id, count(*) AS outs FROM wickets WHERE counts_as_dismissal GROUP BY 1),
          b AS (SELECT x.*, x.runs_batter AS r, coalesce(w.outs, 0) AS outs FROM balls x LEFT JOIN w USING (delivery_id)
                WHERE x.format_group = ? AND x.gender = ? {extra})"""
        agg = """count(*) FILTER (WHERE faced {c}) AS n, sum(r) FILTER (WHERE faced {c}) AS runs, sum(r*r) FILTER (WHERE faced {c}) AS ss,
                 count(*) FILTER (WHERE faced AND (is_four OR is_six) {c}) AS bnd, count(*) FILTER (WHERE faced AND r = 0 {c}) AS dots,
                 sum(outs) FILTER (WHERE TRUE {c}) AS outs"""
        fixed = [sp for sp in _splits(fmt, []) if not sp[0].startswith("opp:")]
        cols = [agg.format(c="").replace(" AS ", " AS tot_")]
        for i, sp in enumerate(fixed):
            cols.append(agg.format(c=f"AND ({sp[3]})").replace(" AS ", f" AS s{i}_"))
        row = db.q1(base + f" SELECT {', '.join(cols)} FROM b", [fmt, gender])
        tot = {f: row[f"tot_{f}"] or 0 for f in FIELDS}
        out = {"__total__": tot}
        for i, sp in enumerate(fixed):
            ins = {f: row[f"s{i}_{f}"] or 0 for f in FIELDS}
            out[sp[0]] = {"in": ins, "out": {f: tot[f] - ins[f] for f in FIELDS}}
        for r in db.q(base + f" SELECT bowling_team, {agg.format(c='')} FROM b GROUP BY 1", [fmt, gender]):
            ins = {f: r[f] or 0 for f in FIELDS}
            out["opp:" + r["bowling_team"]] = {"in": ins, "out": {f: tot[f] - ins[f] for f in FIELDS}}
        _LEAGUE[key] = out
    return _LEAGUE[key]


def _agg(rows):
    faced = [r for r in rows if r["faced"]]
    n = len(faced)
    runs = sum(r["r"] for r in faced)
    return {"n": n, "outs": sum(1 for r in rows if r["out"]), "runs": runs, "ss": sum(r["r"] ** 2 for r in faced),
            "bnd": sum(1 for r in faced if r["is_four"] or r["is_six"]), "dots": sum(1 for r in faced if r["r"] == 0)}


METRICS = [
    # key, label, kind, count-field, higher_is ("good" for batter means strength)
    ("out_rate", "dismissal rate", "rate", "outs", "bad"),
    ("bnd_rate", "boundary rate", "rate", "bnd", "good"),
    ("dot_rate", "dot-ball rate", "rate", "dots", "bad"),
    ("sr", "strike rate", "mean", "runs", "good"),
]


def _fmt_rate(key, x, n):
    if not n:
        return "–"
    if key == "out_rate":
        return f"1 in {n / x:.0f} balls" if x else "no dismissals"
    return f"{100 * x / n:.1f}%"


def insights(db: DB, pid: str, fmt: str, team_type: str | None = None, name: str | None = None) -> dict:
    extra, p = ("AND b.team_type = ?", [team_type]) if team_type else ("", [])
    rows = db.q(BALLS_SQL.format(extra=extra), [pid, pid, fmt, *p])
    name = name or (db.q1("SELECT name FROM player_profile WHERE person_id = ?", [pid]) or {}).get("name", pid)
    if not rows:
        return {"cards": [], "tested": 0, "reason": "no batting in scope"}
    allagg = _agg(rows)
    dates = sorted(r["start_date"] for r in rows if r["faced"])
    median_date = dates[len(dates) // 2] if dates else None
    splits = _splits(fmt, rows)
    gender = (db.q1("SELECT genders FROM player_profile WHERE person_id = ?", [pid]) or {"genders": ["male"]})["genders"][0]
    pos = [r["batter_position"] for r in rows if r["faced"] and r["batter_position"]]
    band = _band(sorted(pos)[len(pos) // 2]) if pos else "top"
    league = _league(db, fmt, gender, team_type, splits, band)
    tests = []
    for key, phrase, ev, cond, pred in splits:
        inside = [r for r in rows if pred(r)]
        outside = [r for r in rows if not pred(r)]
        a, b = _agg(inside), _agg(outside)
        if a["n"] < MIN_IN[fmt] or b["n"] < MIN_OUT[fmt]:
            continue
        L = league[key]
        for mkey, mlabel, kind, field, higher in METRICS:
            if kind == "rate":
                rr = rate_ratio(a[field], a["n"], b[field], b["n"])
                lin, lout = L["in"][field] / max(1, L["in"]["n"]), L["out"][field] / max(1, L["out"]["n"])
                if rr["ratio"] is None or not lin or not lout:
                    continue
                lr = lin / lout                                   # typical change for batters in this situation
                shr = shrink_rate(a[field], a["n"], (b[field] / b["n"]) * lr, K_SHRINK) / (b[field] / b["n"] if b[field] else 1e-9)
                rel, lo, hi = shr / lr, rr["lo"] / lr, rr["hi"] / lr   # player's change relative to the typical change
                import math as _m
                se = (_m.log(rr["hi"]) - _m.log(rr["lo"])) / (2 * 1.6448536269514722)
                z = _m.log(rr["ratio"] / lr) / se if se > 0 else 0
                p = 2 * (1 - 0.5 * (1 + _m.erf(abs(z) / _m.sqrt(2))))
                eff_ok = abs(rel - 1) >= MIN_RATE_EFFECT and (lo > 1 or hi < 1)
                tests.append(dict(split=key, phrase=phrase, evidence=ev, metric=mkey, metric_label=mlabel, kind=kind,
                                  inside=a, outside=b, ratio=rel, player_ratio=shr, league_ratio=lr, lo=lo, hi=hi, p=p,
                                  eff_ok=eff_ok, direction="higher" if rel > 1 else "lower", higher=higher, field=field, pred=pred,
                                  league_in=lin, league_out=lout))
            else:
                md = mean_diff(a["runs"], a["ss"], a["n"], b["runs"], b["ss"], b["n"])
                if md["diff"] is None or not L["in"]["n"] or not L["out"]["n"]:
                    continue
                ld = L["in"]["runs"] / L["in"]["n"] - L["out"]["runs"] / L["out"]["n"]
                m_out = b["runs"] / b["n"]
                shr_mean = (a["runs"] + K_SHRINK * (m_out + ld)) / (a["n"] + K_SHRINK)
                d_player = 100 * (shr_mean - m_out)
                did = d_player - 100 * ld
                lo, hi = 100 * (md["lo"] - ld), 100 * (md["hi"] - ld)
                se = (md["hi"] - md["lo"]) / (2 * 1.6448536269514722)
                z = (md["diff"] - ld) / se if se > 0 else 0
                import math as _m
                p = 2 * (1 - 0.5 * (1 + _m.erf(abs(z) / _m.sqrt(2))))
                eff_ok = abs(did) >= MIN_SR_EFFECT[fmt] and (lo > 0 or hi < 0)
                tests.append(dict(split=key, phrase=phrase, evidence=ev, metric=mkey, metric_label=mlabel, kind=kind,
                                  inside=a, outside=b, diff=did, player_diff=d_player, league_diff=100 * ld, lo=lo, hi=hi, p=p,
                                  eff_ok=eff_ok, direction="higher" if did > 0 else "lower", higher=higher, field=field, pred=pred,
                                  league_in=100 * L["in"]["runs"] / L["in"]["n"], league_out=100 * L["out"]["runs"] / L["out"]["n"]))
    passed = benjamini_hochberg([t["p"] for t in tests], q=0.10)
    cards = []
    for t, ok in zip(tests, passed):
        t["q_pass"] = ok
        if not (ok and t["eff_ok"]):
            continue
        # stability: same direction in both halves of the covered period?
        halves = []
        for part in ([r for r in rows if r["start_date"] < median_date], [r for r in rows if r["start_date"] >= median_date]):
            ins, outs = _agg([r for r in part if t["pred"](r)]), _agg([r for r in part if not t["pred"](r)])
            if ins["n"] < 30 or outs["n"] < 30:
                halves.append(None)
            elif t["kind"] == "rate":
                ri = ins[t["field"]] / ins["n"]; ro = outs[t["field"]] / outs["n"] if outs[t["field"]] else 1e-9
                halves.append("higher" if (ri / ro if ro else 9e9) > t["league_ratio"] else "lower")
            else:
                halves.append("higher" if 100 * (ins["runs"] / ins["n"] - outs["runs"] / outs["n"]) > t["league_diff"] else "lower")
        if None in halves:
            stability = "not enough data in each half of the covered period to check"
        elif all(h == t["direction"] for h in halves):
            stability = "same direction (relative to typical) in both the earlier and later halves of the covered period"
        else:
            stability = "NOT consistent across the earlier and later halves of the covered period"
        good = (t["direction"] == "higher") == (t["higher"] == "good")
        a, b = t["inside"], t["outside"]
        fmt_label = {"T20": "T20", "ODI": "ODI"}[fmt]
        peer_label = (f"a typical {'women' if gender == 'female' else 'men'}'s {fmt_label} {POS_BANDS[band][2]} batter "
                      f"in covered matches")
        if t["kind"] == "rate":
            pv_in, pv_out = a[t["field"]] / a["n"], b[t["field"]] / b["n"]
            stmt = (f"In our covered {fmt_label} data, {name}'s {t['metric_label']} {t['phrase']} is "
                    f"{_fmt_rate(t['metric'], a[t['field']], a['n'])} vs {_fmt_rate(t['metric'], b[t['field']], b['n'])} otherwise "
                    f"(×{t['player_ratio']:.2f}). For {peer_label} the same situation changes it ×{t['league_ratio']:.2f}, so "
                    f"{name}'s is {(t['ratio'] if t['direction'] == 'higher' else 1 / t['ratio']):.1f}× "
                    f"{'higher' if t['direction'] == 'higher' else 'lower'} than the typical change would predict.")
            interval = f"90% interval for the relative effect: ×{t['lo']:.2f} to ×{t['hi']:.2f} (1.00 = same as typical)"
            calc = (f"player ratio (inside/outside, shrunk) {t['player_ratio']:.3f} ÷ typical ratio {t['league_ratio']:.3f} "
                    f"(typical: {100 * t['league_in']:.2f}% inside vs {100 * t['league_out']:.2f}% outside) = {t['ratio']:.3f}")
        else:
            stmt = (f"In our covered {fmt_label} data, {name}'s strike rate {t['phrase']} is "
                    f"{100 * a['runs'] / a['n']:.0f} vs {100 * b['runs'] / b['n']:.0f} otherwise ({t['player_diff']:+.0f}). For {peer_label} "
                    f"it changes {t['league_diff']:+.0f}, so {name} is {abs(t['diff']):.0f} SR points "
                    f"{'better' if t['diff'] > 0 else 'worse'} than typical in this situation.")
            interval = f"90% interval for the difference vs typical: {t['lo']:+.0f} to {t['hi']:+.0f} SR points"
            calc = (f"player change (shrunk) {t['player_diff']:+.1f} SR − typical change {t['league_diff']:+.1f} SR "
                    f"(typical SR {t['league_in']:.1f} inside vs {t['league_out']:.1f} outside) = {t['diff']:+.1f}")
        band_short = POS_BANDS[band][2].split(" (")[0]
        if t["kind"] == "rate":
            mult = t["ratio"] if t["direction"] == "higher" else 1 / t["ratio"]
            headline = (f"{t['phrase'][0].upper() + t['phrase'][1:]}: {t['metric_label']} {mult:.1f}× "
                        f"{'higher' if t['direction'] == 'higher' else 'lower'} than a typical {band_short} batter's change")
        else:
            headline = (f"{t['phrase'][0].upper() + t['phrase'][1:]}: {abs(t['diff']):.0f} strike-rate points "
                        f"{'better' if t['diff'] > 0 else 'worse'} than a typical {band_short} batter")
        cards.append({
            "id": f"{t['split']}|{t['metric']}", "kind": "strength" if good else "weakness",
            "headline": headline, "statement": stmt, "split": t["split"], "metric": t["metric"],
            "effect": round(t["ratio"], 3) if t["kind"] == "rate" else round(t["diff"], 1),
            "sample": {"inside_balls": a["n"], "outside_balls": b["n"], "inside_count": a[t["field"]] if t["kind"] == "rate" else a["runs"],
                       "outside_count": b[t["field"]] if t["kind"] == "rate" else b["runs"]},
            "why": {
                "comparison": f"{t['phrase']} vs the player's other {fmt_label} balls, compared with how {peer_label} changes in the same situation",
                "calculation": calc,
                "inside": f"{a['n']} balls faced, {a['runs']} runs, {a['outs']} dismissals, {a['bnd']} boundaries, {a['dots']} dots",
                "outside": f"{b['n']} balls faced, {b['runs']} runs, {b['outs']} dismissals, {b['bnd']} boundaries, {b['dots']} dots",
                "shrinkage": f"inside estimate shrunk toward 'typical change' with {K_SHRINK:g} pseudo-balls",
                "interval": interval, "p_value": round(t["p"], 5),
                "multiple_testing": f"passed Benjamini–Hochberg FDR (q = 0.10) across {len(tests)} tests for this player",
                "stability": stability,
                "thresholds": f"min {MIN_IN[fmt]} balls inside, {MIN_OUT[fmt]} outside; min effect "
                              + (f"{int(MIN_RATE_EFFECT * 100)}%" if t["kind"] == "rate" else f"{MIN_SR_EFFECT[fmt]:g} SR points"),
            },
            "evidence_query": {"batter_id": pid, "format": fmt, **({"team_type": team_type} if team_type else {}), **t["evidence"]},
            "stable": stability.startswith("same"), "p": t["p"], "prov": "MODELLED (statistical comparison of OBSERVED events)",
            # raw numbers for plain-language rendering (Phase 7 fan copy); the test and thresholds above are unchanged
            "plain": {"phrase": t["phrase"], "metric": t["metric"], "metric_label": t["metric_label"], "kind": t["kind"], "direction": t["direction"],
                      "good": good, "band": band_short,
                      "player_in": round(100 * a[t["field"]] / a["n"], 1) if t["kind"] == "rate" else round(100 * a["runs"] / a["n"], 1),
                      "player_out": round(100 * b[t["field"]] / b["n"], 1) if t["kind"] == "rate" else round(100 * b["runs"] / b["n"], 1),
                      "typical_in": round(100 * t["league_in"], 1) if t["kind"] == "rate" else round(t["league_in"], 1),
                      "typical_out": round(100 * t["league_out"], 1) if t["kind"] == "rate" else round(t["league_out"], 1)},
        })
    cards.sort(key=lambda c: (not c["stable"], c["p"]))
    for i, c in enumerate(cards):
        c["rank"] = i + 1
    return {"player": name, "format": fmt, "tested": len(tests), "cards": cards, "position_band": POS_BANDS[band][2],
            "baseline": f"pooled {('women' if gender == 'female' else 'men')}'s {fmt} {POS_BANDS[band][2]} batters in covered matches", "method": __doc__.strip().split("\n\n")[1]}
