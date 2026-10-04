"use client";
// Career Explorer: move through a player's covered career. Selecting a year transforms the panel into that period.
// Years without covered matches are gaps (hatched); nothing is interpolated.
import Link from "next/link";
import { useEffect, useState } from "react";
import { api, fmt, Params } from "@/lib/api";
import ProvBadge from "./Prov";
import Timeline from "./Timeline";

export default function CareerExplorer({ pid, year, setYear, filters, onDrill }: { pid: string; year: number | null; setYear: (y: number | null) => void; filters: Params; onDrill: (t: string, q: Params) => void }) {
  const [d, setD] = useState<any | null>(null);
  useEffect(() => { api(`/players/${pid}/career`, { year: year ?? undefined }).then((r) => setD(r.data)); }, [pid, year]);
  if (!d) return <div className="loading">Loading the career…</div>;
  const byYear: Record<number, any[]> = {};
  for (const y of d.years) (byYear[y.year] ||= []).push(y);
  const maxRuns = Math.max(1, ...d.years.map((y: any) => y.runs || 0));
  const maxW = Math.max(1, ...d.years.map((y: any) => y.wickets || 0));
  const yd = d.year_detail;
  return (
    <div>
      <div className="career-strip" role="tablist" aria-label="Career years">
        <button className={`cy all ${year == null ? "on" : ""}`} onClick={() => setYear(null)}><b>All</b></button>
        {d.span.map((y: number) => {
          const rows = byYear[y] || [];
          const runs = rows.reduce((t, r) => t + (r.runs || 0), 0), wk = rows.reduce((t, r) => t + (r.wickets || 0), 0);
          const gap = d.gaps.includes(y);
          return (
            <button key={y} className={`cy ${gap ? "gap" : ""} ${year === y ? "on" : ""}`} onClick={() => setYear(y)} title={gap ? `${y}: no covered matches` : `${y}: ${runs} runs, ${wk} wickets`} disabled={gap}>
              <span className="cy-bars"><i className="r" style={{ height: `${(100 * runs) / maxRuns}%` }} /><i className="w" style={{ height: `${(100 * wk) / maxW}%` }} /></span>
              <em>{String(y).slice(2)}</em>
            </button>
          );
        })}
      </div>
      <div className="legend"><span><i style={{ borderTopColor: "#35e0c2", borderTopWidth: 6 }} />runs</span><span><i style={{ borderTopColor: "#ffb547", borderTopWidth: 6 }} />wickets</span><span>hatched = no covered matches (gap, not zero)</span></div>

      {!yd ? (
        <div className="cols2" style={{ marginTop: 8 }}>
          <div>
            <div className="eyebrow" style={{ marginTop: 14 }}>Milestones in covered data <ProvBadge prov="DERIVED" /></div>
            <ol className="ms-line">{d.milestones.map((m: any, i: number) => <li key={i}><button className="linklike" onClick={() => setYear(m.year)}><b>{m.date.slice(0, 4)}</b> {m.label}</button></li>)}</ol>
            {d.milestones.length === 0 && <div className="mini">No batting milestones in covered data.</div>}
          </div>
          <div>
            <div className="eyebrow" style={{ marginTop: 14 }}>Peaks and troughs</div>
            {d.peaks_troughs.length ? d.peaks_troughs.map((p: any) => (
              <button key={p.format + p.kind} className="trow linklike" onClick={() => setYear(p.year)}><span className="n">{p.kind === "peak" ? "▲" : "▼"}</span>
                <span className="t"><b>{p.year} · {p.format}</b><span className="mini">strike rate {p.sr} from {fmt(p.balls)} balls</span></span><span className="v num">{p.sr}</span></button>
            )) : <div className="mini">Not enough qualifying years.</div>}
            <div className="mini" style={{ marginTop: 4 }}>{d.peak_rule}</div>
          </div>
        </div>
      ) : (
        <div className="fade-in" key={yd.year}>
          <div className="display-xl" style={{ fontSize: 44, marginTop: 14 }}>{yd.year}</div>
          {yd.in_gap ? <div className="note">No covered matches in {yd.year}.</div> : <>
            <div className="statline">{(byYear[yd.year] || []).map((r: any) => (
              <div key={r.format}><b className="num">{r.runs ? fmt(r.runs) : r.wickets ?? "–"}</b><span>{r.format} {r.runs ? `runs · SR ${r.sr ?? "–"} · avg ${r.avg ?? "–"}` : "wickets"}{r.wickets ? ` · ${r.wickets} ${r.wickets === 1 ? "wkt" : "wkts"}` : ""}</span></div>))}</div>
            <div className="mini" style={{ marginTop: 6 }}>Teams: {d.teams_by_year[yd.year]?.teams.join(", ")} · {d.teams_by_year[yd.year]?.competitions.slice(0, 4).join(", ")}</div>
            <div className="cols2">
              <div>
                <div className="eyebrow" style={{ marginTop: 14 }}>Innings of {yd.year}</div>
                <div className="tablist">{yd.innings.map((r: any) => (
                  <Link key={r.match_id + r.innings_no} className="trow" href={`/innings/${r.match_id}/${r.innings_no}/${pid}`}><span className="n">▮</span>
                    <span className="t"><b>v {r.opponent}</b><span className="mini">{r.format_group} · {r.competition} · {r.start_date}</span></span><span className="v num">{r.runs}{r.not_out ? "*" : ""}<span className="mini"> ({r.balls})</span></span></Link>))}</div>
                {yd.spells.length > 0 && <>
                  <div className="eyebrow" style={{ marginTop: 14 }}>Spells of {yd.year}</div>
                  <div className="tablist">{yd.spells.map((r: any) => (
                    <Link key={r.match_id + r.innings_no} className="trow" href={`/spell/${r.match_id}/${r.innings_no}/${pid}`}><span className="n">◎</span>
                      <span className="t"><b>v {r.opponent}</b><span className="mini">{r.format_group} · {r.start_date}</span></span><span className="v num">{r.wickets}/{r.runs}</span></Link>))}</div></>}
              </div>
              <div>
                <div className="eyebrow" style={{ marginTop: 14 }}>Bowlers faced most in {yd.year}</div>
                <div className="tablist">{yd.bowlers_faced.map((r: any) => (
                  <Link key={r.bowler_id} className="trow" href={`/battle?bat=${pid}&bowl=${r.bowler_id}`}><span className="n">⚔</span>
                    <span className="t"><b>{r.bowler}</b><span className="mini">{r.balls} balls</span></span><span className="v num">{r.runs}<span className="mini">{r.w ? ` · ${r.w} out` : ""}</span></span></Link>))}</div>
                <div className="eyebrow" style={{ marginTop: 14 }}>Opponents</div>
                <div className="tablist">{yd.opponents.map((o: any) => (
                  <div key={o.opponent} className="trow"><span className="n">◆</span><span className="t"><b>{o.opponent}</b><span className="mini">{o.inns} inns</span></span><span className="v num">{o.runs}<span className="mini"> ({o.balls})</span></span></div>))}</div>
                <div className="eyebrow" style={{ marginTop: 14 }}>Scoring by phase in {yd.year}</div>
                <div className="statline">{yd.phases.map((p: any) => <div key={p.phase}><b className="num">{p.sr}</b><span>{p.phase} · {p.balls} balls</span></div>)}</div>
              </div>
            </div>
          </>}
        </div>
      )}
      <div className="rule-section">
        <div className="eyebrow">Year by year chart</div>
        <Timeline pid={pid} filters={filters} onDrill={onDrill} />
      </div>
      <div className="mini">{d.note}</div>
    </div>
  );
}
