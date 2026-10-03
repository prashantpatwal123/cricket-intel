"use client";
// Explore: the discovery homepage. Everything here is computed from the covered data, with a link to its evidence.
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { api, fmt } from "@/lib/api";
import InsightCard from "@/components/InsightCard";

const G = (g: string) => (g === "female" ? "Women" : "Men");
const ASK_EXAMPLES = ["Who has dismissed Virat Kohli most?", "Most sixes in death overs", "Mandhana strike rate in WPL", "Bumrah v Warner"];

export default function Explore() {
  const router = useRouter();
  const [feed, setFeed] = useState<any | null>(null);
  const [q, setQ] = useState("");
  useEffect(() => { api("/explore").then((r) => setFeed(r.data)).catch(() => setFeed({ error: true })); }, []);
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

      {feed?.battles?.length > 0 && (
        <section className="section">
          <div className="section-head"><div><div className="kicker">Battles</div><div className="h2">The longest-running contests</div>
            <div className="sub">Batter v bowler pairs with the most balls in our data.</div></div>
            <Link href="/battle" className="btn">All battles →</Link></div>
          <div className="ex-cards three">
            {feed.battles.slice(0, 6).map((b: any) => (
              <Link key={b.batter_id + b.bowler_id} href={`/battle?bat=${b.batter_id}&bowl=${b.bowler_id}`} className="bcard">
                <div className="gender-tag">{G(b.gender)}</div>
                <div className="who">{b.batter}<span>v</span>{b.bowler}</div>
                <div className="statstrip" style={{ gridTemplateColumns: "repeat(4, 1fr)", marginTop: 10 }}>
                  <div><b className="num">{b.balls}</b><span className="mini">balls</span></div>
                  <div><b className="num">{b.runs}</b><span className="mini">runs</span></div>
                  <div><b className="num">{b.balls ? fmt((100 * b.runs) / b.balls, 0) : "–"}</b><span className="mini">SR</span></div>
                  <div><b className="num wk">{b.dismissals}</b><span className="mini">outs</span></div>
                </div>
              </Link>
            ))}
          </div>
        </section>
      )}

      {feed?.records?.length > 0 && (
        <section className="section">
          <div className="section-head"><div><div className="kicker">Records</div><div className="h2">Leaderboards</div>
            <div className="sub">Covered data only. These are not official records.</div></div>
            <Link href="/records" className="btn">Records explorer →</Link></div>
          <div className="ex-cards three">
            {feed.records.slice(0, 6).map((r: any) => (
              <Link key={r.preset.id + r.gender} href={`/records?preset=${r.preset.id}&gender=${r.gender}`} className="rcard">
                <div className="gender-tag">{G(r.gender)}</div>
                <div style={{ fontWeight: 800, fontSize: 15, marginTop: 2 }}>{r.preset.title}</div>
                <ol>
                  {r.top.map((x: any) => (
                    <li key={x.rank}><span className="mini">{x.rank}</span><span style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{x.names.join(" v ")}</span><b className="num">{x.value_fmt}</b></li>
                  ))}
                </ol>
                <div className="mini" style={{ marginTop: 6 }}>{r.definition}{r.min_sample ? ` Min ${r.min_sample} ${r.sample_unit}.` : ""}</div>
              </Link>
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
          <Link href="/players" className="rcard"><div className="kicker">Players</div><div style={{ fontWeight: 800, marginTop: 4 }}>Search any player: fingerprint, strengths, dismissals, timeline</div></Link>
          <Link href="/compare" className="rcard"><div className="kicker">Compare</div><div style={{ fontWeight: 800, marginTop: 4 }}>Put 2 to 4 players side by side, with their coverage differences shown</div></Link>
        </div>
      </section>
    </div>
  );
}
