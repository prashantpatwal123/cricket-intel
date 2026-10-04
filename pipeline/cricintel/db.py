"""DuckDB access layer over the canonical Parquet store."""
from __future__ import annotations

import json
import os
import threading
from pathlib import Path

import duckdb

from .build import dataset_dir
from .schema import TABLES

DERIVED = ["batting_order", "keeper_inference", "dismissals", "player_metadata", "player_profile"]

# Analytical working set: one row per delivery with match/innings context and player attributes,
# each attribute carrying its provenance so downstream filters can report what they relied on.
BALLS_SQL = """
CREATE TABLE balls AS
SELECT d.*,
       m.gender, m.format_group, m.match_type, m.team_type, m.competition, m.season, m.start_date,
       year(m.start_date) AS year, m.venue, m.city, m.team1, m.team2, m.winner, m.result, m.method,
       i.batting_team, i.bowling_team, i.super_over,
       bp.bowling_family AS bowler_family, bp.bowling_family_prov AS bowler_family_prov,
       bp.bowling_family_source AS bowler_family_source,
       bp.bowling_arm AS bowler_arm, bp.bowling_style AS bowler_style,
       tp.batting_hand AS batter_hand, tp.batting_hand_source AS batter_hand_source,
       (d.wides = 0) AS faced,
       bo.batting_position AS batter_position{ctx_cols}
FROM deliveries d
JOIN matches m USING (match_id)
JOIN innings i USING (match_id, innings_no)
LEFT JOIN player_profile bp ON bp.person_id = d.bowler_id
LEFT JOIN player_profile tp ON tp.person_id = d.batter_id
LEFT JOIN batting_order bo ON bo.match_id = d.match_id AND bo.innings_no = d.innings_no AND bo.person_id = d.batter_id{ctx_join}
-- Cricsheet (contact page): "Super Overs don't count towards statistics" -> excluded from the analytical working set.
WHERE NOT i.super_over
"""


class DB:
    def __init__(self, dataset: str, materialize: bool = True):
        self.dataset = dataset
        self.dataset_dir = dataset_dir(dataset)
        if not (self.dataset_dir / "manifest.json").exists():
            raise FileNotFoundError(f"dataset '{dataset}' not built. Run python -m cricintel.build --source {dataset}")
        self.manifest = json.loads((self.dataset_dir / "manifest.json").read_text())
        self.con = duckdb.connect()
        self.con.execute("SET enable_progress_bar = false")
        self.con.execute(f"SET threads TO {os.cpu_count() or 4}")
        for t in TABLES:
            self.con.execute(f"CREATE VIEW {t} AS SELECT * FROM read_parquet('{self.dataset_dir / t}/*.parquet')")
        for t in DERIVED:
            self.con.execute(f"CREATE VIEW {t} AS SELECT * FROM read_parquet('{self.dataset_dir / 'derived' / t}.parquet')")
        for t in ("source_missing_matches", "source_coverage_periods", "source_coverage_pct"):
            f = self.dataset_dir / "derived" / f"{t}.parquet"
            self.has_source_coverage = f.exists()
            if f.exists():
                self.con.execute(f"CREATE VIEW {t} AS SELECT * FROM read_parquet('{f}')")
        # Context Engine outputs (analytics/context.py). Optional so older datasets still load.
        self.has_context = (self.dataset_dir / "derived" / "delivery_context.parquet").exists()
        if self.has_context:
            for t in ("delivery_context", "partnerships", "spells"):
                self.con.execute(f"CREATE VIEW {t} AS SELECT * FROM read_parquet('{self.dataset_dir / 'derived' / t}.parquet')")
        sit = self.dataset_dir / "derived" / "situation.parquet"  # Situation Difficulty — Experimental (model/situation.py)
        self.has_situation = sit.exists()
        if self.has_situation:
            self.con.execute(f"CREATE VIEW situation AS SELECT * FROM read_parquet('{sit}')")
        ctx_cols = """, cx.wickets_in_hand, cx.innings_balls_limit, cx.limit_uncertain, cx.balls_left, cx.progress_pct, cx.chase_state,
       cx.batter_stage, cx.batter_balls_since_boundary, cx.team_balls_since_boundary, cx.recent_window, cx.recent_runs,
       cx.recent_wickets, cx.team_dot_streak, cx.batter_dot_streak, cx.team_boundary_streak""" if self.has_context else ""
        ctx_join = "\nLEFT JOIN delivery_context cx ON cx.delivery_id = d.delivery_id" if self.has_context else ""
        if materialize:
            self.con.execute(BALLS_SQL.format(ctx_cols=ctx_cols, ctx_join=ctx_join))
            self.con.execute("""CREATE TABLE dis AS SELECT x.*, b.gender, b.format_group, b.team_type, b.competition,
                b.season, b.start_date, b.year, b.batting_team, b.bowling_team, b.bowler, b.batter, b.bowler_family,
                b.bowler_family_prov, b.bowler_arm, b.bowler_style, b.chasing, b.score_before, b.wickets_before,
                b.batter_runs_before, b.batter_balls_before, b.runs_total, b.required_rate, b.batter_position,
                b.batter_hand, b.bowler_family_source
                FROM dismissals x JOIN balls b USING (delivery_id)""")
        self._lock = threading.Lock()

    def execute(self, sql: str, params=None):
        return self.con.execute(sql, params or [])

    def q(self, sql: str, params=None) -> list[dict]:
        """Thread-safe query returning list of dicts (one cursor per call)."""
        cur = self.con.cursor()
        try:
            res = cur.execute(sql, params or [])
            cols = [c[0] for c in res.description]
            return [dict(zip(cols, r)) for r in res.fetchall()]
        finally:
            cur.close()

    def q1(self, sql: str, params=None) -> dict | None:
        r = self.q(sql, params)
        return r[0] if r else None


def connect(dataset: str, materialize: bool = True) -> DB:
    return DB(dataset, materialize)
