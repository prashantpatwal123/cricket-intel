"""Cricsheet adapter: Cricsheet match JSON -> canonical rows.

Written defensively against the format documented in docs/data/cricsheet-verification.md:
unknown keys are recorded as schema drift (never silently dropped), required fields missing ->
the match is quarantined with a reason, optional fields missing -> nulls.

CLI:
    python -m cricintel.sources.cricsheet download [--file all_json.zip]
    python -m cricintel.sources.cricsheet verify
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import json
import sys
import urllib.request
import zipfile
from collections import Counter, defaultdict
from pathlib import Path

from ..config import RAW, DOCS_DATA
from ..schema import BOWLER_CREDITED, NOT_DISMISSAL, FORMAT_GROUP

BASE = "https://cricsheet.org"
KNOWN_INFO_KEYS = {
    "balls_per_over", "bowl_out", "city", "dates", "event", "gender", "match_type", "match_type_number",
    "missing", "officials", "outcome", "overs", "player_of_match", "players", "registry", "season",
    "supersubs", "team_type", "teams", "toss", "venue",
}
KNOWN_INNINGS_KEYS = {
    "team", "overs", "powerplays", "target", "absent_hurt", "penalty_runs", "declared", "forfeited",
    "super_over", "miscounted_overs",
}
KNOWN_DELIVERY_KEYS = {"actual_delivery", "batter", "bowler", "non_striker", "runs", "extras", "wickets", "replacements", "review"}


class Quarantine(Exception):
    """Raised when a match lacks a required field. The match is excluded and reported."""


def fallback_person_id(name: str) -> str:
    return "unres:" + hashlib.sha1(name.encode()).hexdigest()[:10]


def phase_for(format_group: str, over: int, scheduled_overs: int | None, super_over: bool) -> str:
    if super_over:
        return "super_over"
    if format_group == "T20":
        return "powerplay" if over < 6 else ("death" if over >= 15 else "middle")
    if format_group == "ODI":
        return "powerplay" if over < 10 else ("death" if over >= 40 else "middle")
    if scheduled_overs:  # e.g. 100-ball or other limited formats: proportional phases
        frac = over / scheduled_overs
        return "powerplay" if frac < 0.3 else ("death" if frac >= 0.75 else "middle")
    return "none"  # multi-day: no limited-overs phase


def _date(s):
    try:
        return dt.date.fromisoformat(s)
    except Exception:
        return None


def parse_match(doc: dict, match_id: str, source_id: str, source_ref: str, checksum: str,
                drift: Counter | None = None) -> dict[str, list[dict]]:
    drift = drift if drift is not None else Counter()
    meta, info = doc.get("meta", {}), doc.get("info")
    if not info:
        raise Quarantine("missing info")
    for k in info:
        if k not in KNOWN_INFO_KEYS:
            drift[f"info.{k}"] += 1
    gender = info.get("gender")
    if gender not in ("male", "female"):
        raise Quarantine(f"gender missing/unknown: {gender!r}")
    dates = [d for d in (_date(x) for x in info.get("dates", [])) if d]
    if not dates:
        raise Quarantine("missing dates")
    teams = info.get("teams") or []
    if len(teams) != 2:
        raise Quarantine(f"expected 2 teams, got {teams!r}")
    players = info.get("players") or {}
    registry = (info.get("registry") or {}).get("people") or {}
    match_type = info.get("match_type")
    format_group = FORMAT_GROUP.get(match_type, "other")
    bpo = info.get("balls_per_over") or 6
    sched = info.get("overs")
    outcome = info.get("outcome") or {}
    by = outcome.get("by") or {}
    event = info.get("event") or {}
    toss = info.get("toss") or {}

    unresolved: set[str] = set()

    def pid(name: str | None) -> str | None:
        if name is None:
            return None
        if name in registry:
            return registry[name]
        unresolved.add(name)
        return fallback_person_id(name)

    out: dict[str, list[dict]] = defaultdict(list)
    now = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    out["matches"].append(dict(
        match_id=match_id, source_id=source_id, source_ref=source_ref, source_checksum=checksum,
        data_version=meta.get("data_version"), source_created=meta.get("created"),
        source_revision=meta.get("revision"), gender=gender, match_type=match_type,
        format_group=format_group, team_type=info.get("team_type"),
        match_type_number=info.get("match_type_number"), competition=event.get("name"),
        event_match_number=str(event["match_number"]) if "match_number" in event else None,
        event_group=str(event["group"]) if "group" in event else None, event_stage=event.get("stage"),
        season=str(info.get("season")) if info.get("season") is not None else None,
        start_date=min(dates), end_date=max(dates), n_days=len(dates),
        venue=info.get("venue"), city=info.get("city"), team1=teams[0], team2=teams[1],
        toss_winner=toss.get("winner"), toss_decision=toss.get("decision"),
        toss_uncontested=toss.get("uncontested"), winner=outcome.get("winner"),
        win_by_runs=by.get("runs"), win_by_wickets=by.get("wickets"), win_by_innings=by.get("innings"),
        result=outcome.get("result"), method=outcome.get("method"), eliminator=outcome.get("eliminator"),
        balls_per_over=bpo, scheduled_overs=sched, player_of_match=info.get("player_of_match"),
        missing_flags=json.dumps(info["missing"]) if info.get("missing") else None, ingested_at=now,
    ))
    for team, names in players.items():
        for n in names:
            out["players_in_match"].append(dict(match_id=match_id, team=team, person_id=pid(n), name=n,
                                                identity_resolved=n in registry))

    first_innings_total = None
    for i_idx, inn in enumerate(doc.get("innings") or [], start=1):
        for k in inn:
            if k not in KNOWN_INNINGS_KEYS:
                drift[f"innings.{k}"] += 1
        bat = inn.get("team")
        if bat not in teams:
            raise Quarantine(f"innings {i_idx} team {bat!r} not in teams")
        bowl = teams[1] if bat == teams[0] else teams[0]
        super_over = bool(inn.get("super_over"))
        tgt = inn.get("target") or {}
        target_runs, target_overs, target_prov = tgt.get("runs"), tgt.get("overs"), None
        if target_runs is not None:
            target_prov = "OBSERVED"
        elif i_idx == 2 and format_group in ("T20", "ODI") and not super_over and first_innings_total is not None:
            target_runs, target_overs, target_prov = first_innings_total + 1, sched, "DERIVED"
        chasing = target_runs is not None and format_group != "Test" and format_group != "MDM"
        limit_overs = target_overs if target_overs else (1 if super_over else sched)
        pen = inn.get("penalty_runs") or {}

        score = wkts = legal_before = 0
        part_runs = part_balls = 0
        bat_runs: Counter = Counter()
        bat_balls: Counter = Counter()
        seq = 0
        for ov in inn.get("overs") or []:
            over_no = ov.get("over")
            if over_no is None:
                raise Quarantine("over number missing")
            legal_in_over = 0
            for dl in ov.get("deliveries") or []:
                for k in dl:
                    if k not in KNOWN_DELIVERY_KEYS:
                        drift[f"delivery.{k}"] += 1
                seq += 1
                ex = dl.get("extras") or {}
                runs = dl.get("runs") or {}
                wides, nbs = ex.get("wides", 0), ex.get("noballs", 0)
                legal = wides == 0 and nbs == 0
                # v1.2.0: actual_delivery is the source's own over.ball label (OBSERVED); derive only if absent
                label = dl.get("actual_delivery") or f"{over_no}.{legal_in_over + 1}"
                if legal:
                    legal_in_over += 1
                b, bw, ns = dl.get("batter"), dl.get("bowler"), dl.get("non_striker")
                if b is None or bw is None:
                    raise Quarantine(f"delivery {over_no}/{seq} missing batter/bowler")
                rb, rt = runs.get("batter", 0), runs.get("total", 0)
                nb_flag = bool(runs.get("non_boundary"))
                did = f"{match_id}:{i_idx}:{seq}"
                balls_rem = (limit_overs * bpo - legal_before) if (chasing and limit_overs) else None
                req = (target_runs - score) if chasing else None
                bid = pid(b)
                wk_list = dl.get("wickets") or []
                out["deliveries"].append(dict(
                    delivery_id=did, match_id=match_id, innings_no=i_idx, seq=seq, over=over_no,
                    ball_in_over=legal_in_over if legal else legal_in_over + 1, ball_label=label, legal=legal,
                    batter_id=bid, bowler_id=pid(bw), non_striker_id=pid(ns), batter=b, bowler=bw,
                    non_striker=ns, runs_batter=rb, runs_extras=runs.get("extras", 0), runs_total=rt,
                    non_boundary=nb_flag, wides=wides, noballs=nbs, byes=ex.get("byes", 0),
                    legbyes=ex.get("legbyes", 0), penalty=ex.get("penalty", 0),
                    is_four=rb == 4 and not nb_flag, is_six=rb == 6 and not nb_flag, n_wickets=len(wk_list),
                    source_id=source_id, score_before=score, wickets_before=wkts,
                    legal_balls_before=legal_before, batter_runs_before=bat_runs[bid],
                    batter_balls_before=bat_balls[bid], partnership_runs_before=part_runs,
                    partnership_balls_before=part_balls,
                    phase=phase_for(format_group, int(over_no), sched, super_over), chasing=chasing,
                    target_runs=target_runs if chasing else None, balls_remaining=balls_rem,
                    runs_required=req,
                    required_rate=(req * 6 / balls_rem) if (chasing and balls_rem and balls_rem > 0) else None,
                    current_rate=(score * 6 / legal_before) if legal_before else None,
                ))
                for w_idx, w in enumerate(wk_list):
                    kind = w.get("kind")
                    po = w.get("player_out")
                    out["wickets"].append(dict(
                        delivery_id=did, match_id=match_id, innings_no=i_idx, wicket_idx=w_idx,
                        player_out_id=pid(po), player_out=po, kind=kind,
                        bowler_credited=kind in BOWLER_CREDITED, counts_as_dismissal=kind not in NOT_DISMISSAL,
                        striker_out=(po == b), source_id=source_id,
                    ))
                    for f_idx, f in enumerate(w.get("fielders") or []):
                        fname = f.get("name")
                        out["wicket_fielders"].append(dict(
                            delivery_id=did, match_id=match_id, innings_no=i_idx, wicket_idx=w_idx,
                            fielder_idx=f_idx, fielder_id=pid(fname) if fname else None, fielder=fname,
                            substitute=bool(f.get("substitute")), source_id=source_id,
                        ))
                rv = dl.get("review")
                if rv:
                    out["reviews"].append(dict(delivery_id=did, match_id=match_id, by_team=rv.get("by"),
                                               umpire=rv.get("umpire"), batter=rv.get("batter"),
                                               decision=rv.get("decision"), umpires_call=rv.get("umpires_call"),
                                               type=rv.get("type")))
                rp = dl.get("replacements") or {}
                for scope in ("match", "role"):
                    for r in rp.get(scope) or []:
                        out["replacements"].append(dict(delivery_id=did, match_id=match_id, scope=scope,
                                                        team=r.get("team"), player_in=r.get("in"),
                                                        player_out=r.get("out"), reason=r.get("reason"),
                                                        role=r.get("role")))
                # advance state
                score += rt
                if wides == 0:  # no-balls count as balls faced by the batter; wides do not
                    bat_balls[bid] += 1
                bat_runs[bid] += rb
                if legal:
                    legal_before += 1
                    part_balls += 1
                part_runs += rt
                for w in wk_list:
                    if w.get("kind") not in NOT_DISMISSAL:
                        wkts += 1
                    part_runs = part_balls = 0  # a new partnership starts after any departure
        total = score + (pen.get("pre") or 0) + (pen.get("post") or 0)
        if i_idx == 1:
            first_innings_total = total
        out["innings"].append(dict(
            match_id=match_id, innings_no=i_idx, batting_team=bat, bowling_team=bowl, super_over=super_over,
            declared=bool(inn.get("declared")), forfeited=bool(inn.get("forfeited")), target_runs=target_runs,
            target_overs=float(target_overs) if target_overs is not None else None, target_prov=target_prov,
            penalty_runs_pre=pen.get("pre"), penalty_runs_post=pen.get("post"),
            absent_hurt=inn.get("absent_hurt"), total_runs=total, total_wickets=wkts, legal_balls=legal_before,
        ))
        for pp in inn.get("powerplays") or []:
            out["powerplays"].append(dict(match_id=match_id, innings_no=i_idx, from_over=pp.get("from"),
                                          to_over=pp.get("to"), type=pp.get("type")))
    if unresolved:
        drift["identity_unresolved_names"] += len(unresolved)
    return out


def read_register(path: Path) -> list[dict]:
    """Read people.csv generically: every key_* column becomes an external id."""
    rows = []
    with open(path, newline="", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            ext = {k[4:]: v for k, v in r.items() if k.startswith("key_") and v}
            rows.append(dict(person_id=r["identifier"], name=r.get("name"), unique_name=r.get("unique_name"),
                             external_ids=list(ext.items()), source_id="cricsheet"))
    return rows


# ---------------------------------------------------------------- download / verify CLI
def _fetch(url: str, dest: Path) -> str:
    dest.parent.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(url, timeout=120) as r, open(dest, "wb") as fh:
        h = hashlib.sha256()
        while chunk := r.read(1 << 20):
            h.update(chunk)
            fh.write(chunk)
    return h.hexdigest()


PRIORITY_FILES = ("ipl_json.zip", "wpl_json.zip", "t20s_male_json.zip", "t20s_female_json.zip",
                  "odis_male_json.zip", "odis_female_json.zip")


def download(files=PRIORITY_FILES, register=True) -> dict:
    """Direct route: fetch official downloads from cricsheet.org into raw/cricsheet/{downloads,register}."""
    out = RAW / "cricsheet"
    manifest = {"route": "direct cricsheet.org", "retrieved_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(), "files": {}}
    for f in files:
        manifest["files"][f"downloads/{f}"] = _fetch(f"{BASE}/downloads/{f}", out / "downloads" / f)
    if register:
        for f in ("people.csv", "names.csv"):
            manifest["files"][f"register/{f}"] = _fetch(f"{BASE}/register/{f}", out / "register" / f)
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2))
    return manifest


def import_verified(src: Path) -> dict:
    """GitHub-Actions route: `src` is a checkout of branch data/cricsheet-raw. Every file listed in
    SHA256SUMS is re-hashed locally; any mismatch aborts. Files are copied byte-for-byte."""
    import shutil
    sums = {}
    for line in (src / "SHA256SUMS").read_text().splitlines():
        h, name = line.split(maxsplit=1)
        sums[name.strip()] = h
    out = RAW / "cricsheet"
    checked = {}
    for name, h in sums.items():
        got = hashlib.sha256((src / name).read_bytes()).hexdigest()
        if got != h:
            raise SystemExit(f"CHECKSUM MISMATCH {name}: expected {h} got {got}")
        checked[name] = got
        if name.startswith(("downloads/", "register/")):
            (out / name).parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(src / name, out / name)
    prov = json.loads((src / "PROVENANCE.json").read_text())
    manifest = {"route": "GitHub Actions retrieval from cricsheet.org", "provenance": prov,
                "imported_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(), "files": checked}
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2))
    return manifest


def verify() -> None:
    """Fetch licence page + downloads and append an OBSERVED section to the verification doc."""
    lines = ["", "## 6. Observed (automated run)", f"Run at {dt.datetime.now(dt.timezone.utc).isoformat()}", ""]
    for page in ("/", "/about", "/downloads/", "/register/", "/format/json/"):
        try:
            html = urllib.request.urlopen(BASE + page, timeout=60).read().decode("utf-8", "replace")
            lic = [ln.strip() for ln in html.splitlines() if "icen" in ln][:5]
            lines.append(f"- `{page}` fetched ({len(html)} bytes). Licence-related lines: {lic}")
        except Exception as e:  # noqa: BLE001
            lines.append(f"- `{page}` FAILED: {e}")
    m = json.loads((RAW / "cricsheet" / "manifest.json").read_text()) if (RAW / "cricsheet" / "manifest.json").exists() else download()
    keys: Counter = Counter()
    g: Counter = Counter()
    names = []
    for zpath in sorted((RAW / "cricsheet" / "downloads").glob("*.zip")):
      with zipfile.ZipFile(zpath) as z:
        for n in [x for x in z.namelist() if x.endswith(".json")]:
            names.append(n)
            d = json.loads(z.read(n))
            g[(d["info"].get("gender"), d["info"].get("match_type"), d["info"].get("team_type"))] += 1
            keys.update("info." + k for k in d["info"])
            for inn in d.get("innings", []):
                keys.update("innings." + k for k in inn)
                for ov in inn.get("overs", []):
                    for dl in ov.get("deliveries", []):
                        keys.update("delivery." + k for k in dl)
    lines.append(f"- files + sha256: {json.dumps(m['files'])}; {len(names)} match files")
    lines.append("- Matches by (gender, match_type, team_type): " + json.dumps({"|".join(map(str, k)): v for k, v in g.most_common()}))
    lines.append("- Keys observed (count of occurrences): " + json.dumps(dict(keys.most_common())))
    with open(DOCS_DATA / "cricsheet-verification.md", "a") as fh:
        fh.write("\n".join(lines) + "\n")
    print("\n".join(lines))


def iter_zip(path: Path):
    """Yield (match_id, doc, source_ref, sha256) from a Cricsheet zip."""
    with zipfile.ZipFile(path) as z:
        for n in sorted(z.namelist()):
            if not n.endswith(".json"):
                continue
            raw = z.read(n)
            yield Path(n).stem, json.loads(raw), f"{path.name}!{n}", hashlib.sha256(raw).hexdigest()


def iter_dir(path: Path):
    for p in sorted(path.glob("*.json")):
        raw = p.read_bytes()
        yield p.stem, json.loads(raw), str(p.name), hashlib.sha256(raw).hexdigest()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["download", "import", "verify"])
    ap.add_argument("--file", action="append")
    ap.add_argument("--src", help="checkout of branch data/cricsheet-raw (for import)")
    a = ap.parse_args()
    if a.cmd == "download":
        print(json.dumps(download(tuple(a.file or PRIORITY_FILES)), indent=2))
    elif a.cmd == "import":
        print(json.dumps(import_verified(Path(a.src)), indent=2))
    else:
        verify()
    sys.exit(0)
