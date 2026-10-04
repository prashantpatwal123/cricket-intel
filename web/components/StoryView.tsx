"use client";
// Renders a deterministic Story: a numbered sequence of evidence cards on a vertical timeline (not a grid of boxes).
import Link from "next/link";
import ProvBadge from "./Prov";
import Spark from "./viz/Spark";
import { OUTCOME_COLOR, symbolToOutcome } from "@/lib/viz/model";

function Visual({ v }: { v: any }) {
  if (!v) return null;
  if (v.type === "balls" || v.type === "ball_links") {
    const items = v.type === "balls" ? v.symbols.map((s: string) => ({ symbol: s })) : v.balls;
    return <div className="balls-row" style={{ marginTop: 8 }}>{items.map((b: any, i: number) => {
      const o = symbolToOutcome(b.symbol); const st = { background: o ? OUTCOME_COLOR[o] + (o === "WICKET" ? "" : "44") : "#ffffff10" };
      return b.id ? <Link key={i} href={`/delivery/${encodeURIComponent(b.id)}`} style={st} title={b.label}>{b.symbol}</Link> : <span key={i} style={{ ...st, minWidth: 34, height: 34, borderRadius: 10, display: "inline-grid", placeItems: "center", fontWeight: 800 }}>{b.symbol}</span>;
    })}</div>;
  }
  if (v.type === "series") return <div style={{ marginTop: 8 }}><Spark values={v.values} labels={v.labels} color="#ffb547" /></div>;
  if (v.type === "split") { const t = (v.a || 0) + (v.b || 0) || 1; return <div className="part-split" style={{ height: 10, marginTop: 10 }}><i style={{ width: `${(100 * v.a) / t}%` }} /></div>; }
  if (v.type === "numline") {
    const lo = Math.min(v.lo, v.usual) * 0.9, hi = Math.max(v.hi, v.usual) * 1.1, X = (x: number) => `${(100 * (x - lo)) / (hi - lo)}%`;
    return <div className="numline" style={{ height: 50 }}><div className="axis" /><div className="band" style={{ left: X(v.lo), width: `calc(${X(v.hi)} - ${X(v.lo)})` }} />
      <div className="mark" style={{ left: X(v.here), background: "#35e0c2" }} /><div className="lbl top" style={{ left: X(v.here), color: "#35e0c2" }}>here {v.here}</div>
      <div className="mark" style={{ left: X(v.usual), background: "#edf2fc" }} /><div className="lbl" style={{ left: X(v.usual) }}>usual {v.usual}</div></div>;
  }
  if (v.type === "bars") { const m = Math.max(...v.rows.map((r: any) => r.balls)); return <div style={{ marginTop: 8 }}>{v.rows.map((r: any) => (
    <div key={r.k} className="omap-row"><span className="k">{r.k}</span><span className="t"><i style={{ width: `${(100 * r.balls) / m}%`, background: "#7cc4ff" }} /></span><span className="v mini">SR {r.sr} · {r.outs} out</span></div>))}</div>; }
  if (v.type === "worm") { const m = Math.max(...v.overs); return <div className="mini-manhattan">{v.overs.map((r: number, i: number) => <i key={i} style={{ height: `${(100 * r) / m}%`, background: v.wkts[i] ? "#ff5c74" : "#35e0c2aa" }} title={`over ${i + 1}: ${r}`} />)}</div>; }
  return null;
}

export default function StoryView({ s, share }: { s: any; share?: string }) {
  return (
    <div className="story-view">
      <div className="eyebrow">Story · deterministic</div>
      <h1 className="display-xl">{s.title}</h1>
      <div className="lead">{s.subtitle}</div>
      <div style={{ display: "flex", gap: 8, marginTop: 12, flexWrap: "wrap" }}>
        <Link className="btn" href={s.source.href}>Open the full {s.source.type} →</Link>
        {share && <Link className="btn" href={share}>Share card</Link>}
      </div>
      <ol className="story-line">
        {s.cards.map((c: any, i: number) => (
          <li key={i} className={`story-step ${c.kind}`}>
            <span className="story-n">{i + 1}</span>
            <div className="story-body">
              <div className="story-t">{c.title}</div>
              <p className="story-p">{c.text}</p>
              {c.facts.length > 0 && <div className="story-facts">{c.facts.map((f: any, j: number) => <span key={j}><em>{f.label}</em> <b>{f.value ?? "–"}</b> <span className={`pdot ${f.prov}`} title={f.prov} /></span>)}</div>}
              <Visual v={c.visual} />
              {c.href && <Link className="story-ev" href={c.href}>See the evidence →</Link>}
            </div>
          </li>
        ))}
      </ol>
      <div className="mini" style={{ marginTop: 10 }}>{s.method} <ProvBadge prov="DERIVED" /></div>
    </div>
  );
}
