"use client";
// The optional 60–90 second first-visit tour. It runs on the real pages (no slides): each page shows a one-line hint and a
// "next" link carrying ?tour=N. Leaving the path or tapping ✕ ends it; completion or dismissal is remembered in this browser.
export const KEY = "ci-tour";
export const TOUR_START = "/players/ba607b88?tour=1";
export type TourStatus = "new" | "done" | "dismissed";

export function tourState(): TourStatus {
  try { return (localStorage.getItem(KEY) as TourStatus) || "new"; } catch { return "new"; }
}
export function setTour(s: TourStatus) {
  try { localStorage.setItem(KEY, s); } catch { /* storage blocked: the tour simply offers itself again */ }
}

export interface Step { n: number; match: (path: string) => boolean; text: string; next?: { label: string; href: string | "moment" } }
export const STEPS: Step[] = [
  { n: 1, match: (p) => p.startsWith("/players/ba607b88"), text: "Virat Kohli at a glance: the numbers, what makes Kohli different, the big battles.",
    next: { label: "How Kohli gets out", href: "/how-out/ba607b88?tour=2" } },
  { n: 2, match: (p) => p.startsWith("/how-out/ba607b88"), text: "Every dismissal, by how and to whom. Tap any route to drill in.",
    next: { label: "Kohli v Zampa", href: "/battle?bat=ba607b88&bowl=14f96089&tour=3" } },
  { n: 3, match: (p) => p.startsWith("/battle"), text: "What actually happens when Kohli meets Zampa, compared with their usual numbers.",
    next: { label: "The MCG 82*", href: "/innings/1298150/2/ba607b88?tour=4" } },
  { n: 4, match: (p) => p.startsWith("/innings/1298150/2/ba607b88"), text: "Kohli's 82* at the MCG, ball by ball. Last step: call a ball from it.",
    next: { label: "Predict a ball", href: "moment" } },
  { n: 5, match: (p) => p.startsWith("/live-lab/1298150"), text: "Pick what happened next. That's CRICINTEL: players, battles, matches, questions, and a game." },
];
