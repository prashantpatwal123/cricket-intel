"""Validation for Situation Difficulty — Experimental (SDX). Writes docs/models/situation-difficulty-validation.{md,json}.

Pre-registered checks (decided before looking at results, following the research review):
  1. Holdout skill: trained on matches before 2025-01-01, scored on chases from 2025-01-01. Log loss and Brier on chase
     failure vs (a) the base rate and (b) a required-run-rate-only isotonic model. SDX must beat both in every
     format × gender model with enough holdout chases.
  2. Calibration: holdout deciles of predicted failure vs observed failure.
  3. Monotonicity: on a dense grid, SDX never falls when a wicket falls, when runs required rise, or when a ball passes.
  4. Boundedness: all scores in [0, 100].
  5. Behaviour: dismissal and scoring rate over the next ball by SDX band, reported as observed.
  6. Stability: refit on 2005–2015 vs 2016–2024 and compare SDX at reference states.
Within-match deliveries are correlated, so we also report the number of distinct holdout matches.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

from ..db import DB, connect
from . import situation as S

DOCS = Path(__file__).resolve().parents[3] / "docs" / "models"


def _ll(p: float, y: int) -> float:
    p = min(max(p, 1e-4), 1 - 1e-4)
    return -(y * math.log(p) + (1 - y) * math.log(1 - p))


def _rrr_model(db: DB, fmt: str, g: str) -> list[tuple[float, float]]:
    rows = db.q("""SELECT floor(required_rate * 2) / 2 AS k, avg(CAST(winner <> batting_team AS DOUBLE)) AS f, count(*) AS n
                   FROM balls WHERE innings_no = 2 AND legal AND chasing AND format_group = ? AND gender = ? AND method IS NULL
                     AND winner IS NOT NULL AND start_date < ? AND balls_left > 0 AND runs_required > 0 AND required_rate < 40
                   GROUP BY 1 ORDER BY 1""", [fmt, g, S.CUTOFF])
    fit = S._pav([r["k"] for r in rows], [r["f"] for r in rows], [r["n"] for r in rows])
    return [(r["k"], v) for r, v in zip(rows, fit)]


def _rrr_p(curve, rrr: float) -> float:
    p = curve[0][1]
    for k, v in curve:
        if rrr >= k:
            p = v
    return p


def validate(db: DB) -> dict:
    model = S.SDX(json.loads(S.artifact_path(db).read_text()))
    out = {"version": S.VERSION, "cutoff": S.CUTOFF, "holdout": {}, "calibration": {}, "behaviour": {}, "stability": {}}
    for key in model.a["models"]:
        fmt, g = key.split("|")
        rows = db.q("""SELECT match_id, runs_required AS rr, balls_left AS bl, wickets_before AS w, required_rate AS rrr,
                              CAST(winner <> batting_team AS INTEGER) AS y, team_type
                       FROM balls WHERE innings_no = 2 AND legal AND chasing AND format_group = ? AND gender = ? AND method IS NULL
                         AND winner IS NOT NULL AND start_date >= ? AND balls_left > 0 AND runs_required > 0""", [fmt, g, S.CUTOFF])
        if not rows:
            continue
        base = db.q1("""SELECT avg(CAST(winner <> batting_team AS DOUBLE)) AS f FROM balls WHERE innings_no = 2 AND legal AND chasing
                        AND format_group = ? AND gender = ? AND method IS NULL AND winner IS NOT NULL AND start_date < ?""", [fmt, g, S.CUTOFF])["f"]
        rc = _rrr_model(db, fmt, g)
        agg = {"sdx": [0.0, 0.0], "rrr": [0.0, 0.0], "base": [0.0, 0.0]}
        by_level: dict[str, list] = {}
        deciles = [[0, 0.0, 0] for _ in range(10)]
        for r in rows:
            p = model.score(fmt, g, r["rr"], r["bl"], r["w"])["sdx"] / 100
            q = _rrr_p(rc, r["rrr"])
            for k, pp in (("sdx", p), ("rrr", q), ("base", base)):
                agg[k][0] += _ll(pp, r["y"]); agg[k][1] += (pp - r["y"]) ** 2
            lv = by_level.setdefault(r["team_type"], [0, 0.0, 0.0])
            lv[0] += 1; lv[1] += _ll(p, r["y"]); lv[2] += _ll(q, r["y"])
            d = min(9, int(p * 10)); deciles[d][0] += 1; deciles[d][1] += p; deciles[d][2] += r["y"]
        n = len(rows)
        out["holdout"][key] = {
            "deliveries": n, "matches": len({r["match_id"] for r in rows}),
            "log_loss": {k: round(v[0] / n, 4) for k, v in agg.items()}, "brier": {k: round(v[1] / n, 4) for k, v in agg.items()},
            "by_level_log_loss": {k: {"n": v[0], "sdx": round(v[1] / v[0], 4), "rrr_only": round(v[2] / v[0], 4)} for k, v in by_level.items()}}
        out["calibration"][key] = [{"band": f"{10 * i}–{10 * i + 10}", "n": c[0], "predicted": round(100 * c[1] / c[0], 1),
                                    "observed": round(100 * c[2] / c[0], 1)} for i, c in enumerate(deciles) if c[0]]
    # 3/4. monotonicity + bounds on a dense grid
    viol, total, oob = [], 0, 0
    for key in model.a["models"]:
        fmt, g = key.split("|")
        maxb = 120 if fmt == "T20" else 300
        for b in range(1, maxb + 1, 3):
            for w in range(0, 10):
                for rr in range(1, 2 * maxb, 7):
                    s = model.score(fmt, g, rr, b, w)["sdx"]; total += 1
                    oob += not (0 <= s <= 100)
                    for name, t in (("wicket", model.score(fmt, g, rr, b, w + 1)), ("more runs", model.score(fmt, g, rr + 1, b, w)),
                                    ("dot ball", model.score(fmt, g, rr, b - 1, w))):
                        if t["sdx"] < s - 1e-9:
                            viol.append({"model": key, "state": [rr, b, w], "move": name, "from": s, "to": t["sdx"]})
    out["monotonicity"] = {"states_checked": total, "violations": len(viol), "examples": viol[:5], "out_of_bounds": oob}
    # 5. behaviour by band (all chase data, observed)
    out["behaviour"] = db.q("""SELECT b.format_group, CAST(floor(s.sdx / 20) * 20 AS INTEGER) AS band, count(*) AS balls,
            round(100.0 * sum(CASE WHEN b.n_wickets > 0 THEN 1 ELSE 0 END) / count(*), 2) AS wicket_pct,
            round(100.0 * sum(b.runs_batter) / count(*), 1) AS strike_rate,
            round(100.0 * count(*) FILTER (WHERE b.runs_batter IN (4, 6) AND NOT b.non_boundary) / count(*), 1) AS boundary_pct,
            round(100.0 * count(*) FILTER (WHERE b.runs_total = 0) / count(*), 1) AS dot_pct
        FROM balls b JOIN read_parquet(?) s USING (delivery_id) WHERE b.legal
        GROUP BY ALL ORDER BY 1, 2""", [str(db.dataset_dir / "derived" / "situation.parquet")])
    # 6. stability across eras
    early = S.SDX(S.fit(db, before="2016-01-01", after="2005-01-01"))
    late = S.SDX(S.fit(db, before="2025-01-01", after="2016-01-01"))
    refs = {"T20": [(60, 48, 2), (30, 24, 3), (16, 6, 4), (40, 36, 6), (90, 60, 1)],
            "ODI": [(150, 150, 2), (80, 60, 4), (30, 18, 6), (200, 180, 3), (12, 6, 8)]}
    for key in model.a["models"]:
        fmt, g = key.split("|")
        if not (early.available(fmt, g) and late.available(fmt, g)):
            out["stability"][key] = "insufficient early data"
            continue
        out["stability"][key] = [{"state": f"need {rr} off {b}, {w} down", "2005–15": early.score(fmt, g, rr, b, w)["sdx"],
                                  "2016–24": late.score(fmt, g, rr, b, w)["sdx"], "current": model.score(fmt, g, rr, b, w)["sdx"]}
                                 for rr, b, w in refs[fmt]]
    return out


def write_report(res: dict) -> None:
    DOCS.mkdir(parents=True, exist_ok=True)
    (DOCS / "situation-difficulty-validation.json").write_text(json.dumps(res, indent=1, default=str))
    L = ["# Situation Difficulty — Experimental (SDX v0.1): validation", "",
         "Status: **EXPERIMENTAL, not launched.** Visible only with `CRICINTEL_EXPERIMENTAL=1`. Not called \"Pressure\".", "",
         f"Trained on matches before {res['cutoff']}; holdout = chases from {res['cutoff']} onward. Generated by "
         "`python -m cricintel.model.situation_validate`.", "", "## 1. Holdout skill (lower is better)", "",
         "| Model | Holdout balls | Matches | Log loss SDX | RRR-only | Base rate | Brier SDX | RRR-only | Base rate |",
         "|---|---|---|---|---|---|---|---|---|"]
    for k, h in res["holdout"].items():
        L.append(f"| {k} | {h['deliveries']:,} | {h['matches']} | **{h['log_loss']['sdx']}** | {h['log_loss']['rrr']} | {h['log_loss']['base']} | "
                 f"**{h['brier']['sdx']}** | {h['brier']['rrr']} | {h['brier']['base']} |")
    L += ["", "By level (log loss, SDX v RRR-only):", ""]
    for k, h in res["holdout"].items():
        L.append(f"- {k}: " + "; ".join(f"{lv} ({v['n']:,} balls) {v['sdx']} v {v['rrr_only']}" for lv, v in h["by_level_log_loss"].items()))
    L += ["", "## 2. Calibration (holdout, predicted v observed chase-failure %)", ""]
    for k, c in res["calibration"].items():
        L.append(f"**{k}**: " + " · ".join(f"{x['band']}: {x['predicted']} v {x['observed']} (n={x['n']:,})" for x in c))
        L.append("")
    m = res["monotonicity"]
    L += ["## 3–4. Monotonicity and bounds", "",
          f"{m['states_checked']:,} grid states × 3 moves checked: **{m['violations']} violations**, {m['out_of_bounds']} out of bounds.", "",
          "## 5. What happens on the next ball, by SDX band (observed, chases)", "",
          "| Format | SDX band | Balls | Wicket % | SR | Boundary % | Dot % |", "|---|---|---|---|---|---|---|"]
    for b in res["behaviour"]:
        L.append(f"| {b['format_group']} | {b['band']}–{b['band'] + 20} | {b['balls']:,} | {b['wicket_pct']} | {b['strike_rate']} | {b['boundary_pct']} | {b['dot_pct']} |")
    L += ["", "## 6. Stability across eras (SDX at reference states)", ""]
    for k, rows in res["stability"].items():
        if isinstance(rows, str):
            L.append(f"- {k}: {rows}"); continue
        L.append(f"**{k}**: " + " · ".join(f"{r['state']}: {r['2005–15']} → {r['2016–24']}" for r in rows))
        L.append("")
    (DOCS / "situation-difficulty-validation.md").write_text("\n".join(L) + "\n")


if __name__ == "__main__":
    db = connect("cricsheet")
    r = validate(db)
    write_report(r)
    print(json.dumps({k: r[k] for k in ("holdout", "monotonicity")}, indent=1, default=str))
