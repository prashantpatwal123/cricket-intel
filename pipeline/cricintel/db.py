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
       bo.batting_position AS batter_position
FROM deliveries d
JOIN matches m USING (match_id)
JOIN innings i USING (match_id, innings_no)
LEFT JOIN player_profile bp ON bp.person_id = d.bowler_id
LEFT JOIN player_profile tp ON tp.person_id = d.batter_id
LEFT JOIN batting_order bo ON bo.match_id = d.match_id AND bo.innings_no = d.innings_no AND bo.person_id = d.batter_id
"""


class DB:
    def __init__(self, dataset: str, materialize: bool = True):
        self.dataset = dataset
        self.dataset_dir = dataset_dir(dataset)
        if not (self.dataset_dir / "manifest.json").exists():
            raise FileNotFoundError(f"dataset '{dataset}' not built. Run python -m cricintel.build --source {dataset}")
        self.manifest = json.loads((self.dataset_dir / "manifest.json").read_text())
        self.con = duckdb.connect()
        self.con.execute(f"SET threads TO {os.cpu_count() or 4}")
        for t in TABLES:
            self.con.execute(f"CREATE VIEW {t} AS SELECT * FROM read_parquet('{self.dataset_dir / t}/*.parquet')")
        for t in DERIVED:
            self.con.execute(f"CREATE VIEW {t} AS SELECT * FROM read_parquet('{self.dataset_dir / 'derived' / t}.parquet')")
        if materialize:
            self.con.execute(BALLS_SQL)
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
