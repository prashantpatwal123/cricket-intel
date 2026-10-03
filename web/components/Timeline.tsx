"use client";
// Career timeline from covered data. Lines break across years with no data; gaps are drawn, never interpolated.
import { useEffect, useMemo, useState } from "react";
import { api, fmt, Params } from "@/lib/api";

const METRICS = [["strike_rate", "Strike rate"], ["average", "Average"], ["out_rate", "Outs / 100 balls"], ["boundary_pct", "Boundary %"], ["dot_pct", "Dot %"]] as const;
const COLORS = ["#35e0c2", "#ffb547", "#7cc4ff", "#c49bff", "#ff8a9b", "#9df26b"];

export default function Timeline({ pid, filters, onDrill }: { pid: string; filters: Params; onDrill: (t: string, q: Params) => void }) {
  const [t, setT] = useState<any | null>(null);
  const [metric, setMetric] = useState<string>("strike_rate");
  useEffect(() => { setT(null); api(`/players/${pid}/timeline`, filters).then((r) => setT(r.data)); }, [pid, JSON.stringify(filters)]);
  const series = useMemo(() => {
    if (!t) return [];
    const m: Record<string, any[]> = {};
    for (const r of t.rows) (m[`${r.format_group} · ${r.level}`] ||= []).push(r);
    return Object.entries(m).sort((a, b) => b[1].reduce((s, r) => s + r.balls, 0) - a[1].reduce((s, r) => s + r.balls, 0));
  }, [t]);
  if (!t) return <div className="loading">Loading timeline…</div>;
  if (!t.rows.length) return <div className="empty">No covered batting in this selection.</div>;
  const years = t.rows.map((r: any) => r.period);
  const y0 = Math.min(...years), y1 = Math.max(...years);
  const vals = t.rows.map((r: any) => r[metric]).filter((v: any) => v != null);
  const vmax = Math.max(1, ...vals) * 1.1, vmin = 0;
  const W = 640, H = 280, L = 44, B = 30, T = 22;
  const xOf = (y: number) => L + ((y - y0 + 0.5) / (y1 - y0 + 1)) * (W - L - 8);
  const yOf = (v: number) => T + (1 - (v - vmin) / (vmax - vmin)) * (H - T - B);
  const missing = Object.fromEntries((t.team_missing_odis_by_year || []).map((m: any) => [m.year, m.n]));
  return (
    <div>
      <div className="seg" style={{ flexWrap: "wrap", marginBottom: 10 }}>
        {METRICS.map(([k, l]) => <button key={k} className={metric === k ? "on" : ""} onClick={() => setMetric(k)}>{l}</button>)}
      </div>
      <div className="card">
        <svg viewBox={`0 0 ${W} ${H}`} style={{ width: "100%" }} role="img" aria-label="Career timeline">
          {Array.from({ length: y1 - y0 + 1 }).map((_, i) => {
            const y = y0 + i;
            const covered = series.some(([, rows]) => rows.some((r: any) => r.period === y));
            return <g key={y}>
              {!covered && <rect x={xOf(y) - (W - L) / (y1 - y0 + 1) / 2} y={T} width={(W - L - 8) / (y1 - y0 + 1)} height={H - T - B} fill="url(#tl-hatch)" opacity={0.6} />}
              {(i % Math.ceil((y1 - y0 + 1) / 8) === 0) && <text x={xOf(y)} y={H - 8} textAnchor="middle" fontSize={15} fill="#8d9ab8">{y}</text>}
              {missing[y] ? <text x={xOf(y)} y={T - 6} textAnchor="middle" fontSize={13} fill="#ffb547">⚠{missing[y]}</text> : null}
            </g>;
          })}
          <defs><pattern id="tl-hatch" width="6" height="6" patternUnits="userSpaceOnUse" patternTransform="rotate(45)"><line x1="0" y1="0" x2="0" y2="6" stroke="#5d6a88" strokeWidth="1.2" /></pattern></defs>
          {[0.25, 0.5, 0.75].map((f) => { const v = vmin + f * (vmax - vmin); return <g key={f}><line x1={L} x2={W - 8} y1={yOf(v)} y2={yOf(v)} stroke="#ffffff10" /><text x={L - 4} y={yOf(v) + 3} textAnchor="end" fontSize={13} fill="#5d6a88">{fmt(v, metric === "out_rate" ? 1 : 0)}</text></g>; })}
          {series.map(([name, rows], si) => {
            const pts = rows.filter((r: any) => r[metric] != null).sort((a: any, b: any) => a.period - b.period);
            const segs: any[][] = [];
            for (const p of pts) { const last = segs[segs.length - 1]; if (last && p.period === last[last.length - 1].period + 1) last.push(p); else segs.push([p]); }
            const col = COLORS[si % COLORS.length];
            return <g key={name}>
              {segs.map((sg, i) => sg.length > 1 && <polyline key={i} fill="none" stroke={col} strokeWidth={3} points={sg.map((p) => `${xOf(p.period)},${yOf(p[metric])}`).join(" ")} />)}
              {pts.map((p: any) => <circle key={p.period} cx={xOf(p.period)} cy={yOf(p[metric])} r={p.small_sample ? 4.5 : 6.5} fill={p.small_sample ? "#0b1324" : col} stroke={col} strokeWidth={1.5}
                style={{ cursor: "pointer" }} onClick={() => onDrill(`${name} ${p.period}: every ball faced`, { batter_id: pid, ...filters, format: p.format_group, year_from: p.period, year_to: p.period, ...(p.level === "International" ? { team_type: "international" } : { competition: p.level }) })}>
                <title>{`${name} ${p.period}: ${p[metric]} (${p.balls} balls, ${p.innings} inns)`}</title></circle>)}
            </g>;
          })}
        </svg>
        <div className="legend">
          {series.map(([name], i) => <span key={name}><i style={{ borderTopColor: COLORS[i % COLORS.length], borderTopWidth: 3 }} />{name}</span>)}
          <span>hollow dot = under 60 balls · hatched = no covered data that year{Object.keys(missing).length ? " · ⚠n = team ODIs Cricsheet couldn't source" : ""}</span>
        </div>
        <div className="mini" style={{ marginTop: 6 }}>{t.note} Tap a point to see that year&apos;s deliveries.</div>
      </div>
    </div>
  );
}
