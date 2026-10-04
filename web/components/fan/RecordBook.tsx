"use client";
// Records V2: the record book as something to browse. Human titles, organised by what fans look for; each record opens
// with its definition, minimum sample, filters, coverage and the evidence behind every row.
import Link from "next/link";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";

export default function RecordBook() {
  const [d, setD] = useState<any | null>(null);
  const [cat, setCat] = useState<string>("All");
  useEffect(() => { api("/fan/records").then((r) => setD(r.data)).catch(() => setD({ categories: [] })); }, []);
  const cats = (d?.categories || []) as any[];
  const shown = cat === "All" ? cats : cats.filter((c) => c.category === cat);
  return (
    <div className="fade-in" data-testid="record-book">
      <section className="section" style={{ marginTop: 22 }}>
        <div className="kicker">Record book</div>
        <h1 className="big-title" style={{ fontSize: "clamp(34px, 8vw, 58px)", margin: "6px 0 8px" }}>Records worth a look</h1>
        <div className="sub">From covered matches only, so these are not official records. Every record shows its definition, minimum sample and evidence.</div>
        <div className="mtabs" style={{ marginTop: 12 }}>
          {["All", ...cats.map((c) => c.category)].map((c) => <button key={c} className={`mtab ${cat === c ? "on" : ""}`} onClick={() => setCat(c)}>{c}</button>)}
        </div>
      </section>
      {!d ? <div className="loading">Opening the record book…</div> : shown.map((c) => (
        <section key={c.category} className="rec-cat">
          <div className="eyebrow">{c.category}</div>
          {c.records.map((r: any) => (
            <div key={r.def_id} className="rec-card">
              <Link href={`/records/${r.scopes[0].id}`} className="rt">{r.title} →</Link>
              <div className="rl">{r.scopes[0].leader} · <b>{r.scopes[0].value_fmt}</b> <span className="mini">({r.scopes[0].scope})</span></div>
              <div className="scope-row">{r.scopes.map((s: any) => <Link key={s.id} href={`/records/${s.id}`} className="chip">{s.scope}</Link>)}</div>
            </div>
          ))}
        </section>
      ))}
      <section className="section">
        <div className="play-cta"><div><div className="kicker">Build your own</div><div className="sub">Any statistic, any filter: phase, innings, wickets down, competition, team, years.</div></div>
          <Link href="/records?metric=runs&gender=male" className="btn primary">Leaderboard builder →</Link></div>
        <div className="mini" style={{ marginTop: 10 }}>{d?.coverage}</div>
      </section>
    </div>
  );
}
