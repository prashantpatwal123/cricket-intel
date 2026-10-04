# Terminology, glossary and coverage language (Phase 8)

## Principle: plain by default, exact on request

Default copy uses the plain phrase. The technical term and its exact definition sit one tap away: in the WHY box beside the number, and on `/glossary` (`web/lib/glossary.ts`).

| Technical term | Default (plain) copy | Where the exact term lives |
|---|---|---|
| percentile | "only 2% of them have a lower figure", "higher than 82% of peers" | WHY box (`percentile: 2 (share of peers with a lower value)`), Style tab, glossary |
| shrinkage | "so a short hot streak can't top the list" | WHY box (pseudo-ball weight), glossary |
| confidence interval | "the range the true figure probably sits in"; battle halves show it only in WHY | WHY box (`90% Wilson interval`), glossary |
| false-discovery control | "fewer flukes in unusual lists" | WHY box on discovery lists, glossary |
| calibration | "whether the model's percentages come true" | Play reveal footnote, model card, glossary |
| cohort / peers | "players compared like for like" | WHY box (peer pool definition), glossary |
| baseline | "the usual rate", "normal performance" | battle "Is this battle unusual?", glossary |
| observed / expected | "9 times in 286 balls (about 4 at the usual rate)" | battle edge card, glossary |

**Check:** `scripts/jargon-phase8.mjs` walks the visible text of Home, Player (Kohli, Bumrah, Dhoni), Battle, Match, Play and Ask at 390 px and fails on any of these words outside a WHY box or closed `<details>`. Phase 8 result: **0 hits** (4 before the pass, all the "(Nth percentile)" suffix on player findings, now plain shares).

## Standard coverage language

One phrase per situation (`web/lib/coverage.ts`):

| Situation | Phrase |
|---|---|
| Sentence opener | "Within CRICINTEL's covered matches…" |
| Kicker / label | "In covered matches" |
| Beside career-style numbers | "Covered matches only, not official totals." |
| Beside a record or ranking | "Covered matches only, not official records." |
| Date span | "2008–2026 in covered matches" |
| Absence | "Kohli hasn't faced X in covered matches." |
| Field nobody records | "Not recorded in the data" (line, length, shot, field placement) |
| Replay | "Historical replay, not live" |

Phase 8 applied these on the player hero, the Ask answer kicker, the battle empty state and the match completeness note. It also replaced the engine's 7 generated "in our covered data" phrases with "in covered matches", so an Ask answer and its kicker now use the same words. One wording still reads awkwardly: "Kohli's best covered innings in covered matches". It is in the post-Phase-8 copy backlog.
