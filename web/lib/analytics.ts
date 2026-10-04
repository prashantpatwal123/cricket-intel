"use client";
// Private-beta analytics: DESIGN + LOCAL DEV LOGGING ONLY. No provider is connected and nothing leaves the browser.
// Events are recorded only when localStorage["ci-dev-analytics"] === "1" (developers), into a ring buffer in this browser.
// Schema and future metrics: docs/product/beta-analytics-and-feedback.md.
export type EventName = "session_start" | "search" | "entity_open" | "explore_next_click" | "ask_query" | "ask_followup" | "battle_open"
  | "evidence_open" | "play_start" | "prediction" | "share_card_generate" | "tour" | "feedback";

const BUF = "ci-dev-events", FLAG = "ci-dev-analytics", SESSION = "ci-dev-session", MAX = 500;

function enabled(): boolean {
  try { return localStorage.getItem(FLAG) === "1"; } catch { return false; }
}

/** Random per-tab session id (no user id, no fingerprinting). */
function session(): string {
  try {
    let s = sessionStorage.getItem(SESSION);
    if (!s) { s = Math.random().toString(36).slice(2, 10); sessionStorage.setItem(SESSION, s); }
    return s;
  } catch { return "none"; }
}

/** Props must be coarse product context: entity type/id of public cricket entities, counts, lengths, flags.
 *  Never free text a person typed (queries are logged as their parsed intent kind, not the text). */
export function track(name: EventName, props: Record<string, string | number | boolean | null | undefined> = {}) {
  if (typeof window === "undefined" || !enabled()) return;
  try {
    const ev = { name, ts: Date.now(), session: session(), path: window.location.pathname, viewport: window.innerWidth < 760 ? "phone" : "desktop", ...props };
    const buf = JSON.parse(localStorage.getItem(BUF) || "[]");
    buf.push(ev);
    localStorage.setItem(BUF, JSON.stringify(buf.slice(-MAX)));
  } catch { /* never let analytics break the page */ }
}

export function devEvents(): any[] {
  try { return JSON.parse(localStorage.getItem(BUF) || "[]"); } catch { return []; }
}
