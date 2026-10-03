"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import { api, Dataset } from "@/lib/api";

export default function Shell({ children }: { children: React.ReactNode }) {
  const path = usePathname();
  const [ds, setDs] = useState<Dataset | null>(null);
  useEffect(() => { api("/meta").then((r) => setDs(r.dataset)).catch(() => {}); }, []);
  const nav = [["/", "Players"], ["/ask", "Ask"], ["/play", "Play"]];
  return (
    <>
      {ds?.synthetic && (
        <div className="synthetic" role="alert">
          SYNTHETIC TEST DATA: fictional players and matches, used to test the product. These are not real cricket statistics.
        </div>
      )}
      <header className="topbar">
        <Link href="/" className="brand"><span className="brand-dot" />cricintel</Link>
        <nav className="nav">
          {nav.map(([h, l]) => (
            <Link key={h} href={h} className={(h === "/" ? path === "/" || path.startsWith("/players/") : path === h || path.startsWith(h + "/")) ? "active" : ""}>{l}</Link>
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
