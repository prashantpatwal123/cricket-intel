"use client";
import Link from "next/link";
import { useEffect, useState } from "react";
import { api, fmt } from "@/lib/api";

export default function Competitions() {
  const [d, setD] = useState<any[] | null>(null);
  const [g, setG] = useState("male");
  useEffect(() => { api<any[]>("/competitions").then((r) => setD(r.data)); }, []);
  const rows = (d || []).filter((c) => c.gender === g);
  return (
    <div className="fade-in">
      <section style={{ marginTop: 22 }}><div className="eyebrow">Competitions</div><h1 className="display-xl">Tournaments & series</h1>
        <p className="lead">Every competition with at least six covered matches. Each page says how complete our coverage is.</p></section>
      <div className="seg" style={{ marginTop: 10 }}>{[["male", "Men"], ["female", "Women"]].map(([v, l]) => <button key={v} className={g === v ? "on" : ""} onClick={() => setG(v)}>{l}</button>)}</div>
      {!d ? <div className="loading">Loading…</div> : (
        <div className="tablist" style={{ marginTop: 8 }}>{rows.map((c, i) => (
          <Link key={c.competition} className="trow" href={`/competition?name=${encodeURIComponent(c.competition)}&gender=${c.gender}`}><span className="n">{i + 1}</span>
            <span className="t"><b>{c.competition}</b><span className="mini">{c.format} · {c.team_type === "club" ? "league" : "international"} · {c.editions} editions · {c.first.slice(0, 4)}–{c.last.slice(0, 4)}</span></span>
            <span className="v num">{fmt(c.matches)}</span></Link>))}</div>
      )}
    </div>
  );
}
