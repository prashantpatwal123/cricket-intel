"use client";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { Suspense, useEffect, useState } from "react";
import { api, Dataset } from "@/lib/api";
import TourBar from "@/components/TourBar";
import { track } from "@/lib/analytics";

export default function Shell({ children }: { children: React.ReactNode }) {
  const path = usePathname();
  const [ds, setDs] = useState<Dataset | null>(null);
  // Internal-preview notice: full on the first visit in this browser, then a compact status pill that expands on tap.
  const [seen, setSeen] = useState(true);
  const [open, setOpen] = useState(false);
  useEffect(() => {
    api("/meta").then((r) => setDs(r.dataset)).catch(() => {});
    try { if (!sessionStorage.getItem("ci-dev-session")) track("session_start", { referrer_internal: document.referrer.includes(location.host) }); } catch { /* ignore */ }
    try { setSeen(localStorage.getItem("ci-preview-notice") === "1"); } catch { setSeen(false); }
  }, []);
  const ack = () => { try { localStorage.setItem("ci-preview-notice", "1"); } catch { /* storage blocked: show full notice again next time */ } setSeen(true); setOpen(false); };
  // IA (Phase 8): Home launches the five hero experiences. Players, Battles, Ask and Play are tabs; Match is reached from the
  // home, search and every player/innings/battle page. Search is the box on Home, the header search, and /search.
  // See docs/product/phase8-hero-architecture.md.
  const nav = [["/", "Home"], ["/players", "Players"], ["/battle", "Battles"], ["/ask", "Ask"], ["/play", "Play"]];
  const PLAYER_AREA = ["/players", "/how-out", "/compare", "/partnerships", "/innings", "/spell"];
  const isOn = (h: string) => h === "/" ? path === "/" || path.startsWith("/discover") || path.startsWith("/story") || path.startsWith("/share")
      || path.startsWith("/on-this-day") || path.startsWith("/records") || path.startsWith("/search") || path.startsWith("/match") || path.startsWith("/competition") || path.startsWith("/rivalr")
    : h === "/players" ? PLAYER_AREA.some((p) => path.startsWith(p))
    : h === "/battle" ? path.startsWith("/battle")
    : h === "/play" ? path.startsWith("/play") || path.startsWith("/live-lab")
    : path === h || path.startsWith(h + "/");
  const router = useRouter();
  const [q, setQ] = useState("");
  return (
    <>
      {ds?.synthetic && (
        <div className="synthetic" role="alert">
          SYNTHETIC TEST DATA: fictional players and matches, used to test the product. These are not real cricket statistics.
        </div>
      )}
      <a href="#main" className="skip">Skip to content</a>
      {ds && !ds.synthetic && (!seen || open ? (
        <div className="preview-detail" role="note">
          <b>INTERNAL PREVIEW · DATA LICENCE PENDING.</b> Real ball-by-ball data: {ds.attribution} Not for publication: the licence for Cricsheet
          match data has not been confirmed. Every number is computed from this dataset.{" "}
          <button className="btn" style={{ padding: "2px 10px", fontSize: 12, marginLeft: 6 }} onClick={ack}>{seen ? "Hide" : "Understood"}</button>
        </div>
      ) : (
        <button className="preview-pill" onClick={() => setOpen(true)} aria-expanded={false} aria-label="Internal preview, data licence pending. Show details">
          <span className="dot" />Internal preview · data licence pending<span aria-hidden style={{ opacity: .7 }}>ⓘ</span>
        </button>
      ))}
      <header className="topbar">
        <Link href="/" className="brand"><span className="brand-dot" />cricintel</Link>
        <form className="top-search only-desktop" onSubmit={(e) => { e.preventDefault(); if (q.trim()) router.push(`/search?q=${encodeURIComponent(q.trim())}`); }}>
          <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search players, matches, battles…" aria-label="Search" />
        </form>
        <Link href="/search" className="top-search-btn only-mobile" aria-label="Search players, matches and battles">
          <svg viewBox="0 0 24 24" width="20" height="20" aria-hidden><circle cx="10.5" cy="10.5" r="6.5" fill="none" stroke="currentColor" strokeWidth="2.2" /><path d="M15.5 15.5 21 21" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" /></svg>
        </Link>
        <nav className="nav" aria-label="Main">
          {nav.map(([h, l]) => (
            <Link key={h} href={h} className={isOn(h) ? "active" : ""}>{l}</Link>
          ))}
        </nav>
      </header>
      <main className="wrap" id="main">{children}</main>
      <Suspense fallback={null}><TourBar /></Suspense>
      <footer className="footer">
        {ds ? ds.attribution : "Ball-by-ball data from Cricsheet (cricsheet.org)."} Every number is computed from the dataset shown. Provenance tags:
        OBSERVED · DERIVED · RECONSTRUCTED · MODELLED · ILLUSTRATIVE.
        <nav className="foot-links" aria-label="About the data"><Link href="/glossary">Glossary</Link><Link href="/data">Data &amp; methods</Link><Link href="/discover">Everything we found</Link><Link href="/visual-lab">Visual Lab</Link></nav>
      </footer>
    </>
  );
}
