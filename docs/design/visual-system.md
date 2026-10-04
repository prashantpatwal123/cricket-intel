# CRICINTEL visual system (Phase 8)

Goal: a screenshot is recognisable without the logo. The system is small on purpose; every token lives in `web/app/globals.css` (`:root` and the Phase 8 block).

## Cricket-native motifs

| Motif | Class | Where | Why it's cricket |
|---|---|---|---|
| **Score strip** | `.strip` | player hero, battle hero, battle halves, keeper strip, Play situation | a scoreboard line: heavy top rule, big tabular numbers, small caps labels, thin dividers. Wickets in `--wicket` red (`.wk`). |
| **Crease head** | `.crease-head` | section breaks (match "Scorecard & details") | two short crease ticks either side of a label, like popping-crease marks |
| **Batter v bowler** | `.vs-hero`, `.vs-pitch` | battle | two names across a 22-yard strip with creases at each end; batter left in player-teal, bowler right in battle-orange |
| **Innings sequence** | `.mt-row`, `.beats` | every meeting, match story | a vertical ledger of dated innings with runs (balls) and the dismissal in red |
| **Delivery notation** | pick buttons, recent balls | Play, replay | `•` dot, digits, `W` wicket: the scorer's own notation |
| **Hero rule** | `border-left: 3px solid var(--h-*)` | defining insight, Ask groups, follow-ups, Play situation | one coloured rule per hero instead of a card |

Not everything is a rounded card: cards are kept for interactive objects (finding with evidence, Play challenge). Lists are ruled rows; numbers sit in strips.

## Tokens

| Token | Value | Use |
|---|---|---|
| `--h-player` | #35e0c2 | player |
| `--h-battle` | #ff7a59 | battle |
| `--h-match` | #7cc4ff | match |
| `--h-ask` | #c49bff | ask |
| `--h-play` | #9df26b | play |
| `--wicket` | #ff5c74 | dismissals only |
| `--text` / `--muted` / `--dim` | #edf2fc / #8d9ab8 / #7f8ca8 | text tiers (all ≥ 4.5:1 on `--bg` and `--surface`) |
| `--fs-label` | 11.5px | the smallest text in the product |
| `--fs-small` | 13px | secondary copy |
| `--tap` | 44px | primary tap targets (picks, Ask questions, actions) |

## Rules

1. No text under 11 CSS px, including SVG text after scaling (checked by `scripts/a11y-phase8.mjs`).
2. Labels: small caps, letter-spaced, `--muted`. Values: display face, tabular numbers.
3. Provenance tags (OBSERVED, DERIVED, RECONSTRUCTED, MODELLED, ILLUSTRATIVE) appear wherever a number is MODELLED or RECONSTRUCTED, and on every answer.
4. Intervals are drawn or stated as ranges, never as a single number with "±".
5. Historical replays always carry "Historical replay, not live" (`.replay-flag`).
6. One accent per hero per screen; red means wicket only.
7. Motion: `fade-in` only; disabled under `prefers-reduced-motion`.
