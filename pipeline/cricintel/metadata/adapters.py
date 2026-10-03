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


class Wikidata:
    """Wikidata (CC0). Joined via the ESPNcricinfo player-id property using Register `cricinfo` keys.

    VERIFY before relying on it (network to wikidata.org is blocked in the build environment):
      * P2697 = "ESPNcricinfo player ID" (believed correct)
      * P741  = "playing hand" (values: right-handedness Q3039938 / left-handedness Q789447)
      * No bowling-style property is known to us; bowling style is NOT fetched from Wikidata.
    Results are cached at data/metadata/wikidata_cache.json so builds are reproducible offline.
    """
    name = "wikidata_playing_hand"
    ENDPOINT = "https://query.wikidata.org/sparql"
    HAND = {"Q3039938": "right", "Q789447": "left"}
    CACHE = METADATA / "wikidata_cache.json"

    def _query(self, ids: list[str]) -> list[dict]:
        out = []
        for i in range(0, len(ids), 400):
            vals = " ".join(f'"{x}"' for x in ids[i:i + 400])
            q = f"SELECT ?ci ?hand WHERE {{ VALUES ?ci {{ {vals} }} ?item wdt:P2697 ?ci . ?item wdt:P741 ?hand . }}"
            url = self.ENDPOINT + "?" + urllib.parse.urlencode({"query": q, "format": "json"})
            req = urllib.request.Request(url, headers={"User-Agent": "cricintel/0.1 (research prototype)"})
            data = json.loads(urllib.request.urlopen(req, timeout=60).read())
            for b in data["results"]["bindings"]:
                out.append({"ci": b["ci"]["value"], "hand": b["hand"]["value"].rsplit("/", 1)[-1]})
        return out

    def fetch(self, ext_ids: dict[str, dict]):
        by_ci = {ids["cricinfo"]: pid for pid, ids in ext_ids.items() if ids.get("cricinfo")}
        if not by_ci:
            return [], {"adapter": self.name, "status": "no cricinfo identifiers in Register — skipped"}
        try:
            res = self._query(sorted(by_ci))
            self.CACHE.parent.mkdir(parents=True, exist_ok=True)
            self.CACHE.write_text(json.dumps(res))
            status = "live query"
        except Exception as e:  # noqa: BLE001
            if not self.CACHE.exists():
                return [], {"adapter": self.name, "status": f"unavailable ({type(e).__name__}); no cache"}
            res, status = json.loads(self.CACHE.read_text()), f"cache (live failed: {type(e).__name__})"
        rows = []
        for r in res:
            hand = self.HAND.get(r["hand"])
            if hand and r["ci"] in by_ci:
                rows.append(dict(person_id=by_ci[r["ci"]], field="batting_hand", value=hand, prov="OBSERVED",
                                 source_id="wikidata", method=f"{self.name}/v1", confidence=0.9,
                                 is_override=False, evidence=f"wikidata P2697={r['ci']} P741={r['hand']}"))
        return rows, {"adapter": self.name, "status": f"{status}: {len(rows)} values"}


def for_dataset(dataset: str, raw: Path):
    if dataset == "synthetic":
        return [SyntheticExternal(raw)]
    return [Wikidata()]
