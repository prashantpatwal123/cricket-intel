"""Automated data-quality checks over the canonical store -> docs/data/qa-report-<dataset>.md

Each check is a SQL query returning offending rows. Severity:
  ERROR  data is internally inconsistent; analytics on affected rows would be wrong
  WARN   legitimate-but-unusual cricket (e.g. miscounted overs, impact players) or unresolvable identity
"""
from __future__ import annotations

import argparse
import json
import time

from .config import DOCS_DATA
from .db import connect

CHECKS = [
    # (id, area, severity, description, sql returning offending rows)
    ("dup_match_id", "duplicate matches", "ERROR", "match_id appears more than once",
     "SELECT match_id, count(*) n FROM matches GROUP BY 1 HAVING n > 1"),
    ("dup_match_fingerprint", "duplicate matches", "WARN",
     "same teams + start date + venue under different ids (possible duplicate upload)",
     """SELECT least(team1,team2) a, greatest(team1,team2) b, start_date, venue, list(match_id) AS ids, count(*) n
        FROM matches GROUP BY 1,2,3,4 HAVING n > 1"""),
    ("dup_delivery_id", "duplicate deliveries", "ERROR", "delivery_id not unique",
     "SELECT delivery_id, count(*) n FROM deliveries GROUP BY 1 HAVING n > 1"),
    ("dup_delivery_seq", "duplicate deliveries", "ERROR", "two deliveries share (match, innings, seq)",
     "SELECT match_id, innings_no, seq, count(*) n FROM deliveries GROUP BY ALL HAVING n > 1"),
    ("runs_total_sum", "innings totals", "ERROR", "runs.total != runs.batter + runs.extras",
     "SELECT delivery_id, runs_batter, runs_extras, runs_total FROM deliveries WHERE runs_total <> runs_batter + runs_extras"),
    ("innings_total", "innings totals", "ERROR", "innings total != Σ delivery totals + penalty runs",
     """SELECT i.match_id, i.innings_no, i.total_runs, s.r + coalesce(i.penalty_runs_pre,0) + coalesce(i.penalty_runs_post,0) AS recomputed
        FROM innings i JOIN (SELECT match_id, innings_no, sum(runs_total) r FROM deliveries GROUP BY ALL) s USING (match_id, innings_no)
        WHERE i.total_runs <> s.r + coalesce(i.penalty_runs_pre,0) + coalesce(i.penalty_runs_post,0)"""),
    ("extras_sum", "extras", "ERROR", "runs.extras != wides + noballs + byes + legbyes + penalty",
     "SELECT delivery_id FROM deliveries WHERE runs_extras <> wides + noballs + byes + legbyes + penalty"),
    ("extras_combo", "extras", "WARN", "wide and no-ball on the same delivery",
     "SELECT delivery_id FROM deliveries WHERE wides > 0 AND noballs > 0"),
    ("boundary_four_six", "extras", "WARN", "4 or 6 flagged non_boundary (all-run)",
     "SELECT delivery_id, runs_batter FROM deliveries WHERE runs_batter IN (4,6) AND non_boundary"),
    ("wickets_per_innings", "wicket totals", "ERROR", "more than 10 dismissals in an innings",
     "SELECT match_id, innings_no, count(*) n FROM wickets WHERE counts_as_dismissal GROUP BY ALL HAVING n > 10"),
    ("wickets_vs_xi", "wicket totals", "ERROR", "dismissals >= batting XI size",
     """SELECT w.match_id, w.innings_no, count(*) n, any_value(x.xi) xi FROM wickets w
        JOIN innings i USING (match_id, innings_no)
        JOIN (SELECT match_id, team, count(*) xi FROM players_in_match GROUP BY ALL) x ON x.match_id=w.match_id AND x.team=i.batting_team
        WHERE w.counts_as_dismissal GROUP BY ALL HAVING n >= any_value(x.xi)"""),
    ("legal_per_over", "legal deliveries", "WARN", "over has more legal balls than balls_per_over (umpire miscount?)",
     """SELECT d.match_id, d.innings_no, d.over, count(*) FILTER (WHERE legal) legal_balls, any_value(m.balls_per_over) bpo
        FROM deliveries d JOIN matches m USING (match_id) GROUP BY ALL HAVING legal_balls > any_value(m.balls_per_over)"""),
    ("short_over_mid_innings", "legal deliveries", "WARN", "non-final over with fewer legal balls than balls_per_over",
     """WITH o AS (SELECT d.match_id, d.innings_no, d.over, count(*) FILTER (WHERE legal) lb, any_value(m.balls_per_over) bpo
               FROM deliveries d JOIN matches m USING (match_id) GROUP BY d.match_id, d.innings_no, d.over),
        o2 AS (SELECT *, max(over) OVER (PARTITION BY match_id, innings_no) last_over FROM o)
        SELECT * FROM o2 WHERE over < last_over AND lb < bpo"""),
    ("identity_unresolved", "player identity", "WARN", "player name without a Register id (fallback id used)",
     "SELECT match_id, team, name FROM players_in_match WHERE NOT identity_resolved"),
    ("identity_multi_name", "player identity", "WARN", "one person_id appears under several names",
     "SELECT person_id, list(DISTINCT name) AS name_list FROM players_in_match GROUP BY 1 HAVING count(DISTINCT name) > 1"),
    ("batter_not_in_xi", "player identity", "WARN", "batter/non-striker not in batting XI (check replacements)",
     """SELECT DISTINCT d.match_id, d.batter FROM deliveries d JOIN innings i USING (match_id, innings_no)
        WHERE NOT i.super_over AND NOT EXISTS (SELECT 1 FROM players_in_match p WHERE p.match_id=d.match_id AND p.team=i.batting_team AND p.person_id=d.batter_id)
          AND NOT EXISTS (SELECT 1 FROM replacements r WHERE r.match_id=d.match_id AND r.player_in=d.batter)"""),
    ("bowler_not_in_xi", "team identity", "ERROR", "bowler not in bowling XI (and not a listed replacement)",
     """SELECT DISTINCT d.match_id, d.bowler FROM deliveries d JOIN innings i USING (match_id, innings_no)
        WHERE NOT EXISTS (SELECT 1 FROM players_in_match p WHERE p.match_id=d.match_id AND p.team=i.bowling_team AND p.person_id=d.bowler_id)
          AND NOT EXISTS (SELECT 1 FROM replacements r WHERE r.match_id=d.match_id AND r.player_in=d.bowler)"""),
    ("innings_team", "team identity", "ERROR", "innings batting team not one of the match teams",
     "SELECT i.match_id, i.batting_team FROM innings i JOIN matches m USING (match_id) WHERE i.batting_team NOT IN (m.team1, m.team2)"),
    ("winner_team", "match identity", "ERROR", "winner is not one of the teams",
     "SELECT match_id, winner FROM matches WHERE winner IS NOT NULL AND winner NOT IN (team1, team2)"),
    ("match_required", "match identity", "ERROR", "match missing gender/format/date/teams",
     "SELECT match_id FROM matches WHERE gender IS NULL OR match_type IS NULL OR start_date IS NULL OR team1 IS NULL OR team2 IS NULL"),
    ("player_out_on_ball", "dismissal consistency", "ERROR", "player out is neither batter nor non-striker",
     """SELECT w.delivery_id, w.player_out FROM wickets w JOIN deliveries d USING (delivery_id)
        WHERE w.player_out_id NOT IN (d.batter_id, d.non_striker_id) AND w.kind NOT IN ('retired hurt','retired not out','retired out','timed out')"""),
    ("bowler_kind_non_striker", "dismissal consistency", "ERROR", "bowler-credited dismissal of the non-striker",
     "SELECT delivery_id, kind FROM wickets WHERE bowler_credited AND NOT striker_out"),
    ("dismissed_twice", "dismissal consistency", "ERROR", "same batter dismissed twice in one innings",
     "SELECT match_id, innings_no, player_out_id, count(*) n FROM wickets WHERE counts_as_dismissal GROUP BY ALL HAVING n > 1"),
    ("wicket_on_wide_kind", "dismissal consistency", "ERROR", "bowled/lbw/caught on a wide (impossible)",
     "SELECT w.delivery_id, w.kind FROM wickets w JOIN deliveries d USING (delivery_id) WHERE d.wides > 0 AND w.kind IN ('bowled','lbw','caught','caught and bowled')"),
    ("wicket_on_noball_kind", "dismissal consistency", "ERROR", "bowled/lbw/caught/stumped on a no-ball (impossible)",
     "SELECT w.delivery_id, w.kind FROM wickets w JOIN deliveries d USING (delivery_id) WHERE d.noballs > 0 AND w.kind IN ('bowled','lbw','caught','caught and bowled','stumped')"),
    ("fielder_required", "fielder references", "WARN", "caught/stumped without a named fielder",
     """SELECT w.delivery_id, w.kind FROM wickets w WHERE w.kind IN ('caught','stumped')
        AND NOT EXISTS (SELECT 1 FROM wicket_fielders f WHERE f.delivery_id=w.delivery_id AND f.wicket_idx=w.wicket_idx)"""),
    ("fielder_not_in_xi", "fielder references", "WARN", "non-substitute fielder not in fielding XI",
     """SELECT f.delivery_id, f.fielder FROM wicket_fielders f JOIN innings i ON i.match_id=f.match_id AND i.innings_no=f.innings_no
        WHERE NOT f.substitute AND f.fielder_id IS NOT NULL AND NOT EXISTS (
          SELECT 1 FROM players_in_match p WHERE p.match_id=f.match_id AND p.team=i.bowling_team AND p.person_id=f.fielder_id)"""),
    ("keeper_unresolved", "fielder references", "WARN", "catches whose wicketkeeper status could not be inferred",
     "SELECT delivery_id, fielder FROM dismissals WHERE route = 'CAUGHT_KEEPER_STATUS_UNKNOWN'"),
    ("target_mismatch", "target/chase", "WARN", "observed target != first-innings total + 1 without a DLS-type method",
     """SELECT i2.match_id, i2.target_runs, i1.total_runs + 1 expected, m.method FROM innings i2
        JOIN innings i1 ON i1.match_id=i2.match_id AND i1.innings_no=1 JOIN matches m ON m.match_id=i2.match_id
        WHERE i2.innings_no=2 AND m.format_group IN ('T20','ODI') AND i2.target_runs IS NOT NULL
          AND i2.target_runs <> i1.total_runs + 1 AND m.method IS NULL AND NOT i2.super_over"""),
    ("chase_result", "target/chase", "ERROR", "chasing side reached target but is not recorded as winner",
     """SELECT i.match_id, i.batting_team, i.total_runs, i.target_runs, m.winner FROM innings i JOIN matches m USING (match_id)
        WHERE i.innings_no = 2 AND m.format_group IN ('T20','ODI') AND i.target_runs IS NOT NULL
          AND i.total_runs >= i.target_runs AND m.winner IS DISTINCT FROM i.batting_team AND m.result IS NULL"""),
    ("chase_overshoot", "target/chase", "WARN", "chase continued after the target was reached",
     """SELECT d.match_id, d.delivery_id FROM deliveries d WHERE d.chasing AND d.runs_required <= 0"""),
    ("context_required_rate", "target/chase", "ERROR", "required rate inconsistent with runs required / balls remaining",
     """SELECT delivery_id FROM deliveries WHERE required_rate IS NOT NULL
        AND abs(required_rate - runs_required * 6.0 / balls_remaining) > 1e-6"""),
]


def run(dataset: str) -> dict:
    con = connect(dataset)
    results = []
    t0 = time.time()
    for cid, area, sev, desc, sql in CHECKS:
        n = con.execute(f"SELECT count(*) FROM ({sql})").fetchone()[0]
        ex = con.execute(f"SELECT * FROM ({sql}) LIMIT 3").fetchall() if n else []
        results.append(dict(id=cid, area=area, severity=sev, description=desc, violations=n,
                            examples=[list(map(str, e)) for e in ex], status="PASS" if n == 0 else sev))
    counts = {t: con.execute(f"SELECT count(*) FROM {t}").fetchone()[0]
              for t in ("matches", "innings", "deliveries", "wickets", "wicket_fielders", "players_in_match", "persons")}
    errors = sum(1 for r in results if r["status"] == "ERROR")
    warns = sum(1 for r in results if r["status"] == "WARN")
    manifest = json.loads((con.dataset_dir / "manifest.json").read_text())
    report = dict(dataset=dataset, synthetic=manifest["synthetic"], counts=counts, checks=results,
                  errors=errors, warnings=warns, quarantined=manifest["quarantined"], seconds=round(time.time() - t0, 2))
    _write(report)
    return report


def _write(r: dict):
    DOCS_DATA.mkdir(parents=True, exist_ok=True)
    (DOCS_DATA / f"qa-report-{r['dataset']}.json").write_text(json.dumps(r, indent=2, default=str))
    L = [f"# QA report — dataset `{r['dataset']}`", ""]
    if r["synthetic"]:
        L += ["> ⚠️ SYNTHETIC FIXTURE (fictional matches). This report validates the pipeline, not real data.", ""]
    L += [f"**{len(r['checks'])} checks · {r['errors']} failing ERROR · {r['warnings']} WARN · "
          f"{r['quarantined']} matches quarantined at ingest · ran in {r['seconds']}s**", "",
          "| Table | Rows |", "|---|---|"] + [f"| {k} | {v:,} |" for k, v in r["counts"].items()]
    L += ["", "| Status | Area | Check | Violations | Example |", "|---|---|---|---|---|"]
    for c in r["checks"]:
        icon = {"PASS": "✅ PASS", "WARN": "🟡 WARN", "ERROR": "❌ ERROR"}[c["status"]]
        L.append(f"| {icon} | {c['area']} | {c['description']} (`{c['id']}`) | {c['violations']:,} | "
                 f"{('`' + ' · '.join(c['examples'][0]) + '`') if c['examples'] else ''} |")
    (DOCS_DATA / f"qa-report-{r['dataset']}.md").write_text("\n".join(L) + "\n")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", default="synthetic")
    a = ap.parse_args()
    rep = run(a.dataset)
    print(json.dumps({k: rep[k] for k in ("counts", "errors", "warnings", "seconds")}, indent=1))
    for c in rep["checks"]:
        print(f"{c['status']:5} {c['violations']:>7}  {c['id']}")
