// Phase 8 final inspection screenshots (390px phone + desktop) and the session-memory checks.
import { chromium } from "playwright";
import fs from "fs";
const BASE = "http://localhost:3000", out = process.argv[2] || "phase8"; fs.mkdirSync(out, { recursive: true });
const b = await chromium.launch({ executablePath: process.env.CHROME });
const res = {};
async function ctxFor(w) { const c = await b.newContext({ viewport: { width: w, height: w < 600 ? 844 : 900 }, reducedMotion: "reduce" }); const p = await c.newPage();
  await p.goto(BASE + "/data"); await p.evaluate(() => localStorage.setItem("ci-preview-notice", "1")); return [c, p]; }
const settle = (p, ms = 1500) => p.waitForLoadState("networkidle").then(() => p.waitForTimeout(ms));
const H = (p) => p.evaluate(() => document.documentElement.scrollHeight);
// 1. phone screens, fresh visitor each
const PHONE = [["home", "/?day=2026-10-04"], ["player-kohli", "/players/ba607b88"], ["player-bumrah", "/players/462411b3"], ["player-dhoni", "/players/4a8a2e3b"],
  ["player-hardik", "/players/dbe50b21"], ["battle-kohli-zampa", "/battle?bat=ba607b88&bowl=14f96089"], ["match-mcg-2022", "/match/1298150"], ["ask-empty", "/ask"],
  ["ask-answer", "/ask?q=Who%20dismisses%20Kohli%20most%3F"], ["play", "/play"], ["discover", "/discover"], ["glossary", "/glossary"]];
for (const [n, u] of PHONE) {
  const [c, p] = await ctxFor(390); await p.goto(BASE + u); await settle(p);
  await p.screenshot({ path: `${out}/m-${n}.png` }); await p.screenshot({ path: `${out}/m-${n}-full.png`, fullPage: true });
  res[n] = { height: await H(p), screens: +((await H(p)) / 844).toFixed(1), overflow: await p.evaluate(() => document.documentElement.scrollWidth - innerWidth) };
  if (n === "play") { await p.locator(".play-picks .pick").first().click(); await p.waitForSelector(".reveal-banner"); await p.waitForTimeout(800);
    await p.screenshot({ path: `${out}/m-play-after-first-pick.png`, fullPage: true }); }
  await c.close();
}
// 2. tour bar + session memory (returning visitor)
{ const [c, p] = await ctxFor(390);
  await p.goto(BASE + "/players/ba607b88?tour=1"); await settle(p); await p.screenshot({ path: `${out}/m-tour-step1.png` });
  for (const u of ["/battle?bat=ba607b88&bowl=14f96089", "/match/1298150"]) { await p.goto(BASE + u); await settle(p, 800); }
  await p.goto(BASE + "/?day=2026-10-04"); await settle(p);
  res.continue_rows = await p.locator("[data-testid=continue] .recent-row a").count();
  await p.locator("[data-testid=continue]").screenshot({ path: `${out}/m-home-continue.png` });
  res.storage_keys = await p.evaluate(() => Object.keys(localStorage).sort());
  res.memory_sample = await p.evaluate(() => { const m = JSON.parse(localStorage.getItem("ci-memory-v1") || "{}"); return { keys: Object.keys(m), visited0: m.visited?.[0] }; });
  await p.locator("[data-testid=continue] button", { hasText: "Clear my history" }).click(); await p.waitForTimeout(400);
  res.after_clear = { continue_visible: await p.locator("[data-testid=continue]").count(), memory: await p.evaluate(() => localStorage.getItem("ci-memory-v1")) };
  await p.reload(); await settle(p); res.after_clear.continue_after_reload = await p.locator("[data-testid=continue]").count();
  res.dev_events_without_flag = await p.evaluate(() => localStorage.getItem("ci-dev-events"));
  await c.close(); }
// 3. desktop
for (const [n, u] of [["home", "/?day=2026-10-04"], ["battle", "/battle?bat=ba607b88&bowl=14f96089"], ["match", "/match/1298150"], ["ask", "/ask?q=Who%20dismisses%20Kohli%20most%3F"]]) {
  const [c, p] = await ctxFor(1280); await p.goto(BASE + u); await settle(p); await p.screenshot({ path: `${out}/d-${n}.png`, fullPage: true });
  res["desktop-" + n] = { overflow: await p.evaluate(() => document.documentElement.scrollWidth - innerWidth) }; await c.close(); }
fs.writeFileSync(`${out}/final.json`, JSON.stringify(res, null, 1)); console.log(JSON.stringify(res, null, 1));
await b.close();
