// Phase 8 terminology check: technical terms visible by default (not inside a WHY box / closed <details>) on hero pages.
import { chromium } from "playwright";
const BASE = process.env.BASE || "http://localhost:3000";
const TERMS = /\b(shrinkage|shrunk|percentile|confidence interval|false[- ]discovery|FDR|calibrat\w*|cohort|baseline|observed\/expected|Wilson|Benjamini|p-value|posterior|pseudo-balls?|z-score|regress\w*)\b/gi;
const PAGES = ["/?day=2026-10-04", "/players/ba607b88", "/players/462411b3", "/players/4a8a2e3b", "/battle?bat=ba607b88&bowl=14f96089", "/match/1298150", "/play", "/ask", "/ask?q=Who%20dismisses%20Kohli%20most%3F"];
const b = await chromium.launch({ executablePath: process.env.CHROME });
const p = await (await b.newContext({ viewport: { width: 390, height: 844 } })).newPage();
let bad = 0;
for (const u of PAGES) {
  await p.goto(BASE + u, { waitUntil: "networkidle" }); await p.waitForTimeout(1200);
  const hits = await p.evaluate((src) => { const re = new RegExp(src, "gi"); const out = [];
    const w = document.createTreeWalker(document.querySelector("main"), NodeFilter.SHOW_TEXT);
    while (w.nextNode()) { const n = w.currentNode; const el = n.parentElement; if (!el || !el.offsetParent || el.closest(".why-box,.whybox,details:not([open]),[data-glossary]")) continue;
      const m = n.textContent.match(re); if (m) out.push(`${m[0]} :: ${n.textContent.trim().slice(0, 80)}`); }
    return out; }, TERMS.source);
  bad += hits.length; console.log(u, hits.length, JSON.stringify(hits.slice(0, 8)));
}
console.log("TOTAL", bad);
await b.close();
