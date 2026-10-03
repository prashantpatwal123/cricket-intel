"""Normalise free-text bowling-style strings into a controlled vocabulary.

Unrecognised strings return None (we never guess a classification)."""
import re

_SPIN = {
    "offbreak": ("Off-spin", "finger spin"), "off break": ("Off-spin", "finger spin"),
    "off spin": ("Off-spin", "finger spin"), "legbreak googly": ("Leg-spin", "wrist spin"),
    "legbreak": ("Leg-spin", "wrist spin"), "leg break": ("Leg-spin", "wrist spin"),
    "leg spin": ("Leg-spin", "wrist spin"), "slow left-arm orthodox": ("Left-arm orthodox", "finger spin"),
    "slow left arm orthodox": ("Left-arm orthodox", "finger spin"),
    "left-arm wrist-spin": ("Left-arm wrist-spin", "wrist spin"), "slow left-arm chinaman": ("Left-arm wrist-spin", "wrist spin"),
    "left-arm chinaman": ("Left-arm wrist-spin", "wrist spin"),
}
_PACE = ["fast-medium", "medium-fast", "fast", "medium", "slow-medium"]


def normalise_bowling_style(raw: str) -> dict | None:
    s = re.sub(r"\s+", " ", raw.strip().lower())
    if not s:
        return None
    for key, (label, sub) in _SPIN.items():
        if key in s:
            arm = "left" if ("left" in s or label.startswith("Left")) else "right"
            return {"label": label, "arm": arm, "family": "spin", "subtype": sub}
    arm = "left" if s.startswith("left") else ("right" if s.startswith("right") else None)
    for p in _PACE:
        if p in s:
            pretty = {"fast-medium": "fast-medium", "medium-fast": "medium-fast"}.get(p, p)
            if arm is None:
                return None
            return {"label": f"{arm.capitalize()}-arm {pretty}", "arm": arm, "family": "pace", "subtype": pretty}
    return None
