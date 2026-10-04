# Phase 8: final hero-experience architecture

CRICINTEL is five experiences, reached from one launcher. Everything else is a supporting page one tap away from a hero, or internal.

```
                       HOME (launcher)                         ← "/"
   search · 5 real examples · optional 60-second tour · today's finding / battle / Play
        │            │             │             │            │
     PLAYER       BATTLE        MATCH          ASK          PLAY
 /players/[id]   /battle      /match/[id]     /ask         /play
        │            │        + /live-lab/[id]  │            │
        └── supporting: how-out · innings · spells · partnerships · records · compare · discover · search · glossary
```

Tab bar: **Home · Players · Battles · Ask · Play** (5 targets; search is in the header on every page and at `/search`).

## Page anatomy (phone, top to bottom)

| Hero | Above the fold | Then | Behind navigation |
|---|---|---|---|
| **Home** | promise · search · 5 examples (one per hero) · tour invite | finding · battle · Play challenge · keep-exploring links | `/discover` (everything we found) |
| **Player** | name, covered span, score strip (role-specific), one defining insight, 5 actions | also unusual (3) · how out / how wickets come · biggest battles (3) · best performances · explore more | tabs: Style (fingerprint, every finding, similar), Battles, Innings, Bowling, Partners, Career, Strengths, Dismissals, Situations, Numbers |
| **Battle** | BATTER v BOWLER, crease motif, strip: balls · runs · SR · dismissals | is it unusual (edge + interval, no winner when inconclusive) · how it changes (earlier v later) · how the wickets fell · every meeting (latest 8, expand) · Play a ball · similar battles · what we can't say | every ball, compare, share |
| **Match** | scoreboard, result, "Replay it ball by ball", Share | the story: standout innings · standout spell · biggest partnership · battle of the match · records · Play moment · worm · key events (factual) | scorecard & details · partnerships · all battles · experimental difficulty (collapsed) |
| **Ask** | question box · tappable questions in 6 groups | interpretation (editable) · answer · numbers · "Ask next" (1–2 deterministic follow-ups) · keep exploring | the pipeline, more questions |
| **Play** | "What happens next?" · situation strip · 7 picks | after the first pick: reveal, model comparison, scoring explained, running score | session stats, whole-match replay |

## Role-adaptive player layouts

`pipeline/cricintel/fan/player.py::hero` returns `layout`:

| Layout | Rule (covered T20/ODI balls, `kg.role` + `player.hero`) | Strip | Second block |
|---|---|---|---|
| neutral | balls faced + balls bowled < 300 | what we have | "Not enough covered balls yet to say what kind of player…" (no role claims) |
| allrounder | ≥ 1,000 faced **and** ≥ 1,000 bowled, smaller ≥ 35% of larger | runs + wickets | how out **and** how wickets come (side by side on desktop) |
| bowler | balls bowled > 1.3 × balls faced | wickets · economy · SR | how the wickets come (out-routes, new v set batter) |
| keeper | otherwise, and the profile's `wicketkeeper` flag is set | batting strip | + keeping strip (catches as keeper, stumpings; DERIVED keeper identity) |
| batter | otherwise | runs · SR · average | how they get out |

Verified on real players: Kohli (batter), Bumrah (bowler), Hardik Pandya (allrounder), Dhoni (keeper: 516 ct, 199 st), Mandhana (batter), Kartik Sharma (neutral).
