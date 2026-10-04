"use client";
// Worm + Manhattan: cumulative runs by over for each innings (lines) and runs per over (bars), wickets as dots.
// All DERIVED from recorded deliveries.
import { useEffect, useState } from "react";
const COL = ["#35e0c2", "#ffb547"];

export default function Worm({ innings, maxOvers }: { innings: { team: string; overs: { over: number; runs: number; wkts: number }[] }[]; maxOvers: number }) {
  // Phone: a narrower drawing so axis labels render at ≥11 CSS px instead of shrinking with the viewBox.
  const [narrow, setNarrow] = useState(false);
  useEffect(() => { const q = window.matchMedia("(max-width: 600px)"); setNarrow(q.matches); const f = () => setNarrow(q.matches); q.addEventListener("change", f); return () => q.removeEventListener("change", f); }, []);
  const W = narrow ? 360 : 640, H = narrow ? 220 : 260, L = 34, B = 26, T = 12, MH = narrow ? 50 : 60;
  const cum = innings.map((i) => { let c = 0; return i.overs.map((o) => (c += o.runs)); });
  const top = Math.max(10, ...cum.flat());
  const x = (ov: number) => L + ((ov + 1) / maxOvers) * (W - L - 10);
  const y = (r: number) => T + (1 - r / top) * (H - T - B - MH);
  const maxOver = Math.max(6, ...innings.flatMap((i) => i.overs.map((o) => o.runs)));
  const bw = (W - L - 10) / maxOvers / (innings.length + 0.5);
  const summary = innings.map((inn, k) => `${inn.team}: ${cum[k][cum[k].length - 1] ?? 0} runs in ${inn.overs.length} overs, ${inn.overs.reduce((a, o) => a + o.wkts, 0)} wickets`).join("; ");
  return (
    <svg viewBox={`0 0 ${W} ${H}`} style={{ width: "100%" }} role="img" aria-label={`Worm and Manhattan chart. ${summary}.`}>
      {[0.25, 0.5, 0.75, 1].map((f) => <g key={f}><line x1={L} x2={W - 10} y1={y(f * top)} y2={y(f * top)} stroke="#ffffff0d" />
        <text x={L - 4} y={y(f * top) + 4} fontSize={11.5} textAnchor="end" fill="#8d9ab8">{Math.round(f * top)}</text></g>)}
      {innings.map((inn, k) => (
        <g key={k}>
          {inn.overs.map((o) => <rect key={o.over} x={x(o.over) - (k + 1) * bw} y={H - B - (o.runs / maxOver) * MH} width={bw - 1} height={(o.runs / maxOver) * MH}
            fill={COL[k]} opacity={0.45}><title>{`${inn.team} over ${o.over + 1}: ${o.runs}${o.wkts ? `, ${o.wkts} wkt` : ""}`}</title></rect>)}
          <polyline fill="none" stroke={COL[k]} strokeWidth={2.4} points={[`${L},${y(0)}`, ...inn.overs.map((o, i) => `${x(o.over)},${y(cum[k][i])}`)].join(" ")} />
          {inn.overs.map((o, i) => o.wkts ? <circle key={"w" + o.over} cx={x(o.over)} cy={y(cum[k][i])} r={3 + o.wkts} fill="#ff5c74" stroke="#0b1324" strokeWidth={1.5}>
            <title>{`${o.wkts} wicket${o.wkts > 1 ? "s" : ""} in over ${o.over + 1}`}</title></circle> : null)}
        </g>
      ))}
      {Array.from({ length: maxOvers / (maxOvers > 20 ? 10 : 5) + 1 }).map((_, i) => { const ov = i * (maxOvers > 20 ? 10 : 5); return <text key={ov} x={L + (ov / maxOvers) * (W - L - 10)} y={H - 8} fontSize={11.5} textAnchor="middle" fill="#8d9ab8">{ov}</text>; })}
      <line x1={L} x2={W - 10} y1={H - B} y2={H - B} stroke="#ffffff22" />
    </svg>
  );
}
