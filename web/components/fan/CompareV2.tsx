"use client";
// Compare V2: never one score. Per dimension: both values, samples, and "A leads / B leads / too close to call"
// (a lead needs to clear a Bonferroni-corrected test). Then timeline, records, peer percentiles. The fan judges.
import Link from "next/link";
import { useEffect, useState } from "react";
import { api, fmt, ordinal } from "@/lib/api";
import { WhyBox } from "./bits";

export const PAIRS: [string, string, string][] = [
  ["ba607b88", "740742ef", "Kohli v Rohit"], ["462411b3", "3fb19989", "Bumrah v Starc"], ["5d2eda89", "27e003ce", "Mandhana v Lanning"],
  ["99b75528", "8a75e999", "Buttler v Babar"], ["4a8a2e3b", "99b75528", "Dhoni v Buttler"], ["be150fc8", "cdb82f1c", "Perry v Ecclestone"],
  ["9d430b40", "5f547c8b", "Narine v Rashid Khan"], ["30a45b23", "a343262c", "Smith v Root"],
];

export function SuggestedPairs() {
  return (
    <section className="section" data-testid="compare-suggestions">
      <div className="kicker">Start with a classic</div>
      <div className="mrows">
        {PAIRS.map(([a, b, l]) => <Link key={l} className="mrow" href={`/compare?ids=${a},${b}`}><span className="mn"><b>{l}</b><span className="mini">Where each leads, and where it&apos;s a tie</span></span><span className="mv">→</span></Link>)}
      </div>
    </section>
  );
}

export function CompareWithSimilar({ pid }: { pid: string }) {
  const [d, setD] = useState<any | null>(null);
  useEffect(() => { api(`/fan/player/${pid}/similar`).then((r) => setD(r.data)).catch(() => setD({ available: false })); }, [pid]);
  if (!d?.available) return <SuggestedPairs />;
  return (
    <section className="section" data-testid="compare-suggestions">
      <div className="kicker">Compare with a similar player</div>
      <div className="mrows">
        {d.rows.slice(0, 5).map((r: any) => <Link key={r.pid} className="mrow" href={`/compare?ids=${pid},${r.pid}`}><span className="mn"><b>{r.name}</b>
          <span className="mini">Similar {d.format} {d.role} profile</span></span><span className="mv">→</span></Link>)}
      </div>
    </section>
  );
}

export default function CompareV2({ a, b, format }: { a: string; b: string; format?: string }) {
  const [d, setD] = useState<any | null>(null);
  const [fmtSel, setFmt] = useState<string | undefined>(format || undefined);
  useEffect(() => { setD(null); api("/fan/compare", { ids: `${a},${b}`, format: fmtSel }).then((r) => setD(r.data)).catch(() => setD({ available: false, reason: "unavailable" })); }, [a, b, fmtSel]);
  if (!d) return <div className="loading">Comparing…</div>;
  if (!d.available) return <div className="empty">Can&apos;t compare these two directly: {d.reason}.</div>;
  const [A, B] = d.players;
  const groups = Array.from(new Set(d.dimensions.map((x: any) => x.group))) as string[];
  const fmts = Object.keys(d.formats || {}).filter((f) => d.formats[f][a] && d.formats[f][b]);
  return (
    <section className="section" data-testid="compare-v2">
      <div className="cmp2-head">
        <div className="kicker">{d.format} {d.role} · covered matches</div>
        <h2 className="h2"><span style={{ color: "var(--accent)" }}>{A.name}</span> v <span style={{ color: "var(--mod)" }}>{B.name}</span></h2>
        {fmts.length > 1 && <div className="seg" style={{ marginTop: 8 }}>{fmts.map((f) => <button key={f} className={d.format === f ? "on" : ""} onClick={() => setFmt(f)}>{f}</button>)}</div>}
        {d.gender_note && <div className="note" style={{ marginTop: 8 }}>{d.gender_note}</div>}
      </div>
      <div className="cmp2-verdict" data-testid="compare-leads">
        <div><b style={{ color: "var(--accent)" }}>{A.name} leads</b><span>{d.leads.A.length ? d.leads.A.join(" · ") : "nowhere clearly"}</span></div>
        <div><b style={{ color: "var(--mod)" }}>{B.name} leads</b><span>{d.leads.B.length ? d.leads.B.join(" · ") : "nowhere clearly"}</span></div>
        <div><b>Effectively tied</b><span>{d.leads.tied.length ? d.leads.tied.join(" · ") : "—"}</span></div>
        <div className="mini">No overall score: you decide what matters. <WhyBox why={{ test: `two-sided, α = 0.05 ÷ ${d.dimensions.length} dimensions = ${d.alpha}`, method: d.method }} /></div>
      </div>
      {groups.map((g) => (
        <div key={g} style={{ marginTop: 14 }}>
          <div className="eyebrow">{g}</div>
          {d.dimensions.filter((x: any) => x.group === g).map((x: any) => (
            <div key={x.key} className="cmp-row">
              <span><b style={{ fontSize: 14.5 }}>{x.label}</b><span className="mini" style={{ display: "block" }}>{fmt(x.a_n)} v {fmt(x.b_n)} {x.n_unit}{x.note ? ` · ${x.note}` : ""}</span></span>
              <span className="vals num"><span className={x.verdict === "A leads" ? "lead" : ""}>{fmt(x.a, 1)}</span><span className={x.verdict === "B leads" ? "lead" : ""} style={x.verdict === "B leads" ? { color: "var(--mod)" } : undefined}>{fmt(x.b, 1)}</span></span>
              <span className={`verdict ${x.verdict === "A leads" ? "a" : x.verdict === "B leads" ? "b" : ""}`}>{x.verdict === "A leads" ? A.name.split(" ").slice(-1)[0] : x.verdict === "B leads" ? B.name.split(" ").slice(-1)[0] : "tie"}</span>
            </div>
          ))}
        </div>
      ))}
      <div style={{ marginTop: 18 }}>
        <div className="eyebrow">Career timeline · {d.timeline.metric} per covered year</div>
        <Timeline2 t={d.timeline} A={A} B={B} />
      </div>
      <div style={{ marginTop: 18 }}>
        <div className="eyebrow">Peer percentiles · each against their own peers</div>
        {d.percentiles.dims.filter((x: any) => d.percentiles.a[x.key] != null || d.percentiles.b[x.key] != null).map((x: any) => (
          <div key={x.key} className="pctrow">
            <span className="mini">{x.label}</span>
            <span className="pctbar"><span className="pa" style={{ left: `${d.percentiles.a[x.key] ?? -10}%` }} title={`${A.name}: ${d.percentiles.a[x.key]}`} />
              <span className="pb" style={{ left: `${d.percentiles.b[x.key] ?? -10}%` }} title={`${B.name}: ${d.percentiles.b[x.key]}`} /></span>
            <span className="mini num">{d.percentiles.a[x.key] != null ? ordinal(d.percentiles.a[x.key]) : "–"} · {d.percentiles.b[x.key] != null ? ordinal(d.percentiles.b[x.key]) : "–"}</span>
          </div>
        ))}
        <div className="mini" style={{ marginTop: 4 }}>A percentile describes style, not quality. <WhyBox why={{ [A.name]: d.percentiles.a._pool, [B.name]: d.percentiles.b._pool }} /></div>
      </div>
      <div style={{ marginTop: 18 }} className="grid2">
        {[A, B].map((p: any) => (
          <div key={p.pid}>
            <div className="eyebrow">{p.name} in the record book</div>
            {(d.records[p.pid] || []).length ? d.records[p.pid].map((r: any) => (
              <Link key={r.id} href={`/records/${r.id}`} className="mrow"><span className="mn"><b style={{ fontSize: 14 }}>{r.title}</b></span><span className="mv num"><b>#{r.rank}</b></span></Link>
            )) : <div className="mini">No top-10 entries.</div>}
          </div>
        ))}
      </div>
    </section>
  );
}

function Timeline2({ t, A, B }: { t: any; A: any; B: any }) {
  const years = Array.from(new Set([...t.a, ...t.b].map((p: any) => p.year))).sort() as number[];
  if (!years.length) return null;
  const max = Math.max(...[...t.a, ...t.b].map((p: any) => p.value || 0), 1);
  const y0 = years[0], y1 = years[years.length - 1];
  const all = Array.from({ length: y1 - y0 + 1 }, (_, i) => y0 + i);
  return (<>
    <div className="tl2" role="img" aria-label={`${t.metric} by year`}>
      {all.map((y) => {
        const pa = t.a.find((p: any) => p.year === y), pb = t.b.find((p: any) => p.year === y);
        return <div key={y} className="tl2c" title={`${y}: ${A.name} ${pa?.value ?? "–"} · ${B.name} ${pb?.value ?? "–"}`}>
          <span className="pa" style={{ height: pa ? `${Math.max(3, (100 * pa.value) / max)}%` : 0 }} />
          <span className="pb" style={{ height: pb ? `${Math.max(3, (100 * pb.value) / max)}%` : 0 }} /></div>;
      })}
    </div>
    <div className="cbyears mini" style={{ paddingLeft: 0 }}><span>{y0}</span><span>{y1}</span></div>
    <div className="mini"><span className="lg pa" /> {A.name} <span className="lg pb" /> {B.name}</div>
  </>);
}
