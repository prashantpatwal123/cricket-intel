"use client";
// Graphical component library (Phase 6). Contract for every component:
//  * accepts partial data; renders with Layer 0 alone;
//  * if a layer it needs is absent it renders an explicit, sparse "not recorded" state: never placeholder geometry;
//  * every mark that encodes data carries provenance (tooltip + "Why am I seeing this?");
//  * ILLUSTRATIVE content is drawn in a distinct hatched/dashed style under a diagonal watermark and takes no player ids;
//  * an accessible text equivalent (aria-label + visible caption) accompanies every graphic.
import React from "react";
import type { BallGeom, Layer, Provenance } from "@/lib/visual";
import { ILLUSTRATIVE_NOTE, LENGTHS, LINES } from "@/lib/visual";

const PCOL: Record<string, string> = { OBSERVED: "#35e0c2", DERIVED: "#7cc4ff", RECONSTRUCTED: "#ffb547", MODELLED: "#c49bff", ILLUSTRATIVE: "#9aa4bd" };

export function Why({ p }: { p?: Provenance | null }) {
  if (!p) return null;
  return (
    <details className="why"><summary><span className="pdot" style={{ background: PCOL[p.provenance_type] }} />{p.provenance_type} · why am I seeing this?</summary>
      <div>{p.why}</div>{p.source_event_id && <div className="mini">Event: {p.source_event_id}</div>}</details>
  );
}

export function NotRecorded({ what, why, unlock }: { what: string; why?: string; unlock?: string }) {
  return (
    <div className="notrec" role="note" aria-label={`${what}: not recorded`}>
      <b>{what}: not recorded</b>{why && <span>{why}</span>}{unlock && <span className="mini">Would need: {unlock}</span>}
    </div>
  );
}

function Illus({ children, label }: { children: React.ReactNode; label: string }) {
  return (
    <figure className="illus" aria-label={`${label}. ${ILLUSTRATIVE_NOTE}`}>
      <div className="illus-mark" aria-hidden>ILLUSTRATIVE · NOT REAL DATA</div>
      {children}
      <figcaption className="mini">{ILLUSTRATIVE_NOTE}</figcaption>
    </figure>
  );
}

// ---------------------------------------------------------------- Layer ladder ("Available data")
export function LayerLadder({ layers }: { layers: Layer[] }) {
  return (
    <ol className="ladder" aria-label="Data layers available for this delivery">
      {layers.map((l) => (
        <li key={l.layer} className={l.available ? "on" : "off"}>
          <span className="lc">{l.layer}</span>
          <span className="ln"><b>{l.name}</b>{l.available ? (l.partial ? " · partial" : " · recorded") : " · not recorded"}
            {!l.available && l.why_missing && <span className="mini">{l.why_missing}</span>}
            {l.missing && l.missing.length > 0 && <span className="mini">Missing here: {l.missing.map((m) => m.replace(/_/g, " ")).join(", ")}</span>}</span>
          <span className="lm">{l.available ? "✓" : "✕"}</span>
        </li>))}
    </ol>
  );
}

// ---------------------------------------------------------------- Pitch map (bowler → batter, canonical coordinates)
const PL = 20.12, PW = 3.05;
export function PitchMap({ balls, hand, illustrative, title = "Pitch map" }: { balls: BallGeom[]; hand?: "right" | "left" | null; illustrative?: boolean; title?: string }) {
  const pts = balls.filter((b) => b.pitch_x != null && b.pitch_y != null);
  const W = 200, H = 420, sx = (x: number) => W / 2 + (x / (PW * 1.6)) * W, sy = (y: number) => H - 30 - (y / PL) * (H - 50);
  const svg = (
    <svg viewBox={`0 0 ${W} ${H}`} className="vsvg" role="img" aria-label={`${title}: ${pts.length} pitch points${hand ? `, ${hand}-handed batter` : ""}`}>
      <rect x={sx(-PW / 2)} y={sy(PL)} width={sx(PW / 2) - sx(-PW / 2)} height={sy(0) - sy(PL)} fill="#3b3323" stroke="#6b5a3a" />
      <line x1={sx(-1.32)} x2={sx(1.32)} y1={sy(1.22)} y2={sy(1.22)} stroke="#e8dcc0" strokeWidth={1.5} />
      <line x1={sx(-1.32)} x2={sx(1.32)} y1={sy(PL - 1.22)} y2={sy(PL - 1.22)} stroke="#e8dcc0" strokeWidth={1.5} />
      <text x={W / 2} y={H - 8} textAnchor="middle" fontSize={10} fill="#8d9ab8">batter&apos;s end</text>
      <text x={W / 2} y={14} textAnchor="middle" fontSize={10} fill="#8d9ab8">bowler&apos;s end</text>
      {hand && <><text x={6} y={H - 36} fontSize={9} fill="#8d9ab8">{hand === "right" ? "leg" : "off"}</text><text x={W - 6} y={H - 36} fontSize={9} fill="#8d9ab8" textAnchor="end">{hand === "right" ? "off" : "leg"}</text></>}
      {pts.map((b, i) => <circle key={i} cx={sx(b.pitch_x!)} cy={sy(b.pitch_y!)} r={b.wicket ? 6 : 4} fill={b.wicket ? "#ff5c74" : b.boundary ? "#35e0c2" : "#7cc4ff"}
        fillOpacity={illustrative ? 0.35 : 0.9} stroke={illustrative ? "#cfd6e6" : "none"} strokeDasharray={illustrative ? "2 2" : undefined}>
        <title>{`${b.length ?? ""} ${b.line ?? ""}`}</title></circle>)}
    </svg>);
  if (illustrative) return <Illus label={title}>{svg}</Illus>;
  if (!pts.length) return <NotRecorded what="Pitch points" why="No source available to CRICINTEL records where a ball pitched." unlock="ball-tracking-derived or coded pitch coordinates" />;
  return svg;
}

// ---------------------------------------------------------------- Line & length map
export function LineLengthMap({ balls, illustrative, metric = "count", title = "Line & length" }: { balls: BallGeom[]; illustrative?: boolean; metric?: "count" | "sr"; title?: string }) {
  const g = balls.filter((b) => b.line && b.length);
  if (!g.length && !illustrative) return <NotRecorded what="Line and length" why="Not recorded in Cricsheet, and never inferred from outcomes." unlock="a licensed feed with coded or tracked line/length" />;
  const cell = (l: string, n: string) => g.filter((b) => b.line === l && b.length === n);
  const max = Math.max(1, ...LINES.flatMap(([l]) => LENGTHS.map(([n]) => cell(l, n).length)));
  const grid = (
    <div className="llgrid" role="table" aria-label={`${title}: ${g.length} balls`}>
      <div className="llh" />{LINES.map(([, lab]) => <div key={lab} className="llh">{lab}</div>)}
      {LENGTHS.map(([n, nl]) => (
        <React.Fragment key={n}><div className="llh r">{nl}</div>
          {LINES.map(([l]) => { const c = cell(l, n); const runs = c.reduce((a, b) => a + (b.runs || 0), 0);
            const v = metric === "sr" ? (c.length ? Math.round((100 * runs) / c.length) : null) : c.length;
            return <div key={l} className={`llc ${illustrative ? "ill" : ""}`} style={{ background: `rgba(53,224,194,${c.length / max * 0.8})` }}
              title={`${c.length} balls${c.some((b) => b.wicket) ? `, ${c.filter((b) => b.wicket).length} wkt` : ""}`}>{c.length ? v : ""}{c.some((b) => b.wicket) ? "•" : ""}</div>; })}
        </React.Fragment>))}
    </div>);
  return illustrative ? <Illus label={title}>{grid}</Illus> : grid;
}

// ---------------------------------------------------------------- Wagon / field map (only with real direction data)
export function WagonMap({ balls, illustrative, title = "Wagon wheel" }: { balls: BallGeom[]; illustrative?: boolean; title?: string }) {
  const d = balls.filter((b) => b.direction_deg != null);
  if (!d.length && !illustrative) return <NotRecorded what="Shot direction" why="Cricsheet records that a boundary happened, not where the ball went." unlock="a licensed feed with wagon-wheel angles" />;
  const R = 90, C = 100;
  const svg = (
    <svg viewBox="0 0 200 200" className="vsvg" role="img" aria-label={`${title}: ${d.length} shots with direction`}>
      <circle cx={C} cy={C} r={R} fill="#123a26" stroke="#2d5a3f" /><rect x={C - 4} y={C - 14} width={8} height={28} fill="#8a7550" />
      {d.map((b, i) => { const a = ((b.direction_deg! - 90) * Math.PI) / 180, len = b.boundary ? R : R * 0.55;
        return <line key={i} x1={C} y1={C} x2={C + len * Math.cos(a)} y2={C + len * Math.sin(a)} stroke={b.boundary === 6 ? "#9df26b" : b.boundary === 4 ? "#35e0c2" : "#7cc4ff"}
          strokeWidth={2} strokeDasharray={illustrative ? "4 3" : undefined} opacity={illustrative ? 0.6 : 0.9} />; })}
    </svg>);
  return illustrative ? <Illus label={title}>{svg}</Illus> : svg;
}

// ---------------------------------------------------------------- Shot atlas
export function ShotAtlas({ balls, illustrative, title = "Shot atlas" }: { balls: BallGeom[]; illustrative?: boolean; title?: string }) {
  const s = balls.filter((b) => b.shot);
  if (!s.length && !illustrative) return <NotRecorded what="Shot type" why="No shot labels exist in any source available to CRICINTEL." unlock="a licensed coded feed with shot labels" />;
  const by = new Map<string, BallGeom[]>(); s.forEach((b) => by.set(b.shot!, [...(by.get(b.shot!) || []), b]));
  const t = (
    <table className="atlas" aria-label={title}><thead><tr><th>Shot</th><th>Balls</th><th>Runs</th><th>SR</th><th>4/6</th><th>Out</th></tr></thead>
      <tbody>{[...by.entries()].sort((a, b) => b[1].length - a[1].length).map(([k, v]) => { const r = v.reduce((a, b) => a + (b.runs || 0), 0);
        return <tr key={k}><td>{k.replace(/_/g, " ")}</td><td>{v.length}</td><td>{r}</td><td>{Math.round((100 * r) / v.length)}</td>
          <td>{v.filter((b) => b.boundary).length}</td><td>{v.filter((b) => b.wicket).length}</td></tr>; })}</tbody></table>);
  return illustrative ? <Illus label={title}>{t}</Illus> : t;
}

// ---------------------------------------------------------------- Edge / contact map (architecture only)
export function EdgeMap({ illustrative }: { illustrative?: boolean }) {
  if (!illustrative) return <NotRecorded what="Edges and bat contact" why="No source available to CRICINTEL records edges or contact points. Commentary text is not accepted as ground truth." unlock="validated edge flags or contact tracking" />;
  return <Illus label="Bat contact zones"><svg viewBox="0 0 120 220" className="vsvg" role="img" aria-label="Generic bat face divided into toe, middle, splice and edges">
    <rect x={35} y={20} width={50} height={170} rx={12} fill="none" stroke="#cfd6e6" strokeDasharray="4 3" />
    {[["toe", 160], ["middle", 110], ["splice", 50]].map(([l, y]) => <text key={l as string} x={60} y={y as number} textAnchor="middle" fontSize={11} fill="#cfd6e6">{l}</text>)}
    <text x={28} y={110} fontSize={10} fill="#cfd6e6" textAnchor="end">edge</text><text x={92} y={110} fontSize={10} fill="#cfd6e6">edge</text></svg></Illus>;
}

// ---------------------------------------------------------------- Dismissal theatre V2 (Layer 0 relationship; spatial only if recorded)
export function DismissalTheatre({ d, keeperNote }: { d: any; keeperNote?: string }) {
  if (!d) return null;
  const f = d.fielders?.[0];
  const caughtKeeper = d.keeper?.is_keeper_catch;
  return (
    <figure className="theatre" aria-label={`${d.player_out.name}, ${d.kind}${f ? `, by ${f.name}` : ""}. Positions are not recorded.`}>
      <div className="th-row">
        <div className="th-node out"><span className="mini">out</span><b>{d.player_out.name}</b></div>
        <div className="th-arrow"><span>{d.kind}</span></div>
        {f && <div className="th-node"><span className="mini">{caughtKeeper ? "wicketkeeper (derived)" : d.keeper?.status_unknown ? "fielder (keeper status unknown)" : d.kind === "run out" ? "fielder" : "fielder"}</span><b>{f.name}{f.substitute ? " (sub)" : ""}</b></div>}
        {d.bowler_credited && <div className="th-node bw"><span className="mini">bowler credited</span></div>}
      </div>
      <div className="mini" style={{ marginTop: 6 }}>Relationship only. Where the ball pitched, whether it was edged, and where it was caught are not recorded, so no field position, edge or trajectory is drawn.
        {caughtKeeper && keeperNote ? ` ${keeperNote}` : ""}</div>
      <Why p={d.provenance} />
      {d.keeper?.provenance && <Why p={d.keeper.provenance} />}
    </figure>
  );
}

// ---------------------------------------------------------------- Bowler map / Matchup map (compose the above)
export function BowlerMap({ balls, illustrative }: { balls: BallGeom[]; illustrative?: boolean }) {
  return <div className="vgrid"><LineLengthMap balls={balls} illustrative={illustrative} title="Bowler: line & length" /><PitchMap balls={balls} illustrative={illustrative} title="Bowler: pitch points" /></div>;
}
export function MatchupMap({ balls, illustrative }: { balls: BallGeom[]; illustrative?: boolean }) {
  return <LineLengthMap balls={balls} illustrative={illustrative} metric="sr" title="Matchup: strike rate by line & length" />;
}
