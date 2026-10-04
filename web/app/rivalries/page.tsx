"use client";
import Link from "next/link";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";

export default function Rivalries() {
  const [g, setG] = useState("male");
  const [d, setD] = useState<any[] | null>(null);
  useEffect(() => { setD(null); api<any[]>("/rivalries", { gender: g, limit: 30 }).then((r) => setD(r.data)); }, [g]);
  return (
    <div className="fade-in">
      <section style={{ marginTop: 22 }}><div className="eyebrow">Rivalries</div><h1 className="display-xl">Team v team</h1>
        <p className="lead">The most-played fixtures in covered data, across T20 and ODI. Renamed franchises are grouped.</p></section>
      <div className="seg" style={{ marginTop: 10 }}>{[["male", "Men"], ["female", "Women"]].map(([v, l]) => <button key={v} className={g === v ? "on" : ""} onClick={() => setG(v)}>{l}</button>)}</div>
      {!d ? <div className="loading">Loading…</div> : (
        <div className="tablist" style={{ marginTop: 8 }}>{d.map((r, i) => (
          <Link key={r.ta + r.tb} className="trow" href={`/rivalry?a=${encodeURIComponent(r.ta)}&b=${encodeURIComponent(r.tb)}&gender=${g}`}><span className="n">{i + 1}</span>
            <span className="t"><b>{r.ta} v {r.tb}</b><span className="mini">{r.n} matches · latest {r.last}</span></span>
            <span className="v num">{r.a_won}–{r.b_won}</span></Link>))}</div>
      )}
    </div>
  );
}
