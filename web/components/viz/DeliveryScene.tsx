"use client";
// Delivery Scene + Dismissal Theatre. Figures sit in standard slots (ILLUSTRATIVE). Nothing is drawn between bowler and
// batter: there is no ball path, pitch point, line, length or shot in the data. The event itself is shown as a chain
// beside the pitch (who → what → outcome → who was credited), so it can't be mistaken for a trajectory.
import { useState } from "react";
import { DeliveryModel, VizElement } from "@/lib/viz/model";
import { C, Crease, Defs, Figure, Pitch, Stumps, UnknownZone } from "../cricket/primitives";
import ProvPanel from "./ProvPanel";

const W = 300, H = 380, CX = 150;
const Y = { bowlerStumps: 70, strikerStumps: 300, bowler: 40, nonStriker: 92, striker: 290, keeper: 336 };

export default function DeliveryScene({ model, compact = false }: { model: DeliveryModel; compact?: boolean }) {
  const [sel, setSel] = useState<VizElement | null>(null);
  const el = (id: string) => model.elements.find((e) => e.id === id)!;
  const pick = (e?: VizElement) => e && setSel(sel?.id === e.id ? null : e);
  const hi = (id: string) => (el(id)?.emphasis ? 1 : model.dismissal ? 0.45 : 1);
  const tap = (id: string) => ({ onClick: () => pick(el(id)), style: { cursor: "pointer" }, role: "button", "aria-label": el(id)?.label, tabIndex: 0,
    onKeyDown: (k: React.KeyboardEvent) => (k.key === "Enter" || k.key === " ") && pick(el(id)) });
  const z = model.elements.find((e) => e.kind === "zone");
  const broken = el("stumps_striker").prov === "OBSERVED";
  return (
    <div className={`dscene ${compact ? "compact" : ""}`}>
      <div className="dscene-grid">
        <svg viewBox={`0 0 ${W} ${H}`} className="dscene-svg" role="img" aria-label="Delivery scene: schematic, no ball path">
          <Defs />
          <ellipse cx={CX} cy={190} rx={140} ry={176} fill="url(#ci-turf)" stroke={C.line} />
          <g {...tap("pitch")} opacity={0.95}><Pitch x={CX} top={Y.bowlerStumps - 14} bottom={Y.strikerStumps + 14} width={34} /></g>
          <Crease x={CX} y={Y.bowlerStumps + 18} /><Crease x={CX} y={Y.strikerStumps - 18} />
          <g {...tap("stumps_bowler")}><Stumps x={CX} y={Y.bowlerStumps - 4} /></g>
          <g {...tap("stumps_striker")} opacity={hi("stumps_striker")}><Stumps x={CX} y={Y.strikerStumps - 4} broken={broken} /></g>
          {z?.id === "fielder_zone" && <g {...tap("fielder_zone")}><UnknownZone cx={CX} cy={190} rx={124} ry={160} width={12} label="" /></g>}
          {z?.id === "runout_zone" && <g {...tap("runout_zone")}>
            <rect x={CX - 40} y={Y.bowlerStumps + 8} width={80} height={20} fill="url(#ci-hatch)" opacity={0.9} />
            <rect x={CX - 40} y={Y.strikerStumps - 28} width={80} height={20} fill="url(#ci-hatch)" opacity={0.9} /></g>}
          <g {...tap("bowler")} opacity={hi("bowler")}><Figure x={CX + 26} y={Y.bowler} role="bowler" /></g>
          <g {...tap("non_striker")} opacity={hi("non_striker")}><Figure x={CX - 30} y={Y.nonStriker + 10} role="batter" unknownHand /></g>
          <g {...tap("striker")} opacity={hi("striker")}><Figure x={CX + 22} y={Y.striker} role="batter" unknownHand /></g>
          <g {...tap("keeper")} opacity={hi("keeper")}>
            {el("keeper").prov === "UNKNOWN"
              ? <circle cx={CX} cy={Y.keeper} r={7} fill="none" stroke={C.muted} strokeDasharray="2 3" />
              : <Figure x={CX} y={Y.keeper} role="keeper" />}
          </g>
          <text x={CX + 40} y={Y.bowler + 4} fontSize={11} fill={C.text}>{short(el("bowler").label)}</text>
          <text x={CX - 44} y={Y.nonStriker + 14} fontSize={11} fill={C.muted} textAnchor="end">{short(el("non_striker").label)}</text>
          <text x={CX + 36} y={Y.striker - 4} fontSize={11} fill={C.text}>{short(el("striker").label)}</text>
          {z?.id === "fielder_zone" && <text x={CX} y={26} textAnchor="middle" fontSize={11} fill="#ffd0d8">{z.label}</text>}
          <text x={8} y={H - 8} fontSize={11} fill={C.muted}>Schematic · no ball path recorded</text>
        </svg>
        <div>
          <div className="chain" aria-label="What happened, in order">
            {model.chain.map((c, i) => (
              <span key={c.id} className="chain-step">
                <button className={`chain-node ${c.kind} ${c.emphasis ? "em" : ""} ${c.label.startsWith("OUT") ? "out" : ""} ${sel?.id === c.id ? "on" : ""}`}
                        onClick={() => pick(c)}><span className={`pdot ${c.prov}`} />{c.label}</button>
                {i < model.chain.length - 1 && <span className="chain-arrow" aria-hidden>→</span>}
              </span>
            ))}
          </div>
          {model.dismissal && <div className="theatre fade-in"><div className="kicker" style={{ color: "#ff8a9b" }}>Dismissal theatre</div><div style={{ fontSize: 13.5, marginTop: 4 }}>{model.dismissal.theatre}</div></div>}
          <ProvPanel el={sel} onClose={() => setSel(null)} />
          {!compact && <div className="unk-list"><span className="mini">Not recorded for any delivery in this data:</span> {model.unknowns.map((u) => <span key={u} className="chip unknown">{u}</span>)}</div>}
        </div>
      </div>
    </div>
  );
}

const short = (n: string) => n.length > 18 ? n.split(" ").slice(-1)[0] : n;
