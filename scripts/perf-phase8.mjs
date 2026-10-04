// Phase 8 page-render budget (390px phone, unthrottled and 4× CPU throttle), median of 3 fresh loads:
//   hero pages: navigation → the hero's first meaningful element rendered;
//   Play: navigation → pick buttons enabled (a new user can make their first prediction), and → reveal after one tap.
import { chromium } from "playwright";
const B = process.env.BASE || "http://localhost:3000";
const PAGES = [["home", "/?day=2026-10-04", "[data-testid=home-examples] .launch-row"], ["player", "/players/ba607b88", "[data-testid=defining-insight]"],
  ["battle", "/battle?bat=ba607b88&bowl=14f96089", "[data-testid=battle-hero]"], ["match", "/match/1298150", "[data-testid=match-story] .beat"],
  ["ask-answer", "/ask?q=Who%20dismisses%20Kohli%20most%3F", "[data-testid=ask-followups]"], ["play-picks", "/play", ".play-picks .pick:not([disabled])"]];
const b = await chromium.launch({ executablePath: process.env.CHROME });
const out = {};
for (const thr of [1, 4]) {
  for (const [k, u, sel] of PAGES) {
    const ts = [];
    for (let i = 0; i < 3; i++) {
      const ctx = await b.newContext({ viewport: { width: 390, height: 844 } }); const p = await ctx.newPage();
      const cdp = await ctx.newCDPSession(p); await cdp.send("Emulation.setCPUThrottlingRate", { rate: thr });
      await p.goto(B + "/data"); await p.evaluate(() => localStorage.setItem("ci-preview-notice", "1"));
      const t = Date.now(); await p.goto(B + u); await p.waitForSelector(sel, { timeout: 30000 }); const first = Date.now() - t;
      if (k === "play-picks") { await p.locator(".play-picks .pick").first().click(); await p.waitForSelector(".reveal-banner", { timeout: 30000 }); out[`play-first-reveal@${thr}x#${i}`] = Date.now() - t; }
      ts.push(first); await ctx.close();
    }
    ts.sort((a, c) => a - c); out[`${k}@${thr}x`] = ts[1];
  }
}
for (const thr of [1, 4]) { const r = Object.entries(out).filter(([k]) => k.startsWith(`play-first-reveal@${thr}x#`)).map(([, v]) => v).sort((a, c) => a - c); out[`play-first-reveal@${thr}x`] = r[1];
  Object.keys(out).filter((k) => k.startsWith(`play-first-reveal@${thr}x#`)).forEach((k) => delete out[k]); }
console.log(JSON.stringify(out, null, 1));
await b.close();
