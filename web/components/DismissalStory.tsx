"use client";
// Dismissal Story: tap a route → frequency, formats, phases, overs, who did it, chronology, every dismissal.
import { useEffect, useState } from "react";
import Link from "next/link";
import { api, fmt, Params } from "@/lib/api";
import ProvBadge from "./Prov";

function MiniBars({ rows, kKey = "k", nKey = "n", max, unit = "", onPick }: { rows: any[]; kKey?: string; nKey?: string; max?: number; unit?: string; onPick?: (k: any) => void }) {
  const m = max ?? Math.max(1, ...rows.map((r) => r[nKey]));
  return (
    <div className="mbars">
      {rows.map((r) => (
        <button key={String(r[kKey])} className="mbar" onClick={() => onPick?.(r[kKey])} disabled={!onPick}>
          <span className="mbar-k">{String(r[kKey])}</span>
          <span className="mbar-t"><span style={{ width: `${(100 * r[nKey]) / m}%` }} /></span>
          <span className="mbar-n num">{r[nKey]}{unit}</span>
        </button>
      ))}
    </div>
  );
}

export default function DismissalStory({ pid, route, filters, onDrill }: { pid: string; route: string; filters: Params; onDrill: (t: string, q: Params) => void }) {
  const [s, setS] = useState<any | null>(null);
  useEffect(() => { setS(null); api(`/players/${pid}/dismissal-story`, { route, ...filters }).then((r) => setS(r.data)); }, [pid, route, JSON.stringify(filters)]);
  if (!s) return <div className="loading">Loading the story…</div>;
  if (!s.n) return <div className="empty">No {s.label.toLowerCase()} dismissals in this selection.</div>;
  const overs = s.by_over as any[];
  const omax = Math.max(1, ...overs.map((o) => o.n));
  const years = s.by_year as any[];
  const ymax = Math.max(1, ...years.map((y) => y.all_dismissals));
  return (
    <div className="story fade-in">
      <div className="story-head">
        <div>
          <div className="kicker" style={{ color: "#ff8a9b" }}>Dismissal story <ProvBadge prov={s.prov} /></div>
          <div className="h2" style={{ fontSize: 26 }}>{s.label}: {s.n} times</div>
          <div className="sub">{s.share}% of {s.of_total} dismissals (90% interval {s.share_interval_90?.[0]}–{s.share_interval_90?.[1]}%) · once every {fmt(s.balls_per)} balls faced</div>
          {s.terminology && <div className="note">{s.terminology}</div>}
        </div>
        <button className="btn primary" onClick={() => onDrill(`${s.label}: every dismissal`, s.evidence_query)}>Every dismissal →</button>
      </div>
      <div className="story-grid">
        <div className="card"><div className="sit-title">By format</div><MiniBars rows={s.by_format} onPick={(k) => onDrill(`${s.label} in ${k}`, { ...s.evidence_query, format: k })} /></div>
        <div className="card"><div className="sit-title">By phase</div><MiniBars rows={s.by_phase} onPick={(k) => onDrill(`${s.label} in ${k} overs`, { ...s.evidence_query, phase: k })} /></div>
        <div className="card"><div className="sit-title">Their score when it happened</div><MiniBars rows={s.by_batter_score} /></div>
        <div className="card" style={{ gridColumn: "1 / -1" }}>
          <div className="sit-title">By over</div>
          <svg viewBox="0 0 520 110" style={{ width: "100%" }}>
            {overs.map((o, i) => {
              const bw = 510 / Math.max(20, overs[overs.length - 1].k);
              const x = 5 + (o.k - 1) * bw, h = (80 * o.n) / omax;
              return <g key={o.k} onClick={() => onDrill(`${s.label} in over ${o.k}`, { ...s.evidence_query, over_from: o.k, over_to: o.k })} style={{ cursor: "pointer" }}>
                <title>{`over ${o.k}: ${o.n}`}</title>
                <rect x={x + 1} y={88 - h} width={Math.max(2, bw - 2)} height={h} rx={2} fill="#ff5c74" />
                {(o.k % 5 === 0 || o.k === 1) && <text x={x + bw / 2} y={104} textAnchor="middle" fontSize={9} fill="#8d9ab8">{o.k}</text>}
              </g>;
            })}
          </svg>
        </div>
        <div className="card" style={{ gridColumn: "1 / -1" }}>
          <div className="sit-title">Chronology: this way vs all dismissals each year</div>
          <div className="chrono">
            {years.map((y) => (
              <div key={y.year} className="chrono-col" title={`${y.year}: ${y.n} of ${y.all_dismissals}`}>
                <div className="chrono-bar"><span className="all" style={{ height: `${(100 * y.all_dismissals) / ymax}%` }} /><span className="this" style={{ height: `${(100 * y.n) / ymax}%` }} /></div>
                <div className="mini">{String(y.year).slice(2)}</div>
              </div>
            ))}
          </div>
          <div className="mini">Red = {s.label.toLowerCase()} · grey = all dismissals that year. Years with no dismissals aren&apos;t shown.</div>
        </div>
        <div className="card"><div className="sit-title">Bowlers responsible</div>
          {s.by_bowler.map((b: any) => <Link key={b.bowler_id} className="res" href={`/battle?bat=${pid}&bowl=${b.bowler_id}`}><span>{b.bowler}</span><span className="wk">{b.n}</span></Link>)}
        </div>
        {s.by_fielder.length > 0 && <div className="card"><div className="sit-title">Fielders involved</div>
          {s.by_fielder.map((b: any) => <div key={b.fielder_id || b.fielder} className="res"><span>{b.fielder}</span><span className="wk">{b.n}</span></div>)}
          <div className="mini" style={{ marginTop: 6 }}>Fielding positions are not recorded.</div>
        </div>}
      </div>
    </div>
  );
}
