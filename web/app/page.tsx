"use client";
// Home (Phase 8): the first 60 seconds. One promise, one search box, five real things to do (one per hero experience),
// then today's single finding, battle and Play challenge. Everything else is one tap away, never on top of this.
import Continue from "@/components/fan/Continue";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";
import { api } from "@/lib/api";
import { seenIds } from "@/lib/memory";
import { tourState, TOUR_START } from "@/lib/tour";
import { track } from "@/lib/analytics";
import { PlayCard, WhyBox } from "@/components/fan/bits";

const HERO_LABEL: Record<string, string> = { player: "Player", battle: "Battle", match: "Match", play: "Play", ask: "Ask" };

export default function Page() { return <Suspense fallback={<div className="loading">Loading…</div>}><Home /></Suspense>; }

function Home() {
  const router = useRouter();
  const sp = useSearchParams();
  const [d, setD] = useState<any | null>(null);
  const [q, setQ] = useState("");
  const [tour, setTour] = useState<string>("new");
  useEffect(() => {
    setTour(tourState());
    // ?day= pins the daily selection (visual-regression and golden-journey tests use a fixed date)
    api("/fan/home", { day: sp.get("day") || undefined, seen: sp.get("day") ? "" : seenIds(60).join(",") }).then((r) => setD(r.data)).catch(() => setD({ error: true }));
  }, [sp]);
  const search = (t: string) => { if (t.trim()) { track("search", { q_len: t.trim().length, from: "home" }); router.push(`/search?q=${encodeURIComponent(t.trim())}`); } };
  return (
    <div className="fade-in home">
      <section className="home-hero" aria-labelledby="home-title">
        <div className="kicker">Cricket intelligence · ball by ball</div>
        <h1 id="home-title" className="home-title">See cricket<br />differently.</h1>
        <p className="home-sub">Who really gets whom out, what changes after 30 balls, which battles are lopsided. Every number opens to the deliveries behind it.</p>
        <form className="home-search" role="search" onSubmit={(e) => { e.preventDefault(); search(q); }}>
          <input className="input" value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search a player, match or battle" aria-label="Search a player, match or battle" />
          <button className="btn primary" type="submit">Search</button>
        </form>
        <ol className="launch" data-testid="home-examples" aria-label="Start here">
          {(d?.examples || []).map((x: any) => (
            <li key={x.href}><Link href={x.href} className={`launch-row h-${x.hero}`} onClick={() => track("entity_open", { from: "home_example", hero: x.hero })}>
              <span className="hk">{HERO_LABEL[x.hero]}</span>
              <span className="lt"><b>{x.title}</b><span>{x.fact}</span></span>
              <span className="go" aria-hidden>→</span>
            </Link></li>
          ))}
          {!d && [0, 1, 2, 3, 4].map((i) => <li key={i} className="launch-skel" aria-hidden />)}
        </ol>
        {tour === "new" && (
          <Link className="tour-cta" href={TOUR_START} data-testid="tour-start" onClick={() => track("tour", { action: "start" })}>
            <span>New here? <b>Take the 60-second tour</b></span><span className="mini">Kohli → how Kohli gets out → Kohli v Zampa → the MCG 82* → call a ball</span>
          </Link>
        )}
      </section>

      {d && !d.error && (
        <section className="section today" aria-label="Today">
          <div className="crease-head"><span className="kicker">Today in the data</span><span className="mini">{d.date}</span></div>
          {d.finding && (
            <article className="today-finding" data-testid="home-finding">
              <div className="tk">You probably didn&apos;t know</div>
              <h2 className="tf">{d.finding.headline}</h2>
              <p className="mini">{d.finding.statement}</p>
              <div className="dm"><Link className="btn sm" href={d.finding.href}>See the evidence →</Link><WhyBox why={d.finding.why} /></div>
            </article>
          )}
          {d.battle && (
            <Link className="today-battle" href={d.battle.href} data-testid="home-battle">
              <span className="tk">Great battle</span>
              <span className="vsline">{d.battle.title.split(" v ")[0]} <i>v</i> {d.battle.title.split(" v ")[1]}</span>
              <span className="mini">{d.battle.detail}</span>
            </Link>
          )}
          {d.play && <div data-testid="home-play"><PlayCard m={d.play} /></div>}
        </section>
      )}

      <Continue />
      {d && !d.error && (
        <section className="section keep" aria-label="Keep exploring">
          <div className="kicker">Keep exploring</div>
          <div className="keep-links">
            {d.on_this_day && <Link href="/on-this-day"><b>On this day · {d.on_this_day_label}</b><span>{d.on_this_day.title}</span></Link>}
            {d.record && <Link href={d.record.href}><b>Record book</b><span>{d.record.title} · {d.record.scope}</span></Link>}
            <Link href={d.rabbit_start.href}><b>Rabbit hole</b><span>Start at {d.rabbit_start.title} and follow the links</span></Link>
            <Link href="/discover"><b>Everything we found</b><span>Every finding, today&apos;s mix, strengths and weaknesses</span></Link>
            <Link href="/live-lab" data-testid="gw-live-lab"><b>Replay a match</b><span>Historical replays, ball by ball. Not live</span></Link>
          </div>
        </section>
      )}
      {d?.error && <div className="empty">The data service is not reachable.</div>}
    </div>
  );
}
