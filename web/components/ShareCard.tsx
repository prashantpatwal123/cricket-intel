"use client";
// Share cards: 1080×1350 (portrait) or 1080×1920 (story). Pure SVG built from computed data; exported to PNG in the browser.
// Every card carries: finding, key statistic, players/teams, coverage wording, CRICINTEL branding, Cricsheet attribution,
// provenance, and (while the data licence is pending) an INTERNAL PREVIEW mark.
import React from "react";

export interface CardSpec {
  eyebrow: string;
  title: string;
  big: string;
  bigLabel: string;
  stats: { label: string; value: string }[];
  lines?: string[];
  visual?: { kind: "bars"; values: number[]; colors?: string[] } | { kind: "rank"; rows: { name: string; value: string }[] } |
           { kind: "polar"; values: { label: string; pct: number | null }[] } | { kind: "split"; a: number; b: number; la: string; lb: string } |
           { kind: "worm"; series: number[][] };
  prov: string;
  coverage: string;
}

const FONT = "Arial Narrow, Roboto Condensed, Helvetica Neue, Arial, sans-serif";
const C = { bg1: "#0d1d38", bg2: "#060a14", accent: "#35e0c2", amber: "#ffb547", wicket: "#ff5c74", text: "#edf2fc", muted: "#8d9ab8", line: "#233154" };

function wrap(text: string, max: number): string[] {
  const words = text.split(" "); const out: string[] = []; let cur = "";
  for (const w of words) { if ((cur + " " + w).trim().length > max) { if (cur) out.push(cur); cur = w; } else cur = (cur + " " + w).trim(); }
  if (cur) out.push(cur);
  return out;
}

function Visual({ v, y, h }: { v: CardSpec["visual"]; y: number; h: number }) {
  if (!v) return null;
  const X0 = 80, W = 920;
  if (v.kind === "bars") {
    const m = Math.max(1, ...v.values); const bw = W / v.values.length;
    return <g>{v.values.map((x, i) => <rect key={i} x={X0 + i * bw + 1} y={y + h - (h * x) / m} width={Math.max(2, bw - 3)} height={(h * x) / m} rx={3} fill={v.colors?.[i] ?? C.accent} opacity={0.9} />)}
      <line x1={X0} x2={X0 + W} y1={y + h} y2={y + h} stroke={C.line} strokeWidth={2} /></g>;
  }
  if (v.kind === "rank") {
    return <g>{v.rows.slice(0, 5).map((r, i) => <g key={i} transform={`translate(${X0},${y + i * (h / 5)})`}>
      <text x={0} y={46} fontSize={40} fontWeight={900} fill={C.muted} fontFamily={FONT}>{i + 1}</text>
      <text x={70} y={46} fontSize={40} fontWeight={800} fill={C.text} fontFamily={FONT}>{r.name.length > 28 ? r.name.slice(0, 27) + "…" : r.name}</text>
      <text x={W} y={46} fontSize={44} fontWeight={900} fill={i === 0 ? C.accent : C.text} textAnchor="end" fontFamily={FONT}>{r.value}</text>
      <line x1={0} x2={W} y1={h / 5 - 6} y2={h / 5 - 6} stroke={C.line} /></g>)}</g>;
  }
  if (v.kind === "split") {
    const t = v.a + v.b || 1;
    return <g><rect x={X0} y={y + h / 2 - 30} width={W} height={60} rx={30} fill={C.amber} />
      <rect x={X0} y={y + h / 2 - 30} width={(W * v.a) / t} height={60} rx={30} fill={C.accent} />
      <text x={X0} y={y + h / 2 + 90} fontSize={36} fill={C.text} fontFamily={FONT} fontWeight={800}>{v.la} {v.a}</text>
      <text x={X0 + W} y={y + h / 2 + 90} fontSize={36} fill={C.text} fontFamily={FONT} fontWeight={800} textAnchor="end">{v.lb} {v.b}</text></g>;
  }
  if (v.kind === "polar") {
    const cx = 540, cy = y + h / 2, r0 = 50, R = Math.min(h / 2 - 20, 300), N = v.values.length;
    return <g>{[0.5, 1].map((f) => <circle key={f} cx={cx} cy={cy} r={r0 + (R - r0) * f} fill="none" stroke="#ffffff22" strokeDasharray={f === 1 ? "4 8" : "0"} />)}
      {v.values.map((d, i) => {
        if (d.pct == null) return null;
        const a0 = (i / N) * 2 * Math.PI - Math.PI / 2 + 0.04, a1 = ((i + 1) / N) * 2 * Math.PI - Math.PI / 2 - 0.04, r = r0 + (R - r0) * Math.max(0.04, d.pct / 100);
        const p = (a: number, rr: number) => `${cx + rr * Math.cos(a)} ${cy + rr * Math.sin(a)}`;
        return <path key={i} d={`M ${p(a0, r0)} L ${p(a0, r)} A ${r} ${r} 0 0 1 ${p(a1, r)} L ${p(a1, r0)} Z`} fill={["#35e0c2", "#ff5c74", "#ffb547", "#7cc4ff", "#c49bff"][i % 5]} opacity={0.85} />;
      })}</g>;
  }
  if (v.kind === "worm") {
    const all = v.series.flat(); const m = Math.max(1, ...all); const n = Math.max(...v.series.map((s) => s.length));
    return <g>{v.series.map((s, k) => { let c = 0; const pts = s.map((x, i) => { c += x; return `${X0 + ((i + 1) / n) * W},${y + h - (h * c) / (m * n * 0.6)}`; });
      return <polyline key={k} fill="none" stroke={[C.accent, C.amber][k]} strokeWidth={6} points={[`${X0},${y + h}`, ...pts].join(" ")} />; })}
      <line x1={X0} x2={X0 + W} y1={y + h} y2={y + h} stroke={C.line} strokeWidth={2} /></g>;
  }
  return null;
}

export const ShareCard = React.forwardRef<SVGSVGElement, { spec: CardSpec; story?: boolean }>(function ShareCard({ spec, story }, ref) {
  const H = story ? 1920 : 1350;
  const titleLines = wrap(spec.title, 26).slice(0, 3);
  const lines = (spec.lines || []).slice(0, story ? 4 : 2);
  // Stack every block from the one above so nothing overlaps, whatever the title length.
  const bigSize = story ? 230 : 170;
  const titleEnd = 290 + (titleLines.length - 1) * 76;
  const bigY = titleEnd + 40 + Math.round(bigSize * 0.8);
  const labelY = bigY + 56;
  const statsY = labelY + (story ? 110 : 84);
  const vy = statsY + (story ? 90 : 70);
  const linesTop = H - 176 - lines.length * 40;
  const vh = Math.max(120, linesTop - 30 - vy);
  return (
    <svg ref={ref} xmlns="http://www.w3.org/2000/svg" viewBox={`0 0 1080 ${H}`} width={1080} height={H} style={{ width: "100%", height: "auto", display: "block" }}>
      <defs>
        <radialGradient id="sbg" cx="80%" cy="0%" r="110%"><stop offset="0%" stopColor="#174a58" /><stop offset="45%" stopColor={C.bg1} /><stop offset="100%" stopColor={C.bg2} /></radialGradient>
      </defs>
      <rect width="1080" height={H} fill="url(#sbg)" />
      <circle cx={1010} cy={H - 120} r={260} fill="none" stroke="#ffffff08" strokeWidth={60} />
      <circle cx={92} cy={96} r={14} fill={C.accent} />
      <text x={120} y={108} fontSize={36} fontWeight={900} letterSpacing={6} fill={C.text} fontFamily={FONT}>CRICINTEL</text>
      <text x={1000} y={106} fontSize={22} fontWeight={800} letterSpacing={3} fill={C.amber} textAnchor="end" fontFamily={FONT}>INTERNAL PREVIEW · NOT FOR PUBLICATION</text>
      <text x={80} y={210} fontSize={30} fontWeight={800} letterSpacing={4} fill={C.accent} fontFamily={FONT}>{spec.eyebrow.toUpperCase().slice(0, 52)}</text>
      {titleLines.map((l, i) => <text key={i} x={80} y={290 + i * 76} fontSize={70} fontWeight={900} fill={C.text} fontFamily={FONT}>{l.toUpperCase()}</text>)}
      <text x={80} y={bigY} fontSize={bigSize} fontWeight={900} fill={C.accent} fontFamily={FONT}>{spec.big}</text>
      <text x={84} y={labelY} fontSize={32} fontWeight={700} fill={C.muted} fontFamily={FONT}>{spec.bigLabel}</text>
      <g transform={`translate(80, ${statsY})`}>
        {spec.stats.slice(0, 4).map((s, i) => <g key={i} transform={`translate(${i * 235}, 0)`}>
          <text x={0} y={0} fontSize={48} fontWeight={900} fill={C.text} fontFamily={FONT}>{s.value}</text>
          <text x={0} y={34} fontSize={22} fontWeight={700} letterSpacing={2} fill={C.muted} fontFamily={FONT}>{s.label.toUpperCase()}</text></g>)}
      </g>
      <Visual v={spec.visual} y={vy} h={vh} />
      {lines.map((l, i) => <text key={i} x={80} y={linesTop + 28 + i * 40} fontSize={28} fill="#c4cee6" fontFamily={FONT}>{l.slice(0, 64)}</text>)}
      <line x1={80} x2={1000} y1={H - 150} y2={H - 150} stroke={C.line} strokeWidth={2} />
      <text x={80} y={H - 112} fontSize={20} fill={C.muted} fontFamily={FONT}>{spec.coverage.slice(0, 90)}</text>
      <text x={80} y={H - 82} fontSize={20} fill={C.muted} fontFamily={FONT}>Provenance: {spec.prov.slice(0, 74)}</text>
      <text x={80} y={H - 52} fontSize={20} fill={C.muted} fontFamily={FONT}>Data: Cricsheet (cricsheet.org) · computed by CRICINTEL</text>
    </svg>
  );
});

export async function svgToPng(svg: SVGSVGElement, name: string) {
  const xml = new XMLSerializer().serializeToString(svg);
  const url = "data:image/svg+xml;charset=utf-8," + encodeURIComponent(xml);
  const img = new Image();
  const w = Number(svg.getAttribute("width")), h = Number(svg.getAttribute("height"));
  await new Promise<void>((res, rej) => { img.onload = () => res(); img.onerror = rej; img.src = url; });
  const c = document.createElement("canvas"); c.width = w; c.height = h;
  c.getContext("2d")!.drawImage(img, 0, 0, w, h);
  const blob: Blob = await new Promise((res) => c.toBlob((b) => res(b!), "image/png"));
  const a = document.createElement("a"); a.href = URL.createObjectURL(blob); a.download = name; a.click();
  return blob.size;
}
