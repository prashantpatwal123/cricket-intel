"use client";
export default function Spark({ values, labels, color = "#35e0c2", height = 60, fmt = (v: number) => String(v) }: { values: (number | null)[]; labels?: (string | number)[]; color?: string; height?: number; fmt?: (v: number) => string }) {
  const W = 320, H = height, P = 6;
  const vs = values.filter((v): v is number => v != null);
  if (vs.length < 2) return null;
  const lo = Math.min(...vs), hi = Math.max(...vs) || 1;
  const X = (i: number) => P + (i / (values.length - 1)) * (W - 2 * P);
  const Y = (v: number) => P + (1 - (v - lo) / (hi - lo || 1)) * (H - 2 * P - 12);
  const segs: string[][] = [[]];
  values.forEach((v, i) => { if (v == null) segs.push([]); else segs[segs.length - 1].push(`${X(i)},${Y(v)}`); });
  return (
    <svg viewBox={`0 0 ${W} ${H}`} style={{ width: "100%", maxWidth: 420 }} role="img" aria-label="Trend">
      {segs.filter((s) => s.length > 1).map((s, i) => <polyline key={i} fill="none" stroke={color} strokeWidth={2} points={s.join(" ")} />)}
      {values.map((v, i) => v == null ? null : <circle key={i} cx={X(i)} cy={Y(v)} r={2.6} fill={color}><title>{`${labels?.[i] ?? i}: ${fmt(v)}`}</title></circle>)}
      {labels && <><text x={P} y={H - 1} fontSize={9.5} fill="#5d6a88">{labels[0]}</text><text x={W - P} y={H - 1} fontSize={9.5} fill="#5d6a88" textAnchor="end">{labels[labels.length - 1]}</text></>}
    </svg>
  );
}
