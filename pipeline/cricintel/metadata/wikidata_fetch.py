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


def main(out="out/wikidata"):
    os.makedirs(out, exist_ok=True)
    # 1. discover properties used by cricketer items (sample of 4000 items keeps the query within limits)
    disc = sparql("""SELECT ?p ?pLabel (COUNT(*) AS ?n) WHERE {
      { SELECT ?item WHERE { ?item wdt:P2697 ?ci . } LIMIT 4000 }
      ?item ?wdt ?v . ?p wikibase:directClaim ?wdt .
      SERVICE wikibase:label { bd:serviceParam wikibase:language "en". } }
      GROUP BY ?p ?pLabel ORDER BY DESC(?n)""")
    props = [{"pid": b["p"]["value"].rsplit("/", 1)[-1], "label": b["pLabel"]["value"], "n_in_sample": int(b["n"]["value"])} for b in disc]
    chosen = [p for p in props if re.search(r"hand|bowl|position|specialit", p["label"], re.I)]
    json.dump({"all_properties_in_sample": props, "chosen": chosen}, open(f"{out}/properties.json", "w"), indent=1)
    print("chosen properties:", chosen)
    values = []
    for p in chosen:
        rows = sparql(f"""SELECT ?item ?ci ?v ?vLabel WHERE {{ ?item wdt:P2697 ?ci ; wdt:{p['pid']} ?v .
          SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }} }}""")
        for b in rows:
            values.append({"item": b["item"]["value"].rsplit("/", 1)[-1], "cricinfo_id": b["ci"]["value"], "pid": p["pid"],
                           "property_label": p["label"], "value": b["v"]["value"].rsplit("/", 1)[-1],
                           "value_label": b.get("vLabel", {}).get("value")})
        print(p["pid"], p["label"], len(rows), "rows")
        time.sleep(2)
    json.dump(values, open(f"{out}/values.json", "w"))
    json.dump({"source": "Wikidata Query Service", "endpoint": EP, "licence": "CC0 1.0 (Wikidata structured data)",
               "retrieved_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
               "join_key": "P2697 ESPNcricinfo player ID == Cricsheet Register key_cricinfo",
               "retrieved_by": os.environ.get("RUN_URL", "local")}, open(f"{out}/PROVENANCE.json", "w"), indent=1)


if __name__ == "__main__":
    main()
