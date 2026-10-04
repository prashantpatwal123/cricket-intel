"use client";
// Rivalry (team v team) and team overview. Gender, format and competition filters are explicit.
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";
import { api, fmt } from "@/lib/api";
import ProvBadge from "@/components/Prov";
import Leader from "@/components/Leader";
import ExploreNext from "@/components/ExploreNext";

export default function Page() { return <Suspense fallback={<div className="loading">Loading…</div>}><Rivalry /></Suspense>; }

function Rivalry() {
  const sp = useSearchParams();
  const router = useRouter();
  const a = sp.get("a") || "", b = sp.get("b") || "", gender = sp.get("gender") || "male", format = sp.get("format") || "", competition = sp.get("competition") || "";
  const [d, setD] = useState<any | null>(null);
  const [err, setErr] = useState(false);
  useEffect(() => { setD(null); setErr(false); api("/rivalry", { a, b, gender, format, competition }).then((r) => setD(r.data)).catch(() => setErr(true)); }, [sp.toString()]);
  const set = (kv: Record<string, string>) => { const n = new URLSearchParams(sp.toString()); for (const [k, v] of Object.entries(kv)) v ? n.set(k, v) : n.delete(k); router.replace(`/rivalry?${n}`, { scroll: false }); };
  if (err) return <div className="empty" style={{ marginTop: 30 }}>No covered matches for that selection.</div>;
  if (!d) return <div className="loading">Loading…</div>;
  const segs = (
    <div className="filters" style={{ position: "static", flexWrap: "wrap" }}>
      <div className="seg">{[["male", "Men"], ["female", "Women"]].map(([v, l]) => <button key={v} className={gender === v ? "on" : ""} onClick={() => set({ gender: v })}>{l}</button>)}</div>
      <div className="seg"><span className="lab">Format</span>{[["", "All"], ["T20", "T20"], ["ODI", "ODI"]].map(([v, l]) => <button key={v} className={format === v ? "on" : ""} onClick={() => set({ format: v })}>{l}</button>)}</div>
      {competition && <div className="seg"><span className="lab">Competition</span><button className="on" onClick={() => set({ competition: "" })}>{competition} ×</button></div>}
    </div>
  );
  if (!b) {
    return (
      <div className="fade-in">
        <section style={{ marginTop: 22 }}><div className="eyebrow">Team · {gender === "female" ? "Women" : "Men"}{format ? ` · ${format}` : ""}</div><h1 className="display-xl">{d.team}</h1>
          <div className="statline"><div><b>{d.played}</b><span>covered matches</span></div><div><b>{d.won}</b><span>won</span></div><div><b>{d.lost}</b><span>lost</span></div></div></section>
        {segs}
        <section className="rule-section"><div className="eyebrow">Opponents · tap for the rivalry</div>
          <div className="tablist">{d.opponents.map((o: any, i: number) => (
            <Link key={o.opponent} className="trow" href={`/rivalry?a=${encodeURIComponent(d.team)}&b=${encodeURIComponent(o.opponent)}&gender=${gender}${format ? `&format=${format}` : ""}`}>
              <span className="n">{i + 1}</span><span className="t"><b>v {o.opponent}</b><span className="mini">{o.played} matches</span></span><span className="v num">{o.won}–{o.lost}</span></Link>))}</div></section>
      </div>
    );
  }
  const pl = (r: any) => `/players/${r.pid}`;
  return (
    <div className="fade-in">
      <section style={{ marginTop: 22 }}>
        <div className="eyebrow">Rivalry · {gender === "female" ? "Women" : "Men"} · {d.formats.join(" + ")} · {d.competitions.slice(0, 3).join(", ")}{d.competitions.length > 3 ? "…" : ""}</div>
        <h1 className="display-xl">{d.a} <span style={{ color: "var(--muted)" }}>v</span> {d.b}</h1>
        <div className="h2h">
          <div><b className="num">{d.wins[d.a]}</b><span>{d.a}</span></div>
          <div style={{ textAlign: "right" }}><b className="num">{d.wins[d.b]}</b><span>{d.b}</span></div>
        </div>
        <div className="h2h-bar"><i style={{ width: `${(100 * d.wins[d.a]) / Math.max(1, d.played)}%` }} /><em style={{ width: `${(100 * d.no_result) / Math.max(1, d.played)}%` }} /></div>
        <div className="mini">{d.played} covered matches · {d.no_result} no result/tie <ProvBadge prov="OBSERVED" />{d.renamed_note ? ` · ${d.renamed_note}` : ""}</div>
      </section>
      {segs}
      <section className="rule-section">
        <div className="eyebrow">Run environment <ProvBadge prov="DERIVED" /></div>
        <div className="statline">{d.run_environment.map((r: any) => <div key={r.format_group}><b className="num">{r.avg_first_innings}</b><span>{r.format_group} avg 1st-inns · RR {r.run_rate}</span></div>)}</div>
        <div className="eyebrow" style={{ marginTop: 14 }}>Results by year</div>
        <div className="yr-bars">{yearSpan(d.trend).map((t: any) => t.gap
          ? <div key={t.year} className="gap" title={`${t.year}: no covered matches`}><em>{String(t.year).slice(2)}</em><span className="yg" /></div>
          : <div key={t.year} title={`${t.year}: ${d.a} ${t.a_won}, ${d.b} ${t.b_won}, played ${t.played}`}><em>{String(t.year).slice(2)}</em>
              <span className="ya" style={{ height: `${(56 * t.a_won) / maxPlayed(d.trend)}px` }} /><span className="yb" style={{ height: `${(56 * t.b_won) / maxPlayed(d.trend)}px` }} /></div>)}</div>
        <div className="legend"><span><i style={{ borderTopColor: "#35e0c2", borderTopWidth: 6 }} />{d.a} wins</span><span><i style={{ borderTopColor: "#ffb547", borderTopWidth: 6 }} />{d.b} wins</span><span>dashed stub = no covered meeting that year (gap, not zero)</span></div>
      </section>
      <section className="rule-section cols2">
        <Leader title="Leading batters" rows={d.batters} value={(r) => fmt(r.runs)} sub={(r) => `${r.team} · ${r.inns} inns · SR ${(100 * r.runs / r.balls).toFixed(1)}`} href={pl} />
        <Leader title="Leading bowlers" rows={d.bowlers} value={(r) => r.wickets} sub={(r) => `${r.team} · econ ${(6 * r.runs / r.balls).toFixed(2)}`} href={(r) => `/players/${r.pid}?tab=bowling`} />
        <Leader title="Recurring battles (3+ matches)" rows={d.battles.map((x: any) => ({ ...x, label: `${x.batter} v ${x.bowler}` }))} value={(r) => `${r.runs}/${r.balls}`} sub={(r) => `${r.matches} matches · ${r.outs} out`} href={(r) => `/battle?bat=${r.batter_id}&bowl=${r.bowler_id}`} />
        <Leader title="Biggest partnerships" rows={d.partnerships.map((p: any) => ({ ...p, label: `${p.p1_name} & ${p.p2_name}` }))} value={(r) => r.runs} sub={(r) => `${r.batting_team} · ${r.start_date}`} href={(r) => `/innings/${r.match_id}/${r.innings_no}/${r.p1}`} />
        <Leader title="Notable innings" rows={d.innings} value={(r) => `${r.runs}${r.not_out ? "*" : ""}`} sub={(r) => `${r.team} · ${r.balls} balls · ${r.start_date}`} href={(r) => `/innings/${r.match_id}/${r.innings_no}/${r.pid}`} />
        <Leader title="Notable spells" rows={d.spells} value={(r) => `${r.wickets}/${r.runs}`} sub={(r) => `${r.team} · ${r.start_date}`} href={(r) => `/spell/${r.match_id}/${r.innings_no}/${r.pid}`} />
      </section>
      <section className="rule-section cols2">
        <div><div className="eyebrow">Biggest totals</div><div className="tablist">{d.biggest_totals.map((t: any, i: number) => (
          <Link key={i} className="trow" href={`/match/${t.match_id}`}><span className="n">{i + 1}</span><span className="t"><b>{t.team}</b><span className="mini">{t.date}</span></span><span className="v num">{t.runs}/{t.wkts}</span></Link>))}</div></div>
        <div><div className="eyebrow">Closest finishes</div><div className="mini">Won by ≤ 10 runs, ≤ 2 wickets, or tied.</div><div className="tablist">{d.closest.map((m: any) => (
          <Link key={m.match_id} className="trow" href={`/match/${m.match_id}`}><span className="n">▣</span><span className="t"><b>{m.winner ? `${m.winner} won` : "Tied / no result"}</b><span className="mini">{m.start_date} · {m.competition || "bilateral"}</span></span>
            <span className="v num" style={{ fontSize: 14 }}>{m.win_by_runs != null ? `${m.win_by_runs} runs` : m.win_by_wickets != null ? `${m.win_by_wickets} wkts` : "tie"}</span></Link>))}</div></div>
      </section>
      <section className="rule-section"><div className="eyebrow">Matches</div><div className="tablist">{d.matches.slice(0, 15).map((m: any) => (
        <Link key={m.match_id} className="trow" href={`/match/${m.match_id}`}><span className="n">▣</span><span className="t"><b>{m.competition || "Bilateral"}</b><span className="mini">{m.start_date} · {m.format_group} · {m.winner_c ? `${m.winner_c} won` : "no result"}</span></span>
          <span className="v num" style={{ fontSize: 14 }}>{m.i1_runs}/{m.i1_wkts} · {m.i2_runs ?? "–"}/{m.i2_wkts ?? "–"}</span></Link>))}</div></section>
      <ExploreNext type="rivalry" id={`${d.a}|${d.b}|${gender}`} />
    </div>
  );
}

// Every year in range, with years that have no covered meeting kept as visible gaps (never dropped, never interpolated).
function yearSpan(trend: any[]) {
  if (!trend.length) return [];
  const by = new Map(trend.map((t) => [t.year, t]));
  const out: any[] = [];
  for (let y = trend[0].year; y <= trend[trend.length - 1].year; y++) out.push(by.get(y) ?? { year: y, gap: true });
  return out;
}
function maxPlayed(trend: any[]) { return Math.max(1, ...trend.map((t) => t.played)); }
