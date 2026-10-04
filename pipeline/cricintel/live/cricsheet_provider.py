"""Historical Cricsheet replay implementing the LiveProvider contract.

Reads the raw deliveries (`live_deliveries`, a match-sorted copy of `deliveries`) (which, unlike the analytical `balls` view, includes super overs).
Spoiler safety is enforced at the data-access layer, not in the UI:
  * delivery rows are fetched with ORDER BY … LIMIT upto, so rows after the cursor are never read into the event stream;
  * the next delivery is read for IDENTITY ONLY (who faces, who bowls), mirroring a live feed's "new batter"/"new over"
    messages; its outcome columns are never selected;
  * only raw facts are read (who, runs split, boundary flag, wickets). The precomputed scoreboard columns in `balls`
    (score_before, required_rate, …) and the match result are never used. The engine derives all of them;
  * match_end (result) is emitted only once the cursor is past the last delivery.
Innings starts carry Cricsheet's recorded target. For rain-affected (D/L) matches that target is the final revised one
and Cricsheet does not say when it was revised, so it is applied from the start of the chase and flagged.
"""
from __future__ import annotations

from typing import Iterator

from ..db import DB
from .contract import Event

RAW = """SELECT delivery_id, innings_no, over, seq, batter_id, batter, non_striker_id, non_striker, bowler_id, bowler,
                runs_batter, wides, noballs, byes, legbyes, penalty, is_four, is_six
         FROM live_deliveries WHERE match_id = ? ORDER BY innings_no, seq LIMIT ? OFFSET ?"""


class HistoricalCricsheetProvider:
    def __init__(self, db: DB, match_id: str):
        self.db, self.match_id = db, match_id
        m = db.q1("""SELECT match_id, competition, season, gender, format_group, match_type, team_type, venue, city, start_date,
                            team1, team2, toss_winner, toss_decision, scheduled_overs, balls_per_over, event_stage, method
                     FROM matches WHERE match_id = ?""", [match_id])
        if not m:
            raise KeyError(match_id)
        self.m = m
        # How many deliveries each innings has: server-side only, used to emit innings_end/innings_start at the moment a
        # live feed would (straight after the last ball). Never sent to the client.
        self._counts = {r["innings_no"]: r["n"] for r in db.q("SELECT innings_no, count(*) AS n FROM live_deliveries WHERE match_id = ? GROUP BY 1", [match_id])}
        self._innings = {r["innings_no"]: r for r in db.q("""SELECT innings_no, batting_team, bowling_team, super_over, target_runs, target_overs,
                                                                    penalty_runs_pre, total_runs, total_wickets, legal_balls, declared, forfeited
                                                             FROM innings WHERE match_id = ? ORDER BY innings_no""", [match_id])}
        self.total = sum(self._counts.values())
        self._rows: list[dict] = []        # rows read so far: never beyond the highest cursor requested
        self._wk: dict = {}
        self._xi: dict | None = None
        self._next: dict = {}
        for k, r in self._innings.items():   # super-over chases: Cricsheet stores no target; it is the previous super over + 1
            if not r["target_runs"] and r["super_over"] and k % 2 == 0 and (k - 1) in self._innings and self._innings[k - 1]["super_over"]:
                self._innings[k] = {**r, "target_runs": (self._innings[k - 1]["total_runs"] or 0) + 1, "target_overs": 1}

    # -------------------------------------------------------------- reading (incremental, bounded by the cursor)
    def _fetch(self, upto: int) -> list[dict]:
        have = len(self._rows)
        if upto > have:
            new = self.db.q(RAW, [self.match_id, upto - have, have])
            per_over: dict = {}
            for r in self._rows:
                per_over[(r["innings_no"], r["over"])] = r["idx"]
            for r in new:                          # delivery index within its over (wides/no-balls included)
                k = (r["innings_no"], r["over"])
                per_over[k] = per_over.get(k, 0) + 1
                r["idx"] = per_over[k]
            if new:
                ids = {r["delivery_id"] for r in new}
                rng = "match_id = ? AND delivery_id IN (SELECT delivery_id FROM live_deliveries WHERE match_id = ? ORDER BY innings_no, seq LIMIT ? OFFSET ?)"
                fl: dict = {}
                for f in self.db.q(f"SELECT delivery_id, wicket_idx, fielder FROM live_fielders WHERE {rng} ORDER BY fielder_idx",
                                   [self.match_id, self.match_id, upto - have, have]):
                    fl.setdefault((f["delivery_id"], f["wicket_idx"]), []).append(f["fielder"])
                for w in self.db.q(f"SELECT delivery_id, wicket_idx, player_out_id, player_out, kind FROM live_wickets WHERE {rng} ORDER BY wicket_idx",
                                   [self.match_id, self.match_id, upto - have, have]):
                    if w["delivery_id"] in ids:
                        self._wk.setdefault(w["delivery_id"], []).append({"player_out": {"id": w["player_out_id"], "name": w["player_out"]}, "kind": w["kind"],
                                                                          "fielders": fl.get((w["delivery_id"], w["wicket_idx"]), [])})
            self._rows.extend(new)
        return self._rows[:upto]

    # -------------------------------------------------------------- events
    def meta_payload(self) -> dict:
        m = self.m
        return {"teams": [m["team1"], m["team2"]], "competition": m["competition"], "season": m["season"], "format": m["format_group"],
                "match_type": m["match_type"], "team_type": m["team_type"], "gender": m["gender"], "venue": m["venue"], "city": m["city"],
                "date": str(m["start_date"]), "scheduled_overs": m["scheduled_overs"], "stage": m["event_stage"],
                "toss": {"winner": m["toss_winner"], "decision": m["toss_decision"]} if m["toss_winner"] else None,
                "rain_rule": m["method"] == "D/L"}

    def _start(self, k: int) -> Event:
        r = self._innings[k]
        p = {"innings": k, "batting_team": r["batting_team"], "bowling_team": r["bowling_team"], "super_over": bool(r["super_over"]),
             "penalty_runs": r["penalty_runs_pre"] or 0}
        if r["target_runs"]:
            p.update(target_runs=r["target_runs"], target_overs=r["target_overs"],
                     target_note="Target as recorded by Cricsheet" + (" (final D/L target; when it was revised is not recorded)" if self.m["method"] == "D/L" else ""))
        return Event(f"{self.match_id}:innings_start:{k}", self.match_id, "innings_start", p)

    def _end_reason(self, k: int) -> str:
        r = self._innings[k]
        if r["declared"]:
            return "declared"
        if r["target_runs"] and (r["total_runs"] or 0) >= r["target_runs"]:
            return "target reached"
        if (r["total_wickets"] or 0) >= (2 if r["super_over"] else 10):
            return "all out"
        lim = 6 if r["super_over"] else (int(round(float(r["target_overs"]) * 6)) if r["target_overs"] else (self.m["scheduled_overs"] or 0) * 6)
        if lim and (r["legal_balls"] or 0) >= lim:
            return "overs complete"
        return "innings closed"

    def events(self, upto: int | None = None) -> Iterator[Event]:
        upto = self.total if upto is None else max(0, min(upto, self.total))
        mid, seq = self.match_id, 0

        def ev(eid, kind, payload):
            nonlocal seq
            seq += 1
            return Event(eid, mid, kind, payload, seq)

        yield ev(f"{mid}:meta", "match_meta", self.meta_payload())
        if self._xi is None:
            self._xi = {}
            for r in self.db.q("SELECT team, person_id, name FROM live_players WHERE match_id = ? ORDER BY team, name", [mid]):
                self._xi.setdefault(r["team"], []).append({"id": r["person_id"], "name": r["name"]})
        yield ev(f"{mid}:xi", "playing_xi", {"teams": self._xi})

        rows = self._fetch(upto)
        seen_inn: set[int] = set()
        done = {k: 0 for k in self._counts}
        for r in rows:
            k = r["innings_no"]
            if k not in seen_inn:
                seen_inn.add(k)
                yield self._start(k)
            boundary = 6 if r["is_six"] else 4 if r["is_four"] else None
            yield ev(r["delivery_id"], "delivery", {
                "innings": k, "over": r["over"], "index": r["idx"],
                "batter": {"id": r["batter_id"], "name": r["batter"]}, "non_striker": {"id": r["non_striker_id"], "name": r["non_striker"]},
                "bowler": {"id": r["bowler_id"], "name": r["bowler"]},
                "runs": {"batter": r["runs_batter"], "wides": r["wides"], "noballs": r["noballs"], "byes": r["byes"], "legbyes": r["legbyes"], "penalty": r["penalty"]},
                "boundary": boundary, "wickets": self._wk.get(r["delivery_id"], [])})
            done[k] += 1
            if done[k] == self._counts[k]:
                yield ev(f"{mid}:innings_end:{k}", "innings_end", {"innings": k, "reason": self._end_reason(k)})
                nxt = k + 1
                if nxt in self._innings and nxt in self._counts:
                    seen_inn.add(nxt)
                    yield self._start(nxt)          # innings break: the next innings (and any target) is now known
        if upto < self.total:
            first_inn = min(self._counts)
            if not rows and first_inn in self._innings:
                yield self._start(first_inn)          # before the first ball: the first innings is about to begin
            nb = self._next.get(upto) or self.db.q1("""SELECT innings_no, batter_id, batter, non_striker_id, non_striker, bowler_id, bowler
                               FROM live_deliveries WHERE match_id = ? ORDER BY innings_no, seq LIMIT 1 OFFSET ?""", [mid, upto])
            self._next[upto] = nb
            yield ev(f"{mid}:pre:{upto + 1}", "pre_ball", {"innings": nb["innings_no"], "striker": {"id": nb["batter_id"], "name": nb["batter"]},
                                                            "non_striker": {"id": nb["non_striker_id"], "name": nb["non_striker"]},
                                                            "bowler": {"id": nb["bowler_id"], "name": nb["bowler"]}})
        else:
            m = self.db.q1("SELECT winner, result, method, win_by_runs, win_by_wickets, eliminator FROM matches WHERE match_id = ?", [mid])
            text = (f"{m['winner']} won by {m['win_by_runs']} runs" if m["win_by_runs"] else f"{m['winner']} won by {m['win_by_wickets']} wickets"
                    if m["win_by_wickets"] else f"{m['winner']} won" if m["winner"] else (m["result"] or "no result"))
            if m["result"] == "tie" and m["eliminator"]:
                text = f"Match tied; {m['eliminator']} won the super over"
            if m["method"]:
                text += f" ({m['method']})"
            yield ev(f"{mid}:end", "match_end", {"result": text, "winner": m["winner"] or m["eliminator"], "method": m["method"]})
