"use client";
// "How [player] gets out": dismissal routes on a schematic field, built from the cricket primitives.
// Nodes sit only where the Laws/event data put them (stumps, batter, keeper, bowler, wicket).
// Catches by other fielders are an UnknownZone ring: the data has no fielding positions.
import ProvBadge from "./Prov";
import { C, CountNode, Crease, Defs, EventConnector, Field, Figure, Pitch, Stumps } from "./cricket/primitives";

export interface Route { route: string; label: string; n: number; pct: number | null; prov: string }

const W = 400, H = 470, CX = 200, CY = 240;
const BAT_Y = 318, BOWL_Y = 150, KEEP_Y = 360;
const SHORT: Record<string, string> = { BOWLED: "Bowled", LBW: "LBW", CAUGHT_KEEPER: "Caught by keeper", CAUGHT_BOWLER: "C & B",
  STUMPED: "Stumped", RUN_OUT: "Run out", HIT_WICKET: "Hit wicket" };

export default function HowOut({ routes, hand, selected, onSelect, name }: {
  routes: Route[]; hand?: string | null; selected: string | null; onSelect: (r: string | null) => void; name: string;
}) {
  const by = Object.fromEntries(routes.map((r) => [r.route, r]));
  const max = Math.max(1, ...routes.map((r) => r.n));
  const rad = (n: number) => (n ? 11 + 15 * Math.sqrt(n / max) : 7);
  const side = hand === "left" ? 1 : -1;
  const batX = CX + side * 13;
  const dim = (code: string) => !!selected && selected !== code;
  const pick = (code: string) => onSelect(selected === code ? null : code);

  const nodes: [string, number, number, "below" | "above" | "left" | "right"][] = [
    ["CAUGHT_BOWLER", CX, BOWL_Y - 34, "above"], ["RUN_OUT", CX - 92, CY - 20, "below"], ["HIT_WICKET", CX + 92, CY - 20, "below"],
    ["BOWLED", CX - 70, BAT_Y + 4, "left"], ["LBW", CX + 70, BAT_Y - 4, "right"], ["CAUGHT_KEEPER", CX, KEEP_Y + 16, "left"],
    ["STUMPED", CX + 58, KEEP_Y + 6, "right"],
  ];
  const label = (code: string, x: number, y: number, pos: string) => {
    const r = by[code]; if (!r) return null;
    const rr = rad(r.n);
    const [tx, ty, anchor] = pos === "below" ? [x, y + rr + 14, "middle"] : pos === "above" ? [x, y - rr - 7, "middle"]
      : pos === "left" ? [x - rr - 6, y + 4, "end"] : [x + rr + 6, y + 4, "start"];
    return <text key={code + "l"} x={tx} y={ty} textAnchor={anchor as any} fontSize={11.5} fontWeight={750} fill={r.n ? C.text : "#5d6a88"}
                 opacity={dim(code) ? 0.28 : 1} onClick={() => pick(code)} style={{ cursor: "pointer" }}>{SHORT[code]}{r.prov === "DERIVED" ? "*" : ""}</text>;
  };
  const fielder = by["CAUGHT_FIELDER"];
  const ringW = fielder?.n ? 8 + 14 * Math.sqrt(fielder.n / max) : 5;
  const unresolved = ["CAUGHT_KEEPER_STATUS_UNKNOWN", "CAUGHT_UNKNOWN_FIELDER", "OTHER"].map((c) => by[c]).filter((r) => r && r.n);
  const has = (c: string) => !!by[c]?.n;

  return (
    <div className="howout">
      <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label={`How ${name} gets out: dismissal routes`}>
        <Defs />
        <path id="ringpath" d={`M ${CX - 170} ${CY} a 170 204 0 1 1 340 0 a 170 204 0 1 1 -340 0`} fill="none" />
        <Field cx={CX} cy={CY} rx={188} ry={222} />
        {fielder && (
          <g className="node" opacity={dim("CAUGHT_FIELDER") ? 0.28 : 1} onClick={() => pick("CAUGHT_FIELDER")} role="button"
             aria-label={`${fielder.label}: ${fielder.n}. Fielding position not recorded`}>
            <ellipse cx={CX} cy={CY} rx={170} ry={204} fill="none" stroke={selected === "CAUGHT_FIELDER" ? C.wicket : "url(#ci-hatch)"}
                     strokeWidth={ringW} opacity={selected === "CAUGHT_FIELDER" ? 0.55 : 1} />
            <text fontSize={11} fontWeight={800} fill="#ffd0d8" letterSpacing="1.2" dy={4}>
              <textPath href="#ringpath" startOffset="6%">{`CAUGHT IN THE FIELD · ${fielder.n} (${fielder.pct ?? 0}%) · POSITION NOT RECORDED`}</textPath>
            </text>
          </g>
        )}
        <Pitch x={CX} top={BOWL_Y + 8} bottom={BAT_Y + 6} />
        <Crease x={CX} y={BAT_Y - 12} /><Crease x={CX} y={BOWL_Y + 20} />
        <Stumps x={CX} y={BAT_Y} broken={selected === "BOWLED" || selected === "STUMPED" || selected === "HIT_WICKET"} />
        <Stumps x={CX} y={BOWL_Y + 8} />
        <g>
          {has("CAUGHT_KEEPER") && <EventConnector key={`ck${selected}`} x1={batX} y1={BAT_Y - 4} x2={CX} y2={KEEP_Y - 10} prov="DERIVED" />}
          {has("CAUGHT_BOWLER") && <EventConnector key={`cb${selected}`} x1={batX} y1={BAT_Y - 14} x2={CX} y2={BOWL_Y + 14} />}
          {has("STUMPED") && <EventConnector key={`st${selected}`} x1={CX + 58} y1={KEEP_Y + 6} x2={CX + 6} y2={BAT_Y + 4} />}
          {has("RUN_OUT") && <><EventConnector key={`r1${selected}`} x1={CX - 92} y1={CY - 20} x2={CX - 8} y2={BAT_Y} prov="UNKNOWN" />
            <EventConnector key={`r2${selected}`} x1={CX - 92} y1={CY - 20} x2={CX - 8} y2={BOWL_Y + 10} prov="UNKNOWN" /></>}
          {has("HIT_WICKET") && <EventConnector key={`hw${selected}`} x1={CX + 92} y1={CY - 20} x2={batX} y2={BAT_Y - 8} />}
          {has("BOWLED") && <line x1={CX - 6} y1={BAT_Y + 3} x2={CX - 70 + rad(by["BOWLED"].n)} y2={BAT_Y + 4} stroke={C.wicket} strokeOpacity={0.5} />}
          {has("LBW") && <line x1={batX + 4} y1={BAT_Y - 10} x2={CX + 70 - rad(by["LBW"].n)} y2={BAT_Y - 4} stroke={C.wicket} strokeOpacity={0.5} />}
        </g>
        <Figure x={batX} y={BAT_Y - 18} role="batter" unknownHand={!hand} />
        <Figure x={CX} y={KEEP_Y - 2} role="keeper" />
        <Figure x={CX} y={BOWL_Y - 2} role="bowler" />
        {nodes.map(([code, x, y]) => by[code] && (
          <CountNode key={code} x={x} y={y} r={rad(by[code].n)} n={by[code].n} active={selected === code} dim={dim(code)}
                     onClick={() => pick(code)} ariaLabel={`${by[code].label}: ${by[code].n}`} />
        ))}
        {nodes.map(([code, x, y, pos]) => label(code, x, y, pos))}
      </svg>
      <div className="legend">
        <span><i style={{ borderTopStyle: "dashed" }} />connector = who was involved (not the ball&apos;s path)</span>
        <span><i style={{ borderTopColor: C.wicket, borderTopWidth: 6, opacity: .6 }} />hatched ring = caught in the field (position unknown)</span>
        <span>* derived (keeper inferred) · run-out end unknown</span>
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
