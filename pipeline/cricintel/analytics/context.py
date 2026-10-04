"""Context Engine v1: canonical per-delivery situation features, partnerships and bowling spells.

Everything here is DERIVED: a deterministic calculation over OBSERVED Cricsheet events. Nothing is estimated.
Features are written to derived/delivery_context.parquet (joined into `balls` at load), derived/partnerships.parquet
and derived/spells.parquet. Run:  python -m cricintel.analytics.context --dataset cricsheet

Format rules (we do not force T20 concepts onto ODIs):
  * "recent" windows are 12 legal balls (2 overs) in T20 and 30 legal balls (5 overs) in ODIs, about 10% of an innings;
  * chase "ahead / around / behind" uses a band of ±1.0 run/over in T20 and ±0.5 in ODIs around the current rate;
  * innings limit = revised target overs when Cricsheet records them, otherwise scheduled overs. First innings of
    matches decided by a rain method may have been shortened mid-innings; those limits are flagged as uncertain.
"""
from __future__ import annotations

import argparse
import time

from ..db import connect

CONTEXT_VERSION = "context-1.0"

# key -> (label, definition, provenance, format note)
FEATURES = {
    "innings_no": ("Innings", "1 = setting a target, 2 = chasing (super overs excluded).", "OBSERVED", ""),
    "over": ("Over", "0-based over number from the source; shown 1-based.", "OBSERVED", ""),
    "phase": ("Phase", "T20: powerplay overs 1–6, middle 7–15, death 16–20. ODI: 1–10, 11–40, 41–50.", "DERIVED", "format-specific"),
    "score_before": ("Score", "Team runs before the delivery.", "DERIVED", ""),
    "wickets_before": ("Wickets lost", "Team wickets before the delivery.", "DERIVED", ""),
    "wickets_in_hand": ("Wickets in hand", "10 − wickets lost.", "DERIVED", ""),
    "innings_balls_limit": ("Innings length", "Legal balls available: revised target overs if recorded, else scheduled overs.", "DERIVED",
                            "uncertain for first innings of rain-method matches"),
    "balls_left": ("Balls remaining", "Innings length − legal balls bowled.", "DERIVED", "defined for both innings"),
    "progress_pct": ("Innings progress", "Legal balls bowled ÷ innings length, 0–100.", "DERIVED", ""),
    "target_runs": ("Target", "Runs needed to win, from the source or first-innings total + 1.", "OBSERVED/DERIVED", "chases only"),
    "runs_required": ("Runs required", "Target − score.", "DERIVED", "chases only"),
    "required_rate": ("Required rate", "Runs required × 6 ÷ balls remaining.", "DERIVED", "chases only"),
    "current_rate": ("Current rate", "Score × 6 ÷ legal balls bowled.", "DERIVED", ""),
    "chase_state": ("Chase state", "ahead / around / behind: required rate vs current rate with a ±1.0 (T20) or ±0.5 (ODI) band.",
                    "DERIVED", "chases only; format-specific band"),
    "partnership_runs_before": ("Partnership runs", "Runs (incl. extras) added by the current pair before the delivery.", "DERIVED", ""),
    "partnership_balls_before": ("Partnership balls", "Legal balls in the current partnership before the delivery.", "DERIVED", ""),
    "batter_runs_before": ("Batter runs", "Striker's runs before the delivery.", "DERIVED", ""),
    "batter_balls_before": ("Batter balls", "Balls the striker had faced before the delivery (wides excluded).", "DERIVED", ""),
    "batter_stage": ("Batter stage", "new (0–9 balls faced), settling (10–29), set (30+).", "DERIVED", ""),
    "batter_balls_since_boundary": ("Batter balls since boundary", "Balls faced by the striker since their last 4 or 6 (or since arriving).", "DERIVED", ""),
    "team_balls_since_boundary": ("Team balls since boundary", "Legal balls since the batting side's last 4 or 6 (or since the start).", "DERIVED", ""),
    "recent_window": ("Recent window", "12 legal balls in T20, 30 in ODIs.", "DERIVED", "format-specific"),
    "recent_runs": ("Recent runs", "Runs (incl. extras) in the previous recent-window legal balls.", "DERIVED", "format-specific window"),
    "recent_wickets": ("Recent wickets", "Wickets in the previous recent-window legal balls.", "DERIVED", "format-specific window"),
    "team_dot_streak": ("Dot-ball sequence", "Consecutive previous legal balls with no run of any kind.", "DERIVED", ""),
    "batter_dot_streak": ("Batter dot sequence", "Consecutive previous balls faced by the striker with no run off the bat.", "DERIVED", ""),
    "team_boundary_streak": ("Boundary sequence", "Consecutive previous legal balls that were 4s or 6s.", "DERIVED", ""),
}

CONTEXT_SQL = """
WITH base AS (
  SELECT d.*, m.format_group, m.scheduled_overs, m.balls_per_over, m.method, i.target_overs, i.super_over,
         CASE WHEN m.format_group = 'T20' THEN 12 WHEN m.format_group = 'ODI' THEN 30 ELSE NULL END AS recent_window,
         CASE WHEN d.legal THEN 1 ELSE 0 END AS legal_i,
         CASE WHEN d.runs_batter IN (4, 6) AND NOT d.non_boundary THEN 1 ELSE 0 END AS bnd
  FROM deliveries d JOIN matches m USING (match_id) JOIN innings i USING (match_id, innings_no)
  WHERE NOT i.super_over AND m.format_group IN ('T20', 'ODI')
), w AS (
  SELECT *,
    -- last legal-ball index (1-based) at which the team hit a boundary, before this delivery
    max(CASE WHEN bnd = 1 THEN legal_balls_before + legal_i END) OVER inn_prev AS last_team_bnd,
    max(CASE WHEN runs_total > 0 THEN legal_balls_before + legal_i END) OVER inn_prev AS last_team_run,
    max(CASE WHEN legal AND bnd = 0 THEN legal_balls_before + 1 END) OVER inn_prev AS last_team_nonbnd,
    max(CASE WHEN bnd = 1 THEN batter_balls_before + 1 END) OVER bat_prev AS last_bat_bnd,
    max(CASE WHEN wides = 0 AND runs_batter > 0 THEN batter_balls_before + 1 END) OVER bat_prev AS last_bat_run,
    sum(runs_total) OVER (PARTITION BY match_id, innings_no ORDER BY legal_balls_before
                          RANGE BETWEEN recent_window PRECEDING AND 1 PRECEDING) AS recent_runs,
    sum(n_wickets) OVER (PARTITION BY match_id, innings_no ORDER BY legal_balls_before
                         RANGE BETWEEN recent_window PRECEDING AND 1 PRECEDING) AS recent_wickets
  FROM base
  WINDOW inn_prev AS (PARTITION BY match_id, innings_no ORDER BY seq ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING),
         bat_prev AS (PARTITION BY match_id, innings_no, batter_id ORDER BY seq ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING)
)
SELECT delivery_id,
  10 - wickets_before AS wickets_in_hand,
  CAST(round(coalesce(target_overs, scheduled_overs) * coalesce(balls_per_over, 6)) AS INTEGER) AS innings_balls_limit,
  (innings_no = 1 AND method IS NOT NULL) AS limit_uncertain,
  CAST(round(coalesce(target_overs, scheduled_overs) * coalesce(balls_per_over, 6)) AS INTEGER) - legal_balls_before AS balls_left,
  round(100.0 * legal_balls_before / nullif(coalesce(target_overs, scheduled_overs) * coalesce(balls_per_over, 6), 0), 1) AS progress_pct,
  CASE WHEN required_rate IS NULL OR current_rate IS NULL THEN NULL
       WHEN required_rate < current_rate - (CASE WHEN format_group = 'T20' THEN 1.0 ELSE 0.5 END) THEN 'ahead'
       WHEN required_rate > current_rate + (CASE WHEN format_group = 'T20' THEN 1.0 ELSE 0.5 END) THEN 'behind'
       ELSE 'around' END AS chase_state,
  CASE WHEN batter_balls_before < 10 THEN 'new' WHEN batter_balls_before < 30 THEN 'settling' ELSE 'set' END AS batter_stage,
  batter_balls_before - coalesce(last_bat_bnd, 0) AS batter_balls_since_boundary,
  legal_balls_before - coalesce(last_team_bnd, 0) AS team_balls_since_boundary,
  recent_window, CAST(coalesce(recent_runs, 0) AS INTEGER) AS recent_runs, CAST(coalesce(recent_wickets, 0) AS INTEGER) AS recent_wickets,
  legal_balls_before - coalesce(last_team_run, 0) AS team_dot_streak,
  batter_balls_before - coalesce(last_bat_run, 0) AS batter_dot_streak,
  CASE WHEN last_team_bnd IS NULL THEN 0 ELSE legal_balls_before - coalesce(last_team_nonbnd, 0) END AS team_boundary_streak
FROM w
"""

# A partnership = consecutive deliveries in an innings with the same unordered pair at the crease.
PARTNERSHIP_SQL = """
WITH b AS (
  SELECT d.*, least(batter_id, non_striker_id) AS p1, greatest(batter_id, non_striker_id) AS p2,
         m.gender, m.format_group, m.team_type, m.competition, m.start_date, i.batting_team, i.bowling_team
  FROM deliveries d JOIN matches m USING (match_id) JOIN innings i USING (match_id, innings_no)
  WHERE NOT i.super_over AND m.format_group IN ('T20', 'ODI')
), c AS (
  SELECT *, CASE WHEN p1 || p2 <> coalesce(lag(p1 || p2) OVER (PARTITION BY match_id, innings_no ORDER BY seq), '') THEN 1 ELSE 0 END AS chg
  FROM b
), g AS (
  SELECT *, CAST(sum(chg) OVER (PARTITION BY match_id, innings_no ORDER BY seq) AS INTEGER) AS part_no FROM c
)
SELECT match_id || ':' || innings_no || ':' || part_no AS partnership_id, match_id, innings_no, CAST(part_no AS INTEGER) AS part_no,
  any_value(p1) AS p1, any_value(p2) AS p2, any_value(gender) AS gender, any_value(format_group) AS format_group,
  any_value(team_type) AS team_type, any_value(competition) AS competition, any_value(start_date) AS start_date,
  any_value(batting_team) AS batting_team, any_value(bowling_team) AS bowling_team,
  min(wickets_before) AS wicket_no, min(seq) AS first_seq, max(seq) AS last_seq,
  min(over) AS first_over, max(over) AS last_over, min(score_before) AS score_start,
  CAST(sum(runs_total) AS INTEGER) AS runs, count(*) FILTER (WHERE legal) AS balls,
  CAST(coalesce(sum(runs_batter) FILTER (WHERE batter_id = p1), 0) AS INTEGER) AS p1_runs, count(*) FILTER (WHERE batter_id = p1 AND wides = 0) AS p1_balls,
  CAST(coalesce(sum(runs_batter) FILTER (WHERE batter_id = p2), 0) AS INTEGER) AS p2_runs, count(*) FILTER (WHERE batter_id = p2 AND wides = 0) AS p2_balls,
  CAST(sum(runs_extras) AS INTEGER) AS extras,
  count(*) FILTER (WHERE runs_batter IN (4, 6) AND NOT non_boundary) AS boundaries,
  count(*) FILTER (WHERE legal AND runs_total = 0) AS dots,
  count(*) FILTER (WHERE legal AND runs_batter IN (1, 2, 3) AND NOT (runs_batter IN (4, 6))) AS rotations,
  arg_max(delivery_id, seq) AS last_delivery_id
FROM g GROUP BY match_id, innings_no, part_no
"""

PARTNERSHIP_END_SQL = """
SELECT p.*, CASE WHEN w.delivery_id IS NOT NULL AND (list_contains(w.outs, p.p1) OR list_contains(w.outs, p.p2)) THEN
                   CASE WHEN list_contains(w.kinds, 'retired hurt') OR list_contains(w.kinds, 'retired not out') THEN 'retired' ELSE 'wicket' END
                 WHEN p.last_seq = (SELECT max(seq) FROM deliveries d2 WHERE d2.match_id = p.match_id AND d2.innings_no = p.innings_no) THEN 'unbroken'
                 ELSE 'other' END AS ended,
       w.outs AS ended_outs
FROM parts p LEFT JOIN (SELECT delivery_id, list(player_out_id) AS outs, list(kind) AS kinds FROM wickets GROUP BY 1) w
  ON w.delivery_id = p.last_delivery_id
"""

# A spell = a bowler's overs in an innings where each over follows their previous one by at most 2 overs
# (i.e. bowling unchanged from one end). A gap of more than one intervening over starts a new spell.
SPELL_SQL = """
WITH o AS (
  SELECT d.match_id, d.innings_no, d.bowler_id, d.over, any_value(d.bowler) AS bowler,
         CAST(sum(d.runs_batter + d.wides + d.noballs) AS INTEGER) AS runs, count(*) FILTER (WHERE d.legal) AS balls,
         count(*) FILTER (WHERE d.legal AND d.runs_total = 0) AS dots,
         count(*) FILTER (WHERE d.runs_batter IN (4, 6) AND NOT d.non_boundary) AS boundaries,
         min(d.seq) AS first_seq, max(d.seq) AS last_seq, min(d.score_before) AS score_start, min(d.wickets_before) AS wkts_start
  FROM deliveries d JOIN innings i USING (match_id, innings_no) JOIN matches m USING (match_id)
  WHERE NOT i.super_over AND m.format_group IN ('T20', 'ODI')
  GROUP BY 1, 2, 3, 4
), wk AS (
  SELECT d.match_id, d.innings_no, d.bowler_id, d.over, count(*) AS wickets
  FROM wickets w JOIN deliveries d USING (delivery_id) WHERE w.bowler_credited GROUP BY 1, 2, 3, 4
), s AS (
  SELECT o.*, coalesce(wk.wickets, 0) AS wickets,
         CASE WHEN o.over - lag(o.over) OVER (PARTITION BY o.match_id, o.innings_no, o.bowler_id ORDER BY o.over) <= 2 THEN 0 ELSE 1 END AS brk
  FROM o LEFT JOIN wk USING (match_id, innings_no, bowler_id, over)
)
SELECT *, CAST(sum(brk) OVER (PARTITION BY match_id, innings_no, bowler_id ORDER BY over) AS INTEGER) AS spell_no FROM s
"""


def build_context(dataset: str) -> dict:
    t0 = time.time()
    db = connect(dataset, materialize=False)
    out = db.dataset_dir / "derived"
    db.execute(f"COPY ({CONTEXT_SQL}) TO '{out / 'delivery_context.parquet'}' (FORMAT PARQUET)")
    db.execute(f"CREATE TEMP TABLE parts AS {PARTNERSHIP_SQL}")
    db.execute(f"COPY ({PARTNERSHIP_END_SQL}) TO '{out / 'partnerships.parquet'}' (FORMAT PARQUET)")
    db.execute(f"COPY ({SPELL_SQL}) TO '{out / 'spells.parquet'}' (FORMAT PARQUET)")
    n = {t: db.q1(f"SELECT count(*) AS n FROM read_parquet('{out / (t + '.parquet')}')")["n"]
         for t in ("delivery_context", "partnerships", "spells")}
    return {"version": CONTEXT_VERSION, "rows": n, "seconds": round(time.time() - t0, 1)}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", default="cricsheet")
    print(build_context(ap.parse_args().dataset))
