"use client";
// Universal search: FINDS things. Grouped by entity type. Statistical questions go to Ask.
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";
import { load, reset } from "@/lib/memory";
import { api } from "@/lib/api";

const EXAMPLES = ["Virat Kohli", "Kohli vs Zampa", "India Pakistan 2022", "Bumrah 6/19", "Mandhana partnerships", "2023 World Cup", "death overs economy", "RCB v CSK"];
const BROWSE: [string, string, string][] = [
  ["/players", "Players", "Search or browse every player"], ["/competitions", "Competitions", "IPL, WPL, World Cups and series"],
  ["/rivalries", "Rivalries", "Team v team head-to-heads"], ["/innings", "Innings library", "Highest, fastest, hardest chases"],
  ["/spells", "Spell library", "Best figures, death overs, bursts"], ["/battle", "Battle universe", "Batter v bowler, every angle"],
  ["/records", "Record book", "Records by category, each with its evidence"], ["/on-this-day", "On this day", "Matches, innings and spells on today's date"],
  ["/compare", "Compare", "Two players: where each leads, and where it's a tie"], ["/partnerships", "Partnerships", "Best pairs and biggest stands"],
  ["/live-lab", "Historical Live Lab", "Replay a finished match ball by ball"],
  ["/visual-lab", "Visual Lab", "What our graphics can and cannot show, and why"],
  ["/data", "Data & methodology", "Coverage, definitions, licence status"],
];
const ICON: Record<string, string> = { player: "●", team: "◆", competition: "🏆", edition: "🏆", match: "▣", innings: "▮", spell: "◎", battle: "⚔", pair: "∞", rivalry: "⇄", record: "≡" };

export default function Page() { return <Suspense fallback={<div className="loading">Loading…</div>}><Search /></Suspense>; }

function Search() {
  const sp = useSearchParams();
  const router = useRouter();
  const [q, setQ] = useState(sp.get("q") || "");
  const [res, setRes] = useState<any | null>(null);
  const [recent, setRecent] = useState<any[]>([]);
  useEffect(() => { setRecent(load().visited.slice(0, 10)); }, []);
  useEffect(() => { const x = sp.get("q"); if (x) setQ(x); }, [sp]);
  useEffect(() => {
    const t = setTimeout(() => {
      if (q.trim().length < 2) { setRes(null); return; }
      api("/search", { q: q.trim() }).then((r) => setRes(r.data));
      router.replace(`/search?q=${encodeURIComponent(q.trim())}`, { scroll: false });
    }, 140);
    return () => clearTimeout(t);
  }, [q]);
  return (
    <div className="fade-in">
      <section className="search-top">
        <h1 className="kicker">Search</h1>
        <input className="search-big" value={q} onChange={(e) => setQ(e.target.value)} autoFocus placeholder="Players, matches, battles, records…" aria-label="Search everything" />
        <div className="mini" style={{ marginTop: 8 }}>Search finds things. To ask a statistical question (&ldquo;who has the best death-overs economy?&rdquo;), use <Link href={`/ask${q ? `?q=${encodeURIComponent(q)}` : ""}`} className="ul">Ask</Link>.</div>
        {!res && <div className="chips" style={{ marginTop: 12 }}>{EXAMPLES.map((e) => <button key={e} className="chip" onClick={() => setQ(e)}>{e}</button>)}</div>}
      </section>
      {res && (
        <section className="sresults">
          {res.groups.length === 0 && <div className="empty">Nothing found for &ldquo;{res.query}&rdquo;. Try a surname, two teams (&ldquo;India v Australia&rdquo;) or figures (&ldquo;6/19&rdquo;).</div>}
          {res.groups.map((g: any) => (
            <div key={g.type} className="sgroup">
              <div className="sgroup-h">{g.label}</div>
              {g.items.map((it: any) => (
                <Link key={it.href + it.label} href={it.href} className="srow">
                  <span className={`sicon ${it.type}`}>{ICON[it.type]}</span>
                  <span className="sl"><b>{it.label}</b><span className="mini">{it.sub}</span></span>
                  <span className="sgo">→</span>
                </Link>
              ))}
            </div>
          ))}
        </section>
      )}
      {recent.length > 0 && !q && (
        <section className="section" data-testid="recent">
          <div className="xnext-head"><span className="kicker">Recently viewed</span>
            <button className="why-btn" onClick={() => { reset(); setRecent([]); }}>Clear</button></div>
          <div className="recent-row">{recent.map((v) => <Link key={v.id} href={v.href}>{v.label}</Link>)}</div>
          <div className="mini" style={{ marginTop: 4 }}>Only in this browser.</div>
        </section>
      )}
      <section className="section">
        <div className="kicker">Browse</div>
        <div className="browse">
          {BROWSE.map(([h, l, d]) => <Link key={h} href={h} className="browse-row"><b>{l}</b><span className="mini">{d}</span><span className="sgo">→</span></Link>)}
        </div>
      </section>
    </div>
  );
}
