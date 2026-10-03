"""Scan real Cricsheet JSON files and report which fields actually occur, how often, and their values.

    python -m cricintel.sources.schema_scan > docs/data/cricsheet-schema-observed.json
"""
from __future__ import annotations

import json
import sys
import zipfile
from collections import Counter, defaultdict

from ..config import RAW


def walk(obj, path, keys: Counter, files_with: dict, fid: str, values: dict):
    if isinstance(obj, dict):
        for k, v in obj.items():
            p = f"{path}.{k}"
            # people/players/registry maps are keyed by names/teams: collapse
            if path.endswith(("registry.people", "info.players", "supersubs")):
                p = f"{path}.<key>"
            keys[p] += 1
            files_with[p].add(fid)
            walk(v, p, keys, files_with, fid, values)
    elif isinstance(obj, list):
        for x in obj:
            walk(x, path + "[]", keys, files_with, fid, values)
    else:
        if len(values[path]) < 40:
            values[path].add(obj if not isinstance(obj, float) else round(obj, 1))


ENUM_PATHS = {"info.gender", "info.match_type", "info.team_type", "info.toss.decision", "info.outcome.result",
              "info.outcome.method", "innings[].overs[].deliveries[].wickets[].kind", "innings[].powerplays[].type",
              "innings[].overs[].deliveries[].review.decision", "innings[].overs[].deliveries[].review.type",
              "innings[].overs[].deliveries[].replacements.match[].reason",
              "innings[].overs[].deliveries[].replacements.role[].reason", "innings[].overs[].deliveries[].replacements.role[].role",
              "meta.data_version", "info.balls_per_over", "innings[].overs[].deliveries[].review.umpires_call",
              "info.event.stage"}


def scan():
    keys, files_with, values = Counter(), defaultdict(set), defaultdict(set)
    per_zip = {}
    n = 0
    by_zip_files = defaultdict(set)
    for z in sorted((RAW / "cricsheet" / "downloads").glob("*.zip")):
        c = 0
        with zipfile.ZipFile(z) as zz:
            for name in zz.namelist():
                if not name.endswith(".json"):
                    continue
                d = json.loads(zz.read(name))
                fid = f"{z.name}:{name}"
                walk(d, "", keys, files_with, fid, values)
                for p in files_with:
                    pass
                c += 1
                n += 1
        per_zip[z.name] = c
    out = {"files": n, "per_zip": per_zip, "fields": {}}
    for p in sorted(keys):
        q = p.lstrip(".")
        nf = len(files_with[p])
        f = {"occurrences": keys[p], "files_with_field": nf, "pct_files": round(100 * nf / n, 2)}
        if q in ENUM_PATHS:
            f["values"] = sorted(map(str, values[p]))
        out["fields"][q] = f
    # per-zip presence for key optional fields (competition dependence)
    dep = {}
    for p in keys:
        q = p.lstrip(".")
        if any(t in q for t in ("review", "replacements", "powerplays", "target", "supersubs", "missing", "bowl_out",
                                "player_of_match", "event.stage", "match_type_number", "penalty_runs", "miscounted_overs",
                                "super_over", "absent_hurt", "non_boundary", "event.group", "city")):
            zc = Counter(f.split(":")[0] for f in files_with[p])
            dep[q] = {zn: round(100 * zc.get(zn, 0) / per_zip[zn], 1) for zn in per_zip}
    out["presence_by_zip_pct"] = dep
    return out


if __name__ == "__main__":
    json.dump(scan(), sys.stdout, indent=1, default=str)
