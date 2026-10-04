"use client";
// "How does X get out?" (Dismissal DNA V2). A drill path: how out → by whom → format → phase → every dismissal.
// Filters exist only for recorded or derived facts. Line/length, shot and edge filters are listed as unavailable, with why.
import Link from "next/link";
import { useParams, useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";
import { api } from "@/lib/api";

export default function Page() { return <Suspense fallback={<div className="loading">Loading…</div>}><HowOut /></Suspense>; }

const DIM_LABEL: Record<string, string> = { route: "How out", bowler: "By bowler", format: "By format", phase: "By phase", style: "By bowling family" };

function HowOut() {
  const { id } = useParams<{ id: string }>();
  const sp = useSearchParams();
  const router = useRouter();
  const f = { route: sp.get("route"), bowler: sp.get("bowler"), format: sp.get("format"), phase: sp.get("phase"), style: sp.get("style") };
  const [d, setD] = useState<any | null>(null);
  const [name, setName] = useState<string>("");
  useEffect(() => { api(`/players/${id}/profile`).then((r) => setName(r.data.name)).catch(() => {}); }, [id]);
  useEffect(() => { api(`/visual/dismissals/${id}`, f as any).then((r) => setD(r.data)); /* eslint-disable-next-line react-hooks/exhaustive-deps */ }, [id, sp.toString()]);
  const set = (k: string, v: string | null) => {
    const q = new URLSearchParams(sp.toString());
    if (v) q.set(k, v); else q.delete(k);
    router.push(`/how-out/${id}?${q.toString()}`, { scroll: false });
  };
  if (!d) return <div className="loading">Loading…</div>;
  const labelFor = (dim: string, key: string) => d.tree[dim]?.find((x: any) => x.key === key)?.label ?? key;
  const order = ["route", "bowler", "format", "phase"].filter((k) => !(f as any)[k]);
  return (
    <div className="fade-in" style={{ marginTop: 18 }}>
      <div className="eyebrow">Dismissal DNA</div>
      <h1 className="display-xl" style={{ marginTop: 4 }} data-testid="howout-title">How does {name || "this player"} get out?</h1>
      <div className="drill" data-testid="drill">
        <button className={`crumb ${!Object.values(f).some(Boolean) ? "on" : ""}`} onClick={() => router.push(`/how-out/${id}`)}>All {d.total ? "" : ""}dismissals</button>
        {Object.entries(f).filter(([, v]) => v).map(([k, v]) => (
          <button key={k} className="crumb on" onClick={() => set(k, null)} aria-label={`Remove ${DIM_LABEL[k]}`}>{DIM_LABEL[k]}: {k === "bowler" ? (d.items[0]?.bowler ?? v) : k === "route" ? (labelFor("route", v!) || v) : v} ✕</button>))}
      </div>
      <div className="statline"><div><b className="num" data-testid="howout-total">{d.total}</b><span>dismissals in covered data</span></div>
        {d.keeper_unknown > 0 && <div><b className="num">{d.keeper_unknown}</b><span>caught, keeper status unknown</span></div>}</div>

      <div className="vgrid" style={{ marginTop: 10 }}>
        {order.slice(0, 3).map((dim) => (
          <section key={dim} className="mc-sec" data-testid={`dim-${dim}`}>
            <div className="eyebrow">{DIM_LABEL[dim]}</div>
            {d.tree[dim].map((x: any) => (
              <button key={x.key} className={`dbar ${x.key === "CAUGHT_KEEPER_STATUS_UNKNOWN" || x.key === "unknown" ? "unk" : ""}`} onClick={() => set(dim, x.key)}>
                <span className="lab">{x.label}<i className="bar" style={{ width: `${(100 * x.n) / Math.max(1, d.total)}%` }} /></span><span className="n">{x.n}</span></button>))}
          </section>))}
        <section className="mc-sec" data-testid="dim-style">
          <div className="eyebrow">By bowling family</div>
          {d.style_coverage.offered ? d.tree.style.map((x: any) => (
            <button key={x.key} className={`dbar ${x.key === "unknown" ? "unk" : ""}`} onClick={() => set("style", x.key)}>
              <span className="lab">{x.label}<i className="bar" style={{ width: `${(100 * x.n) / Math.max(1, d.total)}%` }} /></span><span className="n">{x.n}</span></button>))
            : <div className="notrec"><b>Not offered as a split</b><span>{d.style_coverage.note_offered}</span>
                <span className="mini">Bowling style comes only from CC0 Wikidata, which covers few bowlers. A split where most bowlers are unknown would mislead.</span></div>}
        </section>
      </div>

      {(f.route === "CAUGHT_KEEPER" || !f.route) && <div className="mini" style={{ marginTop: 10 }}>{d.keeper_note}</div>}

      <section className="rule-section" data-testid="unavailable-filters">
        <div className="eyebrow">Filters we cannot offer (yet)</div>
        <ul className="edge-list">{d.unavailable_filters.map((u: any) => <li key={u.filter}><b>{u.filter}</b>: {u.why}</li>)}</ul>
      </section>

      <section className="rule-section" data-testid="every-dismissal">
        <div className="eyebrow">Every dismissal{d.total > d.items.length ? ` (latest ${d.items.length} of ${d.total})` : ""}</div>
        <div className="tablist">{d.items.map((x: any) => (
          <Link key={x.delivery_id} href={`/delivery/${x.delivery_id}`} className="trow">
            <span className="n">{x.ball_label}</span>
            <span><b>{x.route_label}{x.fielder && x.route !== "CAUGHT_BOWLER" && !["BOWLED", "LBW"].includes(x.route) ? ` · ${x.fielder}` : ""} · b {x.bowler}</b>
              <div className="mini">{x.competition} · {x.start_date} · {x.format_group} · {x.phase} · on {x.batter_runs_before} ({x.batter_balls_before})</div></span>
            <span className="v">→</span></Link>))}</div>
      </section>
    </div>
  );
}
