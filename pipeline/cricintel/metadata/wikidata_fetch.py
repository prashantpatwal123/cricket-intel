"""Runs on a GitHub-hosted runner (stdlib only). Queries Wikidata (CC0) for cricketers that carry an
ESPNcricinfo player ID (P2697, confirmed) and:
  1. DISCOVERS which properties those items use whose English label mentions hand / bowl / position
     (so property IDs are verified empirically from the primary source, not assumed);
  2. fetches every (cricinfo_id, property, value QID, value label) for those properties.
Writes out/wikidata/{properties.json, values.json, PROVENANCE.json}.
"""
import datetime as dt
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request

EP = "https://query.wikidata.org/sparql"
UA = "cricintel-metadata/1.0 (https://github.com/%s; research prototype)" % os.environ.get("GITHUB_REPOSITORY", "local")


def sparql(q, tries=4):
    for i in range(tries):
        try:
            req = urllib.request.Request(EP + "?" + urllib.parse.urlencode({"query": q, "format": "json"}),
                                         headers={"User-Agent": UA, "Accept": "application/sparql-results+json"})
            return json.loads(urllib.request.urlopen(req, timeout=120).read())["results"]["bindings"]
        except Exception as e:  # noqa: BLE001
            print("retry", i, e, file=sys.stderr)
            time.sleep(10 * (i + 1))
    raise SystemExit("SPARQL failed: " + q[:200])


API = "https://www.wikidata.org/w/api.php"


def wbget(ids, props="claims|labels"):
    out = {}
    for i in range(0, len(ids), 50):
        q = urllib.parse.urlencode({"action": "wbgetentities", "ids": "|".join(ids[i:i + 50]), "props": props,
                                    "languages": "en", "format": "json"})
        req = urllib.request.Request(API + "?" + q, headers={"User-Agent": UA})
        out.update(json.loads(urllib.request.urlopen(req, timeout=120).read())["entities"])
        time.sleep(1)
    return out


def main(out="out/wikidata"):
    os.makedirs(out, exist_ok=True)
    # 1. discovery (light): sample cricketer items, read their claims via the entity API, label the properties
    sample = [b["item"]["value"].rsplit("/", 1)[-1] for b in sparql(
        "SELECT ?item WHERE { ?item wdt:P2697 ?ci . } LIMIT 300")]
    ents = wbget(sample, "claims")
    counts = {}
    for e in ents.values():
        for pid in e.get("claims", {}):
            counts[pid] = counts.get(pid, 0) + 1
    plabels = wbget(sorted(counts), "labels")
    props = sorted(({"pid": pid, "label": plabels.get(pid, {}).get("labels", {}).get("en", {}).get("value", ""),
                     "n_in_sample": n} for pid, n in counts.items()), key=lambda x: -x["n_in_sample"])
    chosen = [p for p in props if re.search(r"hand|bowl|position|specialit", p["label"], re.I)]
    json.dump({"sample_items": len(sample), "all_properties_in_sample": props, "chosen": chosen},
              open(f"{out}/properties.json", "w"), indent=1)
    print("chosen properties:", chosen)
    # 2. values (QIDs only; no label service), then resolve value labels in batches
    values = []
    for p in chosen:
        rows = sparql(f"SELECT ?item ?ci ?v WHERE {{ ?item wdt:P2697 ?ci ; wdt:{p['pid']} ?v . }}")
        for b in rows:
            values.append({"item": b["item"]["value"].rsplit("/", 1)[-1], "cricinfo_id": b["ci"]["value"], "pid": p["pid"],
                           "property_label": p["label"], "value": b["v"]["value"].rsplit("/", 1)[-1]})
        print(p["pid"], p["label"], len(rows), "rows")
        time.sleep(2)
    qids = sorted({v["value"] for v in values if re.fullmatch(r"Q\d+", v["value"])})
    vl = wbget(qids, "labels")
    for v in values:
        v["value_label"] = vl.get(v["value"], {}).get("labels", {}).get("en", {}).get("value")
    json.dump(values, open(f"{out}/values.json", "w"))
    json.dump({"source": "Wikidata (Query Service + wbgetentities API)", "endpoints": [EP, API],
               "licence": "CC0 1.0 (Wikidata structured data)",
               "retrieved_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
               "join_key": "P2697 ESPNcricinfo player ID == Cricsheet Register key_cricinfo",
               "retrieved_by": os.environ.get("RUN_URL", "local")}, open(f"{out}/PROVENANCE.json", "w"), indent=1)


if __name__ == "__main__":
    main()
