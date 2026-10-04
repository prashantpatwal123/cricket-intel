// Phase 8 accessibility check (390px). For each page: rendered text under 11px (SVG text scaled by its CTM),
// text contrast below 4.5:1 (normal) / 3:1 (large) against the nearest opaque background, interactive elements
// without an accessible name, tap targets under 24×24 CSS px (WCAG 2.2 AA minimum), and sideways overflow.
// Usage: CHROME=... node a11y-phase8.mjs [out.json]
import { chromium } from "playwright";
import fs from "fs";
const BASE = process.env.BASE || "http://localhost:3000";
const PAGES = ["/?day=2026-10-04", "/players/ba607b88", "/players/ba607b88?tab=style", "/players/462411b3", "/players/4a8a2e3b",
  "/battle?bat=ba607b88&bowl=14f96089", "/match/1298150", "/play", "/ask", "/ask?q=Who%20dismisses%20Kohli%20most%3F", "/discover",
  "/how-out/ba607b88", "/innings/1298150/2/ba607b88", "/live-lab/1298150", "/search?q=kohli"];
const b = await chromium.launch({ executablePath: process.env.CHROME });
const ctx = await b.newContext({ viewport: { width: 390, height: 844 } });
const p = await ctx.newPage();
await p.goto(BASE + "/data"); await p.evaluate(() => localStorage.setItem("ci-preview-notice", "1"));
const out = {};
for (const u of PAGES) {
  await p.goto(BASE + u, { waitUntil: "networkidle" }); await p.waitForTimeout(1200);
  out[u] = await p.evaluate(() => {
    const parse = (c) => { const m = c.match(/rgba?\(([^)]+)\)/); if (!m) return null; const v = m[1].split(/[ ,/]+/).filter(Boolean).map(Number); return { r: v[0], g: v[1], b: v[2], a: v[3] ?? 1 }; };
    const lum = ({ r, g, b }) => { const f = (x) => { x /= 255; return x <= 0.03928 ? x / 12.92 : ((x + 0.055) / 1.055) ** 2.4; }; return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b); };
    const bgOf = (e) => { let n = e; const stack = []; const er = e.getBoundingClientRect(); const cx = er.left + er.width / 2, cy = er.top + er.height / 2;
      while (n && n.nodeType === 1) { const nr = n.getBoundingClientRect(); const inside = cx >= nr.left && cx <= nr.right && cy >= nr.top && cy <= nr.bottom;
        // absolutely-positioned labels can sit outside their parent's painted box: only count ancestors that contain them
        const c = inside ? parse(getComputedStyle(n).backgroundColor) : null; if (c && c.a > 0) { stack.push(c); if (c.a >= 0.95) break; } n = n.parentElement; }
      let base = stack.length && stack[stack.length - 1].a >= 0.95 ? stack.pop() : parse(getComputedStyle(document.body).backgroundColor);
      for (const c of stack.reverse()) base = { r: c.r * c.a + base.r * (1 - c.a), g: c.g * c.a + base.g * (1 - c.a), b: c.b * c.a + base.b * (1 - c.a), a: 1 }; return base; };
    const tiny = {}, low = {}, noname = [], small = [];
    for (const e of document.querySelectorAll("main *")) {
      const r = e.getBoundingClientRect(); if (!r.width || !r.height) continue;
      const cs = getComputedStyle(e); if (cs.visibility === "hidden" || cs.display === "none" || e.closest("[aria-hidden=true]")) continue;
      const own = [...e.childNodes].some((n) => n.nodeType === 3 && n.textContent.trim());
      if (own) {
        let fs = parseFloat(cs.fontSize);
        if (e instanceof SVGElement && e.getScreenCTM) { const m = e.getScreenCTM(); if (m) fs *= Math.sqrt(Math.abs(m.a * m.d - m.b * m.c)); }
        const k = `${e.tagName.toLowerCase()}.${(e.getAttribute("class") || "").split(" ")[0]}`;
        if (fs < 10.95) tiny[k] = Math.min(tiny[k] ?? 99, Math.round(fs * 10) / 10);
        if (!(e instanceof SVGElement)) {
          const fg = parse(cs.color); const bg = bgOf(e);
          if (fg && bg) { const a = fg.a; const c = { r: fg.r * a + bg.r * (1 - a), g: fg.g * a + bg.g * (1 - a), b: fg.b * a + bg.b * (1 - a) };
            const L1 = lum(c), L2 = lum(bg); const ratio = (Math.max(L1, L2) + 0.05) / (Math.min(L1, L2) + 0.05);
            const large = fs >= 24 || (fs >= 18.66 && +cs.fontWeight >= 700); const need = large ? 3 : 4.5;
            if (ratio < need) low[k] = Math.min(low[k] ?? 99, Math.round(ratio * 100) / 100); }
        }
      }
      if (e.matches("a[href],button,input,select,textarea,summary,[role=button]")) {
        const name = (e.getAttribute("aria-label") || e.getAttribute("title") || e.textContent || e.getAttribute("placeholder") || (e.id && document.querySelector(`label[for="${e.id}"]`)?.textContent) || "").trim();
        if (!name) noname.push(e.outerHTML.slice(0, 90));
        // WCAG 2.5.8 exempts inline links inside a sentence: skip anchors whose parent has other text
        const inline = e.tagName === "A" && [...(e.parentElement?.childNodes || [])].some((n) => n !== e && n.nodeType === 3 && n.textContent.trim());
        if ((r.width < 24 || r.height < 24) && !inline && !e.closest("p,li .pl-h,.mini,dd")) small.push(`${e.tagName.toLowerCase()}.${(e.getAttribute("class") || "").split(" ")[0]} ${Math.round(r.width)}×${Math.round(r.height)} "${(e.textContent || "").trim().slice(0, 24)}"`);
      }
    }
    const svgs = [...document.querySelectorAll("main svg")].filter((s) => s.getBoundingClientRect().width > 60);
    const svgNoAlt = svgs.filter((s) => !s.getAttribute("aria-label") && !s.getAttribute("aria-labelledby") && !s.querySelector("title") && s.getAttribute("aria-hidden") !== "true" && s.getAttribute("role") !== "presentation").length;
    return { overflow: document.documentElement.scrollWidth - innerWidth, tiny, lowContrast: low, unnamed: noname.slice(0, 10), smallTargets: [...new Set(small)].slice(0, 15), svgWithoutTextEquivalent: svgNoAlt, h1: document.querySelectorAll("h1").length };
  });
  console.log(u, JSON.stringify(out[u]));
}
// keyboard: first Tab lands on the skip link
await p.goto(BASE + "/players/ba607b88", { waitUntil: "networkidle" }); await p.keyboard.press("Tab");
out._skip_link_first_tab = await p.evaluate(() => document.activeElement?.className || "");
out._reduced_motion_rule = await p.evaluate(() => [...document.styleSheets].some((s) => { try { return [...s.cssRules].some((r) => r.media && /prefers-reduced-motion/.test(r.media.mediaText)); } catch { return false; } }));
console.log("skip:", out._skip_link_first_tab, "reduced-motion rule:", out._reduced_motion_rule);
if (process.argv[2]) fs.writeFileSync(process.argv[2], JSON.stringify(out, null, 1));
await b.close();
