// Ask Cricket v0 + What Happens Next screenshots. Usage: node scripts/screenshots-2.mjs <outdir>
import { chromium } from "playwright";
import fs from "node:fs";
const out = process.argv[2];
const BASE = process.env.BASE || "http://localhost:3000";
const browser = await chromium.launch({ executablePath: process.env.CHROME || undefined });
const ctx = await browser.newContext({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 2 });
const p = await ctx.newPage();
const errors = [];
p.on("pageerror", (e) => errors.push(String(e)));
p.on("response", (r) => r.status() >= 400 && errors.push(`${r.status()} ${r.url()}`));
const settle = () => p.waitForLoadState("networkidle").then(() => p.waitForTimeout(400));
const log = [];
await p.goto(BASE + "/ask"); await settle();
const chips = await p.locator(".chip").allInnerTexts();
for (const [i, idx] of [[1, 0], [2, 3], [3, 4], [4, 8]]) {
  await p.locator(".chip").nth(idx).click(); await settle();
  log.push({ q: chips[idx], a: await p.locator(".card").first().innerText() });
  await p.screenshot({ path: `${out}/0${i}-ask-mobile.png`, fullPage: true });
}
await p.fill("input", "Is anyone good at cricket?"); await p.click("button[type=submit]"); await settle();
log.push({ q: "unsupported", a: await p.locator(".card").first().innerText() });
await p.goto(BASE + "/play"); await settle();
await p.screenshot({ path: `${out}/05-whn-question-mobile.png`, fullPage: true });
await p.locator("button", { hasText: /^DOT/ }).first().click(); await settle();
await p.screenshot({ path: `${out}/06-whn-reveal-mobile.png`, fullPage: true });
log.push({ whn: await p.locator(".card").last().innerText() });
await p.locator("button", { hasText: "Next moment" }).click(); await settle();
await p.locator("button", { hasText: /^WICKET/ }).first().click(); await settle();
log.push({ whn2: (await p.locator(".card").last().innerText()).slice(0, 120), stored: await p.evaluate(() => localStorage.getItem("whn")) });
fs.writeFileSync(`${out}/report.json`, JSON.stringify({ errors, log }, null, 2));
await browser.close();
console.log(JSON.stringify({ errors }));
