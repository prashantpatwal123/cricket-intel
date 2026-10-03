"""Automated player-metadata enrichment with provenance.

Pipeline:  canonical player (Cricsheet id)
           -> external identifiers (Register key_* columns)
           -> enrichment adapters (automated, legally usable sources)
           -> derived-from-events signals (wicketkeeper, role)
           -> manual overrides (exception path, must cite evidence)
           -> best value per field + PLAYER METADATA COVERAGE report

Precedence per field: manual_override > external adapter > derived. Every candidate value is kept
in player_metadata (long form) so disagreements stay auditable.
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

import duckdb
import pyarrow as pa
import pyarrow.parquet as pq

from ..config import DOCS_DATA, METADATA, RAW
from . import adapters
from .styles import normalise_bowling_style

FIELDS = ["batting_hand", "bowling_arm", "bowling_style", "bowling_family", "role", "wicketkeeper"]
META_SCHEMA = pa.schema([
    ("person_id", pa.string()), ("field", pa.string()), ("value", pa.string()), ("prov", pa.string()),
    ("source_id", pa.string()), ("method", pa.string()), ("confidence", pa.float64()),
    ("is_override", pa.bool_()), ("evidence", pa.string()),
])
PRECEDENCE = {"manual_override": 0, "external": 1, "derived": 2}


def _derived_signals(con) -> list[dict]:
    rows = []
    q = """
    WITH pm AS (SELECT DISTINCT match_id, person_id FROM players_in_match),
    k AS (SELECT person_id, count(DISTINCT match_id) AS keeper_matches,
                 list(DISTINCT method) AS methods FROM keeper_inference GROUP BY 1),
    bowl AS (SELECT bowler_id AS person_id, count(*) FILTER (WHERE legal) AS balls,
                    count(DISTINCT match_id) AS bowl_matches FROM deliveries GROUP BY 1),
    bo AS (SELECT person_id, avg(batting_position) AS avg_pos, count(*) AS bat_inns FROM batting_order GROUP BY 1)
    SELECT pm.person_id, count(DISTINCT pm.match_id) AS matches,
           coalesce(k.keeper_matches, 0) AS keeper_matches, k.methods,
           coalesce(bowl.balls, 0) AS balls_bowled, coalesce(bowl.bowl_matches, 0) AS bowl_matches,
           bo.avg_pos, coalesce(bo.bat_inns, 0) AS bat_inns
    FROM pm LEFT JOIN k USING (person_id) LEFT JOIN bowl USING (person_id) LEFT JOIN bo USING (person_id)
    GROUP BY ALL
    """
    for (pid, matches, kmat, kmeth, balls, bmat, avg_pos, bat_inns) in con.execute(q).fetchall():
        conf_n = min(0.95, 0.5 + matches / 60)  # more matches -> more confident role read
        ev = dict(matches=matches, keeper_matches=kmat, balls_bowled=balls, avg_batting_position=avg_pos and round(avg_pos, 1))
        if kmat >= 1:
            share = kmat / matches
            rows.append(dict(person_id=pid, field="wicketkeeper", value="yes" if share >= 0.25 or kmat >= 3 else "occasional",
                             prov="DERIVED", source_id="derived", method="keeper_inference_aggregate/v1",
                             confidence=round(min(0.97, 0.6 + share * 0.4), 2), is_override=False,
                             evidence=json.dumps(dict(ev, methods=kmeth))))
        bpm = balls / matches if matches else 0
        if kmat >= 3 and kmat / matches >= 0.3:
            role = "wicketkeeper-batter"
        elif bpm >= 12 and avg_pos is not None and avg_pos <= 7:
            role = "all-rounder"
        elif bpm >= 12:
            role = "bowler"
        elif bpm >= 3:
            role = "batting all-rounder"  # bowls a little
        else:
            role = "batter"
        if matches >= 3:
            rows.append(dict(person_id=pid, field="role", value=role, prov="DERIVED", source_id="derived",
                             method="role_from_usage/v1", confidence=round(conf_n, 2), is_override=False,
                             evidence=json.dumps(ev)))
    return rows


def _overrides() -> list[dict]:
    p = METADATA / "overrides.csv"
    rows = []
    if p.exists():
        with open(p, newline="") as fh:
            for r in csv.DictReader(fh):
                if not r.get("evidence"):
                    raise ValueError(f"override without evidence: {r}")
                rows.append(dict(person_id=r["person_id"], field=r["field"], value=r["value"], prov="OBSERVED",
                                 source_id="manual_override", method=f"curator:{r.get('curator', '?')}",
                                 confidence=1.0, is_override=True, evidence=r["evidence"]))
    return rows


def _expand_style(rows: list[dict]) -> list[dict]:
    """A raw bowling_style string also yields arm + family (DERIVED from the same source)."""
    extra = []
    for r in rows:
        if r["field"] == "bowling_style" and r["value"]:
            n = normalise_bowling_style(r["value"])
            if not n:
                continue
            r["value"] = n["label"]
            for f in ("bowling_arm", "bowling_family"):
                if n.get(f.split("_")[1]):
                    extra.append(dict(r, field=f, value=n[f.split("_")[1]], prov="DERIVED",
                                      method=r["method"] + "+style_parse/v1"))
    return rows + extra


def run(out: Path, dataset: str) -> dict:
    con = duckdb.connect()
    for t in ("players_in_match", "keeper_inference", "deliveries", "batting_order", "persons", "matches"):
        src = out / "derived" / f"{t}.parquet" if (out / "derived" / f"{t}.parquet").exists() else f"{out / t}/*.parquet"
        con.execute(f"CREATE VIEW {t} AS SELECT * FROM read_parquet('{src}')")

    ext_ids = {pid: dict(m) for pid, m in con.execute(
        "SELECT person_id, external_ids FROM persons").fetchall()}
    candidates: list[dict] = []
    adapter_reports = []
    for ad in adapters.for_dataset(dataset, RAW):
        got, rep = ad.fetch(ext_ids)
        candidates += got
        adapter_reports.append(rep)
    candidates = _expand_style(candidates)
    candidates += _derived_signals(con)
    candidates += _overrides()
    pq.write_table(pa.Table.from_pylist(candidates, schema=META_SCHEMA), out / "derived" / "player_metadata.parquet")

    con.execute(f"CREATE VIEW player_metadata AS SELECT * FROM read_parquet('{out / 'derived' / 'player_metadata.parquet'}')")
    con.execute("""
    CREATE TABLE best AS
    SELECT * EXCLUDE (rk) FROM (
      SELECT *, row_number() OVER (PARTITION BY person_id, field ORDER BY
        CASE WHEN is_override THEN 0 WHEN source_id = 'derived' THEN 2 ELSE 1 END, confidence DESC NULLS LAST) AS rk
      FROM player_metadata) WHERE rk = 1
    """)
    piv = ", ".join(
        f"max(value) FILTER (WHERE field='{f}') AS {f}, max(source_id || ':' || method) FILTER (WHERE field='{f}') AS {f}_source, "
        f"max(confidence) FILTER (WHERE field='{f}') AS {f}_confidence, max(prov) FILTER (WHERE field='{f}') AS {f}_prov"
        for f in FIELDS)
    con.execute(f"""
    CREATE TABLE player_profile AS
    WITH base AS (
      SELECT p.person_id, any_value(p.name) AS name, list(DISTINCT m.gender) AS genders,
             list(DISTINCT p.team ORDER BY p.team) AS teams, count(DISTINCT p.match_id) AS matches,
             min(m.start_date) AS first_match, max(m.start_date) AS last_match,
             bool_and(p.identity_resolved) AS identity_resolved
      FROM players_in_match p JOIN matches m USING (match_id) GROUP BY 1
    ), meta AS (SELECT person_id, {piv}, bool_or(is_override) AS has_override FROM best GROUP BY 1)
    SELECT base.*, meta.* EXCLUDE (person_id) FROM base LEFT JOIN meta USING (person_id)
    """)
    con.execute(f"COPY player_profile TO '{out / 'derived' / 'player_profile.parquet'}' (FORMAT parquet)")
    report = coverage_report(con, dataset, adapter_reports)
    con.close()
    return report


def coverage_report(con, dataset: str, adapter_reports: list[dict]) -> dict:
    total = con.execute("SELECT count(*) FROM player_profile").fetchone()[0]
    cov = {}
    for f in FIELDS:
        n = con.execute(f"SELECT count(*) FROM player_profile WHERE {f} IS NOT NULL").fetchone()[0]
        by = dict(con.execute(f"SELECT {f}_source, count(*) FROM player_profile WHERE {f} IS NOT NULL GROUP BY 1").fetchall())
        cov[f] = {"known": n, "pct": round(100 * n / total, 1) if total else 0, "by_source": by}
    # weighted by deliveries: what share of balls have known bowler style / batter hand?
    w_style = con.execute("""SELECT avg(CASE WHEN pp.bowling_family IS NOT NULL THEN 1.0 ELSE 0 END)
        FROM deliveries d LEFT JOIN player_profile pp ON pp.person_id = d.bowler_id""").fetchone()[0]
    w_hand = con.execute("""SELECT avg(CASE WHEN pp.batting_hand IS NOT NULL THEN 1.0 ELSE 0 END)
        FROM deliveries d LEFT JOIN player_profile pp ON pp.person_id = d.batter_id""").fetchone()[0]
    DOCS_DATA.mkdir(parents=True, exist_ok=True)
    csv_path = DOCS_DATA / f"player-metadata-coverage-{dataset}.csv"
    con.execute(f"""COPY (SELECT name AS player, person_id AS cricsheet_id, array_to_string(genders, ';') AS gender,
        array_to_string(teams, ';') AS teams, matches, batting_hand, bowling_arm AS bowling_hand, bowling_style,
        bowling_family, role, wicketkeeper AS wicketkeeper_status,
        concat_ws(' | ', batting_hand_source, bowling_style_source, role_source, wicketkeeper_source) AS metadata_source,
        concat_ws(' | ', batting_hand_confidence, bowling_style_confidence, role_confidence, wicketkeeper_confidence) AS confidence,
        coalesce(has_override, false) AS manual_override
        FROM player_profile ORDER BY matches DESC) TO '{csv_path}' (HEADER)""")
    lines = [f"# Player metadata coverage — dataset `{dataset}`", "",
             "Generated by `cricintel.metadata.enrich`. Precedence: manual override > external adapter > derived from events.", "",
             f"Players: **{total}**", "", "| Field | Known | % players | Sources |", "|---|---|---|---|"]
    for f, c in cov.items():
        lines.append(f"| {f} | {c['known']} | {c['pct']}% | {', '.join(f'{k}: {v}' for k, v in c['by_source'].items()) or '—'} |")
    lines += ["", f"Delivery-weighted coverage: bowler family known on **{100 * (w_style or 0):.1f}%** of deliveries; "
              f"batter hand known on **{100 * (w_hand or 0):.1f}%** of deliveries.", "", "## Adapters", ""]
    for r in adapter_reports:
        lines.append(f"- **{r['adapter']}**: {r['status']}")
    lines += ["", f"Full per-player table: `{csv_path.name}` (columns: player, cricsheet_id, gender, teams, batting hand, "
              "bowling hand, bowling style, role, wicketkeeper status, metadata source, confidence, manual override).", ""]
    if dataset == "synthetic":
        lines.insert(1, "\n> ⚠️ SYNTHETIC FIXTURE — fictional players. Coverage numbers describe the pipeline, not real cricket.\n")
    (DOCS_DATA / f"player-metadata-coverage-{dataset}.md").write_text("\n".join(lines))
    return {"players": total, "coverage": cov, "delivery_weighted": {"bowler_family": w_style, "batter_hand": w_hand},
            "adapters": adapter_reports}
