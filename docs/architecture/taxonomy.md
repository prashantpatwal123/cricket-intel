# Canonical cricket taxonomies (Phase 6)

Code: `pipeline/cricintel/enrich/taxonomy.py`. Vendor-independent.
- **Source wording is kept:** every normalised value keeps the source's own wording (`original`) and the source's footnotes (`note`).
- **No guesswork:** a label maps only as far as it says. Unmapped labels stay unknown.

## Bowling style

| Code | Label | Arm | Family | Subtype |
|---|---|---|---|---|
| RF | right-arm fast | right | pace | fast |
| RFM | right-arm fast-medium | right | pace | fast-medium |
| RMF | right-arm medium-fast | right | pace | medium-fast |
| RM | right-arm medium | right | pace | medium |
| LF | left-arm fast | left | pace | fast |
| LFM | left-arm fast-medium | left | pace | fast-medium |
| LMF | left-arm medium-fast | left | pace | medium-fast |
| LM | left-arm medium | left | pace | medium |
| ROB | off break (right-arm finger spin) | right | spin | finger |
| RLB | leg break (right-arm wrist spin) | right | spin | wrist |
| LO | left-arm orthodox (finger spin) | left | spin | finger |
| LWS | left-arm wrist spin | left | spin | wrist |
| PACE | pace, arm and speed band unknown | unknown | pace | unknown |
| PACE_FAST | fast, arm unknown | unknown | pace | fast |
| SPIN | spin, type unknown | unknown | spin | unknown |
| R_UNKNOWN | right-arm, type unknown | right | unknown | unknown |
| L_UNKNOWN | left-arm, type unknown | left | unknown | unknown |

Partial nodes (PACE, PACE_FAST, SPIN, R_UNKNOWN, L_UNKNOWN) exist so that coarse labels such as Wikidata's "fast bowling" are not over-read.

### Source label → canonical rules (in order)

| Pattern (cleaned, lower-case) | Code | Mapping confidence | Note |
|---|---|---|---|
| `(slow )?left[- ]arm (orthodox|finger)` | LO | 0.95 |  |
| `left[- ]arm (unorthodox|wrist|chinaman)` | LWS | 0.95 |  |
| `right[- ]arm (off[- ]?(break|spin))|^off[- ]?break$` | ROB | 0.95 |  |
| `^off[- ]?spin$` | ROB | 0.85 | 'off spin' conventionally means right-arm finger spin; left-arm finger spin is 'left-arm orthodox' |
| `right[- ]arm leg[- ]?(break|spin)|^leg[- ]?break$` | RLB | 0.9 | 'leg break' is by convention right-arm wrist spin |
| `^leg[- ]?spin$` | RLB | 0.8 | 'leg spin' conventionally right-arm wrist spin |
| `right[- ]arm fast[- ]medium` | RFM | 0.95 |  |
| `right[- ]arm medium[- ]fast` | RMF | 0.95 |  |
| `right[- ]arm fast` | RF | 0.95 |  |
| `right[- ]arm medium` | RM | 0.95 |  |
| `left[- ]arm fast[- ]medium` | LFM | 0.95 |  |
| `left[- ]arm medium[- ]fast` | LMF | 0.95 |  |
| `left[- ]arm fast` | LF | 0.95 |  |
| `left[- ]arm medium` | LM | 0.95 |  |
| `^fast bowling$|^fast$` | PACE_FAST | 0.9 | arm not stated |
| `^(seam|pace|swing|medium)( bowling)?$` | PACE | 0.9 | arm and speed band not stated |
| `^spin( bowling)?$` | SPIN | 0.9 | spin type not stated |
| `^right[- ]arm$` | R_UNKNOWN | 0.9 | bowling type not stated |
| `^left[- ]arm$` | L_UNKNOWN | 0.9 | bowling type not stated |

Values with mapping confidence below 0.8 are never used, even from a licence-cleared source.

## Line (batter-relative)

| Code | Label |
|---|---|
| wide_outside_off | Wide outside off |
| outside_off | Outside off stump |
| off_stump | Off stump |
| middle | Middle stump |
| leg_stump | Leg stump |
| down_leg | Down the leg side |

## Length

| Code | Label |
|---|---|
| full_toss | Full toss |
| yorker | Yorker |
| full | Full |
| good_length | Good length |
| back_of_length | Back of a length |
| short | Short |
| bouncer | Bouncer |

**Rule.** Buckets are batter-relative (off side flips for a left-hander). Boundaries between buckets are vendor-defined: CRICINTEL stores the source label and maps it; it never infers line or length from outcomes, dismissals or commentary.

No CRICINTEL data carries line or length today. The live contract accepts them only as canonical codes with provenance (`ENRICHMENT_BLOCKS['L2']`).

## Shots (family → shot)

- **No shot** (`no_shot`): Leave (`leave`), Padded away (`padded_away`)
- **Defensive** (`defensive`): Forward defence (`forward_defence`), Back-foot defence (`back_defence`)
- **Drive** (`drive`): Cover drive (`cover_drive`), Straight drive (`straight_drive`), On drive (`on_drive`), Off drive (`off_drive`), Square drive (`square_drive`), Lofted drive (`lofted_drive`)
- **Cut** (`cut`): Square cut (`square_cut`), Late cut (`late_cut`), Upper cut (`upper_cut`)
- **Pull / hook** (`pull_hook`): Pull (`pull`), Hook (`hook`)
- **Sweep** (`sweep`): Sweep (`sweep`), Slog sweep (`slog_sweep`), Reverse sweep (`reverse_sweep`), Paddle (`paddle`)
- **Leg-side touch** (`leg_side_touch`): Flick (`flick`), Glance (`glance`)
- **Improvised** (`improvised`): Ramp (`ramp`), Scoop (`scoop`), Switch hit (`switch_hit`)
- **Slog** (`slog`)

Modifiers (orthogonal to the shot): Use of feet / charge (`charge`), Lofted (in the air by intent) (`lofted`), Attacking (`attacking`), Defensive (`defensive_intent`).

Each source gets a reviewed mapping table from its label to a canonical code. A label maps to the deepest node the source supports: a source that says "drive" maps to the `drive` family, never to `cover_drive`. Unmapped labels are kept and left unmapped (`map_shot`).
