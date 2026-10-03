// Usage: node scripts/screenshots.mjs <picks.json> <outdir>   (needs `playwright` resolvable, app on :3000)
import { chromium } from "playwright";
import fs from "node:fs";

const [, , picksPath, out] = process.argv;
const picks = JSON.parse(fs.readFileSync(picksPath, "utf8"));
const BASE = process.env.BASE || "http://localhost:3000";
const browser = await chromium.launch({ executablePath: process.env.CHROME || undefined });
const report = [];

async function page(viewport) {
  const ctx = await browser.newContext({ viewport, deviceScaleFactor: 2 });
  const p = await ctx.newPage();
  const errors = [];
  p.on("pageerror", (e) => errors.push(String(e)));
  p.on("console", (m) => m.type() === "error" && errors.push(m.text()));
  p.on("response", (r) => r.status() >= 400 && errors.push(`${r.status()} ${r.url()}`));
  return { p, ctx, errors };
}
async function scrollTo(p, sel) {
  await p.evaluate((s) => { const el = document.querySelector(s); if (el) window.scrollTo(0, el.getBoundingClientRect().top + window.scrollY - 110); }, sel);
  await p.waitForTimeout(500);
}
const settle = (p) => p.waitForLoadState("networkidle").then(() => p.waitForTimeout(400));

// Home (mobile)
{
  const { p, ctx, errors } = await page({ width: 390, height: 844 });
  await p.goto(BASE + "/"); await settle(p);
  await p.screenshot({ path: `${out}/01-home-mobile.png`, fullPage: true });
  report.push({ shot: "home", errors }); await ctx.close();
}
const main = picks.elite_men_batter;
// Player hero + how-out, mobile
{
  const { p, ctx, errors } = await page({ width: 390, height: 844 });
  await p.goto(`${BASE}/players/${main.person_id}`); await settle(p);
  await p.screenshot({ path: `${out}/02-player-hero-mobile.png` });
  await scrollTo(p, "section:nth-of-type(2)");
  await p.screenshot({ path: `${out}/03-howout-mobile.png` });
  // drill: caught by keeper
  await p.locator("button.route", { hasText: "Caught by wicketkeeper" }).click(); await settle(p);
  await scrollTo(p, "#evidence");
  await p.screenshot({ path: `${out}/04-evidence-caught-keeper-mobile.png` });
  await p.locator(".dcard").first().click(); await settle(p);
  await p.screenshot({ path: `${out}/05-delivery-scene-mobile.png` });
  report.push({ shot: "player-mobile", errors }); await ctx.close();
}
// Desktop full pages for every test player + interactions
for (const [role, pl] of Object.entries(picks)) {
  const { p, ctx, errors } = await page({ width: 1280, height: 900 });
  await p.goto(`${BASE}/players/${pl.person_id}`); await settle(p);
  const checks = {};
  checks.coverage = await p.locator(".coverage").innerText();
  checks.notes = await p.locator(".note").allInnerTexts();
  checks.chips = await p.locator(".hero .chip").allInnerTexts();
  checks.routes = await p.locator("button.route").allInnerTexts();
  checks.matchup_rows = await p.locator(".mtable tbody tr").count();
  await p.screenshot({ path: `${out}/10-${role}-desktop.png`, fullPage: true });
  // filter: T20 + death overs
  await p.locator(".seg", { hasText: "Format" }).locator("button", { hasText: "T20" }).click();
  await p.locator(".seg", { hasText: "Phase" }).locator("button", { hasText: "Death" }).click(); await settle(p);
  checks.after_filter_url = p.url();
  checks.after_filter_routes = await p.locator("button.route").allInnerTexts();
  // drill into first non-zero route
  const nz = p.locator("button.route:not(.zero)").first();
  if (await nz.count()) {
    await nz.click(); await settle(p);
    checks.evidence = await p.locator("#evidence .mini").first().innerText();
    if (await p.locator(".dcard").count()) {
      await p.locator(".dcard").first().click(); await settle(p);
      checks.scene_banner = await p.locator(".modal .banner-rec, .modal .mini").first().innerText();
      checks.scene_unknowns = await p.locator(".modal .unk-chips .chip").allInnerTexts();
      await p.screenshot({ path: `${out}/11-${role}-delivery.png` });
      await p.keyboard.press("Escape");
    }
  }
  // matchup by pace/spin
  await p.locator("button", { hasText: "Pace / Spin" }).click(); await settle(p);
  checks.family_rows = await p.locator(".mtable tbody tr").allInnerTexts();
  report.push({ role, player: pl, checks, errors });
  await ctx.close();
}
// Mobile: matchups + situations for main player
{
  const { p, ctx, errors } = await page({ width: 390, height: 844 });
  await p.goto(`${BASE}/players/${main.person_id}`); await settle(p);
  await scrollTo(p, "section:nth-of-type(3)");
  await p.screenshot({ path: `${out}/06-matchups-mobile.png` });
  await scrollTo(p, "section:nth-of-type(4)");
  await p.screenshot({ path: `${out}/07-situations-mobile.png` });
  report.push({ shot: "sections-mobile", errors }); await ctx.close();
}
fs.writeFileSync(`${out}/report.json`, JSON.stringify(report, null, 2));
await browser.close();
console.log(JSON.stringify(report.map((r) => ({ k: r.role || r.shot, errors: r.errors.length })), null, 0));
