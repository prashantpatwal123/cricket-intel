"""Machine-readable provenance (Phase 6). Every enriched field and every visual element can carry one Provenance record.

Types (formalised from Phases 2–5):
  OBSERVED       directly present in a source record.            requires: source, source_field
  DERIVED        deterministic rule over observed data.          requires: method (and the inputs' source)
  RECONSTRUCTED  estimated from sufficient observed inputs.      requires: method, confidence
  MODELLED       statistical / model output.                     requires: method, model_version, confidence
  ILLUSTRATIVE   generic cricket illustration, not a reconstruction of anything that happened.
                 requires: method; FORBIDS source_event_id and subject ids (must not be tied to a real delivery/player)
`explain()` answers "Why am I seeing this?" in plain text; `as_dict()` is the wire format used by the API and the web
`Provenance` type (web/lib/visual.ts).
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field

TYPES = ("OBSERVED", "DERIVED", "RECONSTRUCTED", "MODELLED", "ILLUSTRATIVE")
PLAIN = {
    "OBSERVED": "Recorded directly in the source.",
    "DERIVED": "Calculated by a fixed rule from recorded data.",
    "RECONSTRUCTED": "Estimated from recorded inputs that are sufficient for it; not itself recorded.",
    "MODELLED": "A statistical estimate, not a fact.",
    "ILLUSTRATIVE": "A generic illustration of a cricket idea. It does not show anything that actually happened.",
}


@dataclass(frozen=True)
class Provenance:
    provenance_type: str
    source: str | None = None             # e.g. "cricsheet", "wikidata", "derived"
    source_field: str | None = None       # e.g. "wickets[].kind", "P2545"
    source_event_id: str | None = None    # e.g. a delivery id; never on ILLUSTRATIVE
    confidence: float | None = None       # 0..1 where meaningful
    method: str | None = None             # rule / model / mapping name with version
    model_version: str | None = None
    retrieved_at: str | None = None       # ISO time the source was read
    licence: str | None = None
    subject_ids: tuple = field(default_factory=tuple)   # real player ids the element refers to; never on ILLUSTRATIVE

    def __post_init__(self):
        t = self.provenance_type
        if t not in TYPES:
            raise ValueError(f"unknown provenance type {t}")
        need = {"OBSERVED": ("source", "source_field"), "DERIVED": ("method",), "RECONSTRUCTED": ("method", "confidence"),
                "MODELLED": ("method", "model_version", "confidence"), "ILLUSTRATIVE": ("method",)}[t]
        missing = [k for k in need if getattr(self, k) in (None, "")]
        if missing:
            raise ValueError(f"{t} provenance requires {missing}")
        if t == "ILLUSTRATIVE" and (self.source_event_id or self.subject_ids):
            raise ValueError("ILLUSTRATIVE content must not be attached to a real delivery or player")
        if self.confidence is not None and not 0 <= self.confidence <= 1:
            raise ValueError("confidence must be in [0, 1]")

    def explain(self) -> str:
        bits = [PLAIN[self.provenance_type]]
        if self.source:
            bits.append(f"Source: {self.source}" + (f" ({self.source_field})" if self.source_field else "") + ".")
        if self.method:
            bits.append(f"Method: {self.method}" + (f", model {self.model_version}" if self.model_version else "") + ".")
        if self.confidence is not None:
            bits.append(f"Confidence {round(self.confidence, 2)}.")
        if self.retrieved_at:
            bits.append(f"Retrieved {self.retrieved_at}.")
        if self.licence:
            bits.append(f"Licence: {self.licence}.")
        return " ".join(bits)

    def as_dict(self) -> dict:
        d = {k: v for k, v in asdict(self).items() if v not in (None, (), [])}
        d["subject_ids"] = list(self.subject_ids) if self.subject_ids else []
        d["why"] = self.explain()
        return d


def observed(source: str, source_field: str, event_id: str | None = None, **kw) -> Provenance:
    return Provenance("OBSERVED", source=source, source_field=source_field, source_event_id=event_id, **kw)


def derived(method: str, **kw) -> Provenance:
    return Provenance("DERIVED", method=method, **kw)


def illustrative(method: str) -> Provenance:
    return Provenance("ILLUSTRATIVE", method=method)
