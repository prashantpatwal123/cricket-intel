// Time from navigation start to "Explore next" rendered, phone viewport, unthrottled and 4x CPU throttle.
import { chromium } from "playwright";
const B = "http://localhost:3000";
const pages = [["player", "/players/ba607b88"], ["bowler", "/players/462411b3"], ["battle", "/battle?bat=ba607b88&bowl=14f96089"], ["match", "/match/1298150"],
  ["innings", "/innings/1298150/2/ba607b88"], ["record", "/records/highest-score.male.T20.major"]];
const b = await chromium.launch({ executablePath: process.env.CHROME });
const out = {};
for (const thr of [1, 4]) {
  const ctx = await b.newContext({ viewport: { width: 390, height: 844 } });
  const p = await ctx.newPage();
  const cdp = await ctx.newCDPSession(p); await cdp.send("Emulation.setCPUThrottlingRate", { rate: thr });
  await p.goto(B + "/data"); await p.evaluate(() => localStorage.setItem("ci-preview-notice", "1"));
  for (const [k, u] of pages) {
    const ts = [];
    for (let i = 0; i < 3; i++) {
      const t = Date.now(); await p.goto(B + u); await p.waitForSelector("[data-testid=explore-next] .xnext-row", { timeout: 30000 }); ts.push(Date.now() - t);
    }
    ts.sort((a, c) => a - c); out[`${k}@${thr}x`] = ts[1];
  }
  await ctx.close();
}
console.log(JSON.stringify(out));
await b.close();
