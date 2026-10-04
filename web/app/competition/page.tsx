"use client";
// Competition / series intelligence. Respects coverage: says exactly how complete the covered data is.
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";
import { api, fmt } from "@/lib/api";
import ProvBadge from "@/components/Prov";
import Leader from "@/components/Leader";
import Spark from "@/components/viz/Spark";
import ExploreNext from "@/components/ExploreNext";

export default function Page() { return <Suspense fallback={<div className="loading">Loading…</div>}><Comp /></Suspense>; }

function Comp() {
  const sp = useSearchParams();
  const router = useRouter();
  const name = sp.get("name") || "", gender = sp.get("gender") || "male", season = sp.get("season") || "";
  const [d, setD] = useState<any | null>(null);
  const [err, setErr] = useState(false);
  useEffect(() => { setD(null); setErr(false); api("/competition", { name, gender, season }).then((r) => setD(r.data)).catch(() => setErr(true)); }, [name, gender, season]);
  const setSeason = (s: string) => router.replace(`/competition?name=${encodeURIComponent(name)}&gender=${gender}${s ? `&season=${encodeURIComponent(s)}` : ""}`, { scroll: false });
  if (err) return <div className="empty" style={{ marginTop: 30 }}>No covered matches for this competition.</div>;
  if (!d) return <div className="loading">Loading the competition…</div>;
  const L = d.leaders;
  const pl = (r: any) => `/players/${r.pid}`;
  return (
    <div className="fade-in">
      <section style={{ marginTop: 22 }}>
        <div className="eyebrow">{gender === "female" ? "Women" : "Men"} · {d.format} · {d.first.slice(0, 4)}–{d.last.slice(0, 4)}</div>
        <h1 className="display-xl">{d.name}</h1>
        <div className="statline"><div><b>{fmt(d.matches_total)}</b><span>covered matches</span></div><div><b>{d.editions.length}</b><span>editions</span></div>
          {season && <div><b>{season}</b><span>selected edition</span></div>}</div>
        <div className="cov-line"><span className={`covstat ${d.coverage.status}`}>{d.coverage.status === "COMPLETE" ? "complete" : d.coverage.status === "PARTIAL" ? "gaps known" : "completeness unknown"}</span><span>{d.coverage.text}</span></div>
      </section>

      <section className="rule-section">
        <div className="eyebrow">Editions</div>
        <div className="edition-strip">
          <button className={!season ? "on" : ""} onClick={() => setSeason("")}><b>All</b><span>{d.matches_total} m</span></button>
          {d.editions.map((e: any) => (
            <button key={e.season} className={season === e.season ? "on" : ""} onClick={() => setSeason(e.season)}>
              <b>{e.season}</b><span>{e.matches} m{e.final_winner ? ` · ${e.final_winner}` : ""}</span></button>
          ))}
        </div>
        <div className="mini">{d.definitions.final_winner}</div>
      </section>

      <section className="rule-section cols2">
        <Leader title={`Most runs${season ? ` · ${season}` : ""}`} rows={L.runs} value={(r) => fmt(r.runs)} sub={(r) => `${r.inns} inns · SR ${(100 * r.runs / r.balls).toFixed(1)} · HS ${r.hs}`} href={pl} />
        <Leader title="Most wickets" rows={L.wickets} value={(r) => r.wickets} sub={(r) => `econ ${(6 * r.runs / r.balls).toFixed(2)} · ${Math.floor(r.balls / 6)} overs`} href={(r) => `/players/${r.pid}?tab=bowling`} />
        <Leader title="Highest strike rate" rows={L.strike_rate} value={(r) => r.sr} sub={(r) => `${r.runs} off ${r.balls}`} href={pl} note={d.definitions.strike_rate} />
        <Leader title="Best economy" rows={L.economy} value={(r) => r.econ} sub={(r) => `${Math.floor(r.balls / 6)} overs`} href={(r) => `/players/${r.pid}?tab=bowling`} note={d.definitions.economy} />
      </section>

      <section className="rule-section cols2">
        <Leader title="Highest scores" rows={d.highest_scores} value={(r) => `${r.runs}${r.not_out ? "*" : ""}`} sub={(r) => `${r.balls} balls v ${r.opponent} · ${r.start_date}`} href={(r) => `/innings/${r.match_id}/${r.innings_no}/${r.pid}`} />
        <Leader title="Best figures" rows={d.best_figures} value={(r) => `${r.wickets}/${r.runs}`} sub={(r) => `v ${r.opponent} · ${r.start_date}`} href={(r) => `/spell/${r.match_id}/${r.innings_no}/${r.pid}`} />
        <Leader title="Biggest partnerships" rows={d.partnerships.map((p: any) => ({ ...p, label: `${p.p1_name} & ${p.p2_name}` }))} value={(r) => r.runs} sub={(r) => `${r.balls} balls · ${r.start_date}`} href={(r) => `/innings/${r.match_id}/${r.innings_no}/${r.p1}`} />
        <Leader title="Longest battles" rows={d.battles.map((b: any) => ({ ...b, label: `${b.batter} v ${b.bowler}` }))} value={(r) => `${r.runs}/${r.balls}`} sub={(r) => `${r.outs} out`} href={(r) => `/battle?bat=${r.batter_id}&bowl=${r.bowler_id}`} />
      </section>

      <section className="rule-section">
        <div className="eyebrow">Teams{season ? ` · ${season}` : ""} <ProvBadge prov="OBSERVED" /></div>
        <div className="tablist">{d.teams.map((t: any, i: number) => (
          <Link key={t.team} className="trow" href={`/rivalry?a=${encodeURIComponent(t.team)}&gender=${gender}`}><span className="n">{i + 1}</span>
            <span className="t"><b>{t.team}</b><span className="mini">{t.played} played</span></span><span className="v num">{t.won}–{t.lost}</span></Link>))}</div>
      </section>

      <section className="rule-section">
        <div className="eyebrow">Trends across editions <ProvBadge prov="DERIVED" /></div>
        <div className="cols3">
          <div><div className="sit-title">Run rate</div><Spark values={d.trend.map((t: any) => t.run_rate)} labels={d.trend.map((t: any) => t.season)} /></div>
          <div><div className="sit-title">Boundary %</div><Spark values={d.trend.map((t: any) => t.boundary_pct)} labels={d.trend.map((t: any) => t.season)} color="#9df26b" /></div>
          <div><div className="sit-title">Dot-ball %</div><Spark values={d.trend.map((t: any) => t.dot_pct)} labels={d.trend.map((t: any) => t.season)} color="#7cc4ff" /></div>
        </div>
        <div className="mini">One point per covered edition; editions with few covered matches are less reliable.</div>
      </section>

      <section className="rule-section">
        <div className="eyebrow">Matches{season ? ` · ${season}` : " · most recent"}</div>
        <div className="tablist">{d.matches.slice(0, 20).map((m: any) => (
          <Link key={m.match_id} className="trow" href={`/match/${m.match_id}`}><span className="n">▣</span>
            <span className="t"><b>{m.team1} v {m.team2}</b><span className="mini">{m.start_date}{m.event_stage ? ` · ${m.event_stage}` : ""} · {m.winner ? `${m.winner} won` : "no result"}</span></span>
            <span className="v num" style={{ fontSize: 14 }}>{m.i1_runs}/{m.i1_wkts} · {m.i2_runs ?? "–"}/{m.i2_wkts ?? "–"}</span></Link>))}</div>
      </section>
      <ExploreNext type="competition" id={`${name}|${gender}`} />
    </div>
  );
}
