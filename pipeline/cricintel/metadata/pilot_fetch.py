"""Phase 6 metadata pilot fetch. Runs on a GitHub-hosted runner (stdlib only); this sandbox cannot reach these hosts.

For the 8 pilot players, joined by the ESPNcricinfo id carried in the Cricsheet Register (never by name):
  1. Wikidata (CC0): every claim on the matching item (P2697 = cricinfo id), with value labels.
  2. Wikidata coverage across ALL items carrying P2697: how many have P552 (handedness), P2545 (bowling style), P413 (position);
     plus every P552 value (for a possible scaled enrichment).
  3. English Wikipedia infobox `batting` / `bowling` lines (CC BY-SA 4.0) for the same items via their enwiki sitelink.
     COMPARISON ONLY: share-alike licence; not stored in the product.
Writes out/pilot/{wikidata_pilot.json, wikidata_coverage.json, wikidata_p552.json, wikipedia_infobox_pilot.json, PROVENANCE.json}.
"""
import datetime as dt
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request

UA = "cricintel-metadata-pilot/1.0 (https://github.com/%s; research prototype)" % os.environ.get("GITHUB_REPOSITORY", "local")
SPARQL = "https://query.wikidata.org/sparql"
WD_API = "https://www.wikidata.org/w/api.php"
WP_API = "https://en.wikipedia.org/w/api.php"
PILOT = {  # Cricsheet register id -> ESPNcricinfo id (from the Register's identifiers)
    "ba607b88": "253802", "740742ef": "34102", "462411b3": "625383", "4a8a2e3b": "28081",
    "5d2eda89": "597806", "27e003ce": "329336", "cdb82f1c": "878039", "14f96089": "379504",
}


def get(url, params, accept="application/json", tries=4):
    for i in range(tries):
        try:
            req = urllib.request.Request(url + "?" + urllib.parse.urlencode(params), headers={"User-Agent": UA, "Accept": accept})
            with urllib.request.urlopen(req, timeout=120) as r:
                return json.loads(r.read())
        except Exception as e:  # noqa: BLE001
            print("retry", i, url, e, file=sys.stderr)
            time.sleep(8 * (i + 1))
    raise SystemExit("failed: " + url)


def sparql(q):
    return get(SPARQL, {"query": q, "format": "json"}, "application/sparql-results+json")["results"]["bindings"]


def main():
    out = "out/pilot"
    os.makedirs(out, exist_ok=True)
    now = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    vals = " ".join(f'"{c}"' for c in PILOT.values())
    rows = sparql(f"SELECT ?item ?cid WHERE {{ VALUES ?cid {{ {vals} }} ?item wdt:P2697 ?cid . }}")
    by_cid = {}
    for r in rows:
        by_cid.setdefault(r["cid"]["value"], []).append(r["item"]["value"].rsplit("/", 1)[1])
    qids = sorted({q for v in by_cid.values() for q in v})
    ents = get(WD_API, {"action": "wbgetentities", "ids": "|".join(qids), "props": "claims|labels|sitelinks", "languages": "en",
                        "sitefilter": "enwiki", "format": "json"})["entities"] if qids else {}
    ref = sorted({c["mainsnak"]["datavalue"]["value"]["id"] for e in ents.values() for cl in e.get("claims", {}).values() for c in cl
                  if c["mainsnak"].get("datavalue", {}).get("type") == "wikibase-entityid"})
    labels = {}
    for i in range(0, len(ref), 50):
        part = get(WD_API, {"action": "wbgetentities", "ids": "|".join(ref[i:i + 50]), "props": "labels", "languages": "en", "format": "json"})["entities"]
        labels.update({k: v.get("labels", {}).get("en", {}).get("value") for k, v in part.items()})
    plabels = {}
    pids = sorted({p for e in ents.values() for p in e.get("claims", {})})
    for i in range(0, len(pids), 50):
        part = get(WD_API, {"action": "wbgetentities", "ids": "|".join(pids[i:i + 50]), "props": "labels", "languages": "en", "format": "json"})["entities"]
        plabels.update({k: v.get("labels", {}).get("en", {}).get("value") for k, v in part.items()})
    pilot = {}
    for reg, cid in PILOT.items():
        items = by_cid.get(cid, [])
        rec = {"register_id": reg, "cricinfo_id": cid, "wikidata_items": items, "claims": {}, "enwiki": None}
        for q in items:
            e = ents.get(q, {})
            rec["label"] = e.get("labels", {}).get("en", {}).get("value")
            rec["enwiki"] = e.get("sitelinks", {}).get("enwiki", {}).get("title")
            for p in ("P552", "P2545", "P413", "P106", "P21", "P569", "P27", "P2697"):
                for c in e.get("claims", {}).get(p, []):
                    dv = c["mainsnak"].get("datavalue", {})
                    v = dv.get("value")
                    if isinstance(v, dict) and "id" in v:
                        v = {"qid": v["id"], "label": labels.get(v["id"])}
                    elif isinstance(v, dict) and "time" in v:
                        v = v["time"]
                    rec["claims"].setdefault(p, {"property_label": plabels.get(p), "values": []})["values"].append(
                        {"value": v, "rank": c.get("rank"), "references": len(c.get("references", []))})
            rec["all_properties"] = sorted(e.get("claims", {}))
        pilot[reg] = rec
    json.dump(pilot, open(f"{out}/wikidata_pilot.json", "w"), indent=1, ensure_ascii=False)

    cov = {}
    for p in ("P552", "P2545", "P413"):
        cov[p] = int(sparql(f"SELECT (COUNT(DISTINCT ?i) AS ?n) WHERE {{ ?i wdt:P2697 ?c ; wdt:{p} ?v . }}")[0]["n"]["value"])
    cov["P2697_total"] = int(sparql("SELECT (COUNT(DISTINCT ?i) AS ?n) WHERE { ?i wdt:P2697 ?c . }")[0]["n"]["value"])
    dist = sparql("""SELECT ?v ?vLabel (COUNT(DISTINCT ?i) AS ?n) WHERE { ?i wdt:P2697 ?c ; wdt:P552 ?v .
                     SERVICE wikibase:label { bd:serviceParam wikibase:language "en". } } GROUP BY ?v ?vLabel ORDER BY DESC(?n)""")
    cov["P552_values"] = [{"qid": r["v"]["value"].rsplit("/", 1)[1], "label": r.get("vLabel", {}).get("value"), "n": int(r["n"]["value"])} for r in dist]
    json.dump(cov, open(f"{out}/wikidata_coverage.json", "w"), indent=1)
    hand = sparql("""SELECT ?i ?c ?v WHERE { ?i wdt:P2697 ?c ; wdt:P552 ?v . }""")
    json.dump([{"item": r["i"]["value"].rsplit("/", 1)[1], "cricinfo_id": r["c"]["value"], "value": r["v"]["value"].rsplit("/", 1)[1]} for r in hand],
              open(f"{out}/wikidata_p552.json", "w"))

    info = {}
    for reg, rec in pilot.items():
        t = rec.get("enwiki")
        if not t:
            info[reg] = {"title": None}
            continue
        w = get(WP_API, {"action": "parse", "page": t, "prop": "wikitext|revid", "section": 0, "format": "json", "formatversion": 2})
        txt = w.get("parse", {}).get("wikitext", "")
        f = {}
        for k in ("batting", "bowling", "role", "club1"):
            m = re.search(r"^\s*\|\s*" + k + r"\s*=\s*(.+)$", txt, re.M)
            if m:
                f[k] = m.group(1).strip()
        info[reg] = {"title": t, "revid": w.get("parse", {}).get("revid"), "fields": f}
    json.dump(info, open(f"{out}/wikipedia_infobox_pilot.json", "w"), indent=1, ensure_ascii=False)
    json.dump({"retrieved_at_utc": now, "retrieved_by": os.environ.get("RUN_URL"),
               "sources": {"wikidata": {"endpoints": [SPARQL, WD_API], "licence": "CC0 1.0"},
                           "wikipedia": {"endpoint": WP_API, "licence": "CC BY-SA 4.0 (text); comparison only, not stored in product"}},
               "join_key": "Cricsheet Register cricinfo identifier == Wikidata P2697"},
              open(f"{out}/PROVENANCE.json", "w"), indent=1)


if __name__ == "__main__":
    main()
