// Real-data Ask Cricket + What Happens Next screenshots. Usage: node screenshots-real-ask.mjs <outdir>
import { chromium } from "playwright";
import fs from "node:fs";
const out = process.argv[2];
const BASE = process.env.BASE || "http://localhost:3000";
const QS = ["How many times has Virat Kohli been run out?", "Who has dismissed Virat Kohli the most?",
  "What is Virat Kohli's strike rate against Jasprit Bumrah?", "How many sixes has Rohit Sharma hit in T20s?",
  "How does Virat Kohli perform while chasing?", "How many times has Kohli been caught behind?"];
const browser = await chromium.launch({ executablePath: process.env.CHROME || undefined });
const ctx = await browser.newContext({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 2 });
const p = await ctx.newPage();
const errors = [];
p.on("pageerror", (e) => errors.push(String(e)));
p.on("response", (r) => r.status() >= 400 && errors.push(`${r.status()} ${r.url()}`));
const settle = () => p.waitForLoadState("networkidle").then(() => p.waitForTimeout(400));
const log = [];
await p.goto(BASE + "/ask"); await settle();
for (const [i, q] of QS.entries()) {
  const before = await p.locator(".card").first().innerText().catch(() => "");
  await p.fill("input", q); await p.click("button[type=submit]");
  await p.waitForFunction((b) => { const c = document.querySelector(".card"); return c && c.innerText !== b; }, before, { timeout: 15000 });
  await settle();
  log.push({ q, a: (await p.locator(".card").first().innerText()).split("\n").slice(0, 4).join(" | ") });
  await p.locator(".card").first().screenshot({ path: `${out}/ask-${i + 1}.png` });
}
await p.goto(BASE + "/play"); await settle();
const state = await p.locator(".hero").innerText();
await p.screenshot({ path: `${out}/whn-question.png`, fullPage: true });
await p.locator("button", { hasText: /^1/ }).first().click(); await settle();
await p.screenshot({ path: `${out}/whn-reveal.png`, fullPage: true });
const reveal = await p.locator(".card").last().innerText();
await p.locator("button", { hasText: "Inspect the delivery" }).click(); await settle();
await p.screenshot({ path: `${out}/whn-inspect-delivery.png` });
fs.writeFileSync(`${out}/report.json`, JSON.stringify({ errors, log, whn_state: state, whn_reveal: reveal }, null, 2));
await browser.close();
console.log(JSON.stringify({ errors: errors.length }));
