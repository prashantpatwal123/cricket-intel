// Phase 5 journeys on REAL data: Historical Live Lab and the second-screen Match Centre, phone first.
// Also a browser-level spoiler check: every /api/live response the page receives is scanned for the match result and for
// delivery ids beyond its cursor. Usage: node screenshots-phase5.mjs <outdir>
import { chromium } from "playwright";
import fs from "node:fs";
const out = process.argv[2];
const BASE = process.env.BASE || "http://localhost:3000";
const API = process.env.API || "http://localhost:8000";
const MATCHES = { mcg: "1298150", ipl: "1370353", wpl: "1513703", wodi: "1490443", odi: "1384439", so: "1216517", wt20: "1490709" };
const browser = await chromium.launch({ executablePath: process.env.CHROME || undefined });
const errors = [], log = [], assertions = [], aborted = [], spoil = [];
let cur = null;
const overflow = (p) => p.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
const note = async (k, v) => { if (cur) v.overflow_px = await overflow(cur); if (v.overflow_px > 0) assertions.push(`overflow ${k}: ${v.overflow_px}px`); log.push({ step: k, ...v }); console.log(k, JSON.stringify(v).slice(0, 260)); };
const check = (cond, msg) => { if (!cond) assertions.push(msg); };

// Privileged reference (test harness only): full delivery order and final result per match, to detect leaks.
const ref = {};
for (const [k, mid] of Object.entries(MATCHES)) {
  const end = await (await fetch(`${API}/api/live/${mid}/seek?cursor=0&to=end`)).json();
  const total = end.data.cursor;
  const fin = (await (await fetch(`${API}/api/live/${mid}?cursor=${total}`)).json()).data;
  ref[mid] = { total, result: fin.meta.result };
}
const allIds = {};   // mid -> ordered delivery ids, learned by walking the API (privileged, harness only)
async function idsFor(mid) {
  if (allIds[mid]) return allIds[mid];
  const ids = [];
  for (let n = 1; n <= ref[mid].total; n++) {
    const d = (await (await fetch(`${API}/api/live/${mid}?cursor=${n}`)).json()).data;
    ids.push(d.now.last_ball.event_id);
  }
  return (allIds[mid] = ids);
}

async function session(viewport, fn) {
  const ctx = await browser.newContext({ viewport, deviceScaleFactor: 2 });
  const p = await ctx.newPage(); cur = p;
  p.on("pageerror", (e) => errors.push(`pageerror ${p.url()}: ${e}`));
  p.on("console", (m) => m.type() === "error" && errors.push(`console ${p.url()}: ${m.text()}`));
  p.on("response", async (r) => {
    if (r.status() >= 400) errors.push(`${r.status()} ${r.url()}`);
    const u = new URL(r.url());
    const m = /\/api\/live\/(\d+)(\/play)?$/.exec(u.pathname);
    if (!m || r.status() !== 200) return;
    try {
      const body = await r.text(); const j = JSON.parse(body).data;
      const st = m[2] ? j.state : j; const mid = m[1];
      if (!st || !ref[mid]) return;
      const c = st.replay.cursor;
      if (c < ref[mid].total && body.includes(ref[mid].result)) spoil.push(`${mid} cursor ${c}: final result text present`);
      const ids = [...body.matchAll(new RegExp(`"(${mid}:\\d+:\\d+)"`, "g"))].map((x) => x[1]);
      if (ids.length) spoil.push({ mid, c, ids: [...new Set(ids)] });
    } catch { /* non-JSON */ }
  });
  p.on("requestfailed", (r) => { if (r.url().startsWith("data:")) return; const t = r.failure()?.errorText || "";
    if (t.includes("ERR_ABORTED")) aborted.push(r.url()); else errors.push(`failed ${r.url()} ${t}`); });
  const settle = (ms = 400) => p.waitForLoadState("networkidle").then(() => p.waitForTimeout(ms));
  await p.goto(BASE + "/data"); await p.evaluate(() => localStorage.setItem("ci-preview-notice", "1"));
  await fn(p, settle);
  await ctx.close();
}
const Mo = { width: 390, height: 844 }, De = { width: 1280, height: 900 };
const text = (p, sel) => p.locator(sel).first().innerText().catch(() => "");
const inView = (p, sel) => p.locator(sel).first().evaluate((e) => { const r = e.getBoundingClientRect(); return r.top >= 0 && r.bottom <= window.innerHeight; }).catch(() => false);

await session(Mo, async (p, settle) => {
  // 1. Lab list: no results or scores shown
  await p.goto(`${BASE}/live-lab`); await settle();
  const list = await p.locator("[data-testid=lab-match]").allInnerTexts();
  check(list.length >= 5, "fewer than 5 featured matches");
  for (const mid of Object.keys(ref)) check(!(await p.content()).includes(ref[mid].result), `lab list shows result of ${mid}`);
  await p.screenshot({ path: `${out}/m01-live-lab.png`, fullPage: true });
  await note("lab-list", { n: list.length, first: list[0] });

  // 2. MCG from the first ball
  await p.locator("[data-testid=lab-match]").first().click(); await settle();
  check(p.url().includes(`/live-lab/${MATCHES.mcg}`), "lab click did not open MCG");
  check(await inView(p, "[data-testid=replay-flag]"), "replay flag not visible at top");
  await p.screenshot({ path: `${out}/m02-mcg-start.png`, fullPage: false });
  const before = await text(p, "[data-testid=score-strip]");
  for (let i = 0; i < 3; i++) { await p.click("[data-testid=next-ball]"); await settle(150); }
  const pos = await p.locator("[data-testid=position]").getAttribute("data-n");
  check(pos === "3", `next ball x3 → ${pos}`);
  await note("mcg-steps", { before: before.replace(/\n/g, " | "), after: (await text(p, "[data-testid=score-strip]")).replace(/\n/g, " | "), pos });

  // 3. Mid-chase second screen
  await p.goto(`${BASE}/live-lab/${MATCHES.mcg}?n=236`); await settle(800);
  await p.mouse.wheel(0, 1600); await p.waitForTimeout(300);
  check(await inView(p, "[data-testid=replay-flag]"), "replay flag scrolled away (must stay sticky)");
  await p.mouse.wheel(0, -3000); await p.waitForTimeout(200);
  for (const sel of ["battle", "batter-state", "bowler-state", "partnership", "chase", "right-now", "pitch", "recent", "whn"]) check(await p.locator(`[data-testid=${sel}]`).count() > 0, `MCG 236: missing ${sel}`);
  await p.screenshot({ path: `${out}/m03-mcg-236-above-fold.png`, fullPage: false });
  await p.screenshot({ path: `${out}/m04-mcg-236-now.png`, fullPage: true });
  const rn = await p.locator("[data-testid=rn-item]").allInnerTexts();
  await note("mcg-236", { strip: (await text(p, "[data-testid=score-strip]")).replace(/\n/g, " | "), battle: (await text(p, "[data-testid=battle]")).slice(0, 160).replace(/\n/g, " "),
    right_now: rn.map((x) => x.slice(0, 90).replace(/\n/g, " ")), sdx: await p.locator("[data-testid=sdx]").count(), nothing_new: await p.locator("[data-testid=nothing-new]").count() });
  // scan everything except the labelled experimental block, whose disclaimer says what SDX is NOT ("not pressure, not a win probability")
  const body = await p.evaluate(() => { const c = document.querySelector("main").cloneNode(true); c.querySelectorAll("[data-testid=sdx]").forEach((e) => e.remove()); return c.innerText; });
  check(!/clutch|pressure|nervous|confident|struggling/i.test(body), "psychological / banned words on Match Centre");
  check(!/win probability|chance of winning|% to win/i.test(body), "win probability shown");

  // 4. Tabs
  await p.click("[data-testid=tab-card]"); await settle(200); await p.screenshot({ path: `${out}/m05-mcg-scorecard.png`, fullPage: true });
  await p.click("[data-testid=tab-timeline]"); await settle(200); await p.screenshot({ path: `${out}/m06-mcg-timeline.png`, fullPage: true });
  const tl = await p.locator(".tl li").allInnerTexts();
  check(tl.length > 5, "timeline too short"); check(!tl.some((t) => /game-changing|turning point|momentum/i.test(t)), "editorial timeline label");
  await note("timeline", { events: tl.length, top: tl.slice(0, 4), record_watch: (await text(p, "[data-testid=record-watch]")).slice(0, 240).replace(/\n/g, " ") });
  await p.click("[data-testid=tab-ask]"); await settle(200);
  const asks = {};
  for (const q of ["How has this batter done against this bowler?", "Has this pair batted together before?", "Who has dismissed this batter most?"]) {
    await p.fill("input[aria-label=Ask]", q); await p.click("text=Ask >> nth=-1"); await p.waitForSelector("[data-testid=ask-answer]"); await settle(200);
    const a = await text(p, "[data-testid=ask-answer]");
    asks[q] = a.slice(0, 220).replace(/\n/g, " ");
    check(/before this one|before 2022-10-23/.test(a), `match ask lacks before-this-match chip: ${q}`);
  }
  await p.screenshot({ path: `${out}/m07-mcg-ask.png`, fullPage: true });
  await note("match-ask", asks);

  // 5. Play this match (What Happens Next v3)
  await p.click("[data-testid=tab-now]"); await settle(200);
  await p.click("[data-testid=play-this-match]"); await settle(100);
  const c0 = await text(p, "[data-testid=position]");
  for (const pk of ["1", "DOT", "4"]) { await p.click(`[data-testid=pick-${pk}]`); await p.waitForSelector("[data-testid=reveal]"); await settle(150); }
  const sess = await text(p, "[data-testid=session]");
  check(/3 right|\/3 right/.test(sess) || /\d+\/3 right/.test(sess), `session did not count 3 picks: ${sess}`);
  await p.locator("[data-testid=whn]").scrollIntoViewIfNeeded();
  await p.screenshot({ path: `${out}/m08-play-this-match.png`, fullPage: false });
  await note("play-this-match", { from: c0, to: await text(p, "[data-testid=position]"), session: sess, reveal: (await text(p, "[data-testid=reveal]")).replace(/\n/g, " ") });

  // 6. Autoplay at 5x, then pause
  await p.goto(`${BASE}/live-lab/${MATCHES.wpl}?n=30`); await settle();
  await p.click("[data-testid=speed]"); await p.click("[data-testid=speed]"); await p.click("[data-testid=play]"); await p.waitForTimeout(3600); await p.click("[data-testid=play]"); await settle(300);
  const ap = await p.locator("[data-testid=position]").getAttribute("data-n");
  const apn = Number(ap || 0);
  check(apn >= 33, `autoplay advanced only to ${ap}`);
  await p.screenshot({ path: `${out}/m09-wpl-autoplay.png`, fullPage: false });
  await note("wpl-autoplay", { position: ap });

  // 7. Next over, innings selector (innings break shows target)
  await p.click("[data-testid=next-over]"); await settle(300);
  await note("next-over", { position: await text(p, "[data-testid=position]") });
  await p.selectOption("[data-testid=jump]", "innings:2"); await settle(500);
  const strip = await text(p, "[data-testid=score-strip]");
  check(/Need|need/.test(strip) || /0\/0/.test(strip), `innings 2 start lacks chase context: ${strip}`);
  await p.screenshot({ path: `${out}/m10-wpl-innings2.png`, fullPage: false });
  await note("innings-2", { strip: strip.replace(/\n/g, " | ") });

  // 8. Open battle and come back
  await p.goto(`${BASE}/live-lab/${MATCHES.mcg}?n=200`); await settle();
  await p.click("[data-testid=open-battle]"); await settle(600);
  check(/from=live/.test(p.url()), "open battle lost replay context");
  check(await p.locator("[data-testid=from-live]").count() === 1, "battle page lacks back-to-replay banner");
  await p.screenshot({ path: `${out}/m11-battle-from-replay.png`, fullPage: false });
  await p.click("[data-testid=from-live] a"); await settle(600);
  check(/n=200/.test(p.url()), `back link did not return to ball 200: ${p.url()}`);
  await note("battle-roundtrip", { back: p.url() });

  // 9. Other featured matches at characteristic points
  const points = [["ipl", 160, "m12-ipl-dl-chase"], ["wodi", 420, "m13-women-odi"], ["odi", 400, "m14-men-odi-final"], ["wt20", 150, "m15-women-t20"], ["so", 247, "m16-super-over"]];
  for (const [k, n, f] of points) {
    await p.goto(`${BASE}/live-lab/${MATCHES[k]}?n=${n}`); await settle(600);
    await p.screenshot({ path: `${out}/${f}.png`, fullPage: false });
    await note(f, { strip: (await text(p, "[data-testid=score-strip]")).replace(/\n/g, " | "), rn: (await p.locator("[data-testid=rn-item]").count()) });
  }
  // D/L chase must say so
  await p.goto(`${BASE}/live-lab/${MATCHES.ipl}?n=160`); await settle();
  check(/D\/L/.test(await text(p, "[data-testid=chase]")), "IPL D/L chase lacks D/L note");
  // End of match reveals the result only now
  await p.goto(`${BASE}/live-lab/${MATCHES.so}?n=${ref[MATCHES.so].total}`); await settle();
  check((await text(p, "[data-testid=score-strip]")).includes("super over"), "super over result not shown at the end");
  await p.screenshot({ path: `${out}/m17-super-over-end.png`, fullPage: false });
  await note("so-end", { strip: (await text(p, "[data-testid=score-strip]")).replace(/\n/g, " | ") });

  // 10. Gateways keep the five-tab IA
  await p.goto(`${BASE}/`); await settle();
  check(await p.locator("[data-testid=gw-live-lab]").count() === 1, "Explore lacks Live Lab gateway");
  check((await p.locator("nav.nav a").count()) === 5, "global nav is not 5 tabs");
  await p.goto(`${BASE}/data`); await settle();
  check(await p.locator("[data-testid=data-live-lab]").count() === 1, "/data lacks the Live Lab methodology section");
  await p.locator("[data-testid=data-live-lab]").scrollIntoViewIfNeeded(); await p.screenshot({ path: `${out}/m18-data-live-lab.png`, fullPage: false });
  await p.goto(`${BASE}/play`); await settle();
  check(await p.locator("[data-testid=play-whole-match]").count() === 1, "Play lacks whole-match link");
});

await session(De, async (p, settle) => {
  for (const [f, url] of [["d-live-lab", "/live-lab"], ["d-mcg-236", `/live-lab/${MATCHES.mcg}?n=236`], ["d-mcg-timeline", `/live-lab/${MATCHES.mcg}?n=245&tab=timeline`],
                          ["d-ipl-chase", `/live-lab/${MATCHES.ipl}?n=170`], ["d-women-odi", `/live-lab/${MATCHES.wodi}?n=300`], ["d-mcg-card", `/live-lab/${MATCHES.mcg}?n=245&tab=card`]]) {
    await p.goto(BASE + url); await settle(600);
    await p.screenshot({ path: `${out}/${f}.png`, fullPage: true });
    await note(f, {});
  }
});

// Spoiler audit: every delivery id a page received must be within its cursor.
const leaks = [];
for (const s of spoil) {
  if (typeof s === "string") { leaks.push(s); continue; }
  const ids = await idsFor(s.mid);
  const allowed = new Set(ids.slice(0, s.c));
  for (const id of s.ids) if (!allowed.has(id)) leaks.push(`${s.mid} cursor ${s.c}: received ${id}`);
}
check(leaks.length === 0, `spoiler leaks: ${leaks.slice(0, 5).join("; ")}`);
console.log("spoiler responses checked:", spoil.length, "leaks:", leaks.length);
await browser.close();
fs.writeFileSync(`${out}/report.json`, JSON.stringify({ errors, aborted_by_navigation: aborted.length, assertions, leaks, responses_checked: spoil.length, log }, null, 2));
console.log(JSON.stringify({ errors: errors.length, aborted_by_navigation: aborted.length, assertions: assertions.length, leaks: leaks.length, first_errors: errors.slice(0, 8), first_assertions: assertions.slice(0, 12) }));
