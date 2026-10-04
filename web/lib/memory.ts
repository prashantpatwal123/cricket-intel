"use client";
// Local-only session memory. Lives in this browser's localStorage and nowhere else: no account, no server copy, no tracking.
// Used to (1) avoid recommending what you've already opened, (2) show "continue where you left off", (3) keep a Play score.
// Every read/write is guarded: private windows or blocked storage simply mean an empty memory.
import { track } from "./analytics";
import { useEffect } from "react";

const KEY = "ci-memory-v1";
const MAX_VISITED = 80;

export interface Visit { id: string; type: string; label: string; href: string; ts: number }
export interface Memory { visited: Visit[]; shown: Record<string, number>; play: { pts: number; n: number; right: number; beat: number }; since: number }

const empty = (): Memory => ({ visited: [], shown: {}, play: { pts: 0, n: 0, right: 0, beat: 0 }, since: Date.now() });

export function load(): Memory {
  try {
    const raw = localStorage.getItem(KEY);
    if (!raw) return empty();
    const m = JSON.parse(raw);
    return { ...empty(), ...m };
  } catch { return empty(); }
}

function save(m: Memory) {
  try { localStorage.setItem(KEY, JSON.stringify(m)); } catch { /* storage unavailable: memory is simply off */ }
  try { window.dispatchEvent(new Event("ci-memory")); } catch { /* ignore */ }
}

export function remember(v: Omit<Visit, "ts">) {
  const m = load();
  m.visited = [{ ...v, ts: Date.now() }, ...m.visited.filter((x) => x.id !== v.id)].slice(0, MAX_VISITED);
  save(m);
}

export function markShown(ids: string[]) {
  const m = load();
  for (const id of ids) m.shown[id] = (m.shown[id] || 0) + 1;
  const keys = Object.keys(m.shown);
  if (keys.length > 400) for (const k of keys.slice(0, keys.length - 400)) delete m.shown[k];
  save(m);
}

export function seenIds(limit = 40): string[] {
  return load().visited.slice(0, limit).flatMap((v) => [v.id, v.href]);
}

export function shownIds(): string[] {
  const s = load().shown;
  return Object.keys(s).filter((k) => s[k] >= 2).slice(-150);
}

export function recordPlay(points: number, correct: boolean, modelPoints: number) {
  const m = load();
  m.play = { pts: m.play.pts + points, n: m.play.n + 1, right: m.play.right + (correct ? 1 : 0), beat: m.play.beat + (points > modelPoints ? 1 : 0) };
  save(m);
}

export function reset() {
  try { localStorage.removeItem(KEY); } catch { /* ignore */ }
  try { window.dispatchEvent(new Event("ci-memory")); } catch { /* ignore */ }
}

/** Record that this page (an entity in the knowledge graph) was opened. */
export function useRemember(type: string, key: string | null | undefined, label: string | null | undefined, href?: string) {
  useEffect(() => {
    if (!key || !label) return;
    remember({ id: `${type}:${key}`, type, label, href: href || (typeof window !== "undefined" ? window.location.pathname + window.location.search : "") });
    track("entity_open", { type, id: key, depth: seenIds().length });
  }, [type, key, label, href]);
}
