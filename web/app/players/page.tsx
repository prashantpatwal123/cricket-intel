"use client";
import Link from "next/link";
import { useEffect, useState } from "react";
import { api, fmt } from "@/lib/api";

export default function Players() {
  const [q, setQ] = useState("");
  const [res, setRes] = useState<any[]>([]);
  const [feat, setFeat] = useState<any[] | null>(null);
  useEffect(() => { api<any[]>("/players/featured").then((r) => setFeat(r.data)).catch(() => setFeat([])); }, []);
  useEffect(() => {
    if (q.trim().length < 2) { setRes([]); return; }
    const t = setTimeout(() => api<any[]>("/players/search", { q }).then((r) => setRes(r.data)), 150);
    return () => clearTimeout(t);
  }, [q]);
  const groups = (feat || []).reduce((acc: Record<string, any[]>, p) => {
    const g = (p.genders || ["?"])[0] === "female" ? "Women" : "Men"; (acc[g] ||= []).push(p); return acc;
  }, {});
  return (
    <div className="search-hero fade-in">
      <div className="kicker">Players</div>
      <h1 className="big-title">How do they score?<br />How do they get out?</h1>
      <p className="sub" style={{ maxWidth: 560 }}>Open any player and go from headline numbers to the patterns behind them, down to the individual deliveries. Every number shows where it came from.</p>
      <div style={{ marginTop: 18, maxWidth: 560 }}>
        <input className="input" placeholder="Search a player…" value={q} onChange={(e) => setQ(e.target.value)} aria-label="Search players" />
        {res.length > 0 && (
          <div className="results">
            {res.map((p) => (
              <Link key={p.person_id} href={`/players/${p.person_id}`} className="res">
                <span>{p.name}</span><span className="mini">{p.role ?? "role unknown"} · {p.matches} matches</span>
              </Link>
            ))}
          </div>
        )}
      </div>
      {Object.entries(groups).map(([g, ps]) => (
        <div className="section" key={g}>
          <div className="section-head"><div><div className="kicker">{g}</div><div className="h2">Most data in our set</div></div></div>
          <div className="pgrid">
            {ps.map((p) => (
              <Link key={p.person_id} href={`/players/${p.person_id}`} className="pcard">
                <div className="n">{p.name}</div>
                <div className="mini" style={{ marginTop: 4 }}>{p.role ?? "role unknown"} · {p.matches} matches</div>
                <div className="mini">{fmt(p.balls_faced)} balls faced · {fmt(p.balls_bowled)} bowled</div>
              </Link>
            ))}
          </div>
        </div>
      ))}
      {feat === null && <div className="loading">Loading…</div>}
    </div>
  );
}
