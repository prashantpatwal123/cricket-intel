"""Parse Cricsheet's own /coverage/ and /missing/ pages (archived, checksum-verified) into tables.

missing_matches: matches Cricsheet knows exist but could not source. Per Cricsheet, this list covers
Tests, ODIs and covered club competitions only. T20 internationals are NOT tracked, so T20I completeness
cannot be established from Cricsheet.
"""
from __future__ import annotations

import html
import re

from ..config import RAW

PAGES = RAW / "cricsheet" / "pages"


def _clean(x):
    return html.unescape(re.sub(r"<[^>]+>", "", x)).strip()


def missing_matches() -> list[dict]:
    p = PAGES / "index_missing_.html"
    if not p.exists():
        return []
    t = p.read_text(encoding="utf-8")
    rows, mtype, gender, date = [], None, None, None
    for m in re.finditer(r"<(h5|h6|dt|dd)[^>]*>(.*?)</\1>", t, re.S):
        tag, txt = m.group(1), _clean(m.group(2))
        if tag == "h5":
            mtype = re.sub(r"\s+Matches$", "", txt).strip()
        elif tag == "h6":
            gender = "female" if txt.lower().startswith("female") else "male"
        elif tag == "dt":
            date = txt
        elif tag == "dd" and " vs " in txt:
            a, b = txt.split(" vs ", 1)
            rows.append({"match_type": mtype, "gender": gender, "date": date, "team1": a.strip(), "team2": b.strip()})
    return rows


def coverage_tables() -> dict:
    """periods: (gender, name, earliest_checked, earliest_provided); percentages: (scope, gender, name, have, of, pct)."""
    p = PAGES / "index_coverage_.html"
    if not p.exists():
        return {"periods": [], "percentages": []}
    t = p.read_text(encoding="utf-8")
    periods, pcts = [], []
    section, gender = "periods", None
    for m in re.finditer(r"<(h3|h4|h6)[^>]*>(.*?)</\1>|<table.*?</table>", t, re.S):
        if m.group(1):
            h = _clean(m.group(2))
            if m.group(1) == "h3" and "numbers" in h.lower():
                section, gender = "percentages", None
            elif "women" in h.lower():
                gender = "female"
            elif "men" in h.lower():
                gender = "male"
            elif h in ("By Competition", "By Team"):
                scope, gender = h.split()[-1].lower(), None
            continue
        for r in re.findall(r"<tr[^>]*>(.*?)</tr>", m.group(0), re.S):
            c = [_clean(x) for x in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", r, re.S)]
            if len(c) != 3 or c[1] in ("Earliest checked", "Coverage"):
                continue
            if section == "periods":
                periods.append({"gender": gender, "name": c[0], "earliest_checked": c[1], "earliest_provided": c[2]})
            else:
                mm = re.match(r"(\d+) of (\d+)", c[1])
                if mm:
                    pcts.append({"scope": scope, "gender": gender, "name": c[0], "have": int(mm.group(1)),
                                 "of": int(mm.group(2)), "pct": float(c[2])})
    return {"periods": periods, "percentages": pcts}


if __name__ == "__main__":
    import collections
    import json
    mm = missing_matches()
    print(len(mm), collections.Counter((r["match_type"], r["gender"]) for r in mm).most_common(8))
    ct = coverage_tables()
    print(json.dumps([x for x in ct["periods"] if x["name"] in ("One-day Internationals", "T20 Internationals", "Indian Premier League", "Women's Premier League")], indent=0))
    print([x for x in ct["percentages"] if x["name"] in ("Indian Premier League", "Women's Premier League")])
