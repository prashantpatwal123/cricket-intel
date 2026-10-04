"use client";
// Private-beta feedback: PROTOTYPE, stored only in this browser (localStorage), never sent anywhere.
// The payload carries enough context to reproduce exactly what the person saw. Spec: docs/product/beta-analytics-and-feedback.md
export interface FeedbackPayload {
  kind: "useful" | "not_useful" | "stat_wrong";
  page: string;                 // pathname + search
  entity?: { type: string; id: string } | null;
  item?: string | null;         // the card / metric / query the feedback is about (e.g. "story:death_sr", "ask:dismissed_by")
  note?: string | null;         // optional free text, only for "stat_wrong"
  data_version?: string | null; // dataset build (from /api/meta)
  model_version?: string | null;
  app_version: string;
  ts: number;
}

const KEY = "ci-feedback";
export const APP_VERSION = "phase-8";

export function saveFeedback(p: Omit<FeedbackPayload, "ts" | "app_version">) {
  try {
    const all = JSON.parse(localStorage.getItem(KEY) || "[]");
    all.push({ ...p, app_version: APP_VERSION, ts: Date.now() });
    localStorage.setItem(KEY, JSON.stringify(all.slice(-200)));
  } catch { /* storage unavailable */ }
}

export function localFeedback(): FeedbackPayload[] {
  try { return JSON.parse(localStorage.getItem(KEY) || "[]"); } catch { return []; }
}
