"use client";
// "Continue where you left off": the last entities opened in this browser (local session memory only), with a reset.
// Renders nothing for a first-time visitor.
import Link from "next/link";
import { useEffect, useState } from "react";
import { load, reset } from "@/lib/memory";

export default function Continue({ max = 8 }: { max?: number }) {
  const [recent, setRecent] = useState<any[]>([]);
  const [play, setPlay] = useState<any>(null);
  useEffect(() => { const m = load(); setRecent(m.visited.slice(0, max)); setPlay(m.play); }, [max]);
  if (!recent.length) return null;
  return (
    <section className="section" data-testid="continue">
      <div className="xnext-head"><span className="eyebrow">Continue where you left off</span>
        <button className="why-btn" onClick={() => { reset(); setRecent([]); setPlay(null); }}>Clear my history</button></div>
      <div className="recent-row">{recent.map((v) => <Link key={v.id} href={v.href}>{v.label}</Link>)}</div>
      <div className="mini" style={{ marginTop: 4 }}>Kept only in this browser, used to avoid showing you the same things. {play?.n ? `Play: ${play.pts} pts from ${play.n} calls.` : ""}</div>
    </section>
  );
}
