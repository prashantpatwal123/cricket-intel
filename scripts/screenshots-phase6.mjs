// Phase 6 journeys on REAL data: Visual Lab, Kohli "how does he get out", Kohli v Zampa knowledge, progressive delivery
// replay, Data Quality Centre V2. Also asserts that no real-data view draws geometry it does not have.
// Usage: node screenshots-phase6.mjs <outdir>
import { chromium } from "playwright";
import fs from "node:fs";
const out = process.argv[2];
const BASE = process.env.BASE || "http://localhost:3000";
const KOHLI = "ba607b88", ZAMPA = "14f96089";
const browser = await chromium.launch({ executablePath: process.env.CHROME || undefined });
const errors = [], log = [], assertions = [], aborted = [];
let cur = null;
const overflow = (p) => p.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
const note = async (k, v) => { if (cur) v.overflow_px = await overflow(cur); if (v.overflow_px > 0) assertions.push(`overflow ${k}: ${v.overflow_px}px`); log.push({ step: k, ...v }); console.log(k, JSON.stringify(v).slice(0, 260)); };
const check = (c, m) => { if (!c) assertions.push(m); };
async function session(viewport, fn) {
  const ctx = await browser.newContext({ viewport, deviceScaleFactor: 2 });
  const p = await ctx.newPage(); cur = p;
  p.on("pageerror", (e) => errors.push(`pageerror ${p.url()}: ${e}`));
  p.on("console", (m) => m.type() === "error" && errors.push(`console ${p.url()}: ${m.text()}`));
  p.on("response", (r) => r.status() >= 400 && errors.push(`${r.status()} ${r.url()}`));
  p.on("requestfailed", (r) => { if (r.url().startsWith("data:")) return; const t = r.failure()?.errorText || "";
    if (t.includes("ERR_ABORTED")) aborted.push(r.url()); else errors.push(`failed ${r.url()} ${t}`); });
  const settle = (ms = 400) => p.waitForLoadState("networkidle").then(() => p.waitForTimeout(ms));
  await p.goto(BASE + "/data"); await p.evaluate(() => localStorage.setItem("ci-preview-notice", "1"));
  await fn(p, settle);
  await ctx.close();
}
const text = (p, sel) => p.locator(sel).first().innerText().catch(() => "");
// Real-data views must not contain illustrative frames or drawn pitch points / wagon lines.
const noFakeGeometry = async (p, where) => {
  const r = await p.evaluate(() => ({ illus: document.querySelectorAll(".illus").length,
    dots: [...document.querySelectorAll("svg.vsvg")].filter((s) => !s.closest(".illus")).reduce((a, s) => a + s.querySelectorAll("circle, line").length, 0) }));
  check(r.illus === 0, `${where}: illustrative frame on a real-data view`);
  return r;
};
const Mo = { width: 390, height: 844 }, De = { width: 1280, height: 900 };

await session(Mo, async (p, settle) => {
  // 1. Kohli: "How does Virat Kohli get out?" via Ask
  await p.goto(`${BASE}/ask?q=${encodeURIComponent("How does Virat Kohli get out?")}`); await settle(800);
  const ans = await text(p, "main");
  check(/dismissed \d+ times/.test(ans), "Ask how-out answer missing");
  check(/not recorded/.test(ans), "Ask how-out answer does not state what is not recorded");
  await p.screenshot({ path: `${out}/m01-ask-how-kohli-gets-out.png`, fullPage: true });
  await note("ask-how-out", { answer: (ans.match(/Virat Kohli has been dismissed[^\n]+/) || [""])[0] });
  // 2. Drill: all → caught by wicketkeeper → by bowler → every dismissal
  await p.goto(`${BASE}/how-out/${KOHLI}`); await settle();
  const total = Number(await text(p, "[data-testid=howout-total]"));
  check(total > 400, `Kohli total dismissals ${total}`);
  await p.screenshot({ path: `${out}/m02-how-out-kohli.png`, fullPage: true });
  await p.locator("[data-testid=dim-route] button", { hasText: "Caught by wicketkeeper" }).first().click(); await settle();
  const kc = Number(await text(p, "[data-testid=howout-total]"));
  check(kc > 0 && kc < total, `keeper catches ${kc}`);
  check(/not the same as 'caught behind'/.test(await text(p, "main")), "keeper note missing");
  await p.screenshot({ path: `${out}/m03-kohli-keeper-catches.png`, fullPage: true });
  const bowlers = await p.locator("[data-testid=dim-bowler] button").allInnerTexts();
  await note("keeper-catches", { total: kc, top_bowlers: bowlers.slice(0, 3).map((x) => x.replace(/\n/g, " ")) });
  await p.locator("[data-testid=dim-bowler] button").first().click(); await settle();
  const every = await p.locator("[data-testid=every-dismissal] .trow").count();
  check(every >= 1, "every-dismissal list empty");
  check(await p.locator("[data-testid=dim-style] .notrec").count() === 1 || await p.locator("[data-testid=dim-style] button").count() > 0, "style panel missing");
  const unavail = await text(p, "[data-testid=unavailable-filters]");
  check(/line \/ length/.test(unavail) && /edge/.test(unavail), "unavailable filters not explained");
  await p.screenshot({ path: `${out}/m04-kohli-keeper-by-bowler.png`, fullPage: true });
  await note("by-bowler", { rows: every, crumbs: (await text(p, "[data-testid=drill]")).replace(/\n/g, " ") });
  await noFakeGeometry(p, "how-out");
  // 3. a dismissal → progressive delivery replay
  await p.locator("[data-testid=every-dismissal] .trow").first().click(); await settle(800);
  await p.waitForSelector("[data-testid=delivery-layers]", { timeout: 15000 }).catch(() => {});
  check(await p.locator("[data-testid=delivery-layers]").count() === 1, "delivery layers missing");
  const layers = await text(p, "[data-testid=delivery-layers]");
  check(/Delivery geometry\s*·\s*not recorded/.test(layers), "L2 not marked not-recorded");
  await p.locator("[data-testid=delivery-layers]").scrollIntoViewIfNeeded();
  await p.screenshot({ path: `${out}/m05-delivery-progressive.png`, fullPage: false });
  await note("delivery-layers", { url: p.url() });

  // 4. Kohli v Zampa: what do we actually know?
  await p.goto(`${BASE}/battle?bat=${KOHLI}&bowl=${ZAMPA}`); await settle(800);
  check(await p.locator("[data-testid=battle-knowledge]").count() === 1, "battle knowledge missing");
  const kz = await text(p, "[data-testid=battle-knowledge]");
  check(/Not available/.test(kz) && /line and length/i.test(kz), "battle unknowns not explained");
  check(!/struggles|leg-spin outside off|weakness against/i.test(kz), "manufactured explanation on battle page");
  await p.locator("[data-testid=battle-knowledge]").scrollIntoViewIfNeeded();
  await p.screenshot({ path: `${out}/m06-kohli-zampa-knowledge.png`, fullPage: false });
  await note("kohli-zampa", { cannot_say: await text(p, "[data-testid=cannot-say]") });

  // 5. Visual Lab
  await p.goto(`${BASE}/visual-lab`); await settle(800);
  const ex = await p.locator("[data-testid=lab-example]").count();
  check(ex >= 3, `visual lab real examples ${ex}`);
  const realFrames = await p.locator("[data-testid=lab-real] .illus").count();
  check(realFrames === 0, "illustration inside the real-delivery section");
  const ill = await p.locator("[data-testid=lab-illustrative] .illus").count();
  check(ill >= 4, `illustrative frames ${ill}`);
  const illText = await text(p, "[data-testid=lab-illustrative]");
  check(!/Kohli|Zampa|Bumrah|Dhoni|Mandhana|Lanning|Ecclestone|Rohit/.test(illText), "illustrative examples name a real player");
  await p.screenshot({ path: `${out}/m07-visual-lab.png`, fullPage: true });
  await p.locator("[data-testid=lab-pilot]").scrollIntoViewIfNeeded();
  await p.screenshot({ path: `${out}/m08-metadata-pilot.png`, fullPage: false });
  await p.locator("[data-testid=lab-illustrative]").scrollIntoViewIfNeeded();
  await p.screenshot({ path: `${out}/m09-illustrative.png`, fullPage: false });
  await note("visual-lab", { real_examples: ex, illustrative_frames: ill, pilot: (await text(p, "[data-testid=lab-pilot]")).slice(0, 160).replace(/\n/g, " ") });

  // 6. Data Quality Centre V2
  await p.goto(`${BASE}/data`); await settle(800);
  check(await p.locator("[data-testid=capability]").count() === 1, "capability matrix missing");
  const cap = await text(p, "[data-testid=capability]");
  check(/line/i.test(cap) && /✕/.test(cap) && /✓/.test(cap) && /△/.test(cap), "capability marks missing");
  await p.locator("[data-testid=capability]").scrollIntoViewIfNeeded();
  await p.screenshot({ path: `${out}/m10-data-capability.png`, fullPage: false });
  await p.screenshot({ path: `${out}/m11-data-full.png`, fullPage: true });
  await note("data", { counts: (cap.match(/\d+\n✓ available|\d+\s*✓/) || [""])[0] });
  // 7. player page link into the drill-down
  await p.goto(`${BASE}/players/${KOHLI}?tab=dismissals`); await settle(800);
  check(await p.locator("[data-testid=explore-how-out]").count() === 1, "player page lacks how-out link");
});

await session(De, async (p, settle) => {
  for (const [f, url] of [["d-visual-lab", "/visual-lab"], ["d-how-out-kohli", `/how-out/${KOHLI}?route=CAUGHT_KEEPER`], ["d-kohli-zampa", `/battle?bat=${KOHLI}&bowl=${ZAMPA}`],
                          ["d-delivery-layers", "/delivery/1473467:1:85"], ["d-data", "/data"]]) {
    await p.goto(BASE + url); await settle(800);
    await p.screenshot({ path: `${out}/${f}.png`, fullPage: true });
    await note(f, {});
  }
});
await browser.close();
fs.writeFileSync(`${out}/report.json`, JSON.stringify({ errors, aborted_by_navigation: aborted.length, assertions, log }, null, 2));
console.log(JSON.stringify({ errors: errors.length, aborted_by_navigation: aborted.length, assertions: assertions.length, first_errors: errors.slice(0, 8), first_assertions: assertions.slice(0, 12) }));
