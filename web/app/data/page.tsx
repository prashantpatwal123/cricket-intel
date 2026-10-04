"use client";
// Data Quality & Methodology centre: coverage, gaps, metadata completeness, definitions, provenance, models, licence status.
import Link from "next/link";
import React, { useEffect, useState } from "react";
import { api, fmt } from "@/lib/api";
import ProvBadge from "@/components/Prov";

export default function DataPage() {
  const [d, setD] = useState<any | null>(null);
  const [def, setDef] = useState("records");
  useEffect(() => { api("/methodology").then((r) => setD(r.data)); }, []);
  if (!d) return <div className="loading">Loading…</div>;
  const t = d.totals, md = d.metadata;
  return (
    <div className="fade-in">
      <section style={{ marginTop: 22 }}>
        <div className="eyebrow">Data & methodology</div>
        <h1 className="display-xl">What we know, and how</h1>
        <div className="licence-box">
          <b>Licence status: INTERNAL PREVIEW.</b> {d.source.licence} <span className="mini">Attribution: {d.source.attribution}</span>
        </div>
        <div className="statline"><div><b>{fmt(t.matches)}</b><span>matches</span></div><div><b>{fmt(t.deliveries)}</b><span>deliveries</span></div>
          <div><b>{fmt(t.players)}</b><span>players</span></div><div><b>{t.d0.slice(0, 4)}–{t.d1.slice(0, 4)}</b><span>date range</span></div></div>
        <div className="mini" style={{ marginTop: 6 }}>Dataset build {d.built_at}.</div>
      </section>

      <Capability />
      <section className="rule-section">
        <div className="eyebrow">Coverage by group</div>
        <div className="tablist">{d.groups.map((g: any, i: number) => (
          <div key={i} className="trow"><span className="n">{g.gender === "female" ? "W" : "M"}</span><span className="t"><b>{g.format_group} · {g.team_type === "club" ? "leagues" : "internationals"}</b>
            <span className="mini">{g.d0} → {g.d1}</span></span><span className="v num">{fmt(g.matches)}</span></div>))}</div>
        <div className="eyebrow" style={{ marginTop: 16 }}>Largest competitions · Cricsheet&apos;s own completeness figure</div>
        <div className="tablist">{d.competitions.map((c: any) => (
          <Link key={c.competition + c.gender} className="trow" href={`/competition?name=${encodeURIComponent(c.competition)}&gender=${c.gender}`}><span className="n">{c.gender === "female" ? "W" : "M"}</span>
            <span className="t"><b>{c.competition}</b><span className="mini">{c.d0.slice(0, 4)}–{c.d1.slice(0, 4)} · source completeness {c.source_completeness}</span></span><span className="v num">{fmt(c.matches)}</span></Link>))}</div>
      </section>

      <section className="rule-section cols2">
        <div>
          <div className="eyebrow">Known gaps</div>
          <div className="tablist">{d.missing.map((m: any, i: number) => <div key={i} className="trow"><span className="n">!</span><span className="t"><b>{m.match_type} · {m.gender}</b><span className="mini">matches Cricsheet lists as missing</span></span><span className="v num">{m.n}</span></div>)}</div>
          <div className="eyebrow" style={{ marginTop: 14 }}>Earliest coverage (Cricsheet)</div>
          <div className="tablist">{d.periods.map((p: any, i: number) => <div key={i} className="trow"><span className="n">{p.gender === "female" ? "W" : "M"}</span><span className="t"><b>{p.name}</b><span className="mini">checked from {p.earliest_checked}</span></span><span className="v num" style={{ fontSize: 14 }}>{p.earliest_provided}</span></div>)}</div>
        </div>
        <div>
          <div className="eyebrow">Metadata completeness</div>
          {[["Role", md.players.role], ["Wicketkeeper flag", md.players.keeper_flag], ["Bowling style (players)", md.players.bowling_style], ["Bowling style (deliveries)", md.deliveries.bowling_style],
            ["Batting hand", md.players.batting_hand]].map(([l, v]) => (
            <div key={l as string} className="omap-row" style={{ marginTop: 8 }}><span className="k" style={{ fontWeight: 600, fontSize: 12 }}>{l}</span>
              <span className="t"><i style={{ width: `${v}%`, background: (v as number) > 50 ? "#35e0c2" : "#ffb547" }} /></span><span className="v num">{(v as number).toFixed(1)}%</span></div>))}
          <div className="mini" style={{ marginTop: 6 }}>Low coverage is why pace/spin, left/right-handed and style splits are not shown.</div>
          <div className="eyebrow" style={{ marginTop: 14 }}>Limitations</div>
          <ul className="edge-list">{d.limitations.map((l: string) => <li key={l}>{l}</li>)}</ul>
        </div>
      </section>
      {d.live_lab && (
        <section className="rule-section" data-testid="data-live-lab">
          <div className="eyebrow">Historical Live Lab</div>
          <ul className="edge-list">{["what", "spoiler_safety", "in_sample"].map((k) => <li key={k}>{d.live_lab[k]}</li>)}</ul>
          <div className="mini">Method notes: {d.live_lab.docs.join(" · ")}</div>
          <Link className="btn" href="/live-lab" style={{ marginTop: 8, display: "inline-block" }}>Open the Live Lab →</Link>
        </section>)}

      <section className="rule-section">
        <div className="eyebrow">Provenance</div>
        <div className="tablist">{Object.entries(d.provenance).map(([k, v]) => <div key={k} className="trow"><span className="n"><span className={`pdot ${k}`} /></span><span className="t"><b><ProvBadge prov={k} /></b><span className="mini">{v as string}</span></span><span /></div>)}</div>
      </section>

      <section className="rule-section">
        <div className="eyebrow">Definitions</div>
        <div className="cat-strip">{Object.keys(d.definitions).map((k) => <button key={k} className={def === k ? "on" : ""} onClick={() => setDef(k)}>{k.replace("_", " ")}</button>)}</div>
        <div className="tablist">{d.definitions[def].map((x: any) => <div key={x.key} className="trow"><span className="n">≡</span><span className="t"><b>{x.label}</b><span className="mini">{x.definition}{x.min ? ` · minimum ${x.min} ${x.unit}` : ""}</span></span><span className="mini">{x.prov ?? ""}</span></div>)}</div>
      </section>

      <section className="rule-section cols2">
        <div>
          <div className="eyebrow">Models & versions</div>
          <div className="tablist">{d.models.map((m: any) => <div key={m.file} className="trow"><span className="n">◇</span><span className="t"><b>{m.version}</b><span className="mini">{m.status}{m.trained_before ? ` · trained before ${m.trained_before}` : ""}</span></span><span /></div>)}
            {Object.entries(d.versions).map(([k, v]) => <div key={k} className="trow"><span className="n">·</span><span className="t"><b>{k}</b></span><span className="mini">{v as string}</span></div>)}</div>
        </div>
        <div>
          <div className="eyebrow">Experimental (behind a flag)</div>
          <div className="tablist">{d.experimental.map((x: any) => <div key={x.name} className="trow"><span className="n">⚗</span><span className="t"><b>{x.name}</b><span className="mini">{x.doc}</span></span><span className="mini">{x.status}</span></div>)}</div>
          <div className="eyebrow" style={{ marginTop: 14 }}>Rejected: the data can&apos;t support them</div>
          <div className="tablist">{d.rejected.map((x: any) => <div key={x.name} className="trow"><span className="n">✕</span><span className="t"><b>{x.name}</b><span className="mini">{x.why}</span></span><span /></div>)}</div>
        </div>
      </section>
      <div className="mini" style={{ marginTop: 12 }}>Per-delivery context definitions: <Link href="/context" className="ul">Context Engine</Link>.</div>
    </div>
  );
}


const GROUP: Record<string, string> = { event: "Events", player: "Player metadata", geometry: "Delivery geometry", shot: "Shot", contact: "Contact", fielding: "Fielding" };
// Data Quality Centre V2: field-level capability, from the same audit the docs are generated from (enrich/capability.py).
function Capability() {
  const [c, setC] = useState<any | null>(null);
  const [all, setAll] = useState(false);
  useEffect(() => { api("/capability").then((r) => setC(r.data)).catch(() => setC(null)); }, []);
  if (!c) return null;
  const groups = ["event", "player", "fielding", "geometry", "shot", "contact"];
  return (
    <section className="rule-section" data-testid="capability">
      <div className="eyebrow">What the data can and cannot support · field by field</div>
      <div className="statline"><div><b className="num">{c.counts.available}</b><span>✓ available</span></div><div><b className="num">{c.counts.partial}</b><span>△ partial</span></div>
        <div><b className="num">{c.counts.unavailable}</b><span>✕ unavailable</span></div></div>
      <p className="mini" style={{ fontSize: 13 }}>Cricsheet match-data licence: unresolved (no licence statement found; site footer &quot;All rights reserved&quot;), so everything is internal preview only.
        This is why some CRICINTEL features exist and others don&apos;t: there are no line, length, shot, edge, speed or tracking
        fields in any source we can use, so no feature depends on them. Evidence: {c.evidence}.</p>
      <div style={{ overflowX: "auto" }}><table className="capm"><tbody>
        {groups.map((g) => { const rows = c.fields.filter((f: any) => f.group === g); const show = all || g !== "geometry" ? rows : rows.slice(0, 4);
          return <React.Fragment key={g}><tr className="grp"><th colSpan={3}>{GROUP[g]}</th></tr>
            {show.map((f: any) => <tr key={f.field}><td className={`st ${f.status}`} aria-label={f.status}>{c.legend[f.status]}</td>
              <td><b>{f.field.replace(/_/g, " ")}</b><div className="mini">{f.coverage}</div>{f.notes && <div className="mini">{f.notes}</div>}</td>
              <td className="mini">{f.status === "unavailable" ? <>Unlock: {f.unlock || "a licensed source"}</> : <>{f.source.startsWith("Cricsheet") ? "Cricsheet" + (f.source.includes("derived") ? " (derived)" : "") : f.source.split(";")[0]}
                <br />Licence: {f.licence.startsWith("UNRESOLVED") ? "unresolved (see above)" : f.licence.split(";")[0]}<br />Usable now: {f.usable_now ? "yes" : "no"}</>}</td></tr>)}
            {!all && g === "geometry" && rows.length > 4 && <tr><td /><td colSpan={2}><button className="btn" onClick={() => setAll(true)}>Show all {rows.length} geometry fields</button></td></tr>}</React.Fragment>; })}
      </tbody></table></div>
      <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginTop: 8 }}><Link className="btn" href="/visual-lab">See it in the Visual Lab →</Link></div>
    </section>
  );
}
