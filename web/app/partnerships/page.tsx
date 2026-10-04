"use client";
// Partnership Intelligence: best pairs (sample-controlled), biggest single stands, and a pair's full history.
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";
import { api, fmt } from "@/lib/api";
import ProvBadge from "@/components/Prov";
import Deliveries from "@/components/Deliveries";

const SORTS = [["runs", "Most runs"], ["average", "Highest average"], ["run_rate", "Fastest"], ["innings", "Most stands"]];
export default function Page() { return <Suspense fallback={<div className="loading">Loading…</div>}><Partnerships /></Suspense>; }

function Partnerships() {
  const sp = useSearchParams();
  const router = useRouter();
  const p1 = sp.get("p1"), p2 = sp.get("p2");
  const f = { gender: sp.get("gender") || "male", format: sp.get("format") || "", sort: sp.get("sort") || "runs", phase: sp.get("phase") || "" };
  const [d, setD] = useState<any | null>(null);
  const [st, setSt] = useState<any | null>(null);
  const [pair, setPair] = useState<any | null>(null);
  const [drill, setDrill] = useState<any | null>(null);
  const set = (kv: Record<string, string>) => { const n = new URLSearchParams(sp.toString()); for (const [k, v] of Object.entries(kv)) v ? n.set(k, v) : n.delete(k); router.replace(`/partnerships?${n}`, { scroll: false }); };
  useEffect(() => { if (p1 && p2) { setPair(null); api("/partnerships/pair", { p1, p2, format: f.format }).then((r) => setPair(r.data)); } else setPair(null); }, [p1, p2, f.format]);
  useEffect(() => { setD(null); api("/partnerships", { ...f, limit: 20 }).then((r) => setD(r.data)); }, [sp.toString()]);
  useEffect(() => { api("/partnerships/stands", { gender: f.gender, format: f.format, limit: 10 }).then((r) => setSt(r.data)); }, [f.gender, f.format]);
  return (
    <div className="fade-in">
      <section className="section" style={{ marginTop: 22 }}>
        <div className="kicker">Partnership intelligence</div>
        <h1 className="big-title" style={{ fontSize: "clamp(34px, 8vw, 58px)", margin: "6px 0 10px" }}>Partnerships</h1>
        <p className="sub">Built from every delivery bowled while the same two batters were in. Covered data only; not official records.</p>
      </section>

      {pair && (
        <section className="section">
          <div className="hero">
            <div className="kicker">Pair history {f.format ? `· ${f.format}` : ""} <ProvBadge prov="DERIVED" /></div>
            <div className="h2" style={{ fontSize: "clamp(24px, 6vw, 36px)", marginTop: 4 }}><Link href={`/players/${pair.p1.id}?tab=partners`}>{pair.p1.name}</Link> & <Link href={`/players/${pair.p2.id}?tab=partners`}>{pair.p2.name}</Link></div>
            <div className="statstrip">
              {[["Stands", pair.innings], ["Runs", fmt(pair.totals.runs)], ["Per over", pair.totals.run_rate], ["Average", pair.totals.average ?? "–"], ["Best", pair.totals.best],
                [`${pair.p1.name.split(" ").slice(-1)[0]} runs`, fmt(pair.totals.p1_runs)], [`${pair.p2.name.split(" ").slice(-1)[0]} runs`, fmt(pair.totals.p2_runs)], ["Boundaries", pair.totals.boundaries]].map(([l, v]) =>
                <div key={l as string}><b className="num">{v as any}</b><span className="mini">{l}</span></div>)}
            </div>
            <Link className="btn" style={{ marginTop: 10, marginRight: 8, display: "inline-block" }} href={`/share?type=partnership&p1=${pair.p1.id}&p2=${pair.p2.id}${f.format ? `&format=${f.format}` : ""}`}>Share card</Link>
            <button className="btn" style={{ marginTop: 10 }} onClick={() => setDrill({ title: `Every ball ${pair.p1.name} faced with ${pair.p2.name} at the other end`, q: { batter_id: pair.p1.id, non_striker_id: pair.p2.id, format: f.format } })}>Deliveries →</button>
          </div>
          <div className="dcard-list" style={{ marginTop: 10 }}>
            {pair.rows.slice(0, 30).map((r: any) => (
              <Link key={r.partnership_id} className="rec-row" href={`/innings/${r.match_id}/${r.innings_no}/${pair.p1.id}`}>
                <span className="rec-rank" style={{ fontSize: 14 }}>{r.wicket_no + 1}{["st", "nd", "rd"][r.wicket_no] ?? "th"}</span>
                <span style={{ minWidth: 0 }}><b style={{ display: "block" }}>{r.batting_team} v {r.bowling_team}</b><span className="mini">{r.start_date} · {r.competition} · {r.ended}</span></span>
                <span className="rec-val num">{r.runs}<span className="mini" style={{ fontSize: 12 }}> ({r.balls})</span></span>
              </Link>
            ))}
          </div>
          {drill && <Deliveries title={drill.title} query={drill.q} onClose={() => setDrill(null)} />}
        </section>
      )}

      <section className="section">
        <div className="filters" style={{ position: "static", flexWrap: "wrap" }}>
          <div className="seg">{[["male", "Men"], ["female", "Women"]].map(([v, l]) => <button key={v} className={f.gender === v ? "on" : ""} onClick={() => set({ gender: v })}>{l}</button>)}</div>
          <div className="seg"><span className="lab">Format</span>{[["", "All"], ["T20", "T20"], ["ODI", "ODI"]].map(([v, l]) => <button key={v} className={f.format === v ? "on" : ""} onClick={() => set({ format: v })}>{l}</button>)}</div>
          <div className="seg"><span className="lab">Phase</span>{[["", "All"], ["powerplay", "PP"], ["middle", "Middle"], ["death", "Death"]].map(([v, l]) => <button key={v} className={f.phase === v ? "on" : ""} onClick={() => set({ phase: v })}>{l}</button>)}</div>
          <div className="seg">{SORTS.map(([v, l]) => <button key={v} className={f.sort === v ? "on" : ""} onClick={() => set({ sort: v })}>{l}</button>)}</div>
        </div>
        {!d ? <div className="loading">Ranking pairs…</div> : (
          <>
            <div className="rec-def" style={{ marginTop: 8 }}><dl className="kv"><dt>Definition</dt><dd style={{ fontWeight: 500 }}>{d.definition}</dd><dt>Threshold</dt><dd>{d.thresholds}</dd></dl></div>
            <div className="rec-list">
              {d.rows.map((r: any) => (
                <Link key={r.p1 + r.p2} className="rec-row" href={`/partnerships?p1=${r.p1}&p2=${r.p2}${f.format ? `&format=${f.format}` : ""}&gender=${f.gender}`}>
                  <span className="rec-rank">{r.rank}</span>
                  <span style={{ minWidth: 0 }}><b style={{ display: "block", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{r.p1_name} & {r.p2_name}</b>
                    <span className="mini">{r.innings} stands · {fmt(r.runs)} runs · {r.run_rate}/over · avg {r.average ?? "–"} · split {r.p1_share}/{r.p1_share != null ? Math.round(1000 - 10 * r.p1_share) / 10 : "–"}</span></span>
                  <span className="rec-val num">{f.sort === "run_rate" ? r.run_rate : f.sort === "average" ? r.average : f.sort === "innings" ? r.innings : fmt(r.runs)}</span>
                </Link>
              ))}
            </div>
          </>
        )}
      </section>
      {st && <section className="section">
        <div className="section-head"><div><div className="kicker">Biggest stands</div><div className="h2">Highest single partnerships</div></div></div>
        <div className="rec-list">
          {st.rows.map((r: any, i: number) => (
            <Link key={r.partnership_id} className="rec-row" href={`/innings/${r.match_id}/${r.innings_no}/${r.p1}`}>
              <span className="rec-rank">{i + 1}</span>
              <span style={{ minWidth: 0 }}><b style={{ display: "block" }}>{r.p1_name} & {r.p2_name}</b><span className="mini">{r.wicket_label} · {r.batting_team} v {r.bowling_team} · {r.start_date}</span></span>
              <span className="rec-val num">{r.runs}<span className="mini" style={{ fontSize: 12 }}> ({r.balls})</span></span>
            </Link>
          ))}
        </div>
      </section>}
    </div>
  );
}
