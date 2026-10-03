"""Enrichment adapters. Each returns (candidate rows, status report).

Rules for adding an adapter:
  * the source's licence must permit storage + derived use (record it in the report);
  * join only through identifiers from the Cricsheet Register (never by fuzzy name);
  * never scrape sites whose terms prohibit it (ESPNcricinfo, Cricbuzz, ...). Holding a key_cricinfo
    identifier lets us join to *licensed/open* datasets that use the same key — it does not let us
    fetch data from that site.
"""
from __future__ import annotations

import csv
import json
import urllib.parse
import urllib.request
from pathlib import Path

from ..config import METADATA


class SyntheticExternal:
    """Fictional 'external' source shipped with the synthetic fixture (exercises the pipeline)."""
    name = "synthetic_external_metadata"

    def __init__(self, raw: Path):
        self.path = raw / "synthetic" / "synthetic_external_metadata.csv"

    def fetch(self, ext_ids: dict[str, dict]):
        by_ref = {ids.get("synthetic_ref"): pid for pid, ids in ext_ids.items() if ids.get("synthetic_ref")}
        rows = []
        if not self.path.exists():
            return rows, {"adapter": self.name, "status": "file missing"}
        with open(self.path, newline="") as fh:
            for r in csv.DictReader(fh):
                pid = by_ref.get(r["synthetic_ref"])
                if not pid:
                    continue
                base = dict(person_id=pid, prov="OBSERVED", source_id="synthetic_fixture",
                            method=f"{self.name}/v1", confidence=0.99, is_override=False,
                            evidence=f"synthetic_ref={r['synthetic_ref']}")
                if r["batting_hand"]:
                    rows.append(dict(base, field="batting_hand", value=r["batting_hand"].lower()))
                if r["bowling_style"]:
                    rows.append(dict(base, field="bowling_style", value=r["bowling_style"]))
        return rows, {"adapter": self.name, "status": f"{len(rows)} candidate values for {len(by_ref)} linked players"}


class WikidataBranch:
    """Wikidata (CC0) values retrieved by the fetch-wikidata GitHub workflow (branch data/wikidata-cricketers),
    copied to data/raw/wikidata and re-verified against SHA256SUMS. Joined ONLY via Register cricinfo ids
    (Wikidata P2697). Property IDs were discovered empirically from Wikidata itself:
      P2545 'bowling style', P413 'position played on team / speciality'.
    Wikidata has no batting-hand property in use for cricketers, so batting hand is NOT provided here.
    """
    name = "wikidata_branch"
    DIR = RAW_WD = None
    STYLE = {  # wikidata label -> (canonical style label or None, family, arm, arm_confidence)
        "left-arm orthodox spin": ("Left-arm orthodox", "spin", "left", 0.95),
        "slow left-arm orthodox": ("Left-arm orthodox", "spin", "left", 0.95),
        "left-arm unorthodox spin": ("Left-arm wrist-spin", "spin", "left", 0.95),
        "leg break": ("Leg-spin", "spin", "right", 0.8), "leg spin": ("Leg-spin", "spin", "right", 0.8),
        "leg break googly": ("Leg-spin", "spin", "right", 0.8),
        "off break": ("Off-spin", "spin", "right", 0.8), "off spin": ("Off-spin", "spin", "right", 0.8),
        "spin bowling": (None, "spin", None, 0), "fast bowling": (None, "pace", None, 0),
        "seam bowling": (None, "pace", None, 0), "swing bowling": (None, "pace", None, 0),
        "medium pace": (None, "pace", None, 0), "fast-medium": (None, "pace", None, 0),
    }
    ROLE = {"batter": "batter", "batting": "batter", "batsman": "batter", "bowler": "bowler", "bowling": "bowler",
            "all-rounder": "all-rounder", "wicket-keeper": "wicketkeeper-batter", "wicketkeeper": "wicketkeeper-batter"}

    def __init__(self, raw: Path):
        self.dir = raw / "wikidata"

    def fetch(self, ext_ids: dict[str, dict]):
        import hashlib
        if not (self.dir / "values.json").exists():
            return [], {"adapter": self.name, "status": "no Wikidata snapshot (run fetch-wikidata workflow)"}
        for line in (self.dir / "SHA256SUMS").read_text().splitlines():
            h, n = line.split(maxsplit=1)
            if hashlib.sha256((self.dir / Path(n).name).read_bytes()).hexdigest() != h:
                raise SystemExit(f"Wikidata snapshot checksum mismatch: {n}")
        prov = json.loads((self.dir / "PROVENANCE.json").read_text())
        by_ci = {}
        for pid, ids in ext_ids.items():
            for k in ("cricinfo", "cricinfo_2", "cricinfo_3"):
                if ids.get(k):
                    by_ci[ids[k]] = pid
        per_player: dict[str, list] = {}
        for v in json.loads((self.dir / "values.json").read_text()):
            pid = by_ci.get(v["cricinfo_id"])
            if pid:
                per_player.setdefault(pid, []).append(v)
        rows, unmapped = [], {}
        base = lambda pid, ev: dict(person_id=pid, prov="OBSERVED", source_id="wikidata", method="wikidata_branch/v1",
                                    is_override=False, evidence=ev + f" retrieved {prov['retrieved_at_utc']}")
        for pid, vals in per_player.items():
            styles = [self.STYLE.get((v["value_label"] or "").lower()) for v in vals if v["pid"] == "P2545"]
            for v in vals:
                if v["pid"] == "P2545" and (v["value_label"] or "").lower() not in self.STYLE:
                    unmapped[v["value_label"]] = unmapped.get(v["value_label"], 0) + 1
            styles = [s for s in styles if s]
            fams = {s[1] for s in styles}
            ev = f"wikidata {vals[0]['item']} P2545={[v['value_label'] for v in vals if v['pid'] == 'P2545']}"
            if len(fams) == 1:
                rows.append(dict(base(pid, ev), field="bowling_family", value=fams.pop(), confidence=0.9))
                labelled = [s for s in styles if s[0]]
                if len({s[0] for s in labelled}) == 1:
                    s0 = labelled[0]
                    rows.append(dict(base(pid, ev), field="bowling_style", value=s0[0], confidence=0.9))
                    if s0[2]:
                        rows.append(dict(base(pid, ev), field="bowling_arm", value=s0[2], confidence=s0[3], prov="DERIVED"))
            roles = {self.ROLE.get((v["value_label"] or "").lower()) for v in vals if v["pid"] == "P413"} - {None}
            if len(roles) == 1:
                r = roles.pop()
                rows.append(dict(base(pid, f"wikidata P413"), field="role", value=r, confidence=0.85))
                if r == "wicketkeeper-batter":
                    rows.append(dict(base(pid, "wikidata P413=wicket-keeper"), field="wicketkeeper", value="yes", confidence=0.85))
        return rows, {"adapter": self.name, "status": f"{len(per_player)} Register players linked via cricinfo id; "
                      f"{len(rows)} values; unmapped style labels: {unmapped}", "retrieved_at": prov["retrieved_at_utc"]}


def for_dataset(dataset: str, raw: Path):
    if dataset == "synthetic":
        return [SyntheticExternal(raw)]
    return [WikidataBranch(raw)]
