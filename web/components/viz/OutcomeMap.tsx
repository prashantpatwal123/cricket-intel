"use client";
// Outcome Map: distribution of DOT/1/2/3/4/6/WICKET for a player, matchup, context or model. Optional comparison ticks.
import { fmt } from "@/lib/api";
import { OUTCOMES, OUTCOME_COLOR } from "@/lib/viz/model";
import ProvBadge from "../Prov";

export default function OutcomeMap({ counts, compare, title, prov = "OBSERVED", unit = "balls" }: {
  counts: Record<string, number>; compare?: { label: string; probs: Record<string, number> }; title?: string; prov?: string; unit?: string;
}) {
  const n = OUTCOMES.reduce((a, k) => a + (counts[k] || 0), 0);
  if (!n) return <div className="empty">No balls.</div>;
  return (
    <div className="omap">
      {title && <div className="sit-title">{title} <ProvBadge prov={prov} /></div>}
      <div className="omap-stack" role="img" aria-label="Outcome distribution">
        {OUTCOMES.map((k) => counts[k] ? <span key={k} style={{ width: `${(100 * counts[k]) / n}%`, background: OUTCOME_COLOR[k] }} title={`${k}: ${counts[k]}`} /> : null)}
      </div>
      <div className="omap-rows">
        {OUTCOMES.map((k) => {
          const p = (counts[k] || 0) / n, c = compare?.probs[k];
          return (
            <div key={k} className="omap-row">
              <span className="k" style={{ color: k === "WICKET" ? "var(--wicket)" : undefined }}>{k}</span>
              <span className="t"><i style={{ width: `${100 * p}%`, background: OUTCOME_COLOR[k] }} />{c != null && <b style={{ left: `${100 * c}%` }} title={`${compare!.label}: ${(100 * c).toFixed(1)}%`} />}</span>
              <span className="v num">{(100 * p).toFixed(1)}%<span className="mini"> {fmt(counts[k] || 0)}</span></span>
            </div>
          );
        })}
      </div>
      <div className="mini" style={{ marginTop: 4 }}>{fmt(n)} {unit}{compare ? ` · tick = ${compare.label}` : ""}</div>
    </div>
  );
}
