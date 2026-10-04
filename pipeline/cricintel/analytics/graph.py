"""Cricket knowledge graph: materialized relationship tables over the canonical delivery data.

Entities and edges (all DERIVED from OBSERVED deliveries; built once by `cricintel.precompute`):
  bat_innings   Player —batted in→ Innings (of a Match, for a Team, against a Team, in a Competition)
  bowl_innings  Player —bowled in→ Innings
  battles       Player(batter) —faced→ Player(bowler), with standardized features for similarity
  team_results  Team —played→ Team in Match, with result and totals (rivalries, competitions)
  partnerships  Player —partnered→ Player (analytics/context.py)
A graph database is not needed: every relationship query here is a keyed lookup or an aggregate over one of these
tables, which DuckDB answers in milliseconds (see docs/data/benchmarks-phase4.md).
"""
from __future__ import annotations

GRAPH_VERSION = "graph-1.0"

# Franchise identity (DERIVED, documented): renamed franchises are the same team for rivalries and competition history.
# The original name stays visible on every match; only grouping uses the canonical name.
TEAM_CANON = {"Delhi Daredevils": "Delhi Capitals", "Kings XI Punjab": "Punjab Kings",
              "Royal Challengers Bangalore": "Royal Challengers Bengaluru", "Rising Pune Supergiants": "Rising Pune Supergiant"}
TEAM_ABBR = {"Chennai Super Kings": ["csk"], "Mumbai Indians": ["mi"], "Kolkata Knight Riders": ["kkr"], "Royal Challengers Bengaluru": ["rcb"],
             "Sunrisers Hyderabad": ["srh"], "Delhi Capitals": ["dc", "dd"], "Rajasthan Royals": ["rr"], "Punjab Kings": ["pbks", "kxip"],
             "Gujarat Titans": ["gt"], "Lucknow Super Giants": ["lsg"], "Gujarat Lions": ["gl"], "Rising Pune Supergiant": ["rps"],
             "Kochi Tuskers Kerala": ["ktk"], "Pune Warriors": ["pwi"], "Deccan Chargers": ["dch"], "UP Warriorz": ["upw"], "Gujarat Giants": ["gg"]}


def canon_sql(col: str) -> str:
    return "CASE " + " ".join(f"WHEN {col} = '{a}' THEN '{b}'" for a, b in TEAM_CANON.items()) + f" ELSE {col} END"

BAT_INNINGS_SQL = """
CREATE TABLE bat_innings AS
WITH involved AS (
  SELECT match_id, innings_no, seq, batter_id AS pid FROM balls
  UNION ALL SELECT match_id, innings_no, seq, non_striker_id FROM balls
), arrive AS (
  SELECT match_id, innings_no, pid, min(seq) AS first_seq, max(seq) AS last_seq FROM involved GROUP BY ALL
), faced AS (
  SELECT match_id, innings_no, batter_id AS pid, sum(runs_batter) AS runs, count(*) FILTER (WHERE wides = 0) AS balls,
         count(*) FILTER (WHERE is_four) AS fours, count(*) FILTER (WHERE is_six) AS sixes,
         count(*) FILTER (WHERE wides = 0 AND runs_batter = 0) AS dots,
         sum(runs_batter) FILTER (WHERE phase = 'death') AS death_runs, count(*) FILTER (WHERE wides = 0 AND phase = 'death') AS death_balls,
         -- late acceleration: last 10 balls faced v everything before them
         sum(runs_batter) FILTER (WHERE wides = 0 AND batter_balls_before >= 0) AS r_all
  FROM balls GROUP BY ALL
), last10 AS (
  SELECT match_id, innings_no, batter_id AS pid, sum(runs_batter) AS r10, count(*) AS b10 FROM (
    SELECT match_id, innings_no, batter_id, runs_batter,
           row_number() OVER (PARTITION BY match_id, innings_no, batter_id ORDER BY seq DESC) AS k
    FROM balls WHERE wides = 0) WHERE k <= 10 GROUP BY ALL
), outs AS (
  SELECT match_id, innings_no, player_out_id AS pid, any_value(kind) AS out_kind, any_value(bowler_id) AS out_bowler_id,
         any_value(bowler) AS out_bowler, any_value(delivery_id) AS out_delivery_id
  FROM dis WHERE counts_as_dismissal GROUP BY ALL
)
SELECT a.match_id, a.innings_no, a.pid AS batter_id, s.gender, s.format_group, s.team_type, s.competition, s.season, s.start_date, s.year,
       s.venue, s.city, s.batting_team AS team, s.bowling_team AS opponent, s.winner, s.result, s.method,
       coalesce(f.runs, 0) AS runs, coalesce(f.balls, 0) AS balls, coalesce(f.fours, 0) AS fours, coalesce(f.sixes, 0) AS sixes,
       coalesce(f.dots, 0) AS dots, coalesce(f.death_runs, 0) AS death_runs, coalesce(f.death_balls, 0) AS death_balls,
       l.r10, l.b10, o.out_kind, o.out_bowler_id, o.out_bowler, o.out_delivery_id, (o.pid IS NULL) AS not_out,
       bo.batting_position AS position, s.chasing, (s.winner = s.batting_team) AS won,
       s.score_before AS arrived_score, s.wickets_before AS arrived_wickets, s.over AS arrived_over,
       s.runs_required AS req_at_arrival, s.balls_left AS balls_left_at_arrival, s.required_rate AS rrr_at_arrival,
       a.first_seq, a.last_seq
FROM arrive a
JOIN balls s ON s.match_id = a.match_id AND s.innings_no = a.innings_no AND s.seq = a.first_seq
LEFT JOIN faced f ON f.match_id = a.match_id AND f.innings_no = a.innings_no AND f.pid = a.pid
LEFT JOIN last10 l ON l.match_id = a.match_id AND l.innings_no = a.innings_no AND l.pid = a.pid
LEFT JOIN outs o ON o.match_id = a.match_id AND o.innings_no = a.innings_no AND o.pid = a.pid
LEFT JOIN batting_order bo ON bo.match_id = a.match_id AND bo.innings_no = a.innings_no AND bo.person_id = a.pid
WHERE a.pid IS NOT NULL AND s.format_group IN ('T20', 'ODI')
"""

BOWL_INNINGS_SQL = """
CREATE TABLE bowl_innings AS
WITH w AS (SELECT delivery_id, count(*) AS n FROM wickets WHERE bowler_credited GROUP BY 1),
seqd AS (
  SELECT b.*, coalesce(w.n, 0) AS wk, runs_batter + wides + noballs AS rc,
         sum(coalesce(w.n, 0)) OVER (PARTITION BY match_id, innings_no, bowler_id ORDER BY seq ROWS BETWEEN 11 PRECEDING AND CURRENT ROW) AS burst12
  FROM balls b LEFT JOIN w USING (delivery_id)
), setw AS (
  SELECT match_id, innings_no, bowler_id, count(*) AS set_wkts FROM dis WHERE bowler_credited AND batter_balls_before >= 30 GROUP BY ALL
)
SELECT s.match_id, s.innings_no, s.bowler_id, any_value(s.bowler) AS bowler_name, any_value(s.gender) AS gender,
       any_value(s.format_group) AS format_group, any_value(s.team_type) AS team_type, any_value(s.competition) AS competition,
       any_value(s.season) AS season, any_value(s.start_date) AS start_date, any_value(s.year) AS year, any_value(s.venue) AS venue,
       any_value(s.bowling_team) AS team, any_value(s.batting_team) AS opponent, any_value(s.winner) AS winner,
       bool_or(coalesce(s.chasing, false)) AS defending, (any_value(s.winner) = any_value(s.bowling_team)) AS won,
       count(*) FILTER (WHERE s.legal) AS balls, sum(s.rc) AS runs, sum(s.wk) AS wickets,
       count(*) FILTER (WHERE s.legal AND s.rc = 0) AS dots, count(*) FILTER (WHERE s.is_four OR s.is_six) AS boundaries,
       count(*) FILTER (WHERE s.wides > 0 OR s.noballs > 0) AS extras_balls,
       count(*) FILTER (WHERE s.legal AND s.phase = 'death') AS death_balls, sum(s.rc) FILTER (WHERE s.phase = 'death') AS death_runs,
       sum(s.wk) FILTER (WHERE s.phase = 'death') AS death_wkts,
       count(*) FILTER (WHERE s.legal AND s.batter_stage = 'set') AS set_balls, sum(s.rc) FILTER (WHERE s.batter_stage = 'set') AS set_runs,
       coalesce(any_value(sw.set_wkts), 0) AS set_wkts, max(s.burst12) AS best_burst12,
       count(DISTINCT s.over) AS overs_bowled
FROM seqd s LEFT JOIN setw sw ON sw.match_id = s.match_id AND sw.innings_no = s.innings_no AND sw.bowler_id = s.bowler_id
WHERE s.format_group IN ('T20', 'ODI')
GROUP BY s.match_id, s.innings_no, s.bowler_id
"""

# Battles: one row per batter × bowler × gender, across formats, with the standardized features used for similarity.
BATTLES_SQL = """
CREATE TABLE battles AS
WITH o AS (SELECT batter_id, bowler_id, count(*) AS outs FROM dis WHERE bowler_credited GROUP BY ALL),
bat AS (SELECT batter_id, gender, sum(runs_batter) * 1.0 / count(*) AS rpb, count(*) AS n FROM balls WHERE wides = 0 GROUP BY ALL),
bato AS (SELECT player_out_id AS batter_id, count(*) AS outs FROM dis WHERE bowler_credited GROUP BY ALL),
bowl AS (SELECT bowler_id, gender, sum(runs_batter) * 1.0 / count(*) AS rpb, count(*) AS n FROM balls WHERE wides = 0 GROUP BY ALL),
bowlw AS (SELECT bowler_id, count(*) AS wk FROM dis WHERE bowler_credited GROUP BY ALL),
p AS (
  SELECT batter_id, bowler_id, gender, count(*) FILTER (WHERE wides = 0) AS balls, sum(runs_batter) AS runs,
         count(*) FILTER (WHERE wides = 0 AND runs_batter = 0) AS dots, count(*) FILTER (WHERE is_four) AS fours,
         count(*) FILTER (WHERE is_six) AS sixes, count(DISTINCT match_id) AS matches, min(start_date) AS first_date, max(start_date) AS last_date,
         avg(CASE WHEN phase = 'powerplay' THEN 1.0 ELSE 0 END) AS pp_share, avg(CASE WHEN phase = 'death' THEN 1.0 ELSE 0 END) AS death_share,
         avg(CASE WHEN format_group = 'T20' THEN 1.0 ELSE 0 END) AS t20_share,
         list(DISTINCT format_group) AS formats, list(DISTINCT competition)[1:5] AS competitions,
         any_value(batter) AS batter_name, any_value(bowler) AS bowler_name
  FROM balls WHERE format_group IN ('T20', 'ODI') GROUP BY batter_id, bowler_id, gender
)
SELECT p.*, coalesce(o.outs, 0) AS outs, bat.rpb AS batter_rpb, bat.n AS batter_balls_all, coalesce(bato.outs, 0) * 1.0 / bat.n AS batter_out_rate,
       bowl.rpb AS bowler_rpb, bowl.n AS bowler_balls_all, coalesce(bowlw.wk, 0) * 1.0 / bowl.n AS bowler_wkt_rate
FROM p LEFT JOIN o USING (batter_id, bowler_id)
JOIN bat ON bat.batter_id = p.batter_id AND bat.gender = p.gender LEFT JOIN bato ON bato.batter_id = p.batter_id
JOIN bowl ON bowl.bowler_id = p.bowler_id AND bowl.gender = p.gender LEFT JOIN bowlw ON bowlw.bowler_id = p.bowler_id
WHERE p.balls >= 12
"""

TEAM_RESULTS_SQL = """
CREATE TABLE team_results AS
WITH t AS (
  SELECT match_id, max(total_runs) FILTER (WHERE innings_no = 1) AS i1_runs, max(total_wickets) FILTER (WHERE innings_no = 1) AS i1_wkts,
         max(legal_balls) FILTER (WHERE innings_no = 1) AS i1_balls, max(batting_team) FILTER (WHERE innings_no = 1) AS i1_team,
         max(total_runs) FILTER (WHERE innings_no = 2) AS i2_runs, max(total_wickets) FILTER (WHERE innings_no = 2) AS i2_wkts,
         max(legal_balls) FILTER (WHERE innings_no = 2) AS i2_balls, max(batting_team) FILTER (WHERE innings_no = 2) AS i2_team
  FROM innings WHERE NOT super_over GROUP BY 1
)
SELECT m.match_id, m.start_date, year(m.start_date) AS year, m.season, m.gender, m.format_group, m.team_type, m.competition,
       m.event_stage, m.venue, m.city, m.team1, m.team2,
       least({c1}, {c2}) AS ta, greatest({c1}, {c2}) AS tb, {cw} AS winner_c,
       m.winner, m.result, m.method, m.win_by_runs, m.win_by_wickets, m.toss_winner, m.toss_decision, m.player_of_match,
       t.i1_team, t.i1_runs, t.i1_wkts, t.i1_balls, t.i2_team, t.i2_runs, t.i2_wkts, t.i2_balls
FROM matches m LEFT JOIN t USING (match_id) WHERE m.format_group IN ('T20', 'ODI')
"""

TEAM_RESULTS_SQL = TEAM_RESULTS_SQL.format(c1=canon_sql("m.team1"), c2=canon_sql("m.team2"), cw=canon_sql("m.winner"))
GRAPH_TABLES = {"bat_innings": BAT_INNINGS_SQL, "bowl_innings": BOWL_INNINGS_SQL, "battles": BATTLES_SQL, "team_results": TEAM_RESULTS_SQL}
