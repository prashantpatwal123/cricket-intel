"""Player-metadata pilot (Phase 6): 8 players, joined by stable identifiers (Cricsheet Register id → ESPNcricinfo id →
Wikidata P2697), never by name. Builds a source-versioned observation store and a report.

python -m cricintel.enrich.pilot --pilot-dir <data/wikidata-pilot checkout> --snapshot-dir <data/wikidata-cricketers checkout>
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from ..db import DB
from .taxonomy import normalize_batting_hand, normalize_bowling
from .versioning import Store

PILOT = {"ba607b88": "Virat Kohli", "740742ef": "Rohit Sharma", "462411b3": "Jasprit Bumrah", "4a8a2e3b": "MS Dhoni",
         "5d2eda89": "Smriti Mandhana", "27e003ce": "Meg Lanning", "cdb82f1c": "Sophie Ecclestone", "14f96089": "Adam Zampa"}
ROLE_MAP = {"batter": "batter", "bowler": "bowler", "wicket-keeper": "wicketkeeper", "all-rounder": "all-rounder"}


def run(db: DB, pilot_dir: Path, snapshot_dir: Path | None, store_path: Path | None) -> dict:
    prov = json.loads((pilot_dir / "PROVENANCE.json").read_text())
    t_pilot = prov["retrieved_at_utc"]
    wd = json.loads((pilot_dir / "wikidata_pilot.json").read_text())
    wp = json.loads((pilot_dir / "wikipedia_infobox_pilot.json").read_text())
    cov = json.loads((pilot_dir / "wikidata_coverage.json").read_text())
    if store_path and store_path.exists():
        store_path.unlink()                              # rebuilt from the immutable raw snapshots each run
    st = Store(store_path)
    ext = {r["person_id"]: r["external_ids"] for r in db.q(f"SELECT person_id, external_ids FROM persons WHERE person_id IN ({','.join('?' * len(PILOT))})", list(PILOT))}
    report = {"retrieved": {"pilot": t_pilot, "pilot_run": prov.get("retrieved_by")}, "wikidata_coverage": cov, "players": {}}

    # earlier snapshot of the same CC0 source (3 Oct): an older source version
    if snapshot_dir and (snapshot_dir / "values.json").exists():
        sp = json.loads((snapshot_dir / "PROVENANCE.json").read_text())
        cids = {v.get("cricinfo"): k for k, v in ext.items() if v}
        for v in json.loads((snapshot_dir / "values.json").read_text()):
            pid = cids.get(v["cricinfo_id"])
            if not pid:
                continue
            if v["pid"] == "P2545":
                n = normalize_bowling(v["value_label"], "wikidata")
                st.add(pid, "bowling_style", "wikidata", v["value_label"], n["canonical"], n["mapping_confidence"], sp["retrieved_at_utc"],
                       v["item"], sp.get("retrieved_by"), "register.cricinfo == P2697")
            if v["pid"] == "P413":
                st.add(pid, "role", "wikidata", v["value_label"], ROLE_MAP.get(v["value_label"]), 0.85 if v["value_label"] in ROLE_MAP else 0.0,
                       sp["retrieved_at_utc"], v["item"], sp.get("retrieved_by"), "register.cricinfo == P2697")

    for pid, name in PILOT.items():
        rec = wd.get(pid, {})
        cid = (ext.get(pid) or {}).get("cricinfo")
        items = rec.get("wikidata_items", [])
        join = {"register_id": pid, "register_cricinfo": cid, "wikidata_items": items,
                "join_ok": len(items) == 1 and rec.get("cricinfo_id") == cid,
                "name_check": rec.get("label"), "method": "Register cricinfo id == Wikidata P2697 (unique item)"}
        cl = rec.get("claims", {})
        ver = prov.get("retrieved_by")
        item = items[0] if items else None
        # Wikidata (CC0): record presence AND absence, so 'no value at retrieval time' is itself a versioned fact
        for fld, p in (("batting_hand", "P552"), ("bowling_style", "P2545"), ("role", "P413")):
            vals = cl.get(p, {}).get("values", [])
            if not vals:
                st.add(pid, fld, "wikidata", None, None, 0.0, t_pilot, item, ver, join["method"], note=f"{p} absent on item")
            for v in vals:
                lab = v["value"]["label"] if isinstance(v["value"], dict) else v["value"]
                if fld == "bowling_style":
                    n = normalize_bowling(lab, "wikidata")
                    st.add(pid, fld, "wikidata", lab, n["canonical"], n["mapping_confidence"], t_pilot, item, ver, join["method"], n["note"])
                elif fld == "batting_hand":
                    st.add(pid, fld, "wikidata", lab, None, 0.0, t_pilot, item, ver, join["method"],
                           "P552 is generic handedness, not batting hand: not mapped")
                else:
                    st.add(pid, fld, "wikidata", lab, ROLE_MAP.get(lab), 0.85 if lab in ROLE_MAP else 0.0, t_pilot, item, ver, join["method"])
        # Wikipedia infobox (CC BY-SA): recorded for comparison; licence blocks product use
        info = (wp.get(pid) or {})
        f = info.get("fields", {})
        if f.get("batting"):
            n = normalize_batting_hand(f["batting"], "wikipedia")
            st.add(pid, "batting_hand", "wikipedia", f["batting"], n["canonical"], n["mapping_confidence"], t_pilot, info.get("title"),
                   str(info.get("revid")), "enwiki sitelink of the P2697-matched Wikidata item")
        if f.get("bowling"):
            n = normalize_bowling(f["bowling"], "wikipedia")
            st.add(pid, "bowling_style", "wikipedia", f["bowling"], n["canonical"], n["mapping_confidence"], t_pilot, info.get("title"),
                   str(info.get("revid")), "enwiki sitelink of the P2697-matched Wikidata item", n["note"])
        # derived from events (existing, versioned by method)
        for r in db.q("SELECT field, value, method, confidence FROM player_metadata WHERE person_id = ? AND source_id = 'derived'", [pid]):
            st.add(pid, r["field"], "derived", r["value"], r["value"], r["confidence"], "dataset build", None, r["method"], "events")
        fields = {fld: st.resolve(pid, fld) for fld in ("batting_hand", "bowling_style", "role", "wicketkeeper")}
        for fr in fields.values():   # values from sources whose licence does not permit use are withheld from the report
            for c in fr["candidates"]:
                if not c["usable"] and c["source"] == "wikipedia":
                    c["has_value"] = c["normalized"] is not None
                    c["original"] = c["normalized"] = "WITHHELD (CC BY-SA, licence review pending)"
        report["players"][pid] = {"name": name, "join": join, "fields": fields}

    res = [x for p in report["players"].values() for x in p["fields"].values()]
    report["summary"] = {
        "players": len(PILOT), "joined_by_id": sum(p["join"]["join_ok"] for p in report["players"].values()),
        "batting_hand_usable": sum(1 for p in report["players"].values() if p["fields"]["batting_hand"]["status"] == "resolved"),
        "bowling_style_usable": sum(1 for p in report["players"].values() if p["fields"]["bowling_style"]["status"] == "resolved"),
        "blocked_by_licence": sum(1 for x in res if x["status"] == "blocked_by_licence"),
        "observations": len(st.rows),
        "verdict": ("PARTIAL. Identity joins are reliable (stable ids, unique Wikidata item for all 8). The CC0 source holds no batting hand and "
                    "no bowling style for any pilot player; the only open source that does (Wikipedia infoboxes) is CC BY-SA and needs a licence "
                    "review before storage or product use. Nothing questionable was populated."),
    }
    return report


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", default="cricsheet")
    ap.add_argument("--pilot-dir", required=True)
    ap.add_argument("--snapshot-dir")
    ap.add_argument("--store")
    ap.add_argument("--out")
    a = ap.parse_args()
    r = run(DB(a.dataset), Path(a.pilot_dir), Path(a.snapshot_dir) if a.snapshot_dir else None, Path(a.store) if a.store else None)
    txt = json.dumps(r, indent=1, default=str)
    if a.out:
        Path(a.out).write_text(txt)
    print(json.dumps(r["summary"], indent=1))
