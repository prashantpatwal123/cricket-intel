"use client";
// CRICINTEL graphics system v1: reusable SVG primitives.
// Rules baked in:
//  - Provenance decides the stroke: OBSERVED solid · DERIVED dotted-blue accent · RECONSTRUCTED dashed amber · UNKNOWN hatched.
//  - EventConnector shows WHO was involved in an event. It is never a ball trajectory, and it animates by "drawing in"
//    once rather than travelling like a ball.
//  - Unknown positions are zones (UnknownZone), never points.
import React from "react";

export type ProvState = "OBSERVED" | "DERIVED" | "RECONSTRUCTED" | "MODELLED" | "ILLUSTRATIVE" | "UNKNOWN";

export const C = {
  turf1: "#15553f", turf2: "#0b2c22", line: "#2b6b52", pitch: "#c9b48a", crease: "#ffffff", text: "#edf2fc", muted: "#8d9ab8",
  accent: "#35e0c2", wicket: "#ff5c74", amber: "#ffb547", derived: "#7cc4ff",
};

export const provStroke = (p: ProvState) => ({
  OBSERVED: { stroke: C.text, dash: undefined, opacity: 0.9 },
  DERIVED: { stroke: C.derived, dash: "2 4", opacity: 0.95 },
  RECONSTRUCTED: { stroke: C.amber, dash: "6 5", opacity: 0.95 },
  MODELLED: { stroke: "#c49bff", dash: "1 3", opacity: 0.9 },
  ILLUSTRATIVE: { stroke: C.muted, dash: "4 4", opacity: 0.6 },
  UNKNOWN: { stroke: C.muted, dash: "2 6", opacity: 0.5 },
}[p]);

export function Defs({ id = "ci" }: { id?: string }) {
  return (
    <defs>
      <radialGradient id={`${id}-turf`} cx="50%" cy="45%" r="60%">
        <stop offset="0%" stopColor={C.turf1} /><stop offset="100%" stopColor={C.turf2} />
      </radialGradient>
      <pattern id={`${id}-mow`} width="40" height="40" patternUnits="userSpaceOnUse" patternTransform="rotate(90)">
        <rect width="20" height="40" fill="#ffffff05" />
      </pattern>
      <pattern id={`${id}-hatch`} width="7" height="7" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
        <line x1="0" y1="0" x2="0" y2="7" stroke={C.wicket} strokeWidth="2" opacity=".55" />
      </pattern>
      <pattern id={`${id}-hatch-muted`} width="6" height="6" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
        <line x1="0" y1="0" x2="0" y2="6" stroke={C.muted} strokeWidth="1.5" opacity=".6" />
      </pattern>
      <marker id={`${id}-arrow`} viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
        <path d="M 0 0 L 10 5 L 0 10 z" fill={C.amber} />
      </marker>
    </defs>
  );
}

export function Field({ cx, cy, rx, ry, id = "ci", inner = true }: { cx: number; cy: number; rx: number; ry: number; id?: string; inner?: boolean }) {
  return (
    <g>
      <ellipse cx={cx} cy={cy} rx={rx} ry={ry} fill={`url(#${id}-turf)`} stroke={C.line} strokeWidth={2} />
      <ellipse cx={cx} cy={cy} rx={rx} ry={ry} fill={`url(#${id}-mow)`} />
      {inner && <ellipse cx={cx} cy={cy} rx={rx * 0.575} ry={ry * 0.575} fill="none" stroke="#ffffff22" strokeDasharray="3 6" />}
    </g>
  );
}

export function Pitch({ x, top, bottom, width = 30 }: { x: number; top: number; bottom: number; width?: number }) {
  return <rect x={x - width / 2} y={top} width={width} height={bottom - top} rx={3} fill={C.pitch} opacity={0.88} />;
}

export function Crease({ x, y, half = 22 }: { x: number; y: number; half?: number }) {
  return <line x1={x - half} x2={x + half} y1={y} y2={y} stroke={C.crease} strokeWidth={1.5} opacity={0.9} />;
}

export function Stumps({ x, y, broken = false, size = 1 }: { x: number; y: number; broken?: boolean; size?: number }) {
  return (
    <g className={broken ? "stumps-broken" : undefined}>
      {[-4, 0, 4].map((dx) => <rect key={dx} x={x + dx * size - 1} y={y - 1} width={2 * size} height={7 * size} fill="#fff" />)}
      {broken && <><line x1={x - 6} y1={y - 4} x2={x - 1} y2={y - 2} stroke={C.wicket} strokeWidth={2} /><line x1={x + 1} y1={y - 2} x2={x + 6} y2={y - 5} stroke={C.wicket} strokeWidth={2} /></>}
    </g>
  );
}

export type FigureRole = "batter" | "bowler" | "keeper" | "fielder";
export function Figure({ x, y, role, unknownHand = false, label }: { x: number; y: number; role: FigureRole; unknownHand?: boolean; label?: string }) {
  const fill = role === "keeper" ? C.derived : role === "fielder" ? "#b8c4dd" : unknownHand && role === "batter" ? C.muted : C.text;
  return (
    <g>
      {role === "batter" ? (<><circle cx={x} cy={y - 10} r={6} fill={fill} /><rect x={x - 5} y={y - 4} width={10} height={14} rx={4} fill={fill} /></>)
        : <circle cx={x} cy={y} r={role === "fielder" ? 4 : 5} fill={fill} />}
      {label && <text x={x} y={y + (role === "batter" ? 24 : 16)} textAnchor="middle" fontSize={10} fill={C.text}>{label}</text>}
    </g>
  );
}

export function Ball({ x, y, r = 3.5 }: { x: number; y: number; r?: number }) {
  return <circle cx={x} cy={y} r={r} fill="#d93a3a" stroke="#fff" strokeWidth={0.8} />;
}

/** Who-was-involved connector. NOT a trajectory: straight/curved line that draws in once, with provenance styling. */
export function EventConnector({ x1, y1, x2, y2, prov = "OBSERVED", curve = 0, arrow = false, animate = true }:
  { x1: number; y1: number; x2: number; y2: number; prov?: ProvState; curve?: number; arrow?: boolean; animate?: boolean }) {
  const s = provStroke(prov);
  const mx = (x1 + x2) / 2 + curve, my = (y1 + y2) / 2;
  return (
    <path d={`M ${x1} ${y1} Q ${mx} ${my} ${x2} ${y2}`} fill="none" stroke={s.stroke} strokeWidth={1.6} strokeDasharray={s.dash}
          opacity={s.opacity} markerEnd={arrow ? "url(#ci-arrow)" : undefined}
          className={animate ? (s.dash ? "fade-svg" : "draw-in") : undefined} pathLength={s.dash ? undefined : 1} />
  );
}

/** A region where something happened but the exact position is unknown. Always a zone, never a point. */
export function UnknownZone({ cx, cy, rx, ry, width, id = "ci", label, color = "wicket" }:
  { cx: number; cy: number; rx: number; ry: number; width: number; id?: string; label?: string; color?: "wicket" | "muted" }) {
  return (
    <g>
      <ellipse cx={cx} cy={cy} rx={rx} ry={ry} fill="none" stroke={`url(#${id}-${color === "wicket" ? "hatch" : "hatch-muted"})`} strokeWidth={width} />
      {label && <text x={cx} y={cy - ry - width / 2 - 6} textAnchor="middle" fontSize={10} fill={C.muted}>{label}</text>}
    </g>
  );
}

/** Count bubble used by dismissal graphics. */
export function CountNode({ x, y, r, n, active, dim, onClick, ariaLabel }:
  { x: number; y: number; r: number; n: number; active?: boolean; dim?: boolean; onClick?: () => void; ariaLabel: string }) {
  return (
    <g className="node" opacity={dim ? 0.28 : 1} onClick={onClick} role="button" aria-label={ariaLabel} tabIndex={0}
       onKeyDown={(e) => (e.key === "Enter" || e.key === " ") && onClick?.()}>
      <circle className={active ? "halo pulse" : "halo"} cx={x} cy={y} r={r + 7} fill={active ? C.wicket : "#fff"} opacity={active ? 0.25 : 0.06} />
      <circle cx={x} cy={y} r={r} fill={n ? (active ? C.wicket : "#0b1324") : "#0b132499"} stroke={n ? C.wicket : "#5d6a88"} strokeWidth={active ? 0 : 2} />
      <text x={x} y={y + 6} textAnchor="middle" fontSize={n ? 17 : 12} fontWeight={800} fill={active ? "#0b1020" : C.text}
            style={{ fontFamily: "var(--display)" }}>{n}</text>
    </g>
  );
}
