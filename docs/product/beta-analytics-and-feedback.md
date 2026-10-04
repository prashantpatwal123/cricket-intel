# Private-beta analytics and feedback (Phase 8): specification

**Status: designed, not connected.** No analytics provider, no network calls, no accounts. The code (`web/lib/analytics.ts`, `web/lib/feedback.ts`) writes only to the developer's own browser, and only when switched on.

## Turning on local logging (developers only)

```js
localStorage.setItem("ci-dev-analytics", "1")   // start recording into localStorage["ci-dev-events"] (ring buffer, 500)
JSON.parse(localStorage.getItem("ci-dev-events")) // read
```

## Privacy rules (enforced in code)

- No user ID, no fingerprinting. A random per-tab `session` ID lives in `sessionStorage` and dies with the tab.
- **No free text.** Search and Ask log the *length* of the query and its *parsed intent kind*, never the words.
- Props are coarse product context only: public cricket entity type/ID, counts, flags, rank.
- Feedback notes ("Something wrong with a stat?") are the one free-text field. They stay in the browser (`ci-feedback`, last 200) and are never sent.

## Event schema

Every event: `{ name, ts, session, path, viewport: "phone"|"desktop", ...props }`.

| Event | Fired when | Props | Code |
|---|---|---|---|
| `session_start` | app shell mounts (once per tab) | — | `components/Shell.tsx` |
| `search` | a search is submitted | `q_len`, `from` | `app/page.tsx` |
| `entity_open` | any player / battle / match / innings / record page registers itself in session memory; or a home example is tapped | `type`, `id`, `depth` (entities seen this session, ≤ 40) / `from` | `lib/memory.ts::useRemember`, `app/page.tsx` |
| `explore_next_click` | an "Explore next" row is tapped | `from_type`, `to_type`, `relation`, `rank` | `components/ExploreNext.tsx` |
| `ask_query` | Ask returns | `kind` (intent), `status`, `followups` (count) | `app/ask/page.tsx` |
| `ask_followup` | an "Ask next" item is tapped | `from_kind`, `to` ("question" or "page") | `app/ask/page.tsx` |
| `battle_open` | a battle is opened from a player page | `from` | `components/fan/PlayerHome.tsx` |
| `evidence_open` | a delivery list (the evidence) opens | `kind` | `components/Deliveries.tsx` |
| `play_start` | Play mounts | `returning` | `app/play/page.tsx` |
| `prediction` | a pick is revealed | `n`, `correct`, `model_correct`, `ms_since_open` | `app/play/page.tsx` |
| `share_card_generate` | a share card renders | `type` | `app/share/page.tsx` |
| `tour` | tour started / step / dismissed / done | `step`, `action` | `components/TourBar.tsx`, `app/page.tsx` |
| `feedback` | 👍 / 👎 / stat report saved | `kind`, `entity_type` | `components/Feedback.tsx` |

## Metrics (computed offline from the events)

| Metric | Definition | Beta target (to be validated) |
|---|---|---|
| Activation | share of sessions with ≥ 1 of: `entity_open`, `ask_query` (status ok), `prediction` | ≥ 60% |
| Time to first meaningful action | `ts(first activation event) − ts(session_start)` | median < 60 s |
| Entities per session | distinct `entity_open.id` per session | median ≥ 3 |
| Rabbit-hole depth | max `entity_open.depth` per session | p75 ≥ 5 |
| Ask success rate | `ask_query.status == "ok"` / all `ask_query` | ≥ 85% |
| Ask follow-up rate | `ask_followup` / successful `ask_query` | ≥ 25% |
| Evidence-open rate | sessions with `evidence_open` / sessions with `entity_open` | ≥ 20% (trust signal) |
| Predictions per session | count of `prediction` in sessions with `play_start` | median ≥ 5 |
| Time to first prediction | `prediction(n=1).ms_since_open` | median < 5 s |
| Return-session rate | requires a persistent anonymous ID, **not built**; would need consent design before beta | — |

## Feedback payload

```ts
{ kind: "useful" | "not_useful" | "stat_wrong",
  page: "/players/ba607b88?tab=style",      // pathname + search: reproduces the screen
  entity: { type: "player", id: "ba607b88" } | null,
  item: "player_home" | "battle" | "match" | "ask:<intent kind>" | null,
  note: string | null,                       // only for stat_wrong, ≤ 500 chars, stays in the browser
  data_version: "<dataset built_at from /api/meta>",
  model_version: string | null,              // e.g. the WHN model version on Play
  app_version: "phase-8",
  ts: 1759000000000 }
```

UI: `components/Feedback.tsx` ("Useful? 👍 👎 · Something wrong with a stat?") on Player home, Battle, Match.

## Before connecting anything (beta gate)

1. Cricsheet licence confirmed (hard blocker for any external user).
2. Privacy notice and consent text reviewed.
3. Choose a self-hosted or EU-resident sink; keep the "no free text" rule server-side too.
4. Decide on the return-session identifier (or drop the metric).
