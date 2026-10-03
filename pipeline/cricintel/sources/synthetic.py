"""SYNTHETIC test-fixture generator: emits matches in Cricsheet JSON format.

Purpose: exercise the real ingestion -> QA -> analytics -> UI path end to end while the real
Cricsheet download is blocked, and to benchmark at realistic scale.

Every team, player and match here is FICTIONAL. Rows ingested from this generator carry
source_id = "synthetic_fixture", and the UI shows a permanent SYNTHETIC banner whenever such data
is loaded. No real player's statistics are ever fabricated.

    python -m cricintel.sources.synthetic --matches-scale 1.0 --seed 7
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import datetime as dt
import json
import random
import shutil
from dataclasses import dataclass, field

from ..config import RAW, METADATA

OUT = RAW / "synthetic"

FIRST = ["Arlo", "Bastian", "Corin", "Dacey", "Emrys", "Faron", "Galen", "Halvard", "Idris", "Jory", "Kester",
         "Lorcan", "Mylo", "Nevan", "Oskar", "Perrin", "Quill", "Rowan", "Silas", "Tavin", "Ulric", "Vesper",
         "Wynn", "Xavi", "Yorick", "Zane", "Ansel", "Brin", "Cael", "Dorian"]
FIRST_F = ["Aveline", "Brisa", "Calla", "Delphine", "Elowen", "Fenna", "Greer", "Halle", "Isolde", "Junia",
           "Kaia", "Liesl", "Maren", "Nerys", "Odette", "Pia", "Quinn", "Rhosyn", "Saoirse", "Tamsin", "Una",
           "Verity", "Wren", "Xanthe", "Yara", "Zinnia", "Anwen", "Bryony", "Ceri", "Dilys"]
SUR = ["Ashgrove", "Brackwell", "Corrivan", "Dunmoor", "Elderby", "Farrowind", "Glenhart", "Hollowell",
       "Ironvale", "Jessop-Vane", "Kestrelby", "Larkhurst", "Merriwen", "Northcott-Ray", "Oakhollow",
       "Pellward", "Quarrender", "Ravensby", "Stormholt", "Thistlewood", "Underhay", "Valecourt", "Wexmoor",
       "Yarrowby", "Zephyrine", "Amberlane", "Birchmore", "Coldridge", "Draycombe", "Emberton", "Foxmere",
       "Greystoke-Alm", "Harrowgate", "Inchmere", "Juniperton", "Kingsrow", "Lowenby", "Marchbank"]
SUR_PRE = ["Ash", "Brack", "Corr", "Dun", "Elder", "Farrow", "Glen", "Hollow", "Iron", "Kestrel", "Lark", "Merri",
           "North", "Oak", "Pell", "Quarr", "Raven", "Storm", "Thistle", "Under", "Vale", "Wex", "Yarrow", "Amber",
           "Birch", "Cold", "Dray", "Ember", "Fox", "Grey", "Harrow", "Inch", "Juniper", "King", "Lowen", "March"]
SUR_SUF = ["grove", "well", "van", "moor", "by", "wind", "hart", "stoke", "combe", "mere", "ton", "field", "wick",
           "ford", "ley", "wood", "holt", "bank", "court", "ridge", "away", "son"]
NATIONS = ["Avalor", "Brenmark", "Caldora", "Dunmere", "Estrova", "Fenmarch"]
CLUBS_M = ["Northshire Comets", "Eastvale Kites", "Westmoor Lancers", "Southbay Herons", "Riverton Owls",
           "Highcliff Rams", "Lakeside Falcons", "Stonebridge Wolves"]
CLUBS_F = ["Northshire Comets Women", "Eastvale Kites Women", "Westmoor Lancers Women",
           "Southbay Herons Women", "Riverton Owls Women", "Highcliff Rams Women"]
VENUES = [("Avalon Oval", "Avalor City"), ("Brenmark Park", "Brennholm"), ("Caldora Gardens", "Caldor"),
          ("Dunmere Bowl", "Dunmere"), ("Estrova Arena", "Estrov"), ("Fenmarch Fields", "Fenwick"),
          ("Harbourside Ground", "Port Alder"), ("Kingsmead Common", "Kingsmead")]
STYLES_PACE = ["Right-arm fast", "Right-arm fast-medium", "Left-arm fast-medium", "Right-arm medium",
               "Left-arm fast"]
STYLES_SPIN = ["Right-arm offbreak", "Legbreak", "Slow left-arm orthodox", "Left-arm wrist-spin"]


@dataclass
class Player:
    pid: str
    name: str
    role: str  # batter / allrounder / bowler / keeper
    bat_skill: float
    bowl_skill: float
    bat_hand: str
    style: str | None
    weak_vs: str  # hidden synthetic pattern: "pace_left", "pace_right", "spin_wrist", "spin_finger"
    weak_mult: float
    meta_published: bool = True  # whether the fake "external metadata source" lists this player

    @property
    def is_spin(self):
        return self.style in STYLES_SPIN

    @property
    def style_key(self):
        if self.style is None:
            return None
        if self.is_spin:
            return "spin_wrist" if self.style in ("Legbreak", "Left-arm wrist-spin") else "spin_finger"
        return "pace_left" if self.style.startswith("Left") else "pace_right"


@dataclass
class Team:
    name: str
    players: list[Player] = field(default_factory=list)


class Gen:
    def __init__(self, seed: int):
        self.r = random.Random(seed)
        self.used_names: set[str] = set()
        self.all_players: dict[str, Player] = {}
        self.n_ids = 0

    def name(self, female: bool) -> str:
        """Unique fictional surname per player (prefix x suffix), so scorecards stay readable."""
        while True:
            fn = self.r.choice(FIRST_F if female else FIRST)
            sur = self.r.choice(SUR_PRE) + self.r.choice(SUR_SUF)
            if sur not in self.used_names:
                self.used_names.add(sur)
                return f"{fn[0]} {sur}"

    def player(self, role: str, female: bool) -> Player:
        r = self.r
        self.n_ids += 1
        pid = f"syn{self.n_ids:05d}"
        style = None
        if role in ("bowler", "allrounder") or (role == "batter" and r.random() < 0.25):
            style = r.choice(STYLES_PACE if r.random() < 0.58 else STYLES_SPIN)
        p = Player(pid=pid, name=self.name(female), role=role,
                   bat_skill={"batter": r.uniform(.55, .95), "keeper": r.uniform(.45, .8),
                              "allrounder": r.uniform(.4, .8), "bowler": r.uniform(.05, .35)}[role],
                   bowl_skill=r.uniform(.4, .95) if role in ("bowler", "allrounder") else r.uniform(.1, .3),
                   bat_hand="Left" if r.random() < 0.3 else "Right", style=style,
                   weak_vs=r.choice(["pace_left", "pace_right", "spin_wrist", "spin_finger"]),
                   weak_mult=r.uniform(1.0, 1.9), meta_published=r.random() < 0.8)
        self.all_players[pid] = p
        return p

    def team(self, name: str, female: bool) -> Team:
        roles = ["batter"] * 6 + ["keeper", "keeper"] + ["allrounder"] * 3 + ["bowler"] * 6
        return Team(name, [self.player(ro, female) for ro in roles])

    # ------------------------------------------------------------------ simulation
    def xi(self, t: Team) -> list[Player]:
        r = self.r
        bats = r.sample([p for p in t.players if p.role == "batter"], 4)
        keeper = r.choice([p for p in t.players if p.role == "keeper"])
        ar = r.sample([p for p in t.players if p.role == "allrounder"], 2)
        bowl = r.sample([p for p in t.players if p.role == "bowler"], 4)
        order = bats[:3] + [keeper if r.random() < .5 else bats[3]]
        order += [bats[3] if order[-1] is keeper else keeper] + ar + bowl
        return order

    def ball_probs(self, fmt, phase, bat: Player, bowl: Player, rrr):
        dot, one, two, three, four, six, wk = (.38, .36, .07, .006, .105, .04, .045) if fmt == "T20" else \
            (.50, .30, .07, .006, .085, .012, .025)
        if phase == "powerplay":
            four *= 1.25; dot *= 1.05; six *= .8
        elif phase == "death":
            six *= 1.9; four *= 1.15; wk *= 1.5; dot *= .8
        if rrr is not None and rrr > 10:
            six *= 1.4; wk *= 1.3
        skill = bat.bat_skill
        wk *= (1.7 - skill) * (0.7 + 0.6 * bowl.bowl_skill)
        if bowl.style_key == bat.weak_vs:
            wk *= bat.weak_mult
        four *= 0.55 + 0.8 * skill
        six *= 0.35 + 1.2 * skill
        ps = [dot, one, two, three, four, six, wk]
        s = sum(ps)
        return [p / s for p in ps]

    def dismissal(self, bowl: Player, field: list[Player], keeper: Player, bat, ns):
        r = self.r
        if bowl.is_spin:
            kinds = [("caught", .44), ("stumped", .09), ("lbw", .18), ("bowled", .18), ("run out", .06),
                     ("caught and bowled", .04), ("hit wicket", .005)]
        else:
            kinds = [("caught", .56), ("lbw", .14), ("bowled", .19), ("run out", .07),
                     ("caught and bowled", .015), ("hit wicket", .005)]
        k = r.choices([k for k, _ in kinds], [w for _, w in kinds])[0]
        w = {"player_out": bat.name, "kind": k}
        if k == "caught":
            if r.random() < (0.10 if bowl.is_spin else 0.30):
                w["fielders"] = [{"name": keeper.name}]
            elif r.random() < 0.03:
                w["fielders"] = [{"name": "Sub " + r.choice(SUR), "substitute": True}]
            else:
                w["fielders"] = [{"name": r.choice([f for f in field if f is not keeper and f is not bowl]).name}]
        elif k == "stumped":
            w["fielders"] = [{"name": keeper.name}]
        elif k == "run out":
            if r.random() < 0.45:
                w["player_out"] = ns.name
            fs = r.sample([f for f in field if f is not bowl], r.choice([1, 1, 2]))
            w["fielders"] = [{"name": f.name} for f in fs]
        return w

    def innings(self, fmt, bat_xi, bowl_xi, overs, target=None, bpo=6):
        r = self.r
        bowlers = sorted(bowl_xi, key=lambda p: -p.bowl_skill)[:6]
        bowlers = [b for b in bowlers if b.style] or bowl_xi[-5:]
        while len(bowlers) < 5:
            bowlers.append(r.choice([p for p in bowl_xi if p not in bowlers]))
        keeper = next((p for p in bowl_xi if p.role == "keeper"), bowl_xi[4])
        max_ov = overs // 5
        spent = {b.pid: 0 for b in bowlers}
        striker, ns, nxt = bat_xi[0], bat_xi[1], 2
        score = wk = 0
        out_overs = []
        last = None
        done = False
        for o in range(overs):
            cands = [b for b in bowlers if spent[b.pid] < max_ov and b is not last] or \
                    [b for b in bowl_xi if b is not last]
            bowl = r.choice(cands)
            spent[bowl.pid] = spent.get(bowl.pid, 0) + 1
            last = bowl
            phase = ("powerplay" if o < (6 if fmt == "T20" else 10) else
                     "death" if o >= overs - (5 if fmt == "T20" else 10) else "middle")
            dels, legal = [], 0
            while legal < bpo:
                d = {"batter": striker.name, "bowler": bowl.name, "non_striker": ns.name}
                x = r.random()
                if x < 0.035:  # wide
                    extra = r.choice([1, 1, 1, 1, 5])
                    d["runs"] = {"batter": 0, "extras": extra, "total": extra}
                    d["extras"] = {"wides": extra}
                    dels.append(d); score += extra
                    if target and score >= target:
                        done = True; break
                    continue
                if x < 0.041:  # no-ball
                    rb = r.choice([0, 0, 1, 4, 6])
                    d["runs"] = {"batter": rb, "extras": 1, "total": rb + 1}
                    d["extras"] = {"noballs": 1}
                    dels.append(d); score += rb + 1
                    if rb % 2 == 1:
                        striker, ns = ns, striker
                    if target and score >= target:
                        done = True; break
                    continue
                legal += 1
                rrr = ((target - score) * 6 / max(1, (overs - o) * bpo - legal)) if target else None
                if x < 0.065:  # leg byes / byes
                    rr = r.choice([1, 1, 1, 2, 4])
                    key = "legbyes" if r.random() < .8 else "byes"
                    d["runs"] = {"batter": 0, "extras": rr, "total": rr}
                    d["extras"] = {key: rr}
                    dels.append(d); score += rr
                    if rr % 2 == 1:
                        striker, ns = ns, striker
                else:
                    ps = self.ball_probs(fmt, phase, striker, bowl, rrr)
                    oc = r.choices(range(7), ps)[0]
                    if oc == 6:
                        w = self.dismissal(bowl, bowl_xi, keeper, striker, ns)
                        rb = r.choice([0, 0, 0, 1]) if w["kind"] == "run out" else 0
                        d["runs"] = {"batter": rb, "extras": 0, "total": rb}
                        d["wickets"] = [w]
                        if w["kind"] == "lbw" and r.random() < .3:
                            d["review"] = {"by": "x", "umpire": "Synthetic Umpire", "batter": striker.name,
                                           "decision": "upheld", "type": "wicket"}
                        dels.append(d); score += rb; wk += 1
                        out_name = w["player_out"]
                        if nxt >= len(bat_xi) or wk >= 10:
                            done = True; break
                        newp = bat_xi[nxt]; nxt += 1
                        if out_name == striker.name:
                            striker = newp
                        else:
                            ns = newp
                    else:
                        rb = [0, 1, 2, 3, 4, 6][oc]
                        d["runs"] = {"batter": rb, "extras": 0, "total": rb}
                        dels.append(d); score += rb
                        if rb in (1, 3):
                            striker, ns = ns, striker
                if target and score >= target:
                    done = True; break
            out_overs.append({"over": o, "deliveries": dels})
            if done:
                break
            striker, ns = ns, striker
        return out_overs, score

    def match(self, mid, fmt, team_type, gender, comp, t1: Team, t2: Team, date, season):
        r = self.r
        overs = 20 if fmt == "T20" else 50
        xi1, xi2 = self.xi(t1), self.xi(t2)
        toss_w = r.choice([t1, t2])
        dec = r.choice(["bat", "field"])
        first = toss_w if dec == "bat" else (t2 if toss_w is t1 else t1)
        second = t2 if first is t1 else t1
        fx, sx = (xi1, xi2) if first is t1 else (xi2, xi1)
        o1, s1 = self.innings(fmt, fx, sx, overs)
        dl = r.random() < 0.04
        t_overs = overs - r.randint(3, 8) if dl else overs
        target = (s1 + 1) if not dl else int((s1 + 1) * t_overs / overs) + 1
        o2, s2 = self.innings(fmt, sx, fx, t_overs, target=target)
        names = {p.name: p.pid for p in xi1 + xi2}
        for ov in o1 + o2:
            for d in ov["deliveries"]:
                for w in d.get("wickets", []):
                    for f in w.get("fielders", []):
                        if f.get("substitute") and f["name"] not in names:
                            names[f["name"]] = "subst" + hashlib.sha1(f["name"].encode()).hexdigest()[:8]
                if "review" in d:
                    d["review"]["by"] = second.name if d["batter"] in [p.name for p in sx] else first.name
        registry = dict(names)
        if r.random() < 0.01:  # exercise the unresolved-identity path
            registry.pop(xi1[-1].name, None)
        wickets2 = sum(len(d.get("wickets", [])) for ov in o2 for d in ov["deliveries"])
        if s2 >= target:
            outcome = {"winner": second.name, "by": {"wickets": 10 - wickets2}}
        elif s2 == target - 1:
            outcome = {"result": "tie"}
        else:
            outcome = {"winner": first.name, "by": {"runs": target - 1 - s2}}
        if dl:
            outcome["method"] = "D/L"
        venue, city = r.choice(VENUES)
        inn2 = {"team": second.name, "overs": o2, "target": {"overs": t_overs, "runs": target}}
        pp = 6 if fmt == "T20" else 10
        doc = {
            "meta": {"data_version": "1.1.0", "created": date.isoformat(), "revision": 1},
            "info": {
                "balls_per_over": 6, "city": city, "dates": [date.isoformat()],
                "event": {"name": comp, "match_number": int(mid[-3:]) % 97 + 1},
                "gender": gender, "match_type": fmt if team_type == "club" or fmt == "ODI" else "T20",
                "officials": {"umpires": ["Synthetic Umpire", "Synthetic Umpire Two"]},
                "outcome": outcome, "overs": overs,
                "players": {t1.name: [p.name for p in xi1], t2.name: [p.name for p in xi2]},
                "registry": {"people": registry}, "season": season, "team_type": team_type,
                "teams": [t1.name, t2.name], "toss": {"decision": dec, "winner": toss_w.name},
                "venue": venue,
            },
            "innings": [
                {"team": first.name, "overs": o1, "powerplays": [{"from": 0.1, "to": pp - 1 + .6, "type": "mandatory"}]},
                dict(inn2, powerplays=[{"from": 0.1, "to": pp - 1 + .6, "type": "mandatory"}]),
            ],
        }
        return doc


def generate(scale: float = 1.0, seed: int = 7) -> dict:
    g = Gen(seed)
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir(parents=True)
    plan = []
    clubs_m = [g.team(n, False) for n in CLUBS_M]
    clubs_f = [g.team(n, True) for n in CLUBS_F]
    nat_m = [g.team(n, False) for n in NATIONS]
    nat_f = [g.team(n + " Women", True) for n in NATIONS]
    nmatch = 0

    def schedule(teams, comp, fmt, team_type, gender, years, per_year):
        nonlocal nmatch
        for y in years:
            if team_type == "club" and y != years[0]:
                for t in teams:  # squad turnover: debutants arrive, others leave
                    for _ in range(2):
                        i = g.r.randrange(len(t.players))
                        old = t.players[i]
                        t.players[i] = g.player(old.role, gender == "female")
            for k in range(max(1, int(per_year * scale))):
                t1, t2 = g.r.sample(teams, 2)
                d = dt.date(y, g.r.randint(1, 12), g.r.randint(1, 28))
                nmatch += 1
                plan.append((f"9{nmatch:06d}", fmt, team_type, gender, comp, t1, t2, d,
                             str(y) if team_type == "club" else str(y)))

    schedule(clubs_m, "Synthetic Premier League", "T20", "club", "male", range(2015, 2026), 60)
    schedule(clubs_f, "Synthetic Women's League", "T20", "club", "female", range(2019, 2026), 30)
    schedule(nat_m, "Synthetic International T20 Series", "T20", "international", "male", range(2010, 2026), 18)
    schedule(nat_m, "Synthetic International ODI Series", "ODI", "international", "male", range(2010, 2026), 10)
    schedule(nat_f, "Synthetic Women's International T20 Series", "T20", "international", "female", range(2014, 2026), 12)
    schedule(nat_f, "Synthetic Women's International ODI Series", "ODI", "international", "female", range(2014, 2026), 6)
    for mid, fmt, tt, gender, comp, t1, t2, d, season in plan:
        doc = g.match(mid, fmt, tt, gender, comp, t1, t2, d, season)
        (OUT / f"{mid}.json").write_text(json.dumps(doc, separators=(",", ":")))
    # Register + fictional "external metadata source" (to exercise automated enrichment).
    METADATA.mkdir(parents=True, exist_ok=True)
    reg_dir = OUT / "register"
    reg_dir.mkdir()
    with open(reg_dir / "people.csv", "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["identifier", "name", "unique_name", "key_synthetic_ref"])
        for p in g.all_players.values():
            w.writerow([p.pid, p.name, p.name, "ref-" + p.pid])
    with open(OUT / "synthetic_external_metadata.csv", "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["synthetic_ref", "batting_hand", "bowling_style"])
        for p in g.all_players.values():
            if p.meta_published:
                w.writerow(["ref-" + p.pid, p.bat_hand, p.style or ""])
    return {"matches": len(plan), "players": len(g.all_players)}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--matches-scale", type=float, default=1.0)
    ap.add_argument("--seed", type=int, default=7)
    a = ap.parse_args()
    print(generate(a.matches_scale, a.seed))
