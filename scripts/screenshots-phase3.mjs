// Phase 3 screenshots + interaction checks on REAL data. Usage: node screenshots-phase3.mjs <outdir>
// Server must run with CRICINTEL_EXPERIMENTAL=1 for the lab and Situation Difficulty steps.
import { chromium } from "playwright";
import fs from "node:fs";
const out = process.argv[2];
const BASE = process.env.BASE || "http://localhost:3000";
const KOHLI = "ba607b88", MANDHANA = "5d2eda89", BUMRAH = "462411b3", LANNING = "27e003ce", LOWS = "7b679de5", ECCLESTONE = "cdb82f1c";
const M = "1298150"; // India v Pakistan, ICC Men's T20 World Cup 2022 (Kohli 82*)
const D = { four: `${M}:2:110`, keeper: `${M}:2:33`, bowled: `${M}:2:11`, runout: `${M}:2:37`, field: `${M}:2:20`, stumped: `${M}:2:123`, lbw: `${M}:1:8` };
const browser = await chromium.launch({ executablePath: process.env.CHROME || undefined });
const errors = [], log = [];
let cur = null;
const overflow = (p) => p.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
const note = async (k, v) => { if (cur) v.overflow_px = await overflow(cur); log.push({ step: k, ...v }); console.log(k, JSON.stringify(v).slice(0, 220)); };
async function session(viewport, fn, fresh = false) {
  const ctx = await browser.newContext({ viewport, deviceScaleFactor: 2 });
  const p = await ctx.newPage(); cur = p;
  p.on("pageerror", (e) => errors.push(`pageerror ${p.url()}: ${e}`));
  p.on("console", (m) => m.type() === "error" && errors.push(`console ${p.url()}: ${m.text()}`));
  p.on("response", (r) => r.status() >= 400 && errors.push(`${r.status()} ${r.url()}`));
  const settle = (ms = 500) => p.waitForLoadState("networkidle").then(() => p.waitForTimeout(ms));
  if (!fresh) { await p.goto(BASE + "/players"); await p.evaluate(() => localStorage.setItem("ci-preview-notice", "1")); }
  await fn(p, settle);
  await ctx.close();
}
const Mo = { width: 390, height: 844 }, De = { width: 1280, height: 900 };

// 1. first visit: full notice, then compact
await session(Mo, async (p, settle) => {
  await p.goto(BASE + "/"); await settle(600);
  await p.screenshot({ path: `${out}/m01-first-visit-notice.png` });
  const full = await p.locator(".preview-detail").innerText();
  await p.locator(".preview-detail button").click(); await p.waitForTimeout(200);
  await p.screenshot({ path: `${out}/m02-compact-preview-pill.png` });
  const pillH = await p.locator(".preview-pill").evaluate((e) => e.getBoundingClientRect().height);
  await p.locator(".preview-pill").click(); await p.waitForTimeout(200);
  await note("preview-banner", { full_text: full.slice(0, 160), pill_height_px: pillH, expands: await p.locator(".preview-detail").isVisible() });
}, true);

await session(Mo, async (p, settle) => {
  await p.goto(BASE + "/"); await settle(900);
  await p.screenshot({ path: `${out}/m03-explore-discovery.png`, fullPage: true });
  await p.locator(".disc button", { hasText: "WHY?" }).first().click(); await p.waitForTimeout(250);
  await p.locator(".disc").first().screenshot({ path: `${out}/m04-discovery-why.png` });
  await note("discovery", { cards: await p.locator(".disc").count(), first: (await p.locator(".disc-head").first().innerText()) });
  await p.locator(".chips .chip", { hasText: "Dismissals" }).first().click(); await p.waitForTimeout(200);
  const head = await p.locator(".disc-head").first().innerText();
  await p.locator(".disc a", { hasText: "Show me" }).first().click(); await settle(1200);
  await note("discovery-drill", { card: head, landed: p.url() });

  // Delivery replay: four, then the dismissal theatre for each kind
  await p.goto(`${BASE}/delivery/${encodeURIComponent(D.four)}`); await settle(900);
  await p.screenshot({ path: `${out}/m05-replay-four.png`, fullPage: true });
  await p.locator(".dscene-svg [aria-label='V Kohli']").first().click(); await p.waitForTimeout(200);
  await note("replay-inspect", { panel: await p.locator(".prov-panel").innerText() });
  await p.locator(".dscene").screenshot({ path: `${out}/m06-replay-provenance-inspect.png` });
  await p.keyboard.press("ArrowRight"); await settle(800);
  await note("replay-next-key", { url: p.url() });
  for (const [k, id] of Object.entries(D).filter(([k]) => k !== "four")) {
    await p.goto(`${BASE}/delivery/${encodeURIComponent(id)}`); await settle(800);
    await p.locator(".dscene").screenshot({ path: `${out}/m07-theatre-${k}.png` });
    await note(`theatre-${k}`, { chain: await p.locator(".chain").innerText(), theatre: await p.locator(".theatre").innerText().catch(() => "") });
  }

  // Innings story: Kohli 82*
  await p.goto(`${BASE}/innings/${M}/2/${KOHLI}`); await settle(1000);
  await p.screenshot({ path: `${out}/m08-innings-story-kohli.png`, fullPage: true });
  await p.locator(".scrub").fill("60"); await p.waitForTimeout(300);
  const ballTxt = await p.locator(".grid2 .card").first().innerText();
  await p.locator(".ev-row", { hasText: "50 up" }).click(); await p.waitForTimeout(300);
  await p.locator(".section", { hasText: "Ball by ball" }).screenshot({ path: `${out}/m09-innings-scrub.png` });
  await note("innings-scrub", { at60: ballTxt.split("\n").slice(0, 3).join(" | "), milestone: (await p.locator(".grid2 .card").first().innerText()).split("\n")[0] });
  await p.locator("a", { hasText: "Open delivery replay" }).click(); await settle(800);
  await note("innings-to-replay", { url: p.url() });

  // Spell story: Bumrah 6-19 v England 2022
  await p.goto(`${BASE}/players/${BUMRAH}?tab=bowling`); await settle(1500);
  await p.screenshot({ path: `${out}/m10-bowler-tab-bumrah.png`, fullPage: true });
  await note("bowler-tab", { petals: await p.locator(".petal").count(), states: await p.locator(".state-row").count(), spells: await p.locator(".rec-row").count() });
  await p.locator(".rec-row").first().click(); await settle(1000);
  await p.screenshot({ path: `${out}/m11-spell-story.png`, fullPage: true });
  await note("spell-story", { url: p.url(), head: (await p.locator(".hero").innerText()).split("\n").slice(0, 3).join(" | ") });

  // State analysis + partners
  await p.goto(`${BASE}/players/${KOHLI}?tab=states&format=T20`); await settle(1200);
  await p.screenshot({ path: `${out}/m12-states-kohli-t20.png`, fullPage: true });
  await p.locator(".state-row").nth(2).click(); await settle(800);
  await note("states-drill", { evidence: (await p.locator("#evidence").innerText().catch(() => "")).split("\n").slice(0, 2).join(" | ") });
  await p.goto(`${BASE}/players/${MANDHANA}?tab=partners`); await settle(1000);
  await p.screenshot({ path: `${out}/m13-partners-mandhana.png`, fullPage: true });
  await p.goto(`${BASE}/players/${LOWS}?tab=states`); await settle(1000);
  await note("states-low-sample", { text: (await p.locator(".note, .icard").first().innerText()).slice(0, 200) });
  await p.screenshot({ path: `${out}/m14-states-low-sample.png`, fullPage: true });

  // Partnerships page
  await p.goto(`${BASE}/partnerships?sort=run_rate&phase=death&format=T20`); await settle(1000);
  await p.screenshot({ path: `${out}/m15-partnerships-death.png`, fullPage: true });
  await p.locator(".rec-list .rec-row").first().click(); await settle(1000);
  await p.screenshot({ path: `${out}/m16-pair-history.png`, fullPage: true });
  await note("pair", { url: p.url(), head: (await p.locator(".hero").innerText()).split("\n").slice(0, 2).join(" | ") });

  // WHN v2
  await p.goto(`${BASE}/play`); await settle(900);
  await p.screenshot({ path: `${out}/m17-whn-situation.png`, fullPage: true });
  await p.keyboard.press("4"); await settle(600);
  await p.screenshot({ path: `${out}/m18-whn-reveal.png`, fullPage: true });
  for (const k of ["Enter", "0", "Enter", "1", "Enter", "0", "Enter", "1", "Enter", "0"]) { await p.keyboard.press(k); await p.waitForTimeout(k === "Enter" ? 250 : 450); }
  await p.locator("button", { hasText: "Session stats" }).click(); await p.waitForTimeout(300);
  await p.screenshot({ path: `${out}/m19-whn-session.png`, fullPage: true });
  await note("whn", { mvy: (await p.locator(".mvy").innerText()).replace(/\n/g, " "), sess: (await p.locator(".sess").innerText()).replace(/\n/g, " ") });

  // Ask v2
  for (const [i, q] of ["Which partnerships score fastest in the death overs?", "Show Kohli's dismissals between balls 20 and 30", "How does Bumrah perform in overs 17-20?",
    "Who improves most from middle overs to death overs?"].entries()) {
    await p.goto(`${BASE}/ask?q=${encodeURIComponent(q)}`); await settle(1000);
    await p.screenshot({ path: `${out}/m2${i}-ask-v2-${i + 1}.png`, fullPage: true });
    await note(`ask-${i + 1}`, { q, chips: (await p.locator(".interp .chips").innerText()).replace(/\n/g, " · "), ans: await p.locator(".ans").innerText() });
  }

  // Women and leagues: Lanning innings, Ecclestone spell
  await p.goto(`${BASE}/players/${LANNING}?tab=innings`); await settle(900);
  await p.locator(".rec-row").first().click(); await settle(1000);
  await p.screenshot({ path: `${out}/m24-innings-story-lanning.png`, fullPage: true });
  await note("lanning-innings", { url: p.url(), head: (await p.locator(".hero").innerText()).split("\n").slice(0, 3).join(" | ") });
  await p.goto(`${BASE}/players/${ECCLESTONE}?tab=bowling`); await settle(1500);
  await p.locator(".seg button", { hasText: "Most recent" }).last().click(); await settle(800);
  await p.locator(".rec-row").first().click(); await settle(1000);
  await p.screenshot({ path: `${out}/m25-spell-story-ecclestone.png`, fullPage: true });
  await note("ecclestone-spell", { url: p.url(), head: (await p.locator(".hero").innerText()).split("\n").slice(0, 3).join(" | ") });

  await p.goto(`${BASE}/lab`); await settle(1200);
  await p.screenshot({ path: `${out}/m26-lab.png`, fullPage: true });
  await p.goto(`${BASE}/context`); await settle(600);
  await p.screenshot({ path: `${out}/m27-context-engine.png`, fullPage: true });
});

await session(De, async (p, settle) => {
  await p.goto(BASE + "/"); await settle(900);
  await p.screenshot({ path: `${out}/d01-explore.png`, fullPage: true });
  await p.goto(`${BASE}/delivery/${encodeURIComponent(D.keeper)}`); await settle(900);
  await p.screenshot({ path: `${out}/d02-replay-keeper-catch.png`, fullPage: true });
  await p.goto(`${BASE}/innings/${M}/2/${KOHLI}`); await settle(1000);
  await p.screenshot({ path: `${out}/d03-innings-story.png`, fullPage: true });
  await p.goto(`${BASE}/players/${KOHLI}?tab=states&format=ODI`); await settle(1200);
  await p.screenshot({ path: `${out}/d04-states-kohli-odi.png`, fullPage: true });
  await p.goto(`${BASE}/battle?bat=${KOHLI}&bowl=14f96089`); await settle(1000);
  await p.screenshot({ path: `${out}/d05-battle-outcome-map.png`, fullPage: true });
  await p.goto(`${BASE}/lab`); await settle(1200);
  await p.screenshot({ path: `${out}/d06-lab.png`, fullPage: true });
});

fs.writeFileSync(`${out}/report.json`, JSON.stringify({ errors, log }, null, 2));
await browser.close();
console.log(JSON.stringify({ errors: errors.length, first: errors.slice(0, 10) }));
