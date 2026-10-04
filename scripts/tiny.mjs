import { chromium } from "playwright";
const b = await chromium.launch({ executablePath: process.env.CHROME });
const p = await (await b.newContext({ viewport: { width: 390, height: 844 } })).newPage();
await p.goto("http://localhost:3000/data"); await p.evaluate(() => localStorage.setItem("ci-preview-notice", "1"));
for (const u of process.argv.slice(2)) {
  await p.goto("http://localhost:3000" + u, { waitUntil: "networkidle" }); await p.waitForTimeout(1500);
  const r = await p.evaluate(() => { const c = {}; for (const e of document.querySelectorAll("main *")) { const s = getComputedStyle(e); const r = e.getBoundingClientRect();
    if (e.childElementCount === 0 && e.textContent.trim() && r.width > 0 && parseFloat(s.fontSize) < 11) { const k = `${e.tagName}.${e.getAttribute("class") || ""} ${s.fontSize}`; c[k] = (c[k] || 0) + 1; } } return c; });
  console.log(u, JSON.stringify(r));
}
await b.close();
