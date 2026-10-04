"use client";
import Link from "next/link";
import { useState } from "react";

export default function DiscoveryCard({ c }: { c: any }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="disc">
      <div style={{ display: "flex", justifyContent: "space-between", gap: 8 }}>
        <span className={`disc-type ${c.type}`}>{c.type_label}{c.experimental ? " · experimental" : ""}</span>
        <span className="gender-tag">{c.gender === "female" ? "Women" : "Men"} · {c.format}</span>
      </div>
      <div className="disc-head">{c.headline}</div>
      <div className="disc-nums">{c.numbers.map((n: any) => <div key={n.label}><b className="num">{n.value}</b><span className="mini">{n.label}</span></div>)}</div>
      <div className="sub" style={{ marginTop: 8, fontSize: 13.5 }}>{c.statement}</div>
      <div style={{ display: "flex", gap: 8, marginTop: 10, flexWrap: "wrap" }}>
        <button className="btn" onClick={() => setOpen(!open)} aria-expanded={open}>{open ? "Hide" : "WHY?"}</button>
        <Link className="btn primary" href={c.href}>Show me →</Link>
        <Link className="btn" href={`/share?type=discovery&id=${encodeURIComponent(c.id)}`}>Share</Link>
      </div>
      {open && (
        <dl className="kv why fade-in">
          <dt>Compared</dt><dd>{c.why.comparison}</dd>
          <dt>Calculation</dt><dd>{c.why.calculation}</dd>
          <dt>Test</dt><dd>{c.why.test}</dd>
          <dt>Sample</dt><dd>{c.why.sample}</dd>
          <dt>Ranked by</dt><dd>unusualness {c.score_parts.unusualness} · sample {c.score_parts.sample} · recency ×{c.score_parts.recency} · recognisability {c.score_parts.recognisability}</dd>
          <dt>Written by</dt><dd>A template filled with the computed numbers. No language model.</dd>
        </dl>
      )}
    </div>
  );
}
