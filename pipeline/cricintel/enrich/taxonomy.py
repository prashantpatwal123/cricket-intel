"""Canonical cricket taxonomies (Phase 6), independent of any vendor.

Principles
  * The source's own wording is always kept next to the canonical value (`original`).
  * A label maps only as far as it actually says: "fast bowling" → family pace, arm UNKNOWN. Never filled in by guesswork.
  * Line and length buckets exist so licensed data can be mapped into one vocabulary. CRICINTEL never computes them from
    outcomes, dismissals or commentary; with Cricsheet only, every line/length value is absent.
  * Shot labels map to the deepest node the source supports ("drive" → drive, not cover drive).
"""
from __future__ import annotations

import re

# ------------------------------------------------------------------ bowling style
BOWLING = {
    # code: (label, arm, family, subtype)
    "RF": ("right-arm fast", "right", "pace", "fast"),
    "RFM": ("right-arm fast-medium", "right", "pace", "fast-medium"),
    "RMF": ("right-arm medium-fast", "right", "pace", "medium-fast"),
    "RM": ("right-arm medium", "right", "pace", "medium"),
    "LF": ("left-arm fast", "left", "pace", "fast"),
    "LFM": ("left-arm fast-medium", "left", "pace", "fast-medium"),
    "LMF": ("left-arm medium-fast", "left", "pace", "medium-fast"),
    "LM": ("left-arm medium", "left", "pace", "medium"),
    "ROB": ("off break (right-arm finger spin)", "right", "spin", "finger"),
    "RLB": ("leg break (right-arm wrist spin)", "right", "spin", "wrist"),
    "LO": ("left-arm orthodox (finger spin)", "left", "spin", "finger"),
    "LWS": ("left-arm wrist spin", "left", "spin", "wrist"),
    # partial nodes: what a coarse label can honestly say
    "PACE": ("pace, arm and speed band unknown", None, "pace", None),
    "PACE_FAST": ("fast, arm unknown", None, "pace", "fast"),
    "SPIN": ("spin, type unknown", None, "spin", None),
    "R_UNKNOWN": ("right-arm, type unknown", "right", None, None),
    "L_UNKNOWN": ("left-arm, type unknown", "left", None, None),
}

_RULES = [  # (regex on cleaned lower-case text, code, mapping confidence, note)
    (r"(slow )?left[- ]arm (orthodox|finger)", "LO", 0.95, ""),
    (r"left[- ]arm (unorthodox|wrist|chinaman)", "LWS", 0.95, ""),
    (r"right[- ]arm (off[- ]?(break|spin))|^off[- ]?break$", "ROB", 0.95, ""),
    (r"^off[- ]?spin$", "ROB", 0.85, "'off spin' conventionally means right-arm finger spin; left-arm finger spin is 'left-arm orthodox'"),
    (r"right[- ]arm leg[- ]?(break|spin)|^leg[- ]?break$", "RLB", 0.9, "'leg break' is by convention right-arm wrist spin"),
    (r"^leg[- ]?spin$", "RLB", 0.8, "'leg spin' conventionally right-arm wrist spin"),
    (r"right[- ]arm fast[- ]medium", "RFM", 0.95, ""), (r"right[- ]arm medium[- ]fast", "RMF", 0.95, ""),
    (r"right[- ]arm fast", "RF", 0.95, ""), (r"right[- ]arm medium", "RM", 0.95, ""),
    (r"left[- ]arm fast[- ]medium", "LFM", 0.95, ""), (r"left[- ]arm medium[- ]fast", "LMF", 0.95, ""),
    (r"left[- ]arm fast", "LF", 0.95, ""), (r"left[- ]arm medium", "LM", 0.95, ""),
    (r"^fast bowling$|^fast$", "PACE_FAST", 0.9, "arm not stated"),
    (r"^(seam|pace|swing|medium)( bowling)?$", "PACE", 0.9, "arm and speed band not stated"),
    (r"^spin( bowling)?$", "SPIN", 0.9, "spin type not stated"),
    (r"^right[- ]arm$", "R_UNKNOWN", 0.9, "bowling type not stated"),
    (r"^left[- ]arm$", "L_UNKNOWN", 0.9, "bowling type not stated"),
]


def clean_label(text: str) -> str:
    """Strip wiki markup ([[a|b]] → b, {{…}} notes, <ref>s) and normalise spacing; keep the words."""
    t = re.sub(r"<ref[^>]*>.*?</ref>|<ref[^/]*/>", "", text or "", flags=re.S)
    t = re.sub(r"\{\{.*?\}\}", "", t, flags=re.S)
    t = re.sub(r"\[\[([^\]|]*\|)?([^\]]*)\]\]", r"\2", t)
    return re.sub(r"\s+", " ", t).strip()


def source_notes(text: str | None) -> str:
    """Footnotes a source attaches to the value (e.g. '{{efn|Some sources list X as fast-medium}}'): kept, not discarded."""
    m = re.findall(r"\{\{efn\|(?:name=[^|]*\|)?([^<{}|]+)", text or "")
    return " ".join(x.strip() for x in m)


def normalize_bowling(label: str | None, source: str) -> dict:
    original = label
    t = clean_label(label or "").lower().replace("–", "-")
    sn = source_notes(label)
    for pat, code, conf, note in _RULES:
        if re.search(pat, t):
            lab, arm, fam, sub = BOWLING[code]
            return {"canonical": code, "label": lab, "arm": arm, "family": fam, "subtype": sub, "original": original,
                    "cleaned": t, "source": source, "mapping_confidence": conf, "note": "; ".join(x for x in (note, f"source note: {sn}" if sn else "") if x), "mapped": True}
    return {"canonical": None, "label": None, "arm": None, "family": None, "subtype": None, "original": original, "cleaned": t,
            "source": source, "mapping_confidence": 0.0, "note": "unmapped label: left unknown", "mapped": False}


def normalize_batting_hand(label: str | None, source: str) -> dict:
    t = clean_label(label or "").lower()
    v = "right" if re.search(r"^right[- ]hand(ed)?( bat)?", t) else "left" if re.search(r"^left[- ]hand(ed)?( bat)?", t) else None
    return {"canonical": v, "original": label, "source": source, "mapping_confidence": 0.95 if v else 0.0, "mapped": v is not None}


# ------------------------------------------------------------------ line / length (batter-relative; vendor buckets map in)
LINE = [
    ("wide_outside_off", "Wide outside off"), ("outside_off", "Outside off stump"), ("off_stump", "Off stump"),
    ("middle", "Middle stump"), ("leg_stump", "Leg stump"), ("down_leg", "Down the leg side"),
]
LENGTH = [
    ("full_toss", "Full toss"), ("yorker", "Yorker"), ("full", "Full"), ("good_length", "Good length"),
    ("back_of_length", "Back of a length"), ("short", "Short"), ("bouncer", "Bouncer"),
]
LINE_LENGTH_RULE = ("Buckets are batter-relative (off side flips for a left-hander). Boundaries between buckets are vendor-defined: "
                    "CRICINTEL stores the source label and maps it; it never infers line or length from outcomes, dismissals or commentary.")

# ------------------------------------------------------------------ shots (hierarchy: family → shot)
SHOTS = {
    "no_shot": {"label": "No shot", "children": {"leave": "Leave", "padded_away": "Padded away"}},
    "defensive": {"label": "Defensive", "children": {"forward_defence": "Forward defence", "back_defence": "Back-foot defence"}},
    "drive": {"label": "Drive", "children": {"cover_drive": "Cover drive", "straight_drive": "Straight drive", "on_drive": "On drive",
                                               "off_drive": "Off drive", "square_drive": "Square drive", "lofted_drive": "Lofted drive"}},
    "cut": {"label": "Cut", "children": {"square_cut": "Square cut", "late_cut": "Late cut", "upper_cut": "Upper cut"}},
    "pull_hook": {"label": "Pull / hook", "children": {"pull": "Pull", "hook": "Hook"}},
    "sweep": {"label": "Sweep", "children": {"sweep": "Sweep", "slog_sweep": "Slog sweep", "reverse_sweep": "Reverse sweep", "paddle": "Paddle"}},
    "leg_side_touch": {"label": "Leg-side touch", "children": {"flick": "Flick", "glance": "Glance"}},
    "improvised": {"label": "Improvised", "children": {"ramp": "Ramp", "scoop": "Scoop", "switch_hit": "Switch hit"}},
    "slog": {"label": "Slog", "children": {}},
}
SHOT_MODIFIERS = {"charge": "Use of feet / charge", "lofted": "Lofted (in the air by intent)", "attacking": "Attacking", "defensive_intent": "Defensive"}


def shot_node(code: str) -> dict | None:
    for fam, v in SHOTS.items():
        if code == fam:
            return {"code": fam, "label": v["label"], "family": fam, "level": "family"}
        if code in v["children"]:
            return {"code": code, "label": v["children"][code], "family": fam, "level": "shot"}
    return None


def map_shot(source_label: str, source_map: dict[str, str], source: str) -> dict:
    """source_map is a reviewed, per-source table label → canonical code. Unknown labels are kept and left unmapped."""
    code = source_map.get((source_label or "").strip().lower())
    node = shot_node(code) if code else None
    return {"original": source_label, "source": source, "canonical": node["code"] if node else None,
            "level": node["level"] if node else None, "family": node["family"] if node else None, "mapped": node is not None}


def taxonomy_doc() -> dict:
    return {"bowling": {k: {"label": v[0], "arm": v[1], "family": v[2], "subtype": v[3]} for k, v in BOWLING.items()},
            "line": LINE, "length": LENGTH, "line_length_rule": LINE_LENGTH_RULE,
            "shots": SHOTS, "shot_modifiers": SHOT_MODIFIERS}
