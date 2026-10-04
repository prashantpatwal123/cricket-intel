"use client";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { api, Dataset } from "@/lib/api";

export default function Shell({ children }: { children: React.ReactNode }) {
  const path = usePathname();
  const [ds, setDs] = useState<Dataset | null>(null);
  // Internal-preview notice: full on the first visit in this browser, then a compact status pill that expands on tap.
  const [seen, setSeen] = useState(true);
  const [open, setOpen] = useState(false);
  useEffect(() => {
    api("/meta").then((r) => setDs(r.dataset)).catch(() => {});
    try { setSeen(localStorage.getItem("ci-preview-notice") === "1"); } catch { setSeen(false); }
  }, []);
  const ack = () => { try { localStorage.setItem("ci-preview-notice", "1"); } catch { /* storage blocked: show full notice again next time */ } setSeen(true); setOpen(false); };
  // IA: five destinations. Search is the gateway to every entity (players, matches, competitions, rivalries, libraries,
  // records, methodology); Explore is the gateway to discovery and stories. See docs/architecture/information-architecture.md.
  const nav = [["/", "Explore"], ["/search", "Search"], ["/battle", "Battles"], ["/ask", "Ask"], ["/play", "Play"]];
  const SEARCH_AREA = ["/search", "/players", "/match", "/competition", "/rivalr", "/innings", "/spells", "/spell/", "/records", "/partnerships", "/data", "/context"];
  const isOn = (h: string) => h === "/" ? path === "/" || path.startsWith("/story") || path.startsWith("/share") || path.startsWith("/lab")
    : h === "/search" ? SEARCH_AREA.some((p) => path.startsWith(p))
    : h === "/battle" ? path.startsWith("/battle") || path.startsWith("/compare") : path === h || path.startsWith(h + "/");
  const router = useRouter();
  const [q, setQ] = useState("");
  return (
    <>
      {ds?.synthetic && (
        <div className="synthetic" role="alert">
          SYNTHETIC TEST DATA: fictional players and matches, used to test the product. These are not real cricket statistics.
        </div>
      )}
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
        <nav className="nav">
          {nav.map(([h, l]) => (
            <Link key={h} href={h} className={isOn(h) ? "active" : ""}>{l}</Link>
          ))}
        </nav>
      </header>
      <main className="wrap">{children}</main>
      <footer className="footer">
        {ds ? ds.attribution : "Ball-by-ball data from Cricsheet (cricsheet.org)."} Every number is computed from the dataset shown. Provenance tags:
        OBSERVED · DERIVED · RECONSTRUCTED · MODELLED · ILLUSTRATIVE.
      </footer>
    </>
  );
}
