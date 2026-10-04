"use client";
// Inspect any visual element: what it is, its provenance and what that means.
import { PROV_MEANING, VizElement } from "@/lib/viz/model";
import ProvBadge from "../Prov";

export default function ProvPanel({ el, onClose }: { el: VizElement | null; onClose?: () => void }) {
  if (!el) return <div className="mini prov-hint">Tap any element to see where it comes from.</div>;
  return (
    <div className="prov-panel fade-in" role="status">
      <div style={{ display: "flex", justifyContent: "space-between", gap: 8, alignItems: "center" }}>
        <b>{el.label}</b>
        <span style={{ display: "flex", gap: 6, alignItems: "center" }}><ProvBadge prov={el.prov} />{onClose && <button className="x" onClick={onClose} aria-label="Close">×</button>}</span>
      </div>
      <div className="mini" style={{ marginTop: 4 }}>{PROV_MEANING[el.prov]}</div>
      {el.detail && <div style={{ fontSize: 13, marginTop: 6 }}>{el.detail}</div>}
      {el.source && <div className="mini" style={{ marginTop: 4 }}>Source: {el.source}</div>}
    </div>
  );
}
