"use client";
// Rabbit-hole navigation: deterministic, relevance-based next destinations for the object on screen. Each says why.
import Link from "next/link";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";

const KIND_ICON: Record<string, string> = { innings: "▮", spell: "◎", battle: "⚔", partnership: "∞", competition: "🏆", match: "▣", career: "↗", story: "¶",
  delivery: "•", player: "●", rivalry: "⇄", records: "≡" };

export default function ExploreNext({ type, id, title = "Explore next" }: { type: string; id: string; title?: string }) {
  const [rows, setRows] = useState<any[] | null>(null);
  useEffect(() => { setRows(null); api<any[]>("/related", { type, key: id }).then((r) => setRows(r.data)).catch(() => setRows([])); }, [type, id]);
  if (rows && !rows.length) return null;
  return (
    <section className="xnext" aria-label={title} data-testid="explore-next">
      <div className="eyebrow">{title}</div>
      {!rows ? <div className="loading">…</div> : (
        <div className="xnext-list">
          {rows.map((r) => (
            <Link key={r.href} href={r.href} className="xnext-row">
              <span className={`sicon ${r.kind}`}>{KIND_ICON[r.kind] ?? "→"}</span>
              <span className="sl"><b>{r.label}</b><span className="mini">{r.reason}</span></span>
              <span className="sgo">→</span>
            </Link>
          ))}
        </div>
      )}
    </section>
  );
}
