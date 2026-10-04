// Phase 8 visual regression on golden screens with stable data.
//   node visual-phase8.mjs baseline <dir>   capture the baseline (+ the Play moment fixture)
//   node visual-phase8.mjs compare  <dir> <outdir>   re-capture and pixel-diff against the baseline
// Stability: Home is pinned with ?day=, every capture uses a fresh browser (no session memory), the Play moment is
// replayed from a fixture captured with the baseline, animations are disabled. Diff: share of pixels whose RGB
// differs by more than 24/255 on any channel; fails above 0.5% (or on any size change). Diff runs in Chromium's
// canvas, so no image library is needed.
import { chromium } from "playwright";
import fs from "fs";
const BASE = process.env.BASE || "http://localhost:3000", API = process.env.API || "http://localhost:8000";
const [mode, dir, outdir] = process.argv.slice(2);
const SCREENS = [
  ["phone-home", 390, "/?day=2026-10-04"], ["phone-player", 390, "/players/ba607b88"], ["phone-battle", 390, "/battle?bat=ba607b88&bowl=14f96089"],
  ["phone-match", 390, "/match/1298150"], ["phone-ask", 390, "/ask?q=Who%20dismisses%20Kohli%20most%3F"], ["phone-play", 390, "/play"],
  ["desktop-player", 1280, "/players/ba607b88"], ["desktop-match-centre", 1280, "/live-lab/1298150?n=126"],
];
const THRESH = 0.005;
fs.mkdirSync(dir, { recursive: true }); if (outdir) fs.mkdirSync(outdir, { recursive: true });
const b = await chromium.launch({ executablePath: process.env.CHROME });
const fixture = `${dir}/play-moment.json`;

async function capture(name, w, path, file) {
  const ctx = await b.newContext({ viewport: { width: w, height: w < 600 ? 844 : 900 }, deviceScaleFactor: 1, reducedMotion: "reduce" });
  const p = await ctx.newPage();
  await p.route("**/api/whn/next**", async (route) => {
    if (mode === "compare" && fs.existsSync(fixture)) return route.fulfill({ status: 200, contentType: "application/json", body: fs.readFileSync(fixture, "utf8") });
    const r = await route.fetch(); const body = await r.text(); if (mode === "baseline") fs.writeFileSync(fixture, body);
    return route.fulfill({ response: r, body });
  });
  await p.goto(BASE + "/data"); await p.evaluate(() => { localStorage.clear(); localStorage.setItem("ci-preview-notice", "1"); localStorage.setItem("ci-tour", "dismissed"); });
  await p.goto(BASE + path, { waitUntil: "networkidle" });
  await p.addStyleTag({ content: "*,*::before,*::after{animation:none!important;transition:none!important;caret-color:transparent!important}" });
  await p.waitForTimeout(1800);
  await p.screenshot({ path: file, fullPage: true });
  await ctx.close();
}

async function diff(a, bfile, outfile) {
  const ctx = await b.newContext(); const p = await ctx.newPage();
  const r = await p.evaluate(async ([A, B]) => {
    const load = (src) => new Promise((res) => { const i = new Image(); i.onload = () => res(i); i.src = src; });
    const [ia, ib] = await Promise.all([load(A), load(B)]);
    if (ia.width !== ib.width || ia.height !== ib.height) return { size: [ia.width, ia.height, ib.width, ib.height] };
    const c = (img) => { const cv = document.createElement("canvas"); cv.width = img.width; cv.height = img.height; const x = cv.getContext("2d"); x.drawImage(img, 0, 0); return x.getImageData(0, 0, img.width, img.height); };
    const da = c(ia), db = c(ib); const out = document.createElement("canvas"); out.width = ia.width; out.height = ia.height; const ox = out.getContext("2d"); const od = ox.createImageData(ia.width, ia.height);
    let n = 0; for (let k = 0; k < da.data.length; k += 4) { const d = Math.max(Math.abs(da.data[k] - db.data[k]), Math.abs(da.data[k + 1] - db.data[k + 1]), Math.abs(da.data[k + 2] - db.data[k + 2]));
      if (d > 24) { n++; od.data[k] = 255; od.data[k + 3] = 255; } else { od.data[k] = od.data[k + 1] = od.data[k + 2] = da.data[k] / 4; od.data[k + 3] = 255; } }
    ox.putImageData(od, 0, 0); return { share: n / (da.data.length / 4), png: out.toDataURL("image/png") };
  }, [`data:image/png;base64,${fs.readFileSync(a).toString("base64")}`, `data:image/png;base64,${fs.readFileSync(bfile).toString("base64")}`]);
  if (r.png) fs.writeFileSync(outfile, Buffer.from(r.png.split(",")[1], "base64"));
  await ctx.close(); return r;
}

let fails = 0;
for (const [name, w, path] of SCREENS) {
  if (mode === "baseline") { await capture(name, w, path, `${dir}/${name}.png`); console.log("baseline", name); continue; }
  const cur = `${outdir}/${name}.png`; await capture(name, w, path, cur);
  const r = await diff(`${dir}/${name}.png`, cur, `${outdir}/${name}.diff.png`);
  const bad = r.size || r.share > THRESH; if (bad) fails++;
  console.log(`${bad ? "DIFF" : "same"} ${name} ${r.size ? `size ${r.size.join("×")}` : `${(100 * r.share).toFixed(3)}% px`}`);
}
await b.close();
if (mode === "compare") { console.log(`VISUAL ${SCREENS.length - fails}/${SCREENS.length}`); process.exit(fails ? 1 : 0); }
