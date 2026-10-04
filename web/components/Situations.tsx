"use client";
import { useEffect, useState } from "react";
import { api, fmt, Params } from "@/lib/api";
import ProvBadge from "./Prov";

const METRICS = [
  ["strike_rate", "Strike rate"], ["dismissal_rate", "Outs / 100 balls"], ["dot_pct", "Dot %"], ["boundary_pct", "Boundary %"],
] as const;
const PANELS = [
  ["by_over", "By over", "Over"],
  ["by_innings_stage", "Balls already faced", "Balls faced so far"],
  ["by_wickets_down", "Wickets down when batting", "Wickets lost"],
  ["by_required_rate", "Required run-rate (chasing)", "RRR band"],
  ["by_chase_state", "Setting vs chasing", ""],
  ["by_phase", "Match phase", ""],
] as const;
const MIN_BALLS = 20;
const ORDER: Record<string, string[]> = {
  by_required_rate: ["<6", "6–8", "8–10", "10–12", "12+"],
  by_phase: ["powerplay", "middle", "death", "super_over", "none"],
  by_innings_stage: ["0–9", "10–19", "20–29", "30–49", "50+"],
  by_chase_state: ["Setting / no target", "Chasing"],
};
const sortRows = (key: string, rows: any[]) => {
  const o = ORDER[key];
  return o ? [...rows].sort((a, b) => o.indexOf(String(a.bucket)) - o.indexOf(String(b.bucket))) : rows;
};

export default function Situations({ pid, filters, onDrill }: { pid: string; filters: Params; onDrill: (t: string, q: Params) => void }) {
  const [data, setData] = useState<any | null>(null);
  const [metric, setMetric] = useState<string>("strike_rate");
  useEffect(() => { api(`/players/${pid}/situations`, filters).then((r) => setData(r.data)); }, [pid, JSON.stringify(filters)]);
  return (
    <div>
      <div className="seg" style={{ marginBottom: 12, flexWrap: "wrap" }}>
        {METRICS.map(([k, l]) => <button key={k} className={metric === k ? "on" : ""} onClick={() => setMetric(k)}>{l}</button>)}
      </div>
      <div className="sit-grid">
        {PANELS.map(([key, title, axis]) => {
          const rows = sortRows(key, (data?.[key] || []).filter((r: any) => r.bucket !== null));
          if (!rows.length) return null;
          return (
            <div key={key} className="card">
              <div className="sit-title">{title}</div>
              <div className="mini">{axis ? `${axis} → ` : ""}{METRICS.find((m) => m[0] === metric)![1]} · faded bars = fewer than {MIN_BALLS} balls · red dots = dismissals</div>
              <Bars rows={rows} metric={metric} onPick={key === "by_over" ? (b) => onDrill(`Balls faced in over ${b}`, { batter_id: pid, ...filters, over_from: b, over_to: b }) : undefined} />
            </div>
          );
        })}
      </div>
      <div className="mini" style={{ marginTop: 8 }}><ProvBadge prov="DERIVED" /> Situations (score, wickets down, required rate) are computed from the ball-by-ball sequence. There are no pitch coordinates in this data, so we don't draw pitch maps.</div>
    </div>
  );
}

function Bars({ rows, metric, onPick }: { rows: any[]; metric: string; onPick?: (b: any) => void }) {
  const W = 520, H = 170, PADB = 36, PADT = 16;
  const vals = rows.map((r) => r[metric] ?? 0);
  const max = Math.max(1, ...vals);
  const bw = (W - 10) / rows.length;
  return (
    <svg viewBox={`0 0 ${W} ${H}`} style={{ width: "100%", height: "auto", marginTop: 8 }}>
      {rows.map((r, i) => {
        const v = r[metric]; const h = v == null ? 0 : ((H - PADB - PADT) * v) / max;
        const x = 5 + i * bw; const small = r.balls < MIN_BALLS;
        return (
          <g key={i} opacity={small ? 0.35 : 1} style={{ cursor: onPick ? "pointer" : "default" }} onClick={() => onPick?.(r.bucket)}>
            <title>{`${r.bucket}: ${metric} ${v ?? "–"} · ${r.balls} balls · ${r.runs} runs · ${r.dismissals} outs`}</title>
            <rect x={x + bw * 0.12} y={H - PADB - h} width={bw * 0.76} height={Math.max(h, 1)} rx={3}
                  fill={metric === "dismissal_rate" ? "#ff5c74" : "#35e0c2"} />
            {rows.length <= 12 && v != null && <text x={x + bw / 2} y={H - PADB - h - 4} textAnchor="middle" fontSize={11} fill="#edf2fc" fontWeight={700}>{fmt(v, metric === "dismissal_rate" ? 1 : 0)}</text>}
            {r.dismissals > 0 && <circle cx={x + bw / 2} cy={H - PADB + 7} r={Math.min(3 + r.dismissals * 0.6, 7)} fill="#ff5c74" />}
            {(rows.length <= 25 || Number(r.bucket) % 5 === 0 || i === 0) && <text x={x + bw / 2} y={H - 8} textAnchor="middle" fontSize={11} fill="#8d9ab8">{String(r.bucket)}</text>}
          </g>
        );
      })}
    </svg>
  );
}
