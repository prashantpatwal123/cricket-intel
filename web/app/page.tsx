"use client";
// Explore: the discovery homepage. Everything here is computed from the covered data, with a link to its evidence.
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { api, fmt } from "@/lib/api";
import InsightCard from "@/components/InsightCard";
import DiscoveryCard from "@/components/DiscoveryCard";

const TYPES = [["all", "All"], ["matchup", "Matchups"], ["dismissal", "Dismissals"], ["partnership", "Partnerships"], ["state", "When they change"],
  ["trend", "Trends"], ["record", "Records"], ["comeback", "Comebacks"]] as const;

const G = (g: string) => (g === "female" ? "Women" : "Men");
const ASK_EXAMPLES = ["Who has dismissed Virat Kohli most?", "Most sixes in death overs", "Mandhana strike rate in WPL", "Bumrah v Warner"];

export default function Explore() {
  const router = useRouter();
  const [feed, setFeed] = useState<any | null>(null);
  const [q, setQ] = useState("");
  const [disc, setDisc] = useState<any | null>(null);
  const [type, setType] = useState("all");
  const [more, setMore] = useState(false);
  useEffect(() => { api("/explore").then((r) => setFeed(r.data)).catch(() => setFeed({ error: true })); }, []);
  useEffect(() => { api("/discover").then((r) => setDisc(r.data)).catch(() => setDisc({ items: [] })); }, []);
  const [exp, setExp] = useState(false);
  const [feed2, setFeed2] = useState<any | null>(null);
  useEffect(() => { api("/feed").then((r) => setFeed2(r.data)).catch(() => setFeed2({ cards: [] })); }, []);
  useEffect(() => { api("/meta").then((r) => setExp(!!r.data.experimental)).catch(() => {}); }, []);
  // Findings already in today's feed are not repeated in the discovery grid below it.
  const inFeed = new Set((feed2?.cards || []).map((c: any) => c.href));
  const items = (disc?.items || []).filter((c: any) => (type === "all" || c.type === type) && !inFeed.has(c.href));
  const types = TYPES.filter(([k]) => k === "all" || (disc?.items || []).some((c: any) => c.type === k));
  const ask = (text: string) => text.trim() && router.push(`/ask?q=${encodeURIComponent(text.trim())}`);
  const evidenceHref = (c: any) => {
    const p = new URLSearchParams({ tab: "strengths", format: c.format });
    return `/players/${c.person_id}?${p}`;
  };
  return (
    <div className="fade-in">
      <section className="ex-hero">
        <div className="kicker">Explore · from {feed?.built_at ? "the covered Cricsheet data" : "the data"}</div>
        <h1 className="big-title">What the ball-by-ball<br />record actually shows</h1>
        <p className="sub" style={{ maxWidth: 620 }}>Patterns, battles and records found in our covered T20 and ODI data. Each one opens to its calculation and the deliveries behind it.</p>
        <form className="ex-ask" onSubmit={(e) => { e.preventDefault(); ask(q); }}>
          <input className="input" value={q} onChange={(e) => setQ(e.target.value)} placeholder="Ask cricket a question…" aria-label="Ask a question" />
          <button className="btn primary" type="submit">Ask</button>
        </form>
        <div className="chips" style={{ marginTop: 10 }}>
          {ASK_EXAMPLES.map((e) => <button key={e} className="chip" onClick={() => ask(e)}>{e}</button>)}
        </div>
      </section>

      <section className="section" aria-label="Today's feed">
        <div className="eyebrow">Today · {feed2?.day ?? ""}</div>
        <div className="h2" style={{ marginTop: 4 }}>{feed2?.cards?.length ? `${feed2.cards.length} things worth your time` : "Things worth your time"}</div>
        <div className="mini" style={{ marginTop: 8 }}>A fresh, deterministic mix each day: findings, innings, spells, battles, records, partnerships, a historical moment and a game. Every item says why it was picked.</div>
        {!feed2 ? <div className="loading">Building today&apos;s feed…</div> : feed2.cards.length > 0 && (<>
          <Link href={feed2.cards[0].href} className="feed-lead">
            <span className={`ft ${feed2.cards[0].type}`} style={{ fontSize: 11, fontWeight: 900, letterSpacing: ".12em", textTransform: "uppercase" }}>{feed2.cards[0].label}</span>
            <div className="t">{feed2.cards[0].title}</div>
            <div className="lead" style={{ marginTop: 8 }}>{feed2.cards[0].text}</div>
            <div className="why mini" style={{ marginTop: 6 }}>Why this: {feed2.cards[0].reason}</div>
          </Link>
          <div>{feed2.cards.slice(1).map((c: any, i: number) => (
            <Link key={i} href={c.href} className="feed-row" data-testid="feed-card">
              <span className={`ft ${c.type}`}>{c.label}</span>
              <span className="fb"><b>{c.title}</b><span className="mini">{c.text}</span><div className="why">Why this: {c.reason}</div></span>
              <span className="fn num">{c.numbers?.[0]?.value ?? "→"}</span>
            </Link>))}</div>
        </>)}
      </section>

      <section className="section">
        <div className="section-head"><div><div className="kicker">Discoveries</div><div className="h2">Found in the data</div>
          <div className="sub">Generated by fixed statistical tests and ranked by how unusual, well-sampled, recent and recognisable they are. Every card shows its working.</div></div></div>
        <div className="chips" style={{ marginBottom: 10 }}>
          {types.map(([k, l]) => <button key={k} className="chip" style={type === k ? { borderColor: "var(--accent)", color: "var(--accent)" } : undefined} onClick={() => { setType(k); setMore(false); }}>{l}</button>)}
        </div>
        {!disc ? <div className="loading">Running the discovery engine…</div> : (
          <>
            <div className="ex-cards">{items.slice(0, more ? 40 : 8).map((c: any) => <DiscoveryCard key={c.id} c={c} />)}</div>
            {items.length > 8 && <button className="btn" style={{ marginTop: 10 }} onClick={() => setMore(!more)}>{more ? "Show fewer" : `Show all ${items.length}`}</button>}
          </>
        )}
      </section>

      {!feed && <div className="loading">Finding patterns in the data…</div>}
      {feed?.error && <div className="empty" style={{ marginTop: 20 }}>The data service is not reachable.</div>}

      {feed?.insights?.length > 0 && (
        <section className="section">
          <div className="section-head"><div><div className="kicker">Patterns</div><div className="h2">Strengths and weaknesses that stand out</div>
            <div className="sub">Each finding compares a batter with similar batters, passes a false-discovery check and shows its working.</div></div></div>
          <div className="icards">
            {feed.insights.slice(0, 6).map((c: any) => (
              <InsightCard key={c.person_id + c.id} c={c} compact
                playerLink={<Link href={evidenceHref(c)} className="mini" style={{ display: "block", marginTop: 6 }}>
                  <b style={{ color: "var(--text)", fontSize: 14 }}>{c.player}</b> · {G(c.gender)}&apos;s {c.format} →</Link>} />
            ))}
          </div>
        </section>
      )}

      <section className="section">
        <div className="play-cta">
          <div><div className="kicker" style={{ color: "var(--accent-2)" }}>Play</div><div className="h2">What happens next?</div>
            <div className="sub">Real moments from past matches. Call the next ball and see if you can beat the model.</div></div>
          <Link href="/play" className="btn primary">Play →</Link>
        </div>
      </section>
      <section className="section">
        <div className="ex-cards">
          <Link href="/competitions" className="rcard"><div className="kicker">Competitions</div><div style={{ fontWeight: 800, marginTop: 4 }}>IPL, WPL, World Cups: editions, leaders, trends and coverage</div></Link>
          <Link href="/innings" className="rcard"><div className="kicker">Innings & spells</div><div style={{ fontWeight: 800, marginTop: 4 }}>Libraries of the highest, fastest and hardest innings, and the best spells</div></Link>
          <Link href="/players" className="rcard"><div className="kicker">Players</div><div style={{ fontWeight: 800, marginTop: 4 }}>Search any player: fingerprint, strengths, dismissals, timeline</div></Link>
          <Link href="/compare" className="rcard"><div className="kicker">Compare</div><div style={{ fontWeight: 800, marginTop: 4 }}>Put 2 to 4 players side by side, with their coverage differences shown</div></Link>
          <Link href="/partnerships" className="rcard"><div className="kicker">Partnerships</div><div style={{ fontWeight: 800, marginTop: 4 }}>The best batting pairs, the biggest stands and who brings out the best in whom</div></Link>
          <Link href="/context" className="rcard"><div className="kicker">Context Engine</div><div style={{ fontWeight: 800, marginTop: 4 }}>The 27 situation features we calculate for every ball, and how</div></Link>
          {exp && <Link href="/lab" className="rcard" style={{ borderColor: "#c49bff66" }}><div className="kicker" style={{ color: "var(--mod)" }}>Experimental lab</div><div style={{ fontWeight: 800, marginTop: 4 }}>Situation Difficulty (v0.1) and its validation. Internal only</div></Link>}
        </div>
      </section>
    </div>
  );
}
