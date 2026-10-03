"use client";
import { useState } from "react";
import { Params } from "@/lib/api";

export default function InsightCard({ c, onDrill, compact = false, playerLink }: { c: any; onDrill?: (t: string, q: Params) => void; compact?: boolean; playerLink?: React.ReactNode }) {
  const [open, setOpen] = useState(false);
  return (
    <div className={`icard ${c.kind}`}>
      <div className="icard-top">
        <span className={`ikind ${c.kind}`}>{c.kind === "strength" ? "Above typical" : "Below typical"}</span>
        {c.stable ? <span className="chip-mini ok">holds in both halves</span> : <span className="chip-mini">stability unclear</span>}
        <span className="mini">{c.sample.inside_balls} balls</span>
      </div>
      {playerLink}
      <div className="ihead">{c.headline}</div>
      {!compact && <div className="sub" style={{ marginTop: 4 }}>{c.statement}</div>}
      <div style={{ display: "flex", gap: 8, marginTop: 10, flexWrap: "wrap" }}>
        <button className="btn" onClick={() => setOpen(!open)} aria-expanded={open}>{open ? "Hide" : "WHY?"}</button>
        {onDrill && <button className="btn" onClick={() => onDrill(c.headline, c.evidence_query)}>Deliveries →</button>}
      </div>
      {open && (
        <dl className="kv why fade-in">
          {compact && <><dt>Finding</dt><dd>{c.statement}</dd></>}
          <dt>Compared</dt><dd>{c.why.comparison}</dd>
          <dt>Calculation</dt><dd>{c.why.calculation}</dd>
          <dt>Inside</dt><dd>{c.why.inside}</dd>
          <dt>Otherwise</dt><dd>{c.why.outside}</dd>
          <dt>Uncertainty</dt><dd>{c.why.interval} · p = {c.why.p_value}</dd>
          <dt>Testing</dt><dd>{c.why.multiple_testing}</dd>
          <dt>Stability</dt><dd>{c.why.stability}</dd>
          <dt>Shrinkage</dt><dd>{c.why.shrinkage}</dd>
          <dt>Thresholds</dt><dd>{c.why.thresholds}</dd>
          <dt>Status</dt><dd>MODELLED: a statistical comparison of observed events. It says what happened in our covered data, not why.</dd>
        </dl>
      )}
    </div>
  );
}
