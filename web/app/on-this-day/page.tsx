"use client";
// On This Day: matches, innings, spells and partnerships from covered data on a calendar date.
// "N years ago today" is only claimed for single-day matches; multi-day matches are marked as "began on this day".
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";
import { api } from "@/lib/api";
import { WhyBox } from "@/components/fan/bits";

export default function Page() { return <Suspense fallback={<div className="loading">Loading…</div>}><OnThisDay /></Suspense>; }

function shift(day: string, n: number) {
  const d = new Date(day + "T12:00:00Z"); d.setUTCDate(d.getUTCDate() + n); return d.toISOString().slice(0, 10);
}

function OnThisDay() {
  const sp = useSearchParams();
  const router = useRouter();
  const [d, setD] = useState<any | null>(null);
  const day = sp.get("day") || "";
  useEffect(() => { setD(null); api("/fan/onthisday", { day: day || undefined }).then((r) => setD(r.data)).catch(() => setD({ error: true })); }, [day]);
  if (!d) return <div className="loading">Looking through the calendar…</div>;
  if (d.error) return <div className="empty" style={{ marginTop: 30 }}>Could not load this date.</div>;
  return (
    <div className="fade-in" data-testid="on-this-day-page">
      <section className="section" style={{ marginTop: 22 }}>
        <div className="kicker">On this day</div>
        <h1 className="big-title" style={{ fontSize: "clamp(34px, 9vw, 58px)", margin: "6px 0 8px" }}>{d.label}</h1>
        <div className="hero-foot">
          <button className="btn sm" onClick={() => router.replace(`/on-this-day?day=${shift(d.date, -1)}`)}>← Previous day</button>
          <button className="btn sm" onClick={() => router.replace(`/on-this-day?day=${shift(d.date, 1)}`)}>Next day →</button>
          <WhyBox why={{ rule: d.rule, matches_on_this_date: d.matches_on_this_day }} />
        </div>
      </section>
      {d.items.length ? (
        <section className="section">
          <div className="mrows">{d.items.map((x: any, i: number) => (
            <Link key={i} href={x.href} className="mrow"><span className="mn"><span className="mini" style={{ color: "var(--accent)" }}>{x.when}</span><b>{x.title}</b>
              <span className="mini">{x.detail} · {x.gender === "female" ? "Women's" : "Men's"} {x.format}</span></span><span className="mv">→</span></Link>))}</div>
        </section>
      ) : <div className="empty">No standout innings, spells or finishes in covered matches on this date.</div>}
    </div>
  );
}
