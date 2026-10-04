// Phase 7 fan audit: walk the current product at 390px and measure friction signals per page.
import { chromium } from "playwright";
import fs from "node:fs";
const out = process.argv[2];
const BASE = "http://localhost:3000";
const browser = await chromium.launch({ executablePath: process.env.CHROME || undefined });
const ctx = await browser.newContext({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 1 });
const p = await ctx.newPage();
const errors = [];
p.on("pageerror", (e) => errors.push(`pageerror ${p.url()}: ${e}`));
p.on("console", (m) => m.type() === "error" && errors.push(`console ${p.url()}: ${m.text()}`));
p.on("response", (r) => r.status() >= 400 && errors.push(`${r.status()} ${r.url()}`));
await p.goto(BASE + "/data"); await p.evaluate(() => localStorage.setItem("ci-preview-notice", "1"));
const pages = [
  ["explore", "/"], ["kohli", "/players/ba607b88"], ["bumrah", "/players/462411b3"], ["mandhana", "/players/5d2eda89"],
  ["lesser", "/players/7b679de5"], ["kohli-zampa", "/battle?bat=ba607b88&bowl=14f96089"], ["mcg-2022", "/match/1298150"],
  ["kohli-82", "/innings/1298150/2/ba607b88"], ["ask", "/ask"], ["ask-kohli-out", "/ask?q=" + encodeURIComponent("Who dismisses Kohli most?")],
  ["play", "/play"], ["records", "/records"], ["compare", "/compare"], ["search", "/search"], ["live-lab", "/live-lab"],
];
const res = [];
for (const [k, path] of pages) {
  await p.goto(BASE + path, { waitUntil: "networkidle" }).catch(() => {}); await p.waitForTimeout(1200);
  const m = await p.evaluate(() => {
    const main = document.querySelector("main") || document.body;
    const vis = (e) => { const r = e.getBoundingClientRect(); return r.width > 0 && r.height > 0; };
    const links = [...main.querySelectorAll("a[href]")].filter(vis);
    const internal = links.map((a) => a.getAttribute("href")).filter((h) => h.startsWith("/"));
    const kinds = {}; internal.forEach((h) => { const t = h.split(/[/?]/)[1] || "home"; kinds[t] = (kinds[t] || 0) + 1; });
    const txt = main.innerText;
    const method = (txt.match(/methodolog|shrink|credib|posterior|provenance|prior|confidence interval|Bayes|multiple.compar|Benjamini|percentile|DERIVED|OBSERVED|MODELLED/gi) || []).length;
    const tiny = [...main.querySelectorAll("*")].filter((e) => e.childElementCount === 0 && e.innerText?.trim() && vis(e) && parseFloat(getComputedStyle(e).fontSize) < 11).length;
    const tables = main.querySelectorAll("table, .trow").length;
    const heads = [...main.querySelectorAll("h1,h2,h3")].filter(vis).map((h) => h.tagName + ":" + h.innerText.trim().slice(0, 60));
    const fold = [...main.querySelectorAll("h1,h2,h3,p,a,button")].filter((e) => vis(e) && e.getBoundingClientRect().top < 844 && e.getBoundingClientRect().top >= 0).map((e) => e.innerText.trim().slice(0, 50)).filter(Boolean).slice(0, 14);
    const lastLinkY = links.length ? Math.max(...links.map((a) => a.getBoundingClientRect().top + scrollY)) : 0;
    return { height: document.documentElement.scrollHeight, screens: +(document.documentElement.scrollHeight / 844).toFixed(1),
      overflow: document.documentElement.scrollWidth - innerWidth, links: internal.length, uniqueLinks: new Set(internal).size, kinds,
      explore_next: !!main.querySelector("[data-testid=explore-next]"), method_terms: method, tiny_text: tiny, table_rows: tables,
      words: txt.split(/\s+/).length, heads, fold, links_after_last: Math.round((document.documentElement.scrollHeight - lastLinkY) / 844 * 10) / 10 };
  });
  await p.screenshot({ path: `${out}/${k}.png`, fullPage: true });
  res.push({ page: k, path, ...m }); console.log(k, JSON.stringify({ ...m, heads: m.heads.length, fold: undefined }));
}
fs.writeFileSync(`${out}/metrics.json`, JSON.stringify({ res, errors }, null, 1));
console.log("errors", errors.length, errors.slice(0, 5));
await browser.close();
