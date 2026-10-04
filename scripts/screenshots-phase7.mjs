// Phase 7 fan-experience journeys on REAL data (390 px primary, desktop secondary).
// Measures: dead ends, repeated recommendations, broken relationships, pages without a next action; checks session memory,
// spoiler safety of Play moments, share cards, Compare V2, Records V2, On This Day, Ask, no causal language, no fake geometry.
// Usage: node screenshots-phase7.mjs <outdir>
import { chromium } from "playwright";
import fs from "node:fs";
const out = process.argv[2];
const BASE = process.env.BASE || "http://localhost:3000";
const KOHLI = "ba607b88", ZAMPA = "14f96089", BUMRAH = "462411b3", MANDHANA = "5d2eda89", LESSER = "7b679de5", MCG = "1298150";
const browser = await chromium.launch({ executablePath: process.env.CHROME || undefined });
const errors = [], log = [], assertions = [], aborted = [];
let cur = null;
const CAUSAL = /\b(because|clutch|handles? pressure|loses concentration|choke[sd]?|bottled)\b/i;
const overflow = (p) => p.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
const note = async (k, v = {}) => { if (cur) v.overflow_px = await overflow(cur); if (v.overflow_px > 0) assertions.push(`overflow ${k}: ${v.overflow_px}px`); log.push({ step: k, ...v }); console.log(k, JSON.stringify(v).slice(0, 300)); };
const check = (c, m) => { if (!c) assertions.push(m); };
async function session(viewport, fn) {
  const ctx = await browser.newContext({ viewport, deviceScaleFactor: 2 });
  const p = await ctx.newPage(); cur = p;
  p.on("pageerror", (e) => errors.push(`pageerror ${p.url()}: ${e}`));
  p.on("console", (m) => m.type() === "error" && errors.push(`console ${p.url()}: ${m.text()}`));
  p.on("response", (r) => r.status() >= 400 && errors.push(`${r.status()} ${r.url()}`));
  p.on("requestfailed", (r) => { if (r.url().startsWith("data:")) return; const t = r.failure()?.errorText || "";
    if (t.includes("ERR_ABORTED")) aborted.push(r.url()); else errors.push(`failed ${r.url()} ${t}`); });
  const settle = (ms = 500) => p.waitForLoadState("networkidle").then(() => p.waitForTimeout(ms));
  await p.goto(BASE + "/data"); await p.evaluate(() => { localStorage.setItem("ci-preview-notice", "1"); localStorage.removeItem("ci-memory-v1"); });
  await fn(p, settle);
  await ctx.close();
}
const text = (p, sel = "main") => p.locator(sel).first().innerText().catch(() => "");
const waitNext = (p) => p.waitForSelector("[data-testid=explore-next] .xnext-row", { timeout: 20000 }).catch(() => null);
const nextRows = (p) => p.locator("[data-testid=explore-next] .xnext-row").evaluateAll((as) => as.map((a) => ({ href: a.getAttribute("href"), type: a.dataset.type, rel: a.dataset.rel, text: a.innerText.split("\n").slice(0, 2).join(" · ") })));
async function hop(p, settle, pred, label, hops) {
  await waitNext(p);
  const rows = await nextRows(p);
  const r = rows.find(pred);
  check(!!r, `${label}: no matching Explore-next row (${rows.map((x) => x.type + ":" + x.rel).join(", ")})`);
  if (!r) return false;
  await p.goto(BASE + r.href); await settle(900);
  hops.push({ via: label, to: p.url().replace(BASE, ""), row: r.text });
  return true;
}
const guard = async (p, where) => {
  const t = await text(p);
  check(!CAUSAL.test(t), `${where}: causal language "${(t.match(CAUSAL) || [])[0]}"`);
  check(!/\(score \d/.test(t), `${where}: internal ranking score shown to fans`);
  check(await p.locator(".illus").count() === 0, `${where}: illustrative frame on a real-data page`);
};
const Mo = { width: 390, height: 844 }, De = { width: 1280, height: 900 };

// ------------------------------------------------------------------ 1. Explore + the three journeys
await session(Mo, async (p, settle) => {
  await p.goto(BASE + "/"); await settle(1500);
  for (const t of ["didnt-know", "great-battles", "record-of-day", "rabbit-hole", "beat-the-model"]) check(await p.locator(`[data-testid=${t}]`).count() === 1, `Explore lacks ${t}`);
  check(await p.locator("[data-testid=gw-live-lab]").count() === 1, "Explore lost the Live Lab gateway");
  await guard(p, "explore");
  await p.screenshot({ path: `${out}/m01-explore.png`, fullPage: true });
  await note("explore", { otd: await p.locator("[data-testid=on-this-day]").count(), worth: await p.locator("[data-testid=didnt-know] .dk-card").count() });

  // J1: Explore → Kohli → dismissal → bowler → battle → match → innings → another player
  const j1 = [];
  await p.goto(`${BASE}/players/${KOHLI}`); await settle(1500); j1.push({ via: "start", to: p.url().replace(BASE, "") });
  check(await p.locator("[data-testid=what-different] .diff").count() >= 3, "Kohli: fewer than 3 'what makes them different' findings");
  check(await p.locator("[data-testid=player-stories] .storycard").count() >= 3, "Kohli: fewer than 3 player stories");
  check(await p.locator("[data-testid=matchup-discovery]").count() === 1, "Kohli: no matchup discovery");
  check(await p.locator("[data-testid=similar-players] .simrow").count() >= 3, "Kohli: fewer than 3 similar players");
  check(await p.locator(".petal").count() > 5, "Kohli: fingerprint petals missing");
  await guard(p, "kohli");
  await p.screenshot({ path: `${out}/m02-kohli-home.png`, fullPage: true });
  await p.click("[data-testid=explore-how-out-home]"); await settle(900); j1.push({ via: "dismissal DNA", to: p.url().replace(BASE, "") });
  await p.locator("[data-testid=dim-route] button", { hasText: "Caught by wicketkeeper" }).first().click(); await settle(700);
  await p.locator("[data-testid=dim-bowler] button").first().click(); await settle(900); j1.push({ via: "bowler", to: p.url().replace(BASE, "") });
  await p.click("[data-testid=open-battle]"); await settle(1200); j1.push({ via: "battle", to: p.url().replace(BASE, "") });
  await p.screenshot({ path: `${out}/m03-j1-battle.png`, fullPage: true });
  await hop(p, settle, (r) => r.type === "match", "battle→match", j1);
  await hop(p, settle, (r) => r.type === "innings", "match→innings", j1);
  await hop(p, settle, (r) => (r.type === "player" && !r.href.includes(KOHLI)) || r.type === "battle", "innings→another player", j1);
  if (!/\/players\//.test(j1[j1.length - 1]?.to || "")) {
    // a battle page names both players in its header; the fan taps the one who isn't Kohli
    const other = await p.locator("main .hero a[href^='/players/']").evaluateAll((as, k) => as.map((a) => a.getAttribute("href")).find((h) => !h.includes(k)), KOHLI);
    check(!!other, "battle page has no link to the other player");
    if (other) { await p.goto(BASE + other); await settle(900); j1.push({ via: "battle header → the other player", to: p.url().replace(BASE, "") }); }
  }
  await note("journey-1", { hops: j1 });
  const want1 = [/\/players\//, /\/how-out\//, /bowler=/, /\/battle\?/, /\/match\//, /\/innings\//, /\/players\/|\/battle\?/, /\/players\//];
  check(/\/players\//.test(j1[j1.length - 1].to) && !j1[j1.length - 1].to.includes(KOHLI), "J1 did not end on another player");
  j1.forEach((h, i) => check(want1[i]?.test(h.to), `J1 hop ${i} unexpected: ${h.to}`));

  // J2: Mandhana → partner → match → record → another player
  const j2 = [];
  await p.goto(`${BASE}/players/${MANDHANA}`); await settle(1500); j2.push({ via: "start", to: p.url().replace(BASE, "") });
  await p.screenshot({ path: `${out}/m04-mandhana-home.png`, fullPage: true });
  // a fan tries partners in turn until a stand's match leads into the record book
  const parts = await p.locator("a.mrow[href^='/partnerships?']").evaluateAll((as) => as.map((a) => a.getAttribute("href")));
  let reached = false;
  for (const part of parts) {
    const trial = [];
    await p.goto(BASE + part); await settle(1200); trial.push({ via: "partner", to: p.url().replace(BASE, "") });
    if (!(await hop(p, settle, (r) => r.type === "match", "partnership→match", trial))) continue;
    await waitNext(p);
    if (!(await nextRows(p)).some((r) => r.type === "record")) { j2.push({ via: "tried partner (no record from that match)", to: trial[0].to }); continue; }
    await hop(p, settle, (r) => r.type === "record", "match→record", trial);
    j2.push(...trial); reached = true; break;
  }
  assertions.splice(0, assertions.length, ...assertions.filter((a) => !a.startsWith("partnership→match")));
  check(reached, "J2: no partner's match led to a record");
  if (reached) {
    await p.screenshot({ path: `${out}/m05-j2-record.png`, fullPage: true });
    const rr = await p.locator("[data-testid=record-rows] a").first().getAttribute("href");
    await p.goto(BASE + rr); await settle(1000); j2.push({ via: "record row", to: p.url().replace(BASE, "") });
    await hop(p, settle, (r) => ["player", "innings", "battle"].includes(r.type) && !r.href.includes(MANDHANA), "→another player", j2);
  }
  await note("journey-2", { hops: j2 });
  check(j2.some((h) => /\/records\//.test(h.to)), "J2 did not reach a record");

  // J3: Bumrah → spell → match → opposing batter → battle
  const j3 = [];
  await p.goto(`${BASE}/players/${BUMRAH}`); await settle(1500); j3.push({ via: "start", to: p.url().replace(BASE, "") });
  check(await p.locator("[data-testid=how-wickets]").count() === 1, "Bumrah: no 'how they take wickets'");
  check(!/How Jasprit Bumrah gets out/.test(await text(p)), "Bumrah home still leads with his batting dismissals");
  await p.screenshot({ path: `${out}/m06-bumrah-home.png`, fullPage: true });
  await hop(p, settle, (r) => r.type === "spell", "player→spell", j3);
  await hop(p, settle, (r) => r.type === "match", "spell→match", j3);
  await hop(p, settle, (r) => r.type === "innings", "match→opposing batter's innings", j3);
  await hop(p, settle, (r) => r.type === "battle", "innings→battle", j3);
  await note("journey-3", { hops: j3 });
  check(/\/battle\?/.test(j3[j3.length - 1]?.to || ""), "J3 did not end on a battle");
});

// ------------------------------------------------------------------ 2. Automated exploration crawl: dead ends, repetition, broken links
await session(Mo, async (p, settle) => {
  const seeds = [`/players/${KOHLI}`, `/players/${BUMRAH}`, `/players/${MANDHANA}`, `/players/${LESSER}`, `/battle?bat=${KOHLI}&bowl=${ZAMPA}`, `/match/${MCG}`,
    `/innings/${MCG}/2/${KOHLI}`, `/spell/1276907/1/${BUMRAH}`, "/competition?name=Indian%20Premier%20League&gender=male", "/rivalry?a=India&b=Australia&gender=male",
    "/records/highest-score.male.T20.major", `/delivery/${encodeURIComponent(`${MCG}:2:33`)}`, `/partnerships?p1=740742ef&p2=${KOHLI}`, `/how-out/${KOHLI}`];
  const byType = {}, recs = [], dead = [], broken = [];
  let pages = 0;
  for (const s of seeds) {
    let url = s;
    const visited = new Set();
    for (let step = 0; step < 5; step++) {
      const resp = await p.goto(BASE + url); await settle(700);
      pages++;
      const kind = url.split(/[/?]/)[1] || "home";
      const status = resp?.status() ?? 0;
      const body = await text(p);
      if (status >= 400 || /not found|couldn.t load|could not load/i.test(body.slice(0, 400))) broken.push(url);
      await waitNext(p);
      const rows = await nextRows(p);
      const internal = await p.locator("main a[href^='/']").evaluateAll((as) => new Set(as.map((a) => a.getAttribute("href"))).size);
      byType[kind] = byType[kind] || { pages: 0, min_next: 99, dead: 0 };
      byType[kind].pages++; byType[kind].min_next = Math.min(byType[kind].min_next, rows.length);
      if (rows.length === 0) { byType[kind].dead++; dead.push(url); }
      if (step === 0) await guard(p, `crawl ${url}`);
      recs.push(...rows.map((r) => r.href));
      visited.add(url);
      const nxt = rows.find((r) => !visited.has(r.href) && !r.href.startsWith("/live-lab") && !r.href.startsWith("/compare"));
      if (!nxt) break;
      url = nxt.href;
    }
  }
  const counts = {}; recs.forEach((h) => (counts[h] = (counts[h] || 0) + 1));
  const repeated = Object.values(counts).filter((n) => n > 1).length;
  await note("crawl", { pages, page_types: byType, dead_ends: dead, broken, recommendations: recs.length, distinct: Object.keys(counts).length,
    destinations_recommended_more_than_once: repeated, max_repeat: Math.max(...Object.values(counts)),
    most_repeated: Object.entries(counts).sort((a, b) => b[1] - a[1]).slice(0, 6) });
  check(dead.length === 0, `dead ends: ${dead.join(", ")}`);
  check(broken.length === 0, `broken pages: ${broken.join(", ")}`);
});

// ------------------------------------------------------------------ 3. Session memory, Play spoiler safety, shares, compare, records, OTD, Ask
await session(Mo, async (p, settle) => {
  // memory changes recommendations and can be reset
  await p.goto(`${BASE}/players/${KOHLI}`); await settle(1200); await waitNext(p);
  const before = (await nextRows(p)).map((r) => r.href);
  await p.goto(BASE + before[0]); await settle(900);
  await p.goto(`${BASE}/players/${KOHLI}`); await settle(1200); await waitNext(p);
  const after = (await nextRows(p)).map((r) => r.href);
  check(after[0] !== before[0], "visiting the top recommendation did not change the next recommendations");
  await note("memory-aware", { before: before.slice(0, 3), after: after.slice(0, 3) });
  await p.goto(BASE + "/"); await settle(1200);
  check(await p.locator("[data-testid=continue] .recent-row a").count() >= 2, "Explore lacks 'continue where you left off'");
  await p.locator("[data-testid=continue]").screenshot({ path: `${out}/m07-continue.png` });
  await p.locator("[data-testid=continue] button", { hasText: "Clear my history" }).click(); await p.waitForTimeout(300);
  check(await p.locator("[data-testid=continue]").count() === 0, "reset did not clear the history");
  check(await p.evaluate(() => localStorage.getItem("ci-memory-v1")) === null, "reset left memory in localStorage");

  // Play moment inside the 82* innings: spoiler-safe
  await p.goto(`${BASE}/innings/${MCG}/2/${KOHLI}`); await settle(1200);
  const mhref = await p.locator("[data-testid=play-moment]").first().getAttribute("href");
  check(!!mhref && /game=1/.test(mhref), "innings page lacks a Play moment");
  await p.goto(BASE + mhref); await settle(1500);
  const lt = await text(p);
  const n = Number(new URL(BASE + mhref).searchParams.get("n"));
  check(Number(await p.locator("[data-testid=position]").getAttribute("data-n")) === n, "Play moment did not open at its cursor");
  check(!/82\*|won by 4 wickets/.test(lt), "Play moment shows the result before the call");
  check(await p.locator("[data-testid=explore-next]").count() === 0, "replay shows onward links before the end");
  await p.screenshot({ path: `${out}/m08-play-moment.png`, fullPage: false });
  await p.click("[data-testid=pick-1]").catch(() => assertions.push("no pick buttons in game mode"));
  await p.waitForSelector("[data-testid=reveal]", { timeout: 15000 }).catch(() => assertions.push("no reveal after the call"));
  await settle(300);
  await p.screenshot({ path: `${out}/m09-play-reveal.png`, fullPage: false });
  await note("play-moment", { href: mhref, n });

  // share cards (one idea per card)
  const fid = await (await fetch("http://localhost:8000/api/fan/didnt-know")).json().then((j) => j.data.items[0].id);
  for (const [k, q] of [["finding", `type=finding&id=${encodeURIComponent(fid)}`], ["story", `type=story&pid=${KOHLI}&id=death_sr`],
                        ["record", "type=rec2&id=highest-score.male.T20.major"], ["prediction", "type=prediction&ok=1&pick=4&actual=4&pts=3&mpick=1&mpts=0&line=ICC%20T20%20World%20Cup"],
                        ["matchup", `type=battle&bat=${KOHLI}&bowl=${ZAMPA}`], ["innings", `type=innings&m=${MCG}&i=2&pid=${KOHLI}`]]) {
    await p.goto(`${BASE}/share?${q}`); await settle(1000);
    check(await p.locator(".share-frame svg").count() === 1, `share card ${k} did not render`);
    if (["finding", "record", "story", "prediction"].includes(k)) await p.locator(".share-frame").screenshot({ path: `${out}/m10-share-${k}.png` });
  }
  await note("share-cards", {});

  // Compare V2
  await p.goto(`${BASE}/compare`); await settle(800);
  check(await p.locator("[data-testid=compare-suggestions] a").count() >= 3, "empty Compare has no suggestions");
  await p.locator("[data-testid=compare-suggestions] a", { hasText: "Kohli v Rohit" }).click(); await settle(1500);
  check(await p.locator("[data-testid=compare-v2]").count() === 1, "Compare V2 missing");
  const ct = await text(p, "[data-testid=compare-v2]");
  check(/leads/.test(ct) && /tied/i.test(ct), "Compare V2 lacks lead / tie statements");
  check(!/winner is|overall rating|\bscore: \d/i.test(ct.replace(/No overall score/g, "")), "Compare V2 shows a single score");
  await p.screenshot({ path: `${out}/m11-compare-v2.png`, fullPage: true });
  await p.goto(`${BASE}/compare?ids=${BUMRAH},3fb19989`); await settle(1500);
  check(await p.locator("[data-testid=compare-v2] .cmp-row").count() >= 6, "Bumrah v Starc compare too thin");
  await note("compare", {});

  // Records V2, On This Day
  await p.goto(`${BASE}/records`); await settle(1000);
  check(await p.locator("[data-testid=record-book] .rec-card").count() >= 20, "record book too small");
  await p.screenshot({ path: `${out}/m12-record-book.png`, fullPage: false });
  await p.goto(`${BASE}/records/highest-score.male.T20.major`); await settle(1000);
  check(await p.locator("[data-testid=record-rows] a").count() >= 5, "record page has fewer than 5 rows");
  await p.screenshot({ path: `${out}/m13-record.png`, fullPage: true });
  await p.goto(`${BASE}/on-this-day`); await settle(1000);
  check(await p.locator("[data-testid=on-this-day-page]").count() === 1, "On This Day page missing");
  await p.screenshot({ path: `${out}/m14-on-this-day.png`, fullPage: true });
  await note("records-otd", {});

  // Ask V3: the ten required questions
  const QS = ["Who dismisses Kohli most?", "Who has Kohli scored fastest against?", "What changes after Kohli faces 30 balls?",
    "Who are the best death-over bowlers since 2020?", "Which players are most similar to Rohit?", "What is Bumrah's best spell?",
    "Who partners Mandhana best?", "Compare Kohli and Rohit in chases", "Show India's biggest successful T20 chases",
    "Which Kohli-Zampa dismissals happened in death overs?"];
  const asked = [];
  for (const [i, q] of QS.entries()) {
    await p.goto(`${BASE}/ask?q=${encodeURIComponent(q)}`); await settle(900);
    const interp = await text(p, ".interp");
    const ans = await text(p, "[data-testid=ask-answer]");
    check(/How I interpreted/.test(interp), `Ask "${q}": no interpretation shown`);
    check(ans.length > 20 && !/couldn.t tell|isn't supported|can't yet/i.test(ans), `Ask "${q}": no answer (${ans.slice(0, 80)})`);
    asked.push({ q, a: ans.split("\n").find((l) => l.length > 30)?.slice(0, 140) });
    if (i === 1 || i === 7 || i === 9) await p.screenshot({ path: `${out}/m15-ask-${i}.png`, fullPage: true });
  }
  await note("ask", { answers: asked });
});

// ------------------------------------------------------------------ 4. Desktop
await session(De, async (p, settle) => {
  for (const [k, u] of [["explore", "/"], ["kohli", `/players/${KOHLI}`], ["bumrah", `/players/${BUMRAH}`], ["compare", `/compare?ids=${MANDHANA},27e003ce`],
                        ["records", "/records"], ["battle", `/battle?bat=${KOHLI}&bowl=${ZAMPA}`], ["lesser", `/players/${LESSER}`]]) {
    await p.goto(BASE + u); await settle(1500);
    await p.screenshot({ path: `${out}/d-${k}.png`, fullPage: true });
    await note(`desktop-${k}`, {});
  }
});

fs.writeFileSync(`${out}/report.json`, JSON.stringify({ errors, aborted_by_navigation: aborted.length, assertions, log }, null, 2));
await browser.close();
console.log(JSON.stringify({ errors: errors.length, aborted_by_navigation: aborted.length, assertions: assertions.length, first_errors: errors.slice(0, 8), first_assertions: assertions.slice(0, 15) }));
