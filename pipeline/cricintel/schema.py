"""Canonical cricket event model (physical Parquet schemas).

The Delivery is the atomic fact. Core OBSERVED facts live in wide typed tables; anything derived
carries explicit provenance columns. Enrichment that open data cannot provide (tracking, shot,
fielder positions, bat contact) has its own nullable satellite tables so licensed or
computer-vision sources can plug in later without touching the core tables.

Gender is a required, explicit column on every match and is never defaulted.
"""
import pyarrow as pa

S, I, F, B, D = pa.string(), pa.int32(), pa.float64(), pa.bool_(), pa.date32()

PROV_COLS = [
    ("prov", S),            # Prov enum value
    ("prov_source_id", S),  # SOURCES key
    ("prov_method", S),     # e.g. "keeper_inference"
    ("prov_method_version", S),
    ("prov_confidence", F),  # 0..1, null for OBSERVED
]

TABLES: dict[str, pa.Schema] = {
    "matches": pa.schema([
        ("match_id", S), ("source_id", S), ("source_ref", S), ("source_checksum", S),
        ("data_version", S), ("source_created", S), ("source_revision", I),
        ("gender", S), ("match_type", S), ("format_group", S), ("team_type", S),
        ("match_type_number", I), ("competition", S), ("event_match_number", S), ("event_group", S),
        ("event_stage", S), ("season", S), ("start_date", D), ("end_date", D), ("n_days", I),
        ("venue", S), ("city", S), ("team1", S), ("team2", S),
        ("toss_winner", S), ("toss_decision", S), ("toss_uncontested", B),
        ("winner", S), ("win_by_runs", I), ("win_by_wickets", I), ("win_by_innings", I),
        ("result", S), ("method", S), ("eliminator", S),
        ("balls_per_over", I), ("scheduled_overs", I), ("player_of_match", pa.list_(S)),
        ("missing_flags", S), ("ingested_at", S),
    ]),
    "innings": pa.schema([
        ("match_id", S), ("innings_no", I), ("batting_team", S), ("bowling_team", S),
        ("super_over", B), ("declared", B), ("forfeited", B),
        ("target_runs", I), ("target_overs", F), ("target_prov", S),
        ("penalty_runs_pre", I), ("penalty_runs_post", I), ("absent_hurt", pa.list_(S)),
        ("total_runs", I), ("total_wickets", I), ("legal_balls", I),
    ]),
    "players_in_match": pa.schema([
        ("match_id", S), ("team", S), ("person_id", S), ("name", S), ("identity_resolved", B),
    ]),
    "deliveries": pa.schema([
        ("delivery_id", S), ("match_id", S), ("innings_no", I), ("seq", I),
        ("over", I), ("ball_in_over", I), ("ball_label", S), ("legal", B),
        ("batter_id", S), ("bowler_id", S), ("non_striker_id", S),
        ("batter", S), ("bowler", S), ("non_striker", S),
        ("runs_batter", I), ("runs_extras", I), ("runs_total", I), ("non_boundary", B),
        ("wides", I), ("noballs", I), ("byes", I), ("legbyes", I), ("penalty", I),
        ("is_four", B), ("is_six", B), ("n_wickets", I),
        ("source_id", S),
        # DERIVED context: deterministic from the delivery sequence (prov = DERIVED, confidence 1).
        ("score_before", I), ("wickets_before", I), ("legal_balls_before", I),
        ("batter_runs_before", I), ("batter_balls_before", I),
        ("partnership_runs_before", I), ("partnership_balls_before", I),
        ("phase", S), ("chasing", B), ("target_runs", I), ("balls_remaining", I),
        ("runs_required", I), ("required_rate", F), ("current_rate", F),
    ]),
    "wickets": pa.schema([
        ("delivery_id", S), ("match_id", S), ("innings_no", I), ("wicket_idx", I),
        ("player_out_id", S), ("player_out", S), ("kind", S), ("bowler_credited", B),
        ("counts_as_dismissal", B), ("striker_out", B), ("source_id", S),
    ]),
    "wicket_fielders": pa.schema([
        ("delivery_id", S), ("match_id", S), ("innings_no", I), ("wicket_idx", I), ("fielder_idx", I),
        ("fielder_id", S), ("fielder", S), ("substitute", B), ("source_id", S),
    ]),
    "reviews": pa.schema([
        ("delivery_id", S), ("match_id", S), ("by_team", S), ("umpire", S), ("batter", S),
        ("decision", S), ("umpires_call", B), ("type", S),
    ]),
    "replacements": pa.schema([
        ("delivery_id", S), ("match_id", S), ("scope", S), ("team", S), ("player_in", S),
        ("player_out", S), ("reason", S), ("role", S),
    ]),
    "powerplays": pa.schema([
        ("match_id", S), ("innings_no", I), ("from_over", F), ("to_over", F), ("type", S),
    ]),
    "persons": pa.schema([
        ("person_id", S), ("name", S), ("unique_name", S), ("external_ids", pa.map_(S, S)),
        ("source_id", S),
    ]),
    # ---- Enrichment satellites: empty until a licensed/CV source exists. All nullable, all provenance-tagged.
    "delivery_tracking": pa.schema([
        ("delivery_id", S), ("release_x_m", F), ("release_y_m", F), ("release_z_m", F),
        ("speed_release_kph", F), ("speed_pitch_kph", F), ("pitch_x_m", F), ("pitch_y_m", F),
        ("line_bucket", S), ("length_bucket", S), ("bounce_height_m", F), ("swing_deg", F),
        ("seam_deg", F), ("spin_rpm", F), ("arrival_x_m", F), ("arrival_z_m", F),
        ("trajectory_ref", S), *PROV_COLS,
    ]),
    "delivery_shot": pa.schema([
        ("delivery_id", S), ("shot_type", S), ("shot_family", S), ("foot", S),
        ("direction_deg", F), ("distance_m", F), ("control", S), ("edge_type", S), *PROV_COLS,
    ]),
    "delivery_fielding": pa.schema([
        ("delivery_id", S), ("fielder_id", S), ("position_label", S), ("x_m", F), ("y_m", F),
        ("action", S), *PROV_COLS,
    ]),
    "delivery_contact": pa.schema([
        ("delivery_id", S), ("contact_zone", S), ("contact_x", F), ("contact_y", F), *PROV_COLS,
    ]),
}

ENRICHMENT_TABLES = ["delivery_tracking", "delivery_shot", "delivery_fielding", "delivery_contact"]

# Dismissal semantics (Laws of Cricket).
BOWLER_CREDITED = {"bowled", "caught", "caught and bowled", "lbw", "stumped", "hit wicket"}
NOT_DISMISSAL = {"retired hurt", "retired not out"}

FORMAT_GROUP = {"T20": "T20", "IT20": "T20", "ODI": "ODI", "ODM": "ODI", "Test": "Test", "MDM": "MDM"}
