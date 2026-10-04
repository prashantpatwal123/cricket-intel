"use client";
// Context Engine reference: every per-delivery feature, its definition, provenance and format rule.
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import ProvBadge from "@/components/Prov";

export default function ContextPage() {
  const [d, setD] = useState<any | null>(null);
  useEffect(() => { api("/context/features").then((r) => setD(r.data)); }, []);
  return (
    <div className="fade-in" style={{ maxWidth: 820 }}>
      <section className="section" style={{ marginTop: 22 }}>
        <div className="kicker">Context Engine · {d?.version}</div>
        <h1 className="big-title" style={{ fontSize: "clamp(32px, 8vw, 54px)", margin: "6px 0 10px" }}>What we know about every ball</h1>
        <p className="sub">These features are calculated for every delivery from the recorded events. T20 and ODI use different windows and bands where the game differs. Nothing here is estimated.</p>
      </section>
      {!d ? <div className="loading">Loading…</div> : (
        <div className="dcard-list">
          {d.features.map((f: any) => (
            <div key={f.key} className="card" style={{ padding: 12 }}>
              <div style={{ display: "flex", justifyContent: "space-between", gap: 8 }}><b>{f.label}</b><ProvBadge prov={f.prov.split("/")[0]} /></div>
              <div style={{ fontSize: 13.5, marginTop: 4 }}>{f.definition}</div>
              {f.format_note && <div className="mini" style={{ marginTop: 2 }}>{f.format_note}</div>}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
