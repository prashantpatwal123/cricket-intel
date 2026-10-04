"use client";
// Explore's daily discovery (Phase 7): everything from the database, deterministic for the day, skipping what this browser
// has already opened. Sections: continue · you probably didn't know · great battles · on this day · record book ·
// player rabbit hole · can you beat the model.
import Link from "next/link";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { load, reset, seenIds } from "@/lib/memory";
import { PlayCard, WhyBox } from "./bits";

export default function DailyDiscovery({ onItems }: { onItems?: (hrefs: string[]) => void }) {
  const [d, setD] = useState<any | null>(null);
  const [recent, setRecent] = useState<any[]>([]);
  const [play, setPlay] = useState<any>(null);
  useEffect(() => {
    const m = load();
    setRecent(m.visited.slice(0, 8)); setPlay(m.play);
    api("/fan/explore", { seen: seenIds(60).join(",") }).then((r) => {
      setD(r.data);
      onItems?.([...r.data.worth_knowing.map((x: any) => x.href), ...r.data.battles.map((x: any) => x.href)]);
    }).catch(() => setD({ error: true }));
  }, []);
  if (!d) return <div className="loading">Picking today&apos;s rabbit holes…</div>;
  if (d.error) return null;
  return (
    <>
      {recent.length > 0 && (
        <section className="section" data-testid="continue">
          <div className="xnext-head"><span className="eyebrow">Continue where you left off</span>
            <button className="why-btn" onClick={() => { reset(); setRecent([]); setPlay(null); }}>Clear my history</button></div>
          <div className="recent-row">{recent.map((v) => <Link key={v.id} href={v.href}>{v.label}</Link>)}</div>
          <div className="mini" style={{ marginTop: 4 }}>Kept only in this browser, used to avoid showing you the same things. {play?.n ? `Play: ${play.pts} pts from ${play.n} calls.` : ""}</div>
        </section>
      )}

      <section className="section" data-testid="didnt-know">
        <div className="kicker">You probably didn&apos;t know</div>
        <h2 className="h2">Worth knowing today</h2>
        <div className="fan-sec-list" style={{ marginTop: 10 }}>
          {d.worth_knowing.map((c: any) => (
            <div key={c.id} className="dk-card">
              <div className="dh">{c.headline}</div>
              <div className="db">{c.statement}</div>
              <div className="dm"><span className="mini">{c.type_label} · {c.n.toLocaleString("en-GB")} {c.type === "dismissal" ? "dismissals" : "balls"}</span>
                <WhyBox why={c.why} /><Link className="btn sm" href={c.href}>Evidence →</Link>
                <Link className="why-btn" href={`/share?type=finding&id=${encodeURIComponent(c.id)}`}>Share</Link></div>
            </div>
          ))}
        </div>
        <div className="mini" style={{ marginTop: 6 }}>Each fact passed a false-discovery check across every pattern tested.</div>
      </section>

      <section className="section" data-testid="great-battles">
        <div className="kicker">Great battles</div>
        <div className="mrows">{d.battles.map((b: any) => <Link key={b.id} href={b.href} className="mrow"><span className="mn"><b>{b.title}</b><span className="mini">{b.detail}</span></span><span className="mv">⚔</span></Link>)}</div>
      </section>

      {d.on_this_day?.items?.length > 0 && (
        <section className="section" data-testid="on-this-day">
          <div className="xnext-head"><span className="kicker">On this day · {d.on_this_day.label}</span><Link href="/on-this-day" className="btn sm">All →</Link></div>
          <div className="mrows">{d.on_this_day.items.slice(0, 4).map((x: any, i: number) => (
            <Link key={i} href={x.href} className="mrow"><span className="mn"><b>{x.title}</b><span className="mini">{x.detail}</span><span className="mini" style={{ color: "var(--accent)" }}>{x.when}</span></span><span className="mv">→</span></Link>))}</div>
        </section>
      )}

      {d.record_book?.length > 0 && (
        <section className="section" data-testid="record-of-day">
          <div className="xnext-head"><span className="kicker">Record book</span><Link href="/records" className="btn sm">All records →</Link></div>
          {d.record_book.map((r: any) => (
            <Link key={r.id} href={r.href} className="rec-card"><div className="rt">{r.title} <span className="mini">· {r.scope}</span></div>
              {r.top.map((x: any) => <div key={x.rank} className="rl">{x.rank}. {x.label} · <b>{x.value_fmt}</b></div>)}</Link>))}
        </section>
      )}

      {d.rabbit_hole?.path?.length > 0 && (
        <section className="section" data-testid="rabbit-hole">
          <div className="kicker">Player rabbit hole</div>
          <h2 className="h2" style={{ fontSize: 24 }}>Start at <Link href={d.rabbit_hole.start.href} style={{ color: "var(--accent)" }}>{d.rabbit_hole.start.title}</Link> and keep going</h2>
          <div className="hole">{d.rabbit_hole.path.map((s: any, i: number) => (
            <Link key={s.id} href={s.href}><span className="dot" /><span className="mn" style={{ display: "flex", flexDirection: "column" }}><b>{i + 1}. {s.title}</b><span className="mini">{s.reason}</span></span></Link>))}</div>
        </section>
      )}

      {d.play?.length > 0 && (
        <section className="section" data-testid="beat-the-model">
          <div className="kicker">Can you beat the model?</div>
          {d.play.map((m: any) => <PlayCard key={m.id} m={m} context={m.context} />)}
        </section>
      )}
    </>
  );
}
