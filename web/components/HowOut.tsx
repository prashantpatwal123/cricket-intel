"use client";
// "How [player] gets out": dismissal routes drawn on a schematic field.
// Rules: nodes sit only where the Laws/event data put them (stumps, batter, keeper, bowler, wicket).
// Catches by other fielders are a ring band, never a point: the data has no fielding positions.
import ProvBadge from "./Prov";

export interface Route { route: string; label: string; n: number; pct: number | null; prov: string }

const W = 400, H = 470, CX = 200, CY = 240;
const BAT_Y = 318, BOWL_Y = 150, KEEP_Y = 360;

export default function HowOut({ routes, hand, selected, onSelect, name }: {
  routes: Route[]; hand?: string | null; selected: string | null; onSelect: (r: string | null) => void; name: string;
}) {
  const by = Object.fromEntries(routes.map((r) => [r.route, r]));
  const max = Math.max(1, ...routes.map((r) => r.n));
  const rad = (n: number) => (n ? 11 + 15 * Math.sqrt(n / max) : 7);
  const side = hand === "left" ? 1 : -1; // batter stands to one side of the stumps (schematic)
  const batX = CX + side * 13;
  const dim = (code: string) => (selected && selected !== code ? 0.28 : 1);
  const pick = (code: string) => onSelect(selected === code ? null : code);

  const Node = ({ code, x, y, icon }: { code: string; x: number; y: number; icon?: React.ReactNode }) => {
    const r = by[code]; if (!r) return null;
    const on = selected === code; const rr = rad(r.n);
    return (
      <g className="node" opacity={dim(code)} onClick={() => pick(code)} role="button" aria-label={`${r.label}: ${r.n}`}
         tabIndex={0} onKeyDown={(e) => (e.key === "Enter" || e.key === " ") && pick(code)}>
        <circle className="halo" cx={x} cy={y} r={rr + 7} fill={on ? "#ff5c74" : "#ffffff"} opacity={on ? 0.25 : 0.06} />
        <circle cx={x} cy={y} r={rr} fill={r.n ? (on ? "#ff5c74" : "#0b1324") : "#0b132499"} stroke={r.n ? "#ff5c74" : "#5d6a88"}
                strokeWidth={on ? 0 : 2} strokeDasharray={r.prov === "DERIVED" ? "0" : "0"} />
        {icon}
        <text x={x} y={y + 6} textAnchor="middle" fontSize={r.n ? 17 : 12} fontWeight={800} fill={on ? "#0b1020" : "#edf2fc"}
              style={{ fontFamily: "var(--display)" }}>{r.n}</text>
      </g>
    );
  };
  const SHORT: Record<string, string> = { BOWLED: "Bowled", LBW: "LBW", CAUGHT_KEEPER: "Caught keeper", CAUGHT_BOWLER: "C & B",
    STUMPED: "Stumped", RUN_OUT: "Run out", HIT_WICKET: "Hit wicket" };
  const Label = ({ code, x, y, pos = "below" }: { code: string; x: number; y: number; pos?: "below" | "above" | "left" | "right" }) => {
    const r = by[code]; if (!r) return null;
    const rr = rad(r.n);
    const [tx, ty, anchor] = pos === "below" ? [x, y + rr + 14, "middle"] : pos === "above" ? [x, y - rr - 7, "middle"]
      : pos === "left" ? [x - rr - 6, y + 4, "end"] : [x + rr + 6, y + 4, "start"];
    return (
      <text x={tx} y={ty} textAnchor={anchor as any} fontSize={11.5} fontWeight={750} fill={r.n ? "#edf2fc" : "#5d6a88"}
            opacity={dim(code)} onClick={() => pick(code)} style={{ cursor: "pointer" }}>
        {SHORT[code]}{r.prov === "DERIVED" ? "*" : ""}
      </text>
    );
  };

  const fielder = by["CAUGHT_FIELDER"];
  const ringW = fielder?.n ? 8 + 14 * Math.sqrt(fielder.n / max) : 5;
  const unresolved = ["CAUGHT_KEEPER_STATUS_UNKNOWN", "CAUGHT_UNKNOWN_FIELDER", "OTHER"].map((c) => by[c]).filter((r) => r && r.n);

  return (
    <div className="howout">
      <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label={`How ${name} gets out: dismissal routes`}>
        <defs>
          <radialGradient id="turf" cx="50%" cy="45%" r="60%">
            <stop offset="0%" stopColor="#15553f" /><stop offset="100%" stopColor="#0b2c22" />
          </radialGradient>
          <pattern id="mow" width="40" height="40" patternUnits="userSpaceOnUse" patternTransform="rotate(90)">
            <rect width="20" height="40" fill="#ffffff05" />
          </pattern>
          <pattern id="hatch" width="7" height="7" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
            <line x1="0" y1="0" x2="0" y2="7" stroke="#ff5c74" strokeWidth="2" opacity=".55" />
          </pattern>
          <clipPath id="field"><ellipse cx={CX} cy={CY} rx={188} ry={222} /></clipPath>
          <path id="ringpath" d={`M ${CX - 170} ${CY} a 170 204 0 1 1 340 0 a 170 204 0 1 1 -340 0`} />
        </defs>
        {/* field */}
        <ellipse cx={CX} cy={CY} rx={188} ry={222} fill="url(#turf)" stroke="#2b6b52" strokeWidth={2} />
        <ellipse cx={CX} cy={CY} rx={188} ry={222} fill="url(#mow)" />
        <ellipse cx={CX} cy={CY} rx={108} ry={128} fill="none" stroke="#ffffff22" strokeDasharray="3 6" />
        {/* caught-in-field ring: a zone, not a position */}
        {fielder && (
          <g className="node" opacity={dim("CAUGHT_FIELDER")} onClick={() => pick("CAUGHT_FIELDER")} role="button"
             aria-label={`${fielder.label}: ${fielder.n}. Fielding position not recorded`}>
            <ellipse cx={CX} cy={CY} rx={170} ry={204} fill="none" stroke={selected === "CAUGHT_FIELDER" ? "#ff5c74" : "url(#hatch)"}
                     strokeWidth={ringW} opacity={selected === "CAUGHT_FIELDER" ? 0.55 : 1} />
            <text fontSize={10.5} fontWeight={800} fill="#ffd0d8" letterSpacing="1.2" dy={4}>
              <textPath href="#ringpath" startOffset="6%">
                {`CAUGHT IN THE FIELD · ${fielder.n} (${fielder.pct ?? 0}%) · POSITION NOT RECORDED`}
              </textPath>
            </text>
          </g>
        )}
        {/* pitch */}
        <rect x={CX - 15} y={BOWL_Y + 8} width={30} height={BAT_Y - BOWL_Y - 2} rx={3} fill="#c9b48a" opacity={0.88} />
        <line x1={CX - 22} x2={CX + 22} y1={BAT_Y - 12} y2={BAT_Y - 12} stroke="#fff" strokeWidth={1.5} opacity={0.9} />
        <line x1={CX - 22} x2={CX + 22} y1={BOWL_Y + 20} y2={BOWL_Y + 20} stroke="#fff" strokeWidth={1.5} opacity={0.9} />
        {/* stumps */}
        {[BAT_Y, BOWL_Y + 8].map((y, i) => (
          <g key={i}>{[-4, 0, 4].map((dx) => <rect key={dx} x={CX + dx - 1} y={y - 1} width={2} height={7} fill="#fff" />)}</g>
        ))}
        {/* connectors: who was involved, not the ball's path */}
        <g stroke="#ffffff55" strokeWidth={1.2} strokeDasharray="2 4" fill="none">
          {by["CAUGHT_KEEPER"]?.n ? <line x1={batX} y1={BAT_Y - 4} x2={CX} y2={KEEP_Y - 10} /> : null}
          {by["CAUGHT_BOWLER"]?.n ? <line x1={batX} y1={BAT_Y - 14} x2={CX} y2={BOWL_Y + 14} /> : null}
          {by["STUMPED"]?.n ? <line x1={CX + 58} y1={KEEP_Y + 6} x2={CX + 6} y2={BAT_Y + 4} /> : null}
          {by["RUN_OUT"]?.n ? <><line x1={CX - 92} y1={CY - 20} x2={CX - 8} y2={BAT_Y} /><line x1={CX - 92} y1={CY - 20} x2={CX - 8} y2={BOWL_Y + 10} /></> : null}
          {by["HIT_WICKET"]?.n ? <line x1={CX + 92} y1={CY - 20} x2={batX} y2={BAT_Y - 8} /> : null}
        </g>
        {/* batter + keeper + bowler figures (generic, illustrative) */}
        <g opacity={0.95}>
          <circle cx={batX} cy={BAT_Y - 24} r={6} fill="#edf2fc" />
          <rect x={batX - 5} y={BAT_Y - 18} width={10} height={14} rx={4} fill="#edf2fc" />
          <circle cx={CX} cy={KEEP_Y - 2} r={5} fill="#7cc4ff" />
          <circle cx={CX} cy={BOWL_Y - 2} r={5} fill="#edf2fc" />
        </g>
        {/* nodes: only at places the Laws/event data identify */}
        <Node code="CAUGHT_BOWLER" x={CX} y={BOWL_Y - 34} />
        <Label code="CAUGHT_BOWLER" x={CX} y={BOWL_Y - 34} pos="above" />
        <Node code="RUN_OUT" x={CX - 92} y={CY - 20} />
        <Label code="RUN_OUT" x={CX - 92} y={CY - 20} />
        <Node code="HIT_WICKET" x={CX + 92} y={CY - 20} />
        <Label code="HIT_WICKET" x={CX + 92} y={CY - 20} />
        <Node code="BOWLED" x={CX - 70} y={BAT_Y + 4} />
        <Label code="BOWLED" x={CX - 70} y={BAT_Y + 4} pos="left" />
        <Node code="LBW" x={CX + 70} y={BAT_Y - 4} />
        <Label code="LBW" x={CX + 70} y={BAT_Y - 4} pos="right" />
        <Node code="CAUGHT_KEEPER" x={CX} y={KEEP_Y + 16} />
        <Label code="CAUGHT_KEEPER" x={CX} y={KEEP_Y + 16} pos="left" />
        <Node code="STUMPED" x={CX + 58} y={KEEP_Y + 6} />
        <Label code="STUMPED" x={CX + 58} y={KEEP_Y + 6} pos="right" />
        {/* connector from stumps to bowled / batter to lbw */}
        <g stroke="#ff5c7466" strokeWidth={1.2} fill="none">
          {by["BOWLED"]?.n ? <line x1={CX - 6} y1={BAT_Y + 3} x2={CX - 70 + rad(by["BOWLED"].n)} y2={BAT_Y + 4} /> : null}
          {by["LBW"]?.n ? <line x1={batX + 4} y1={BAT_Y - 10} x2={CX + 70 - rad(by["LBW"].n)} y2={BAT_Y - 4} /> : null}
        </g>
      </svg>
      <div className="legend">
        <span><i style={{ borderTopStyle: "dashed" }} />connector = who was involved (not the ball&apos;s path)</span>
        <span><i style={{ borderTopColor: "#ff5c74", borderTopWidth: 6, opacity: .6 }} />hatched ring = caught in the field (position unknown)</span>
        <span>bubble size ∝ dismissals · * derived (keeper inferred)</span>
      </div>
      {unresolved.length > 0 && (
        <div className="chips" style={{ marginTop: 10 }}>
          {unresolved.map((r) => (
            <button key={r!.route} className={`chip ${selected === r!.route ? "" : "unknown"}`} onClick={() => pick(r!.route)}>
              {r!.label}: <b>{r!.n}</b> <ProvBadge prov="UNKNOWN" title="Not placed on the field: role or fielder unresolved" />
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
