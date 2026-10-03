"use client";
// Reconstruction v0: renders a SceneSpec (scene/v0) from the API.
// Draws only what the spec contains; every element keeps its provenance styling.
// Future tracking/shot/fielding data arrive as additional OBSERVED elements, with no component redesign.
import ProvBadge from "./Prov";

const W = 300, H = 430, CX = 150, TOP = 52, BAT = 342, KEEP = 392, PITCH_M = 20.12;
const yOf = (m: number) => BAT - (m / PITCH_M) * (BAT - TOP);

function anchor(name: string, hand: string): [number, number] {
  const side = hand === "left" ? 1 : -1;
  switch (name) {
    case "bowler": return [CX, TOP - 22];
    case "batter": return [CX + side * 13, BAT - 12];
    case "batter_pad": return [CX + side * 8, BAT - 6];
    case "stumps_batter": return [CX, BAT + 2];
    case "keeper": return [CX, KEEP];
    case "field_ring": return [W - 30, 120];
    default: return [CX, 200];
  }
}

const COLORS: Record<string, string> = {
  OBSERVED: "#edf2fc", DERIVED: "#7cc4ff", RECONSTRUCTED: "#ffb547", MODELLED: "#c49bff", ILLUSTRATIVE: "#8d9ab8", UNKNOWN: "#6b7795",
};

export default function Scene({ scene }: { scene: any }) {
  const els: any[] = scene.elements;
  const batter = els.find((e) => e.kind === "batter");
  const hand = batter?.hand || "unknown";
  const legSign = hand === "left" ? 1 : -1; // leg side on screen (bowler at top): RHB leg side = screen left
  return (
    <div>
      <div className={scene.overall_prov === "RECONSTRUCTED" ? "banner-rec" : "mini"}>{scene.banner}</div>
      <div style={{ display: "grid", gridTemplateColumns: "minmax(0, 300px) 1fr", gap: 16, marginTop: 12, alignItems: "start" }} className="scene-grid">
        <svg viewBox={`0 0 ${W} ${H}`} style={{ width: "100%", maxWidth: 300, background: "#0b2c22", borderRadius: 16, border: "1px solid #233154" }}
             role="img" aria-label="Delivery reconstruction">
          <defs>
            <marker id="arr" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
              <path d="M 0 0 L 10 5 L 0 10 z" fill="#ffb547" />
            </marker>
            <pattern id="hatch2" width="6" height="6" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
              <line x1="0" y1="0" x2="0" y2="6" stroke="#8d9ab8" strokeWidth="1.5" opacity=".6" />
            </pattern>
          </defs>
          {/* pitch (illustrative standard geometry) */}
          <rect x={CX - 32} y={TOP} width={64} height={BAT - TOP + 10} fill="#c9b48a" opacity={0.92} rx={2} />
          <line x1={CX - 40} x2={CX + 40} y1={BAT - 22} y2={BAT - 22} stroke="#fff" strokeWidth={2} />
          <line x1={CX - 40} x2={CX + 40} y1={TOP + 22} y2={TOP + 22} stroke="#fff" strokeWidth={2} />
          {[BAT, TOP].map((y, i) => <g key={i}>{[-5, 0, 5].map((dx) => <rect key={dx} x={CX + dx - 1.5} y={y - 4} width={3} height={10} fill="#fff" />)}</g>)}
          {els.map((e, i) => <El key={i} e={e} hand={hand} legSign={legSign} />)}
          {/* figures */}
          <g>
            {(() => { const [x, y] = anchor("batter", hand); return <><circle cx={x} cy={y - 10} r={7} fill={hand === "unknown" ? "#8d9ab8" : "#edf2fc"} /><rect x={x - 6} y={y - 3} width={12} height={16} rx={5} fill={hand === "unknown" ? "#8d9ab8" : "#edf2fc"} /></>; })()}
            {(() => { const [x, y] = anchor("bowler", hand); return <circle cx={x} cy={y} r={7} fill="#edf2fc" />; })()}
            {els.some((e) => e.kind === "keeper") && (() => { const [x, y] = anchor("keeper", hand); return <circle cx={x} cy={y} r={7} fill="#7cc4ff" />; })()}
          </g>
          <text x={CX} y={TOP - 36} textAnchor="middle" fontSize={10} fill="#edf2fc">{els.find((e) => e.kind === "bowler")?.name}</text>
          <text x={CX + 52} y={BAT + 16} fontSize={10} fill="#edf2fc">{batter?.name}</text>
          <text x={8} y={H - 8} fontSize={9} fill="#8d9ab8">Pitch geometry illustrative · not to scale laterally</text>
        </svg>
        <div>
          <dl className="kv">
            {scene.facts.map((f: any, i: number) => (
              <div key={i} style={{ display: "contents" }}><dt>{f.label}</dt><dd>{f.value} <ProvBadge prov={f.prov} /></dd></div>
            ))}
          </dl>
          <div className="mini" style={{ marginTop: 14, fontWeight: 700 }}>Not in our data for this delivery</div>
          <div className="unk-chips">
            {scene.unknowns.map((u: any) => <span key={u.key} className="chip unknown">{u.label} <ProvBadge prov="UNKNOWN" /></span>)}
          </div>
          <div className="mini" style={{ marginTop: 14 }}>
            {els.filter((e) => e.note && !["pitch", "stumps"].includes(e.kind)).map((e, i) => (
              <div key={i} style={{ marginTop: 4 }}><ProvBadge prov={e.prov} /> {e.note}</div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

function El({ e, hand, legSign }: { e: any; hand: string; legSign: number }) {
  const c = COLORS[e.prov] || "#fff";
  if (e.kind === "path") {
    const [x1, y1] = anchor(e.frm, hand); const [x2, y2] = anchor(e.to, hand);
    const mx = (x1 + x2) / 2 + (e.to === "keeper" ? 18 : e.to === "field_ring" ? 30 : 10), my = (y1 + y2) / 2;
    return <path d={`M ${x1} ${y1} Q ${mx} ${my} ${x2} ${y2}`} fill="none" stroke={c} strokeWidth={2.2} strokeDasharray="6 5" markerEnd="url(#arr)" opacity={0.95} />;
  }
  if (e.kind === "impact") {
    const [x, y] = anchor(e.at, hand);
    return <g><circle cx={x} cy={y} r={11} fill="none" stroke="#ff5c74" strokeWidth={2.5} /><circle cx={x} cy={y} r={4} fill="#ff5c74" /></g>;
  }
  if (e.kind === "catch") {
    const [x, y] = anchor(e.at, hand);
    return <g><circle cx={x} cy={y} r={13} fill="none" stroke="#ff5c74" strokeWidth={2.5} strokeDasharray={e.prov === "DERIVED" ? "4 3" : "0"} /><text x={x} y={y + 4} textAnchor="middle" fontSize={10} fontWeight={800} fill="#ff5c74">C</text></g>;
  }
  if (e.kind === "projection") {
    const [x1, y1] = anchor(e.frm, hand); const [x2, y2] = anchor(e.to, hand);
    return <line x1={x1} y1={y1} x2={x2} y2={y2} stroke={c} strokeWidth={2} strokeDasharray="2 3" />;
  }
  if (e.kind === "constraint" && e.zone === "outside_leg_excluded") {
    if (hand === "unknown") return null; // leg side unknown without batting hand; constraint listed in text only
    const x = legSign < 0 ? CX - 32 : CX + 7;
    return <g><rect x={x} y={TOP + 30} width={25} height={BAT - TOP - 60} fill="url(#hatch2)" /><text x={x + 12} y={TOP + 26} textAnchor="middle" fontSize={8.5} fill="#7cc4ff">no pitch</text></g>;
  }
  if (e.kind === "unknown_zone") {
    if (e.zone === "both_ends") return <g>{[BAT, TOP].map((y, i) => <text key={i} x={CX + 26} y={y + 6} fontSize={18} fontWeight={900} fill="#ffb547">?</text>)}</g>;
    return <g><rect x={4} y={4} width={W - 8} height={H - 8} rx={14} fill="none" stroke="url(#hatch2)" strokeWidth={12} />
      <text x={W - 30} y={124} textAnchor="middle" fontSize={20} fontWeight={900} fill="#ffb547">?</text></g>;
  }
  if (e.kind === "pitch_point" && typeof e.x === "number") {
    return <circle cx={CX + e.x * 22} cy={yOf(e.y)} r={5} fill={c} />;
  }
  return null;
}
