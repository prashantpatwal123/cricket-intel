"""Data Quality & Methodology centre: what is covered, what is missing, how every number is defined, which models exist."""
from __future__ import annotations

import json
from pathlib import Path

from ..db import DB
from ..provenance import SOURCES

PROV = {"OBSERVED": "Directly recorded in the source data.", "DERIVED": "Calculated deterministically from recorded data.",
        "RECONSTRUCTED": "Arrangement inferred from reliable event information.", "MODELLED": "A statistical estimate, not a fact.",
        "ILLUSTRATIVE": "A generic cricket graphic to aid understanding; not a reconstruction of the event.",
        "UNKNOWN": "Not recorded in the data; shown as unknown, never guessed."}


def methodology(db: DB, experimental: bool) -> dict:
    tot = db.q1("""SELECT count(*) AS matches, min(start_date) AS d0, max(start_date) AS d1 FROM team_results""")
    tot["deliveries"] = db.q1("SELECT count(*) AS n FROM balls")["n"]
    tot["players"] = db.q1("SELECT count(*) AS n FROM player_profile WHERE matches > 0")["n"]
    groups = db.q("""SELECT gender, format_group, team_type, count(*) AS matches, min(start_date) AS d0, max(start_date) AS d1 FROM team_results
                     GROUP BY ALL ORDER BY gender, format_group, team_type""")
    comps = db.q("""SELECT competition, gender, count(*) AS matches, min(start_date) AS d0, max(start_date) AS d1 FROM team_results WHERE competition IS NOT NULL
                    GROUP BY 1, 2 ORDER BY matches DESC LIMIT 25""")
    cov = {(r["name"], r["gender"]): r for r in db.q("SELECT * FROM source_coverage_pct WHERE scope = 'competition'")} if db.has_source_coverage else {}
    for c in comps:
        r = cov.get((c["competition"], c["gender"])) or cov.get((c["competition"], None))
        c["source_completeness"] = f"{r['have']}/{r['of']} ({r['pct']}%)" if r else "not published"
    periods = db.q("SELECT * FROM source_coverage_periods") if db.has_source_coverage else []
    missing = db.q("""SELECT match_type, gender, count(*) AS n FROM source_missing_matches WHERE match_type IN ('ODI', 'T20I', 'IT20', 'T20')
                      GROUP BY 1, 2 ORDER BY n DESC""") if db.has_source_coverage else []
    meta = db.q1("""SELECT count(*) AS players,
                       100.0 * count(*) FILTER (WHERE batting_hand IS NOT NULL) / count(*) AS batting_hand,
                       100.0 * count(*) FILTER (WHERE bowling_style IS NOT NULL) / count(*) AS bowling_style,
                       100.0 * count(*) FILTER (WHERE role IS NOT NULL) / count(*) AS role,
                       100.0 * count(*) FILTER (WHERE wicketkeeper IS NOT NULL) / count(*) AS keeper_flag
                    FROM player_profile WHERE matches > 0""")
    deliv = db.q1("""SELECT 100.0 * count(*) FILTER (WHERE batter_hand IS NOT NULL) / count(*) AS batting_hand,
                            100.0 * count(*) FILTER (WHERE bowler_style IS NOT NULL) / count(*) AS bowling_style FROM balls""")
    from .context import CONTEXT_VERSION, FEATURES
    from .discovery import VERSION as DISC_V
    from .feed import VERSION as FEED_V
    from .graph import GRAPH_VERSION
    from .libraries import BATTLE_CATS, INNINGS_CATS, SPELL_CATS
    from .records import METRICS
    from .search import VERSION as SEARCH_V
    from ..db import WORKING_VERSION
    models = []
    mdir = Path(__file__).resolve().parents[3] / "data" / "models"
    for f in sorted(mdir.glob(f"*-{db.dataset}.json")) if mdir.exists() else []:
        try:
            d = json.loads(f.read_text())
            models.append({"file": f.name, "version": d.get("model_version") or d.get("version"), "trained_before": d.get("cutoff") or d.get("trained_before"),
                           "status": "IN USE (What Happens Next)" if "baseline" in f.name else "data"})
        except (ValueError, OSError):
            pass
    sdx = db.dataset_dir / "derived" / f"sdx-0.1-{db.dataset}.json"
    if sdx.exists():
        models.append({"file": sdx.name, "version": "sdx-0.1", "trained_before": "2025-01-01",
                       "status": "EXPERIMENTAL (flag " + ("on" if experimental else "off") + "): Situation Difficulty"})
    return {"source": SOURCES[db.manifest["source_id"]], "built_at": db.manifest["built_at"], "totals": {**tot, "d0": str(tot["d0"]), "d1": str(tot["d1"])},
            "groups": [{**g, "d0": str(g["d0"]), "d1": str(g["d1"])} for g in groups],
            "competitions": [{**c, "d0": str(c["d0"]), "d1": str(c["d1"])} for c in comps], "periods": periods, "missing": missing,
            "metadata": {"players": meta, "deliveries": deliv},
            "provenance": PROV,
            "definitions": {"records": [{"key": k, "label": v[0], "definition": v[8], "min": v[5], "unit": v[4]} for k, v in METRICS.items()],
                            "context": [{"key": k, "label": v[0], "definition": v[1], "prov": v[2]} for k, v in FEATURES.items()],
                            "innings_library": [{"key": k, "label": v[0], "definition": v[1]} for k, v in INNINGS_CATS.items()],
                            "spell_library": [{"key": k, "label": v[0], "definition": v[1]} for k, v in SPELL_CATS.items()],
                            "battles": [{"key": k, "label": v[0], "definition": v[1]} for k, v in BATTLE_CATS.items()]},
            "models": models,
            "versions": {"live_engine": _live_versions()[0], "right_now": _live_versions()[1], "context": CONTEXT_VERSION, "graph": GRAPH_VERSION, "working_db": WORKING_VERSION, "search": SEARCH_V, "discovery": DISC_V, "feed": FEED_V, **_fan_versions()},
            "fan": {"rabbit_hole": "Explore-next destinations are real relationships in covered data, ranked by strength, unusualness, sample, "
                                   "recognisability, recency and relationship kind, diversified, and pushed down when already opened in this browser. "
                                   "Session memory stays in the browser; the page sends the list of opened pages with each request and nothing is stored.",
                    "similar_players": "Nearest neighbours on fingerprint dimensions (style, not quality), validated on held-out halves of each player's "
                                       "matches; pools that fail the stability bar are not shown.",
                    "didnt_know": "Discovery findings that survive Benjamini–Hochberg (q = 0.01) across every candidate tested, with minimum samples.",
                    "compare": "Per-dimension verdicts with a Bonferroni-corrected test; no overall score.",
                    "records": "Record book: named definitions × scope, each with definition, minimum sample, filters, coverage and evidence. "
                               "Single-match records have a 'major teams' view (leagues + full-member internationals) and an all-covered view.",
                    "on_this_day": "'N years ago today' only for single-day matches; matches spanning days are labelled as having begun that day.",
                    "play_moments": "Pre-ball state only; the replay opens at that cursor and reveals the ball after the call.",
                    "docs": ["docs/architecture/knowledge-graph-and-rabbit-hole.md", "docs/models/similar-players.md", "docs/product/phase7-fan-audit.md"]},
            "experimental": [{"name": "Situation Difficulty — Experimental (SDX v0.1)", "status": "on" if experimental else "off",
                              "doc": "docs/models/situation-difficulty.md"},
                             {"name": "Performance in difficult chases", "status": "on" if experimental else "off",
                              "doc": "Split-half test found no stable trait; the word 'clutch' is not used."}],
            "rejected": [{"name": "What Would You Do?", "why": "Intent is not recorded; ~80–90% of balls can't be labelled without guessing."},
                         {"name": "Win probability (not shipped)", "why": "Research gate: ODI men and women fail calibration (over-confident, slope 0.75/0.84). "
                          "T20 passes the pre-registered rules but a wicket can raise the probability in some states and club T20 is poorly calibrated; "
                          "display needs owner approval. See docs/models/win-probability-research.md."},
                         {"name": "Turning points", "why": "No validated turning-point algorithm; match pages list defined factual events instead."},
                         {"name": "'Clutch'", "why": "Beating expectation in hard chases does not persist across halves of a career (split-half r ≈ 0)."},
                         {"name": "Pace/spin, line/length, shot maps", "why": "Not in the data; bowling-style metadata covers only a few % of deliveries."}],
            "live_lab": {"what": "Historical Live Lab: completed matches replayed ball by ball through a provider-neutral live event contract. Never live.",
                         "spoiler_safety": "The server reads and sends only deliveries up to the cursor; every historical comparison uses matches before the replayed one.",
                         "in_sample": "The next-ball model (trained before 2024-01-01) and Situation Difficulty (before 2025-01-01) are in-sample for earlier matches; the Match Centre says so.",
                         "docs": ["docs/architecture/live-data-contract.md", "docs/models/right-now-engine.md", "docs/architecture/notifications.md"]},
            "limitations": ["Historical Live Lab: Cricsheet records only the final D/L target, so a revised target is applied from the start of the chase and labelled.",
                            "Franchise renames are grouped for rivalries and team filters (e.g. Kings XI Punjab → Punjab Kings); original names stay on every match.",
                            "T20I completeness cannot be established from Cricsheet's pages; competition pages say when completeness is unknown.",
                            "Cricsheet withholds matches involving Afghanistan men.", "Batting hand is unknown for almost all players."]}


def _fan_versions() -> dict:
    from ..fan import kg, rabbit, records2, similar
    return {"fan_graph": kg.VERSION, "rabbit_hole": rabbit.VERSION, "similar_players": similar.VERSION, "records_v2": records2.VERSION}


def _live_versions() -> tuple[str, str]:
    from ..live.engine import VERSION as E
    from ..live.insights import VERSION as R
    return E, R
