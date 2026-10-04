"use client";
// Partnership Intelligence for one player: who they bat with, and whether their own scoring changes with the partner.
import Link from "next/link";
import { useEffect, useState } from "react";
import { api, fmt, Params } from "@/lib/api";
import ProvBadge from "./Prov";

export default function Partners({ pid, format, teamType, onDrill }: { pid: string; format?: string; teamType?: string; onDrill: (t: string, q: Params) => void }) {
  const [d, setD] = useState<any | null>(null);
  useEffect(() => { setD(null); api(`/players/${pid}/partners`, { format, team_type: teamType }).then((r) => setD(r.data)); }, [pid, format, teamType]);
  if (!d) return <div className="loading">Finding partnerships…</div>;
  if (!d.available) return <div className="empty">{d.reason}.</div>;
  const card = (p: any, tone: string) => (
    <div key={p.partner} className={`icard ${tone}`}>
      <div className="ihead">{p.partner_name}: {p.my_sr} with them v {p.phase_adjusted_expected_sr} expected</div>
      <div className="mini" style={{ marginTop: 4 }}>{fmt(p.my_balls)} balls faced together · v everyone else {p.sr_with_others} (difference 90% interval {p.diff_vs_others.lo} to {p.diff_vs_others.hi})</div>
      <button className="btn" style={{ marginTop: 8 }} onClick={() => onDrill(`Balls faced with ${p.partner_name} at the other end`, p.evidence)}>Deliveries →</button>
    </div>
  );
  return (
    <div>
      <div className="mini">{d.format} · overall strike rate {d.overall_sr} <ProvBadge prov="DERIVED" /></div>
      <div className="grid2" style={{ marginTop: 10 }}>
        <div><div className="sit-title">Scores faster with</div>
          {d.brings_out_best.length ? <div className="icards" style={{ gridTemplateColumns: "1fr" }}>{d.brings_out_best.map((p: any) => card(p, "strength"))}</div>
            : <div className="empty">No partner clears the evidence bar.</div>}</div>
        <div><div className="sit-title">Scores slower with</div>
          {d.quieter_with.length ? <div className="icards" style={{ gridTemplateColumns: "1fr" }}>{d.quieter_with.map((p: any) => card(p, "weakness"))}</div>
            : <div className="empty">No partner clears the evidence bar.</div>}</div>
      </div>
      <div className="card" style={{ marginTop: 12 }}>
        <div className="sit-title">Most runs together</div>
        <div className="mcards" style={{ marginTop: 8 }}>
          {d.partners.slice(0, 12).map((p: any) => (
            <div key={p.partner} className="mcard">
              <div className="mcard-top"><Link href={`/partnerships?p1=${pid}&p2=${p.partner}&format=${d.format}`} className="mcard-name">{p.partner_name} →</Link><span className="mini">{p.innings} stands</span></div>
              <div className="mcard-stats">
                <span><b className="num">{fmt(p.runs)}</b>runs</span><span><b className="num">{p.run_rate}</b>per over</span>
                <span><b className="num">{p.best}</b>best</span><span><b className="num">{p.my_share}%</b>their share</span>
              </div>
              <div className="srbar"><i style={{ left: 0, width: `${p.my_share}%` }} /></div>
            </div>
          ))}
        </div>
      </div>
      <div className="mini" style={{ marginTop: 8 }}>{d.method}</div>
    </div>
  );
}
