// Phase 2 screenshots + interaction checks on REAL data. Usage: node screenshots-phase2.mjs <outdir>
import { chromium } from "playwright";
import fs from "node:fs";
const out = process.argv[2];
const BASE = process.env.BASE || "http://localhost:3000";
const KOHLI = "ba607b88", ZAMPA = "14f96089", MANDHANA = "5d2eda89", LANNING = "27e003ce", BUMRAH = "462411b3", DHONI = "4a8a2e3b";
const browser = await chromium.launch({ executablePath: process.env.CHROME || undefined });
const errors = [], log = [];
let curPage = null;
const note = async (k, v) => { if (curPage) v.overflow_px = await overflow(curPage); log.push({ step: k, ...v }); console.log(k, JSON.stringify(v).slice(0, 200)); };

async function session(viewport, fn) {
  const ctx = await browser.newContext({ viewport, deviceScaleFactor: 2 });
  const p = await ctx.newPage();
  p.on("pageerror", (e) => errors.push(`pageerror ${p.url()}: ${e}`));
  p.on("console", (m) => m.type() === "error" && errors.push(`console ${p.url()}: ${m.text()}`));
  p.on("response", (r) => r.status() >= 400 && errors.push(`${r.status()} ${r.url()}`));
  curPage = p;
  const settle = (ms = 500) => p.waitForLoadState("networkidle").then(() => p.waitForTimeout(ms));
  await fn(p, settle);
  // horizontal overflow check on every page we visited is done per step
  await ctx.close();
}
const overflow = (p) => p.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);

const M = { width: 390, height: 844 }, D = { width: 1280, height: 900 };

await session(M, async (p, settle) => {
  await p.goto(BASE + "/"); await settle(800);
  await p.screenshot({ path: `${out}/m01-explore.png`, fullPage: true });
  await note("explore", { insights: await p.locator(".icard").count(), battles: await p.locator(".bcard").count(), records: await p.locator(".rcard").count(), overflow: await overflow(p) });
  await p.locator(".icard button", { hasText: "WHY?" }).first().click(); await p.waitForTimeout(300);
  await p.locator(".icard").first().screenshot({ path: `${out}/m02-explore-insight-why.png` });

  await p.goto(`${BASE}/players/${KOHLI}`); await settle(1200);
  await p.screenshot({ path: `${out}/m03-player-overview.png`, fullPage: true });
  await note("player-overview", { petals: await p.locator(".petal").count(), overflow: await overflow(p) });
  await p.locator(".fp-svg text", { hasText: "Death SR" }).first().click().catch(() => {});
  await p.waitForTimeout(300);
  await p.locator(".fp").screenshot({ path: `${out}/m04-fingerprint-selected.png` });
  await p.locator(".fp-detail button", { hasText: "See the deliveries" }).click(); await settle();
  await p.locator("#evidence").screenshot({ path: `${out}/m05-fingerprint-drill-deliveries.png` });
  await note("fingerprint-drill", { title: (await p.locator("#evidence").innerText()).split("\n")[0], cards: await p.locator("#evidence .dcard").count() });

  await p.locator(".tabs button", { hasText: "Strengths" }).click(); await settle(1000);
  await p.locator(".icard button", { hasText: "WHY?" }).first().click(); await p.waitForTimeout(300);
  await p.screenshot({ path: `${out}/m06-strengths.png`, fullPage: true });
  await note("strengths", { cards: await p.locator(".icard").count(), url: p.url() });

  await p.locator(".tabs button", { hasText: "Dismissals" }).click(); await settle();
  await p.locator(".route", { hasText: "Caught by wicketkeeper" }).first().click(); await settle(900);
  await p.screenshot({ path: `${out}/m07-dismissal-story.png`, fullPage: true });
  const story = await p.locator(".story").innerText();
  await note("dismissal-story", { head: story.split("\n").slice(0, 3).join(" | "), saysEdge: /edge|edged/i.test(await p.locator("main").innerText()) });

  await p.locator(".tabs button", { hasText: "Matchups" }).click(); await settle(900);
  await p.locator(".mcards").screenshot({ path: `${out}/m08-matchups-cards.png` });
  await note("matchups-mobile", { cards: await p.locator(".mcard").count(), tableVisible: await p.locator(".mtable").first().isVisible() });

  await p.goto(`${BASE}/players/${LANNING}?tab=timeline`); await settle(1000);
  await p.screenshot({ path: `${out}/m09-timeline-lanning.png`, fullPage: true });
  await note("timeline", { overflow: await overflow(p) });

  await p.goto(`${BASE}/battle?bat=${KOHLI}&bowl=${ZAMPA}`); await settle(1000);
  await p.screenshot({ path: `${out}/m10-battle.png`, fullPage: true });
  await p.locator(".seg button", { hasText: "Setting / chasing" }).click(); await p.waitForTimeout(200);
  await p.locator("button.brk").first().click(); await settle();
  await note("battle", { edge: (await p.locator(".card", { hasText: "Who has the edge" }).innerText()).slice(0, 400), drill: (await p.locator("#evidence").innerText()).split("\n")[0], overflow: await overflow(p) });
  await p.locator("#evidence").screenshot({ path: `${out}/m11-battle-drill.png` });

  await p.goto(`${BASE}/battle`); await settle();
  await p.locator(".picker input").first().fill("Mandhana"); await p.waitForTimeout(700);
  await p.locator(".results .res").first().click();
  await p.locator(".picker input").first().fill("Ecclestone"); await p.waitForTimeout(700);
  await p.locator(".results .res").first().click(); await settle(1000);
  await p.screenshot({ path: `${out}/m12-battle-picked-women.png`, fullPage: true });
  await note("battle-picker", { url: p.url(), head: (await p.locator(".hero").innerText().catch(() => "not met")).split("\n").slice(0, 3).join(" | ") });

  await p.goto(`${BASE}/compare?ids=${KOHLI},${MANDHANA},${LANNING}`); await settle(1000);
  await p.screenshot({ path: `${out}/m13-compare.png`, fullPage: true });
  await note("compare", { warnings: await p.locator(".cmp-warn li").count(), overflow: await overflow(p) });

  await p.goto(`${BASE}/records?preset=death-economy&gender=male`); await settle(1200);
  await p.screenshot({ path: `${out}/m14-records.png`, fullPage: true });
  await note("records", { url: p.url(), rows: await p.locator(".rec-row").count(), first: await p.locator(".rec-row").first().innerText() });
  await p.locator(".seg button", { hasText: "Women" }).click(); await settle(900);
  const wfirst = await p.locator(".rec-row").first().innerText();
  await p.locator(".rec-row").first().click(); await settle(900);
  await note("records-row-click", { women_first: wfirst, landed: p.url() });

  await p.goto(`${BASE}/ask?q=${encodeURIComponent("Lowest economy in death overs since 2020")}`); await settle(1000);
  await p.screenshot({ path: `${out}/m15-ask-leaderboard.png`, fullPage: true });
  const before = await p.locator(".ans").innerText();
  await p.locator(".ichip", { hasText: "Full members" }).locator("button").click(); await settle(900);
  const after = await p.locator(".ans").innerText();
  await note("ask-remove-chip", { before, after });
  await p.locator("button", { hasText: "Show the pipeline" }).click(); await p.waitForTimeout(200);
  await p.locator(".interp").screenshot({ path: `${out}/m16-ask-interpretation.png` });
  await p.goto(`${BASE}/ask?q=${encodeURIComponent("Bumrah v Warner")}`); await settle(900);
  await note("ask-matchup", { ans: await p.locator(".ans").innerText(), chips: await p.locator(".interp").innerText() });
  await p.screenshot({ path: `${out}/m17-ask-matchup.png`, fullPage: true });
  await p.goto(`${BASE}/ask?q=${encodeURIComponent("Sharma strike rate")}`); await settle(900);
  await p.screenshot({ path: `${out}/m18-ask-ambiguous.png`, fullPage: true });
  await p.locator(".card", { hasText: "Which" }).locator(".chip").first().click(); await settle(1000);
  await note("ask-disambiguate", { ans: await p.locator(".ans").innerText().catch(() => "none") });

  await p.goto(`${BASE}/play`); await settle(900);
  await p.screenshot({ path: `${out}/m19-play-question.png`, fullPage: true });
  await p.keyboard.press("1"); await settle(500);
  await p.screenshot({ path: `${out}/m20-play-reveal.png`, fullPage: true });
  const r1 = await p.locator(".mvy").innerText();
  const t0 = Date.now(); await p.keyboard.press("Enter"); await p.locator(".pick:not([disabled])").first().waitFor(); const nextMs = Date.now() - t0;
  await p.keyboard.press("0"); await settle(400);
  await note("play", { after1: r1.replace(/\n/g, " "), after2: (await p.locator(".mvy").innerText()).replace(/\n/g, " "), next_ball_ms: nextMs });
});

await session(D, async (p, settle) => {
  await p.goto(BASE + "/"); await settle(800);
  await p.screenshot({ path: `${out}/d01-explore.png`, fullPage: true });
  await p.goto(`${BASE}/players/${KOHLI}`); await settle(1200);
  await p.screenshot({ path: `${out}/d02-player-overview.png`, fullPage: true });
  await p.goto(`${BASE}/players/${BUMRAH}`); await settle(1200);
  await p.locator(".fp").screenshot({ path: `${out}/d03-fingerprint-bowler.png` });
  await p.goto(`${BASE}/players/${DHONI}?tab=dismissals&route=STUMPED`); await settle(1200);
  await p.screenshot({ path: `${out}/d04-dismissals-dhoni.png`, fullPage: true });
  await p.goto(`${BASE}/players/${KOHLI}?tab=timeline`); await settle(1000);
  await p.locator(".section").first().screenshot({ path: `${out}/d05-timeline-kohli.png` });
  await p.goto(`${BASE}/battle?bat=${KOHLI}&bowl=${ZAMPA}`); await settle(1000);
  await p.screenshot({ path: `${out}/d06-battle.png`, fullPage: true });
  await p.goto(`${BASE}/compare?ids=${KOHLI},${MANDHANA},${LANNING}&format=T20&team_type=international`); await settle(1000);
  await p.screenshot({ path: `${out}/d07-compare-t20i.png`, fullPage: true });
  await p.goto(`${BASE}/records?preset=one-bowler&gender=male`); await settle(1200);
  await p.screenshot({ path: `${out}/d08-records-pairs.png`, fullPage: true });
  await p.locator(".rec-row").first().click(); await settle(1000);
  await note("records-pair-click", { landed: p.url() });
  await p.goto(`${BASE}/play`); await settle(800);
  await p.keyboard.press("4"); await settle(400);
  await p.screenshot({ path: `${out}/d09-play-reveal.png`, fullPage: true });
});

fs.writeFileSync(`${out}/report.json`, JSON.stringify({ errors, log }, null, 2));
await browser.close();
console.log(JSON.stringify({ errors: errors.length, first: errors.slice(0, 8) }));
