"use client";
// Aggregate -> evidence. Lists the deliveries behind a number; tapping one opens the delivery card + scene.
import { useEffect, useState } from "react";
import { createPortal } from "react-dom";
import { api, Params } from "@/lib/api";
import Link from "next/link";
import DeliveryScene from "./viz/DeliveryScene";
import MatchSituation from "./viz/MatchSituation";
import { deliveryModel } from "@/lib/viz/model";

export function outcomeText(d: any) {
  const w = d.wickets?.[0];
  if (w) return w.route_label;
  const r = d.runs;
  if (r.six) return "SIX"; if (r.four) return "FOUR";
  if (r.wides) return `Wide +${r.extras}`; if (r.noballs) return `No-ball +${r.total}`;
  if (r.byes || r.legbyes) return `${r.extras} ${r.byes ? "bye" : "leg-bye"}`;
  return r.total === 0 ? "Dot" : `${r.batter} run${r.batter === 1 ? "" : "s"}`;
}

export default function Deliveries({ title, query, onClose }: { title: string; query: Params; onClose: () => void }) {
  const [data, setData] = useState<any | null>(null);
  const [offset, setOffset] = useState(0);
  const [open, setOpen] = useState<string | null>(null);
  useEffect(() => { setOffset(0); }, [JSON.stringify(query)]);
  useEffect(() => {
    api("/deliveries", { ...query, offset, limit: 20 }).then((r) => setData((prev: any) =>
      offset === 0 || !prev ? r.data : { ...r.data, deliveries: [...prev.deliveries, ...r.data.deliveries] }));
  }, [JSON.stringify(query), offset]);
  return (
    <div className="sheet fade-in" id="evidence">
      <div className="section-head" style={{ marginBottom: 0 }}>
        <div>
          <div className="kicker" style={{ color: "#ff8a9b" }}>Evidence</div>
          <div className="h2" style={{ fontSize: 22 }}>{title}</div>
          <div className="mini">{data ? `${data.total} deliveries · newest first · tap one to inspect` : "Loading…"}</div>
        </div>
        <button className="btn" onClick={onClose}>Close</button>
      </div>
      <div className="dlist">
        {data?.deliveries.map((d: any) => (
          <button key={d.delivery_id} className="dcard" onClick={() => setOpen(d.delivery_id)}>
            <div className="ob num">{d.over_ball}</div>
            <div>
              <span className={`pill ${d.wickets?.length ? "" : "runs"}`}>{outcomeText(d)}</span>
              <div className="dmain">{d.bowler.name} <span className="mini">to</span> {d.batter.name}</div>
              <div className="dmeta">{d.date} · {d.batting_team} v {d.bowling_team} · inns {d.innings_no} · {d.score_before}
                {d.context.chasing && d.context.runs_required != null ? ` · needed ${d.context.runs_required} off ${d.context.balls_remaining}` : ""}</div>
              {d.wickets?.[0]?.fielders?.length ? <div className="dmeta">fielder: {d.wickets[0].fielders.map((f: any) => `${f.name} (${f.role})`).join(", ")}</div> : null}
            </div>
          </button>
        ))}
        {data && data.deliveries.length < data.total && (
          <button className="btn" onClick={() => setOffset(data.deliveries.length)}>Load more ({data.total - data.deliveries.length} left)</button>
        )}
        {data && data.total === 0 && <div className="empty">No deliveries match.</div>}
      </div>
      {open && <DeliveryModal id={open} onClose={() => setOpen(null)} />}
    </div>
  );
}

export function DeliveryModal({ id, onClose }: { id: string; onClose: () => void }) {
  const [d, setD] = useState<any | null>(null);
  useEffect(() => { api(`/deliveries/${encodeURIComponent(id)}/replay`).then((r) => setD(r.data)); }, [id]);
  useEffect(() => {
    const k = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", k); return () => window.removeEventListener("keydown", k);
  }, [onClose]);
  if (typeof document === "undefined") return null;
  return createPortal(
    <div className="modal-bg" onClick={onClose}>
      <div className="modal fade-in" onClick={(e) => e.stopPropagation()} role="dialog" aria-modal="true">
        {!d ? <div className="loading">Loading delivery…</div> : (
          <>
            <div className="section-head">
              <div>
                <div className="kicker">{d.match.competition} · {d.match.start_date}</div>
                <div className="h2" style={{ fontSize: 24 }}>{d.over_ball} · {d.bowler.name} to {d.batter.name}</div>
                <div className="mini">{d.batting_team} v {d.bowling_team} · {d.match.venue} · innings {d.innings_no} · {d.match.result_line}</div>
              </div>
              <button className="btn" onClick={onClose}>Close</button>
            </div>
            <MatchSituation compact s={{ ...d.situation, recent: d.recent.map((x: any) => x.symbol), next_ball: d.over_ball }} />
            <div style={{ marginTop: 12 }}><DeliveryScene model={deliveryModel(d)} compact /></div>
            <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginTop: 12 }}>
              <Link className="btn primary" href={`/delivery/${encodeURIComponent(d.delivery_id)}`}>Open full replay →</Link>
              <Link className="btn" href={`/innings/${d.links.innings.match_id}/${d.links.innings.innings_no}/${d.links.innings.batter_id}?ball=${encodeURIComponent(d.delivery_id)}`}>Innings story →</Link>
            </div>
          </>
        )}
      </div>
    </div>,
    document.body
  );

}
