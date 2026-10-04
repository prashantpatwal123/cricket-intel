"""Source-versioned metadata observations (Phase 6). Enrichment must never corrupt history.

Every value any source ever gave us is kept as an immutable observation:
  entity_id (Cricsheet register id) · field · source · source_ref (item / page) · source_version (revid / retrieval run)
  · retrieved_at · original (verbatim) · normalized (canonical) · mapping_confidence · licence · usable (licence permits
  product use?) · join (how the entity was matched, never by name alone) · content_hash
Observations are appended, never overwritten. `resolve()` picks the value CRICINTEL uses by a written policy and
returns the full answer to: what value, from which source, retrieved when, has the source changed since, and do
sources disagree.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

POLICY = ["manual_override", "wikidata", "derived"]   # precedence among USABLE sources; anything not usable is never chosen
LICENCES = {"wikidata": ("CC0 1.0", True), "wikipedia": ("CC BY-SA 4.0: licence review required before product use", False),
            "derived": ("derived from Cricsheet match data (licence unresolved)", True), "manual_override": ("CRICINTEL editorial", True)}


def _hash(obj) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, default=str).encode()).hexdigest()[:16]


class Store:
    def __init__(self, path: Path | None = None):
        self.path = path
        self.rows: list[dict] = []
        if path and path.exists():
            self.rows = [json.loads(x) for x in path.read_text().splitlines() if x.strip()]

    def add(self, entity_id: str, field: str, source: str, original, normalized, mapping_confidence: float, retrieved_at: str,
            source_ref: str | None = None, source_version: str | None = None, join: str = "", note: str = "") -> dict | None:
        lic, usable = LICENCES.get(source, ("UNKNOWN", False))
        row = {"entity_id": entity_id, "field": field, "source": source, "source_ref": source_ref, "source_version": source_version,
               "retrieved_at": retrieved_at, "original": original, "normalized": normalized, "mapping_confidence": mapping_confidence,
               "licence": lic, "usable": usable and normalized is not None and mapping_confidence >= 0.8, "join": join, "note": note}
        row["content_hash"] = _hash({k: row[k] for k in ("entity_id", "field", "source", "original", "normalized")})
        dup = any(r["content_hash"] == row["content_hash"] and r["source_version"] == row["source_version"] for r in self.rows)
        if dup:
            return None                                   # same value from the same source version: idempotent
        self.rows.append(row)
        if self.path:
            with self.path.open("a") as fh:
                fh.write(json.dumps(row, default=str) + "\n")
        return row

    def history(self, entity_id: str, field: str) -> list[dict]:
        return sorted([r for r in self.rows if r["entity_id"] == entity_id and r["field"] == field], key=lambda r: (r["source"], r["retrieved_at"]))

    def resolve(self, entity_id: str, field: str) -> dict:
        hist = self.history(entity_id, field)
        latest: dict[str, dict] = {}
        for r in hist:
            latest[r["source"]] = r                       # latest observation per source
        usable = [latest[s] for s in POLICY if s in latest and latest[s]["usable"]]
        chosen = usable[0] if usable else None
        changed = {}
        for s in latest:
            obs = [r for r in hist if r["source"] == s]
            changed[s] = len({r["content_hash"] for r in obs}) > 1
        values = {s: r["normalized"] for s, r in latest.items() if r["normalized"] is not None}
        return {"entity_id": entity_id, "field": field,
                "value": chosen["normalized"] if chosen else None,
                "used_source": chosen["source"] if chosen else None,
                "retrieved_at": chosen["retrieved_at"] if chosen else None,
                "source_version": chosen["source_version"] if chosen else None,
                "status": "resolved" if chosen else ("blocked_by_licence" if latest else "no_source"),
                "source_changed_since_first_seen": changed,
                "sources_disagree": len({json.dumps(v, sort_keys=True) for v in values.values()}) > 1,
                "candidates": [{k: r[k] for k in ("source", "original", "normalized", "mapping_confidence", "licence", "usable", "retrieved_at", "source_version")}
                               for r in latest.values()],
                "history_length": len(hist)}
