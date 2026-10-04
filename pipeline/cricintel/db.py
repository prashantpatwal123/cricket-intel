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


WORKING_VERSION = "working-1.1"
DIS_SQL = """CREATE TABLE dis AS SELECT x.*, b.gender, b.format_group, b.team_type, b.competition,
                b.season, b.start_date, b.year, b.batting_team, b.bowling_team, b.bowler, b.batter, b.bowler_family,
                b.bowler_family_prov, b.bowler_arm, b.bowler_style, b.chasing, b.score_before, b.wickets_before,
                b.batter_runs_before, b.batter_balls_before, b.runs_total, b.required_rate, b.batter_position,
                b.batter_hand, b.bowler_family_source
                FROM dismissals x JOIN balls b USING (delivery_id)"""


def _setup(con, dsdir: Path, materialize: bool, graph: bool) -> dict:
    """Create the views and working tables on a connection (in-memory, or the persisted working file)."""
    flags = {}
    for t in TABLES:
        con.execute(f"CREATE VIEW {t} AS SELECT * FROM read_parquet('{dsdir / t}/*.parquet')")
    for t in DERIVED:
        con.execute(f"CREATE VIEW {t} AS SELECT * FROM read_parquet('{dsdir / 'derived' / t}.parquet')")
    flags["has_source_coverage"] = False
    for t in ("source_missing_matches", "source_coverage_periods", "source_coverage_pct"):
        f = dsdir / "derived" / f"{t}.parquet"
        if f.exists():
            flags["has_source_coverage"] = True
            con.execute(f"CREATE VIEW {t} AS SELECT * FROM read_parquet('{f}')")
    # Context Engine outputs (analytics/context.py). Optional so older datasets still load.
    flags["has_context"] = (dsdir / "derived" / "delivery_context.parquet").exists()
    if flags["has_context"]:
        for t in ("delivery_context", "partnerships", "spells"):
            con.execute(f"CREATE VIEW {t} AS SELECT * FROM read_parquet('{dsdir / 'derived' / t}.parquet')")
    sit = dsdir / "derived" / "situation.parquet"  # Situation Difficulty — Experimental (model/situation.py)
    flags["has_situation"] = sit.exists()
    if flags["has_situation"]:
        con.execute(f"CREATE VIEW situation AS SELECT * FROM read_parquet('{sit}')")
    ctx_cols = """, cx.wickets_in_hand, cx.innings_balls_limit, cx.limit_uncertain, cx.balls_left, cx.progress_pct, cx.chase_state,
       cx.batter_stage, cx.batter_balls_since_boundary, cx.team_balls_since_boundary, cx.recent_window, cx.recent_runs,
       cx.recent_wickets, cx.team_dot_streak, cx.batter_dot_streak, cx.team_boundary_streak""" if flags["has_context"] else ""
    ctx_join = "\nLEFT JOIN delivery_context cx ON cx.delivery_id = d.delivery_id" if flags["has_context"] else ""
    flags["has_graph"] = False
    if materialize:
        con.execute(BALLS_SQL.format(ctx_cols=ctx_cols, ctx_join=ctx_join))
        con.execute(DIS_SQL)
        # Historical Live Lab (Phase 5): raw events sorted by match so one match's rows are read via zone maps, not a scan.
        con.execute("CREATE TABLE live_deliveries AS SELECT * FROM deliveries ORDER BY match_id, innings_no, seq")
        con.execute("CREATE TABLE live_wickets AS SELECT * FROM wickets ORDER BY match_id, delivery_id, wicket_idx")
        con.execute("CREATE TABLE live_fielders AS SELECT * FROM wicket_fielders ORDER BY match_id, delivery_id, wicket_idx, fielder_idx")
        con.execute("CREATE TABLE live_players AS SELECT * FROM players_in_match ORDER BY match_id")
        flags["has_live"] = True
        if graph and flags["has_context"]:
            from .analytics.graph import GRAPH_TABLES
            for sql in GRAPH_TABLES.values():
                con.execute(sql)
            flags["has_graph"] = True
    return flags


class DB:
    """Analytical access to one dataset.

    Fast path: open the persisted working database (derived/working.duckdb, built by `cricintel.precompute`) read-only:
    startup drops from ~10 s (rebuilding 3.3M-row working tables) to well under a second. Falls back to building the
    working tables in memory when the file is missing or was built from a different dataset build.
    """
    def __init__(self, dataset: str, materialize: bool = True, graph: bool = True, prefer_working: bool = True):
        self.dataset = dataset
        self.dataset_dir = dataset_dir(dataset)
        if not (self.dataset_dir / "manifest.json").exists():
            raise FileNotFoundError(f"dataset '{dataset}' not built. Run python -m cricintel.build --source {dataset}")
        self.manifest = json.loads((self.dataset_dir / "manifest.json").read_text())
        self.working = False
        wf = self.dataset_dir / "derived" / "working.duckdb"
        if materialize and prefer_working and wf.exists():
            try:
                con = duckdb.connect(str(wf), read_only=True)
                meta = con.execute("SELECT built_at, version, flags FROM _meta").fetchone()
                if meta[0] == self.manifest["built_at"] and meta[1] == WORKING_VERSION:
                    self.con, self.working = con, True
                    for k, v in json.loads(meta[2]).items():
                        setattr(self, k, v)
                else:
                    con.close()
            except duckdb.Error:
                self.working = False
        if not self.working:
            self.con = duckdb.connect()
            for k, v in _setup(self.con, self.dataset_dir, materialize, graph).items():
                setattr(self, k, v)
        self.con.execute("SET enable_progress_bar = false")
        self.con.execute(f"SET threads TO {os.cpu_count() or 4}")
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


def build_working(dataset: str) -> dict:
    """Persist the working tables + knowledge graph to derived/working.duckdb (atomic replace)."""
    import time
    t0 = time.time()
    dsdir = dataset_dir(dataset)
    manifest = json.loads((dsdir / "manifest.json").read_text())
    final = dsdir / "derived" / "working.duckdb"
    tmp = dsdir / "derived" / "working.duckdb.tmp"
    for f in (tmp, Path(str(tmp) + ".wal")):
        if f.exists():
            f.unlink()
    con = duckdb.connect(str(tmp))
    con.execute("SET enable_progress_bar = false")
    flags = _setup(con, dsdir, True, True)
    con.execute("CREATE TABLE _meta (built_at VARCHAR, version VARCHAR, flags VARCHAR)")
    con.execute("INSERT INTO _meta VALUES (?, ?, ?)", [manifest["built_at"], WORKING_VERSION, json.dumps(flags)])
    con.execute("CHECKPOINT")
    con.close()
    tmp.replace(final)
    return {"file": str(final), "mb": round(final.stat().st_size / 1e6, 1), "seconds": round(time.time() - t0, 1), "flags": flags}
