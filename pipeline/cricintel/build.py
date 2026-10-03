"""Build the canonical store: raw source files -> canonical Parquet -> derived Parquet.

    python -m cricintel.build --source synthetic        # fixture dataset
    python -m cricintel.build --source cricsheet        # real data (data/raw/cricsheet/all_json.zip)

Output: data/canonical/<dataset>/{table}/part-*.parquet, derived/*.parquet, manifest.json
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import shutil
import time
from collections import Counter, defaultdict
from pathlib import Path

import duckdb
import pyarrow as pa
import pyarrow.parquet as pq

from .config import CANONICAL, RAW
from .provenance import SOURCES
from .schema import ENRICHMENT_TABLES, TABLES
from .sources import cricsheet
from .metadata import enrich

BATCH = 400


def dataset_dir(name: str) -> Path:
    return CANONICAL / name


def _flush(out: Path, buf: dict[str, list[dict]], part: int):
    for t, rows in buf.items():
        if not rows:
            continue
        tbl = pa.Table.from_pylist(rows, schema=TABLES[t])
        d = out / t
        d.mkdir(parents=True, exist_ok=True)
        pq.write_table(tbl, d / f"part-{part:05d}.parquet", compression="zstd")


def ingest(source: str, out: Path) -> dict:
    if source == "cricsheet":
        z = RAW / "cricsheet" / "all_json.zip"
        if not z.exists():
            raise SystemExit(f"{z} not found. Run: python -m cricintel.sources.cricsheet download")
        it, source_id, reg = cricsheet.iter_zip(z), "cricsheet", RAW / "cricsheet" / "register" / "people.csv"
    elif source == "synthetic":
        it, source_id, reg = cricsheet.iter_dir(RAW / "synthetic"), "synthetic_fixture", RAW / "synthetic" / "register" / "people.csv"
    else:
        raise SystemExit(f"unknown source {source}")

    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    buf: dict[str, list[dict]] = defaultdict(list)
    drift: Counter = Counter()
    quarantine, seen, n, part = [], {}, 0, 0
    for match_id, doc, ref, sha in it:
        if match_id in seen:
            quarantine.append({"match_id": match_id, "source_ref": ref, "reason": f"duplicate match_id (first: {seen[match_id]})"})
            continue
        seen[match_id] = ref
        try:
            rows = cricsheet.parse_match(doc, match_id, source_id, ref, sha, drift)
        except cricsheet.Quarantine as e:
            quarantine.append({"match_id": match_id, "source_ref": ref, "reason": str(e)})
            continue
        for t, rs in rows.items():
            buf[t].extend(rs)
        n += 1
        if n % BATCH == 0:
            _flush(out, buf, part); part += 1; buf = defaultdict(list)
    _flush(out, buf, part)
    # Empty-but-present tables (incl. enrichment satellites) so queries never fail on absence.
    for t, schema in TABLES.items():
        if not (out / t).exists():
            (out / t).mkdir(parents=True)
            pq.write_table(schema.empty_table(), out / t / "part-00000.parquet")
    persons = cricsheet.read_register(reg) if reg.exists() else []
    if persons:
        pq.write_table(pa.Table.from_pylist(persons, schema=TABLES["persons"]), out / "persons" / "part-00000.parquet")
    return {"matches_ingested": n, "quarantined": quarantine, "schema_drift": dict(drift),
            "register_rows": len(persons), "source_id": source_id}


DERIVED_SQL = r"""
-- ------------------------------------------------------------------ batting order (DERIVED)
CREATE OR REPLACE TABLE batting_order AS
WITH appear AS (
  SELECT match_id, innings_no, batter_id AS person_id, seq FROM deliveries
  UNION ALL SELECT match_id, innings_no, non_striker_id, seq FROM deliveries
  UNION ALL SELECT d.match_id, d.innings_no, w.player_out_id, d.seq
    FROM wickets w JOIN deliveries d USING (delivery_id)
), first AS (
  SELECT match_id, innings_no, person_id, min(seq) AS first_seq FROM appear GROUP BY ALL
)
SELECT match_id, innings_no, person_id,
       row_number() OVER (PARTITION BY match_id, innings_no ORDER BY first_seq,
            -- opening pair both appear on ball 1: striker first
            person_id) AS position_raw, first_seq
FROM first;

CREATE OR REPLACE TABLE batting_order AS
SELECT b.match_id, b.innings_no, b.person_id,
       CASE WHEN b.first_seq = 1 THEN
            CASE WHEN b.person_id = (SELECT batter_id FROM deliveries d WHERE d.match_id=b.match_id AND d.innings_no=b.innings_no AND d.seq=1) THEN 1 ELSE 2 END
            ELSE b.position_raw END AS batting_position
FROM batting_order b;

-- ------------------------------------------------------------------ wicketkeeper inference (DERIVED)
CREATE OR REPLACE TABLE keeper_inference AS
WITH stump AS (   -- who effected a stumping, for which bowling team, in which match
  SELECT w.match_id, i.bowling_team AS team, f.fielder_id AS person_id, count(*) AS n
  FROM wickets w JOIN wicket_fielders f USING (delivery_id, wicket_idx)
  JOIN innings i ON i.match_id = w.match_id AND i.innings_no = w.innings_no
  WHERE w.kind = 'stumped' AND NOT f.substitute AND f.fielder_id IS NOT NULL
  GROUP BY ALL
), in_match AS (
  SELECT match_id, team, person_id, 'stumping_in_match' AS method, 0.97::DOUBLE AS confidence
  FROM (SELECT *, count(*) OVER (PARTITION BY match_id, team) AS k FROM stump) WHERE k = 1
), career AS (
  SELECT person_id, count(DISTINCT match_id) AS stumping_matches FROM stump GROUP BY 1
), bowled AS (
  SELECT DISTINCT d.match_id, i.bowling_team AS team, d.bowler_id AS person_id
  FROM deliveries d JOIN innings i USING (match_id, innings_no)
), cands AS (
  SELECT p.match_id, p.team, p.person_id, c.stumping_matches
  FROM players_in_match p JOIN career c USING (person_id)
  WHERE NOT EXISTS (SELECT 1 FROM bowled b WHERE b.match_id=p.match_id AND b.team=p.team AND b.person_id=p.person_id)
), ranked AS (
  SELECT *, row_number() OVER w AS rk, lead(stumping_matches) OVER w AS next_best, count(*) OVER (PARTITION BY match_id, team) AS ncand
  FROM cands WINDOW w AS (PARTITION BY match_id, team ORDER BY stumping_matches DESC)
), by_career AS (
  SELECT match_id, team, person_id,
         CASE WHEN ncand = 1 THEN 'sole_career_keeper_in_xi' ELSE 'dominant_career_keeper_in_xi' END AS method,
         (CASE WHEN ncand = 1 THEN 0.85 ELSE 0.75 END)::DOUBLE AS confidence
  FROM ranked WHERE rk = 1 AND stumping_matches >= 2
    AND (ncand = 1 OR stumping_matches >= 3 * coalesce(next_best, 0))
)
SELECT * FROM in_match
UNION ALL
SELECT * FROM by_career b WHERE NOT EXISTS (SELECT 1 FROM in_match m WHERE m.match_id=b.match_id AND m.team=b.team);

-- ------------------------------------------------------------------ dismissal routes (DERIVED, never invents positions)
CREATE OR REPLACE TABLE dismissals AS
WITH f1 AS (SELECT * FROM wicket_fielders WHERE fielder_idx = 0),
base AS (
  SELECT w.*, d.bowler_id, d.batter_id, d.over, d.ball_label, d.phase, i.bowling_team,
         f1.fielder_id, f1.fielder, f1.substitute,
         (SELECT list(struct_pack(id := f.fielder_id, name := f.fielder, sub := f.substitute) ORDER BY f.fielder_idx)
            FROM wicket_fielders f WHERE f.delivery_id = w.delivery_id AND f.wicket_idx = w.wicket_idx) AS fielders,
         k.person_id AS keeper_id, k.method AS keeper_method, k.confidence AS keeper_conf
  FROM wickets w JOIN deliveries d USING (delivery_id)
  JOIN innings i ON i.match_id = w.match_id AND i.innings_no = w.innings_no
  LEFT JOIN f1 ON f1.delivery_id = w.delivery_id AND f1.wicket_idx = w.wicket_idx
  LEFT JOIN keeper_inference k ON k.match_id = w.match_id AND k.team = i.bowling_team
)
SELECT *,
  CASE
    WHEN kind = 'bowled' THEN 'BOWLED'
    WHEN kind = 'lbw' THEN 'LBW'
    WHEN kind = 'stumped' THEN 'STUMPED'
    WHEN kind = 'caught and bowled' THEN 'CAUGHT_BOWLER'
    WHEN kind = 'caught' AND fielder_id = bowler_id THEN 'CAUGHT_BOWLER'
    WHEN kind = 'caught' AND fielder_id IS NULL THEN 'CAUGHT_UNKNOWN_FIELDER'
    WHEN kind = 'caught' AND NOT substitute AND keeper_id IS NOT NULL AND fielder_id = keeper_id THEN 'CAUGHT_KEEPER'
    WHEN kind = 'caught' AND (substitute OR keeper_id IS NOT NULL) THEN 'CAUGHT_FIELDER'
    WHEN kind = 'caught' THEN 'CAUGHT_KEEPER_STATUS_UNKNOWN'
    WHEN kind = 'run out' THEN 'RUN_OUT'
    WHEN kind = 'hit wicket' THEN 'HIT_WICKET'
    WHEN kind IN ('retired hurt', 'retired not out') THEN 'RETIRED_NOT_OUT'
    ELSE 'OTHER'
  END AS route,
  CASE
    WHEN kind = 'caught' AND fielder_id IS NOT NULL AND fielder_id <> bowler_id THEN 'DERIVED'
    ELSE 'OBSERVED' END AS route_prov,
  CASE
    WHEN kind = 'caught' AND substitute THEN 0.95
    WHEN kind = 'caught' AND NOT coalesce(substitute, false) AND fielder_id = keeper_id THEN keeper_conf
    WHEN kind = 'caught' AND keeper_id IS NOT NULL AND fielder_id <> bowler_id THEN keeper_conf
    ELSE NULL END::DOUBLE AS route_confidence,
  CASE WHEN kind = 'caught' AND fielder_id IS NOT NULL AND fielder_id <> bowler_id
       THEN 'route_from_keeper_inference/v1' END AS route_method
FROM base;
"""


def derive(out: Path) -> dict:
    con = duckdb.connect()
    for t in TABLES:
        con.execute(f"CREATE VIEW {t} AS SELECT * FROM read_parquet('{out / t}/*.parquet')")
    con.execute(DERIVED_SQL)
    dd = out / "derived"
    dd.mkdir(exist_ok=True)
    for t in ("batting_order", "keeper_inference", "dismissals"):
        con.execute(f"COPY {t} TO '{dd / t}.parquet' (FORMAT parquet, COMPRESSION zstd)")
    stats = {t: con.execute(f"SELECT count(*) FROM {t}").fetchone()[0] for t in ("batting_order", "keeper_inference", "dismissals")}
    stats["routes"] = dict(con.execute("SELECT route, count(*) FROM dismissals GROUP BY 1 ORDER BY 2 DESC").fetchall())
    con.close()
    return stats


def build(source: str) -> dict:
    t0 = time.time()
    out = dataset_dir(source)
    info = ingest(source, out)
    t1 = time.time()
    info["derived"] = derive(out)
    t2 = time.time()
    info["metadata"] = enrich.run(out, source)
    t3 = time.time()
    src = SOURCES[info["source_id"]]
    manifest = {
        "dataset": source, "built_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "source_id": info["source_id"], "synthetic": src["synthetic"], "licence": src["licence"],
        "attribution": src["attribution"], "matches_ingested": info["matches_ingested"],
        "quarantined": len(info["quarantined"]), "schema_drift": info["schema_drift"],
        "register_rows": info["register_rows"], "derived": info["derived"],
        "metadata": info["metadata"], "enrichment_tables": ENRICHMENT_TABLES,
        "timings_s": {"ingest": round(t1 - t0, 1), "derive": round(t2 - t1, 1), "metadata": round(t3 - t2, 1)},
    }
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2, default=str))
    (out / "quarantine.json").write_text(json.dumps(info["quarantined"], indent=2))
    return manifest


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", default="synthetic", choices=["synthetic", "cricsheet"])
    a = ap.parse_args()
    print(json.dumps(build(a.source), indent=2, default=str))
