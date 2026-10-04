// Phase 8: ten golden journeys, real data, 390px phone, each in a fresh browser (a new fan).
// Every journey asserts the screens it passes through, and the run fails on any console error, failed request,
// HTTP ≥ 400 from our own servers, or sideways overflow on any screen visited.
// Usage: CHROME=... node golden-phase8.mjs <outdir>
import { chromium } from "playwright";
import fs from "fs";
const BASE = process.env.BASE || "http://localhost:3000";
const out = process.argv[2] || "golden8"; fs.mkdirSync(out, { recursive: true });
const KOHLI = "ba607b88", ZAMPA = "14f96089", BUMRAH = "462411b3", MCG = "1298150";
const b = await chromium.launch({ executablePath: process.env.CHROME });
const results = [];

async function journey(n, name, fn) {
  const ctx = await b.newContext({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 1 });
  const p = await ctx.newPage();
  const errs = [], steps = [], fails = [];
  p.on("console", (m) => { if (m.type() === "error") errs.push(m.text().slice(0, 200)); });
  p.on("pageerror", (e) => errs.push(String(e).slice(0, 200)));
  p.on("requestfailed", (r) => { const u = r.url(); if (r.failure()?.errorText === "net::ERR_ABORTED") return; // navigation-cancelled prefetch / in-flight fetch: expected
    if (u.startsWith(BASE) || u.includes(":8000")) errs.push(`requestfailed ${u} ${r.failure()?.errorText}`); });
  p.on("response", (r) => { const u = r.url(); if ((u.startsWith(BASE) || u.includes(":8000")) && r.status() >= 400) errs.push(`HTTP ${r.status()} ${u}`); });
  await p.goto(BASE + "/data"); await p.evaluate(() => localStorage.setItem("ci-preview-notice", "1"));
  const t0 = Date.now();
  const ok = (c, msg) => { if (!c) fails.push(msg); };
  const settle = async (ms = 900) => { await p.waitForLoadState("networkidle").catch(() => {}); await p.waitForTimeout(ms); };
  const step = async (label) => {
    const ov = await p.evaluate(() => document.documentElement.scrollWidth - innerWidth);
    ok(ov <= 0, `${label}: sideways overflow ${ov}px`);
    steps.push({ label, url: p.url().replace(BASE, ""), ms: Date.now() - t0 });
  };
  try { await fn(p, { ok, settle, step }); } catch (e) { fails.push(`exception: ${String(e).split("\n")[0]}`); }
  await p.screenshot({ path: `${out}/j${String(n).padStart(2, "0")}.png` }).catch(() => {});
  const r = { n, name, pass: !fails.length && !errs.length, fails, errs, steps, ms: Date.now() - t0 };
  results.push(r); console.log(`${r.pass ? "PASS" : "FAIL"} J${n} ${name} (${r.steps.length} screens, ${r.ms} ms)${fails.length ? " :: " + fails.join(" | ") : ""}${errs.length ? " :: ERR " + errs.slice(0, 3).join(" | ") : ""}`);
  await ctx.close();
}

// 1. New fan → Kohli
await journey(1, "new fan → Kohli", async (p, { ok, settle, step }) => {
  await p.goto(BASE + "/", { waitUntil: "networkidle" }); await settle();
  ok(await p.locator("#home-title").isVisible(), "home title not visible");
  ok(await p.locator("[data-testid=home-examples] .launch-row").count() === 5, "home: not 5 hero examples");
  const sb = await p.locator("form[role=search] input").boundingBox(); ok(sb && sb.y < 844, "search box not in first viewport");
  await step("home");
  await p.locator(".launch-row.h-player").click(); await p.waitForURL(/\/players\//); await settle(1200);
  ok(p.url().includes(KOHLI), "player example did not open Kohli");
  ok(await p.locator("h1").innerText().then((t) => /kohli/i.test(t)), "player h1 is not Kohli");
  const def = await p.locator("[data-testid=defining-insight]").boundingBox(); ok(def && def.y < 844 * 1.25, "defining insight not near the fold");
  ok(await p.locator("[data-testid=player-actions] a").count() >= 4, "fewer than 4 player actions");
  const h = await p.evaluate(() => document.documentElement.scrollHeight); ok(h <= 844 * 5.2, `Kohli overview is ${(h / 844).toFixed(1)} screens (>5)`);
  await step("player");
});

// 2. Kohli → dismissal evidence
await journey(2, "Kohli → dismissal evidence", async (p, { ok, settle, step }) => {
  await p.goto(`${BASE}/players/${KOHLI}`, { waitUntil: "networkidle" }); await settle(1200); await step("player");
  await p.click("[data-testid=explore-how-out-home]"); await p.waitForURL(/\/how-out\//); await settle(1200); await step("how-out");
  await p.locator("[data-testid=dim-route] button").first().click(); await settle(800);
  const rows = p.locator("[data-testid=every-dismissal] .trow"); ok(await rows.count() >= 1, "no dismissal evidence rows after filtering");
  await rows.first().click(); await p.waitForURL(/\/delivery\//); await settle(1500);
  ok(/OBSERVED|RECONSTRUCTED|DERIVED/.test(await p.locator("main").innerText()), "delivery evidence has no provenance tag");
  await step("evidence");
});

// 3. Kohli → Zampa battle
await journey(3, "Kohli → Zampa battle", async (p, { ok, settle, step }) => {
  await p.goto(`${BASE}/players/${KOHLI}`, { waitUntil: "networkidle" }); await settle(1500); await step("player");
  const zr = p.locator("[data-testid=biggest-battles] a", { hasText: "Zampa" }).first();
  ok(await zr.count() === 1, "Zampa not in Kohli's biggest battles"); await zr.click();
  await p.waitForURL(/\/battle\?/); await settle(1500);
  const hero = p.locator("[data-testid=battle-hero]"); ok(await hero.isVisible(), "battle hero missing");
  const ht = await hero.innerText(); ok(/Kohli/.test(ht) && /Zampa/.test(ht) && /385/.test(ht) && /425/.test(ht), `battle hero numbers wrong: ${ht.replace(/\n/g, " ").slice(0, 120)}`);
  const hb = await hero.boundingBox(); ok(hb && hb.y + hb.height < 844, "battle hero not fully above the fold");
  ok(await p.locator("[data-testid=battle-changes] .half").count() === 2, "no earlier/later halves");
  ok(await p.locator("[data-testid=battle-meetings] .mt-row").count() === 8, "meetings not collapsed to 8");
  await p.click("[data-testid=meetings-all]"); ok(await p.locator("[data-testid=battle-meetings] .mt-row").count() === 30, "not 30 meetings when expanded");
  ok(/don't declare a winner/i.test(await p.locator("[data-testid=battle-compared]").innerText()), "no-winner safeguard text missing");
  await step("battle");
});

// 4. MCG 2022 → innings replay
await journey(4, "MCG 2022 → innings replay", async (p, { ok, settle, step }) => {
  await p.goto(`${BASE}/match/${MCG}`, { waitUntil: "networkidle" }); await settle(1500);
  ok(await p.locator("[data-testid=match-story] .beat").count() >= 3, "match story has fewer than 3 beats");
  const st = await p.locator("[data-testid=match-story]").boundingBox(); const sc = await p.locator(".crease-head").first().boundingBox();
  ok(st && sc && st.y < sc.y, "story is not above the scorecard"); await step("match");
  await p.locator("[data-testid=match-story] .beat", { hasText: "Standout innings" }).click(); await p.waitForURL(/\/innings\//); await settle(1500);
  ok(/82/.test(await p.locator("main").innerText()), "innings page does not show 82"); await step("innings");
  await p.goto(`${BASE}/match/${MCG}`, { waitUntil: "networkidle" }); await settle(800);
  await p.click("[data-testid=match-replay]"); await p.waitForURL(/\/live-lab\//); await settle(1500);
  ok(/not live/i.test(await p.locator("[data-testid=replay-flag]").innerText()), "replay not flagged as historical"); await step("replay");
});

// 5. Match → Play (spoiler-safe)
await journey(5, "Match → Play", async (p, { ok, settle, step }) => {
  await p.goto(`${BASE}/match/${MCG}`, { waitUntil: "networkidle" }); await settle(1500); await step("match");
  const mh = await p.locator("[data-testid=play-moment]").first().getAttribute("href"); ok(!!mh, "no Play moment on the match");
  await p.goto(BASE + mh, { waitUntil: "networkidle" }); await settle(1500);
  const n = Number(await p.locator("[data-testid=position]").getAttribute("data-n"));
  ok(await p.locator("[data-testid=reveal]").count() === 0, "reveal visible before the pick (spoiler)");
  ok(await p.locator("[data-testid=explore-next]").count() === 0, "onward links before the end (spoiler)"); await step("moment");
  await p.click("[data-testid=pick-1]"); await p.waitForSelector("[data-testid=reveal]", { timeout: 15000 });
  ok(Number(await p.locator("[data-testid=position]").getAttribute("data-n")) >= n, "cursor moved backwards"); await step("reveal");
});

// 6. Bumrah → best spell
await journey(6, "Bumrah → best spell", async (p, { ok, settle, step }) => {
  await p.goto(`${BASE}/players/${BUMRAH}`, { waitUntil: "networkidle" }); await settle(1500);
  ok(await p.locator("[data-testid=how-wickets]").count() === 1, "Bumrah: bowler layout missing 'how the wickets come'");
  ok(await p.locator("[data-testid=how-out-summary]").count() === 0, "Bumrah: batter block shown on a bowler page"); await step("player");
  await p.locator("[data-testid=player-stories] .perf", { hasText: "Best spell" }).click(); await p.waitForURL(/\/spell\//); await settle(1500);
  ok(/Bumrah/.test(await p.locator("main").innerText()), "spell page lacks Bumrah"); await step("spell");
});

// 7. Mandhana → partnership
await journey(7, "Mandhana → partnership", async (p, { ok, settle, step }) => {
  await p.goto(`${BASE}/search?q=Mandhana`, { waitUntil: "networkidle" }); await settle(1500); await step("search");
  await p.locator("main a[href^='/players/']").first().click(); await p.waitForURL(/\/players\//);
  ok(await p.waitForFunction(() => /Mandhana/.test(document.querySelector("h1")?.textContent || ""), null, { timeout: 15000 }).then(() => true).catch(() => false), "search did not lead to Mandhana"); await settle(1200); await step("player");
  await p.locator("[data-testid=explore-more] button", { hasText: "Partnerships" }).click(); await settle(1500);
  const pl = p.locator("a[href^='/partnerships?p1=']").first(); ok(await pl.count() === 1, "no partner link"); await pl.click();
  await p.waitForURL(/\/partnerships\?/); await settle(1500);
  ok(/Mandhana/.test(await p.locator("main").innerText()), "partnership page lacks Mandhana"); await step("partnership");
});

// 8. Ask → answer → follow-up
await journey(8, "Ask → answer → follow-up", async (p, { ok, settle, step }) => {
  await p.goto(`${BASE}/ask`, { waitUntil: "networkidle" }); await settle(800);
  ok(await p.locator("[data-testid=ask-empty] .ask-group").count() === 6, "Ask empty state lacks 6 groups"); await step("ask");
  await p.locator(".ask-q", { hasText: "Who dismisses Kohli most?" }).click(); await p.waitForSelector("[data-testid=ask-answer]"); await settle(800);
  ok(/Zampa/.test(await p.locator("[data-testid=ask-answer]").innerText()), "answer lacks Zampa");
  const fu = p.locator("[data-testid=ask-followups] .ask-q"); ok(await fu.count() >= 1 && await fu.count() <= 2, "not 1–2 follow-ups"); await step("answer");
  await fu.first().click(); await settle(1500);
  ok(/425|385/.test(await p.locator("[data-testid=ask-answer]").innerText()), "follow-up did not answer Kohli v Zampa"); await step("follow-up");
});

// 9. Record → player → evidence
await journey(9, "record → player → evidence", async (p, { ok, settle, step }) => {
  await p.goto(`${BASE}/records/highest-score.male.T20.major`, { waitUntil: "networkidle" }); await settle(1200);
  ok(await p.locator("[data-testid=record-rows] a").count() >= 5, "record has fewer than 5 rows"); await step("record");
  await p.locator("[data-testid=record-rows] a").first().click(); await settle(1500); await step("record row");
  if (!/\/players\//.test(p.url())) { const pl = p.locator("main a[href^='/players/']").first(); ok(await pl.count() >= 1, "no player link from the record row"); await pl.click(); await p.waitForURL(/\/players\//); await settle(1500); }
  await step("player");
  const d = p.locator("[data-testid=defining-insight] button, [data-testid=what-different] button.why-btn", { hasText: /Deliveries/ }).first();
  ok(await d.count() === 1, "no evidence button on the player"); await d.click(); await settle(1500);
  ok(await p.locator(".dcard").count() >= 1, "evidence list empty"); await step("evidence");
});

// 10. Home → 5+ entity rabbit hole
await journey(10, "Explore → 5+ entity rabbit hole", async (p, { ok, settle, step }) => {
  await p.goto(`${BASE}/?day=2026-10-04`, { waitUntil: "networkidle" }); await settle(800); await step("home");
  await p.locator(".keep-links a", { hasText: "Rabbit hole" }).click(); await settle(1500); await step("start");
  const seen = new Set([p.url()]);
  for (let i = 0; i < 5; i++) {
    await p.waitForSelector("[data-testid=explore-next] .xnext-row", { timeout: 20000 });
    const rows = await p.locator("[data-testid=explore-next] .xnext-row").evaluateAll((as) => as.map((a) => a.getAttribute("href")));
    const nx = rows.find((h) => !seen.has(BASE + h) && !/\/live-lab\//.test(h)); ok(!!nx, `hop ${i + 1}: no fresh destination`); if (!nx) break;
    await p.locator(`[data-testid=explore-next] .xnext-row[href="${nx}"]`).first().click(); await p.waitForURL((u) => u.toString() !== [...seen].pop()); await settle(1500);
    seen.add(p.url()); await step(`hop ${i + 1}`);
  }
  ok(seen.size >= 6, `only ${seen.size - 1} hops`);
  const mem = await p.evaluate(() => JSON.parse(localStorage.getItem("ci-memory-v1") || "{}")); const n = (mem.visited || []).length;
  ok(n >= 5, `session memory holds ${n} entities (<5)`);
});

fs.writeFileSync(`${out}/golden.json`, JSON.stringify(results, null, 1));
const pass = results.filter((r) => r.pass).length;
console.log(`\nGOLDEN ${pass}/${results.length}`);
await b.close();
process.exit(pass === results.length ? 0 : 1);
