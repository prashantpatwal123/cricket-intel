// Phase 4 journeys on REAL data: search, match, competition, rivalry, career, libraries, battle universe, records v2, ask v3,
// stories, share cards, daily feed, rabbit-hole navigation, methodology. Usage: node screenshots-phase4.mjs <outdir>
import { chromium } from "playwright";
import fs from "node:fs";
const out = process.argv[2];
const BASE = process.env.BASE || "http://localhost:3000";
const KOHLI = "ba607b88", ZAMPA = "14f96089", MANDHANA = "5d2eda89", BUMRAH = "462411b3", LOWS = "7b679de5";
const MATCH = "1298150", WPL_FINAL = "1513703";
const browser = await chromium.launch({ executablePath: process.env.CHROME || undefined });
const errors = [], log = [], assertions = [], aborted = [];
let cur = null;
const overflow = (p) => p.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
const note = async (k, v) => { if (cur) v.overflow_px = await overflow(cur); if (v.overflow_px > 0) assertions.push(`overflow ${k}: ${v.overflow_px}px`); log.push({ step: k, ...v }); console.log(k, JSON.stringify(v).slice(0, 230)); };
const check = (cond, msg) => { if (!cond) assertions.push(msg); };
async function session(viewport, fn) {
  const ctx = await browser.newContext({ viewport, deviceScaleFactor: 2, acceptDownloads: true });
  const p = await ctx.newPage(); cur = p;
  p.on("pageerror", (e) => errors.push(`pageerror ${p.url()}: ${e}`));
  p.on("console", (m) => m.type() === "error" && errors.push(`console ${p.url()}: ${m.text()}`));
  p.on("response", (r) => r.status() >= 400 && errors.push(`${r.status()} ${r.url()}`));
  // net::ERR_ABORTED = a prefetch/in-flight request cancelled by our own navigation; counted separately, not a failure.
  p.on("requestfailed", (r) => { if (r.url().startsWith("data:")) return; const t = r.failure()?.errorText || "";
    if (t.includes("ERR_ABORTED")) aborted.push(r.url()); else errors.push(`failed ${r.url()} ${t}`); });
  const settle = (ms = 500) => p.waitForLoadState("networkidle").then(() => p.waitForTimeout(ms));
  await p.goto(BASE + "/players"); await p.evaluate(() => localStorage.setItem("ci-preview-notice", "1"));
  await fn(p, settle);
  await ctx.close();
}
const Mo = { width: 390, height: 844 }, De = { width: 1280, height: 900 };

await session(Mo, async (p, settle) => {
  // 1. Universal search
  await p.goto(`${BASE}/search`); await settle();
  const results = {};
  for (const [i, q] of ["Virat Kohli", "Kohli vs Zampa", "India Pakistan 2022", "Bumrah 6/19", "Mandhana partnerships", "2023 World Cup", "death overs economy", "RCB v CSK"].entries()) {
    await p.fill(".search-big", q); await p.waitForTimeout(500); await settle(200);
    const groups = await p.locator(".sgroup").evaluateAll((els) => els.map((e) => e.querySelector(".sgroup-h").textContent + ": " + (e.querySelector(".srow b")?.textContent || "")));
    results[q] = groups.slice(0, 2);
    check(groups.length > 0, `search returned nothing for ${q}`);
    if ([1, 2, 3, 7].includes(i)) await p.screenshot({ path: `${out}/m01-search-${i}.png`, fullPage: true });
  }
  await note("search", { results });
  await p.fill(".search-big", "Bumrah 6/19"); await p.waitForTimeout(600); await settle(200);
  await p.locator(".srow").first().click(); await settle(800);
  await note("search-open", { url: p.url() }); check(p.url().includes("/spell/1276907"), "Bumrah 6/19 search did not open the spell");

  // 2. Match intelligence (famous match) + WPL final
  await p.goto(`${BASE}/match/${MATCH}`); await settle(900);
  await p.screenshot({ path: `${out}/m02-match.png`, fullPage: true });
  await note("match", { head: (await p.locator(".match-head").innerText()).split("\n").slice(0, 6).join(" | "), events: await p.locator(".ev-line").count(),
    xnext: await p.locator(".xnext-row").count() });
  await p.locator(".tabs button").nth(1).click(); await p.waitForTimeout(200);
  await p.locator(".sc-row", { hasText: "Virat Kohli" }).first().click(); await settle(700);
  await note("match-to-innings", { url: p.url() }); check(p.url().includes(`/innings/${MATCH}/2/${KOHLI}`), "match batting row did not open innings");
  await p.goto(`${BASE}/match/${WPL_FINAL}`); await settle(900);
  await p.screenshot({ path: `${out}/m03-match-wpl-final.png`, fullPage: true });
  await note("match-wpl", { head: (await p.locator(".match-head").innerText()).split("\n").slice(0, 5).join(" | ") });

  // 3. Competitions
  for (const [k, u] of [["ipl", "/competition?name=Indian%20Premier%20League&gender=male"], ["t20wc", "/competition?name=ICC%20Men%27s%20T20%20World%20Cup&gender=male"],
                        ["wpl", "/competition?name=Women%27s%20Premier%20League&gender=female&season=2024/25"]]) {
    await p.goto(BASE + u); await settle(1000);
    await p.screenshot({ path: `${out}/m04-competition-${k}.png`, fullPage: true });
    await note(`competition-${k}`, { coverage: await p.locator(".cov-line").innerText(), editions: await p.locator(".edition-strip button").count() });
  }
  await p.locator(".edition-strip button").nth(1).click(); await settle(800);
  await note("competition-edition-click", { url: p.url() });

  // 4. Rivalries
  for (const [k, u] of [["ind-aus", "/rivalry?a=India&b=Australia&gender=male"], ["rcb-csk", "/rivalry?a=Royal%20Challengers%20Bangalore&b=Chennai%20Super%20Kings&gender=male"],
                        ["india-women", "/rivalry?a=India&gender=female"]]) {
    await p.goto(BASE + u); await settle(1000);
    await p.screenshot({ path: `${out}/m05-rivalry-${k}.png`, fullPage: true });
    await note(`rivalry-${k}`, { head: (await p.locator("section").first().innerText()).split("\n").slice(0, 6).join(" | ") });
  }

  // 5. Career explorer: famous and less-covered player
  await p.goto(`${BASE}/players/${KOHLI}?tab=career`); await settle(1200);
  await p.screenshot({ path: `${out}/m06-career-kohli.png`, fullPage: true });
  await p.locator(".cy:not(.gap):not(.all)").nth(8).click(); await settle(900);
  await note("career-year", { url: p.url(), year: await p.locator(".display-xl").last().innerText(), innings: await p.locator(".tablist .trow").count() });
  await p.screenshot({ path: `${out}/m07-career-year.png`, fullPage: true });
  await p.goto(`${BASE}/players/${LOWS}?tab=career`); await settle(1000);
  await p.screenshot({ path: `${out}/m08-career-low-coverage.png`, fullPage: true });
  await note("career-low", { strip: await p.locator(".cy").count(), chips: (await p.locator(".hero .chips").innerText()).replace(/\n/g, " ") });

  // 6. Libraries
  await p.goto(`${BASE}/innings?cat=difficult_chase`); await settle(900);
  await p.screenshot({ path: `${out}/m09-innings-library.png`, fullPage: true });
  await note("innings-library", { def: await p.locator(".def-line").innerText(), rows: await p.locator(".trow").count() });
  await p.goto(`${BASE}/innings?cat=fastest&gender=female&competition=Women%27s%20Premier%20League`); await settle(900);
  await note("innings-library-wpl", { first: await p.locator(".trow").first().innerText() });
  await p.goto(`${BASE}/spells?cat=death_spells`); await settle(900);
  await p.screenshot({ path: `${out}/m10-spell-library.png`, fullPage: true });
  await p.locator(".trow").first().click(); await settle(900);
  await note("spell-library-open", { url: p.url() }); check(p.url().includes("/spell/"), "spell library row did not open a spell");

  // 7. Battle universe + similar + low-sample battle
  await p.goto(`${BASE}/battle`); await settle(900);
  await p.locator(".cat-strip button", { hasText: "Unusually one-sided" }).click(); await settle(700);
  await p.screenshot({ path: `${out}/m11-battle-universe.png`, fullPage: true });
  await note("universe", { first: await p.locator(".trow").first().innerText() });
  await p.goto(`${BASE}/battle?bat=${KOHLI}&bowl=${ZAMPA}`); await settle(1300);
  await p.locator(".rule-section", { hasText: "Similar battles" }).screenshot({ path: `${out}/m12-similar-battles.png` });
  await note("similar", { rows: await p.locator(".trow", { hasText: "d " }).count() });
  await p.goto(`${BASE}/battle?bat=${LOWS}&bowl=f9e6e7ef`); await settle(1300);
  await p.screenshot({ path: `${out}/m13-battle-low-sample.png`, fullPage: true });
  await note("battle-low-sample", { sample: await p.locator(".note").first().innerText().catch(() => ""), sim: await p.locator(".rule-section", { hasText: "Similar battles" }).innerText() });

  // 8. Records v2
  await p.goto(`${BASE}/records?metric=bowling_average&gender=male&format=ODI&full_members=true&min_matches=20`); await settle(1200);
  await p.screenshot({ path: `${out}/m14-records-v2.png`, fullPage: true });
  await note("records-v2", { sql: await p.locator("code.sqldef").innerText(), first: await p.locator(".rec-row").first().innerText() });
  await p.goto(`${BASE}/records?metric=strike_rate&gender=male&competition=Indian%20Premier%20League&team=Royal%20Challengers%20Bengaluru&batter_stage=set&min=200`); await settle(1000);
  await note("records-team-stage", { first: await p.locator(".rec-row").first().innerText().catch(() => "none") });

  // 9. Ask v3
  const asks = ["Show Kohli's best covered innings while chasing", "What happened in India v Pakistan in Melbourne in 2022?", "Who partners Mandhana best?",
    "Show Bumrah's best death-over spells", "Which bowlers have troubled Kohli most?", "Compare Kohli before and after 2020",
    "Who improved their strike rate most after 30 balls?", "Show me unusual India-Australia battles"];
  for (const [i, q] of asks.entries()) {
    await p.goto(`${BASE}/ask?q=${encodeURIComponent(q)}`); await settle(800);
    const ans = await p.locator(".ans").innerText().catch(() => "NO ANSWER");
    check(ans !== "NO ANSWER", `ask failed: ${q}`);
    if ([0, 1, 4, 7].includes(i)) await p.screenshot({ path: `${out}/m15-ask-${i + 1}.png`, fullPage: true });
    await note(`ask-${i + 1}`, { q, ans: ans.slice(0, 160) });
  }

  // 10. Stories
  for (const [k, u] of [["innings", `/story/innings/${MATCH}/2/${KOHLI}`], ["battle", `/story/battle?bat=${KOHLI}&bowl=${ZAMPA}`], ["match", `/story/match/${MATCH}`]]) {
    await p.goto(BASE + u); await settle(900);
    await p.screenshot({ path: `${out}/m16-story-${k}.png`, fullPage: true });
    await note(`story-${k}`, { title: await p.locator(".display-xl").innerText(), cards: await p.locator(".story-step").count(),
      causal: /\bwhy\b/i.test(await p.locator(".display-xl").innerText()) });
  }

  // 11. Share cards + PNG export
  for (const [k, u] of [["innings", `/share?type=innings&m=${MATCH}&i=2&pid=${KOHLI}`], ["battle", `/share?type=battle&bat=${KOHLI}&bowl=${ZAMPA}`],
                        ["record", `/share?type=record&metric=sixes&phase=death&gender=male`], ["fingerprint", `/share?type=fingerprint&pid=${MANDHANA}`],
                        ["spell", `/share?type=spell&m=1276907&i=1&pid=${BUMRAH}`], ["whn", `/share?type=whn&pts=120&n=14&acc=43&mpts=110&beat=2`]]) {
    await p.goto(BASE + u); await settle(900);
    await p.locator(".share-frame").screenshot({ path: `${out}/m17-share-${k}.png` });
    const [dl] = await Promise.all([p.waitForEvent("download"), p.locator("[data-testid=download-png]").click()]);
    const path = `${out}/card-${k}.png`; await dl.saveAs(path);
    await note(`share-${k}`, { file: dl.suggestedFilename(), bytes: fs.statSync(path).size });
    check(fs.statSync(path).size > 20000, `share ${k} PNG too small`);
  }
  await p.locator(".seg button", { hasText: "1080×1920" }).click(); await p.waitForTimeout(300);
  await p.locator(".share-frame").screenshot({ path: `${out}/m18-share-story-format.png` });

  // 12. Explore feed
  await p.goto(`${BASE}/`); await settle(1200);
  await p.screenshot({ path: `${out}/m19-explore-feed.png`, fullPage: true });
  const feed = await p.locator("[data-testid=feed-card] .ft").allInnerTexts();
  await note("explore-feed", { cards: feed.length + 1, types: [...new Set(feed)], lead: await p.locator(".feed-lead .t").innerText() });
  check(feed.length >= 10, "feed has fewer than 11 cards");

  // 13. Methodology centre
  await p.goto(`${BASE}/data`); await settle(900);
  await p.screenshot({ path: `${out}/m20-data-centre.png`, fullPage: true });
  await note("data", { licence: await p.locator(".licence-box").innerText() });

  // 14. Rabbit hole: Kohli → Kohli–Zampa → a dismissal → (spell) → that match → tournament → record → another player
  const hops = [];
  await p.goto(`${BASE}/players/${KOHLI}`); await settle(1500); hops.push(p.url());
  // Phase 7: Explore-next is ranked per session (Rabbit-Hole engine), so hops are chosen by destination type, not fixed labels;
  // the asserted chain of page types below is unchanged.
  const X = (sel) => p.locator(`[data-testid=explore-next] ${sel}`).first();
  await p.waitForSelector("[data-testid=explore-next] .xnext-row");
  await X(".xnext-row[data-type=battle]").click(); await settle(1300); hops.push(p.url());
  await p.waitForSelector("[data-testid=explore-next] .xnext-row");
  await X(".xnext-row[data-type=delivery]").click(); await settle(1000); hops.push(p.url());
  await p.waitForSelector("[data-testid=explore-next] .xnext-row");
  await X(".xnext-row[data-type=spell]").click(); await settle(1000); hops.push(p.url());
  await p.waitForSelector("[data-testid=explore-next] .xnext-row");
  await X(".xnext-row[data-type=match]").click(); await settle(1000); hops.push(p.url());
  await p.locator("main a[href^='/competition?']").first().click(); await settle(1200); hops.push(p.url());
  await p.waitForSelector("[data-testid=explore-next] .xnext-row");
  await X(".xnext-row[href^='/records?']").click(); await settle(1200); hops.push(p.url());
  await p.locator(".rec-row").nth(1).click(); await settle(1000); hops.push(p.url());
  await note("rabbit-hole", { hops });
  const want = [/\/players\//, /\/battle\?/, /\/delivery\//, /\/spell\//, /\/match\//, /\/competition\?/, /\/records\?/, /\/players\//];
  hops.forEach((u, i) => check(want[i].test(u), `rabbit hop ${i} unexpected: ${u}`));
});

// Rabbit-hole instrumentation: every major page type must offer >= 3 meaningful next destinations
await session(Mo, async (p, settle) => {
  const pages = { player: `/players/${MANDHANA}`, battle: `/battle?bat=${KOHLI}&bowl=${ZAMPA}`, match: `/match/${MATCH}`, innings: `/innings/${MATCH}/2/${KOHLI}`,
    spell: `/spell/1276907/1/${BUMRAH}`, delivery: `/delivery/${encodeURIComponent(`${MATCH}:2:33`)}`, competition: "/competition?name=Indian%20Premier%20League&gender=male",
    rivalry: "/rivalry?a=India&b=Australia&gender=male", story: `/story/innings/${MATCH}/2/${KOHLI}` };
  const counts = {};
  for (const [k, u] of Object.entries(pages)) {
    await p.goto(BASE + u); await settle(1300);
    const n = await p.locator(".xnext-row").count();
    const links = await p.locator("main a[href^='/']").evaluateAll((as) => new Set(as.map((a) => a.getAttribute("href"))).size);
    counts[k] = { explore_next: n, internal_links: links };
    check(n >= 3, `${k} page has only ${n} Explore-next destinations`);
  }
  await note("rabbit-hole-instrumentation", { counts });
});

await session(De, async (p, settle) => {
  for (const [k, u] of [["explore", "/"], ["search", "/search?q=India%20Pakistan%202022"], ["match", `/match/${MATCH}`], ["competition", "/competition?name=Indian%20Premier%20League&gender=male"],
                        ["rivalry", "/rivalry?a=India&b=Australia&gender=male"], ["career", `/players/${MANDHANA}?tab=career&year=2025`], ["story", `/story/battle?bat=${KOHLI}&bowl=${ZAMPA}`],
                        ["share", `/share?type=innings&m=${MATCH}&i=2&pid=${KOHLI}`], ["data", "/data"], ["battle-universe", "/battle"]]) {
    await p.goto(BASE + u); await settle(1200);
    await p.screenshot({ path: `${out}/d-${k}.png`, fullPage: true });
    await note(`desktop-${k}`, {});
  }
});

fs.writeFileSync(`${out}/report.json`, JSON.stringify({ errors, aborted_by_navigation: aborted.length, assertions, log }, null, 2));
await browser.close();
console.log(JSON.stringify({ errors: errors.length, aborted_by_navigation: aborted.length, assertions: assertions.length, first_errors: errors.slice(0, 8), first_assertions: assertions.slice(0, 12) }));
