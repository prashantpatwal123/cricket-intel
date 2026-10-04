"use client";
// Innings Journey: every delivery while the batter was at the crease, left to right. Balls they faced are bars
// (height = runs off the bat); balls at the other end are small marks below. Cumulative runs, phases, partner changes,
// milestones and wickets are drawn on the same timeline. Scrub with the slider or arrow keys; a selection opens Replay.
import { useEffect, useRef } from "react";
import { OUTCOME_COLOR } from "@/lib/viz/model";

const STEP = 9, H = 210, BASE = 150, TOP = 24;

export default function InningsJourney({ story, sel, onSel }: { story: any; sel: number; onSel: (i: number) => void }) {
  const balls = story.balls as any[];
  const n = balls.length;
  const Wd = Math.max(320, n * STEP + 40);
  const maxRuns = Math.max(10, story.summary.runs);
  const yCum = (r: number) => BASE - 8 - (r / maxRuns) * (BASE - TOP - 20);
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const el = ref.current; if (!el) return;
    const x = 20 + sel * STEP;
    if (x < el.scrollLeft + 30 || x > el.scrollLeft + el.clientWidth - 30) el.scrollTo({ left: x - el.clientWidth / 2, behavior: "smooth" });
  }, [sel]);
  const ix = (seq: number) => balls.findIndex((b) => b.seq >= seq);
  const cum = balls.map((b, i) => `${20 + i * STEP},${yCum(b.cum_runs)}`).join(" ");
  const phaseRuns: { phase: string; a: number; b: number }[] = [];
  balls.forEach((b, i) => { const last = phaseRuns[phaseRuns.length - 1]; if (last && last.phase === b.phase) last.b = i; else phaseRuns.push({ phase: b.phase, a: i, b: i }); });
  return (
    <div className="journey">
      <div className="journey-scroll" ref={ref}>
        <svg width={Wd} height={H} role="img" aria-label="Innings journey">
          {phaseRuns.map((p) => <g key={p.a}>
            <rect x={14 + p.a * STEP} y={TOP - 14} width={(p.b - p.a + 1) * STEP} height={BASE - TOP + 40} fill={{ powerplay: "#7cc4ff", middle: "#ffffff", death: "#ffb547" }[p.phase] || "#fff"} opacity={0.04} />
            <text x={16 + p.a * STEP} y={TOP - 4} fontSize={9} fill="#5d6a88">{p.phase}</text></g>)}
          <line x1={14} x2={Wd - 10} y1={BASE} y2={BASE} stroke="#ffffff22" />
          {story.events.filter((e: any) => e.kind === "partner").map((e: any) => { const i = ix(e.seq); return <g key={"p" + e.seq}>
            <line x1={14 + i * STEP} x2={14 + i * STEP} y1={TOP} y2={H - 14} stroke="#7cc4ff" strokeDasharray="2 3" opacity={0.6} />
            <text x={16 + i * STEP} y={H - 4} fontSize={9} fill="#7cc4ff">{e.label.replace("new partner: ", "+ ")}</text></g>; })}
          {story.events.filter((e: any) => e.kind === "milestone").map((e: any) => { const i = ix(e.seq); return <g key={"m" + e.seq}>
            <line x1={20 + i * STEP} x2={20 + i * STEP} y1={yCum(balls[i].cum_runs)} y2={TOP - 2} stroke="#9df26b" />
            <text x={23 + i * STEP} y={TOP + 6} fontSize={10} fill="#9df26b" fontWeight={800}>{e.label.split(" ")[0]}</text></g>; })}
          <polyline points={cum} fill="none" stroke="#edf2fc" strokeWidth={1.6} opacity={0.75} />
          {balls.map((b, i) => {
            const x = 20 + i * STEP, on = i === sel;
            if (!b.on_strike) return <g key={b.seq} onClick={() => onSel(i)} style={{ cursor: "pointer" }}>
              <rect x={x - STEP / 2} y={BASE + 2} width={STEP} height={30} fill="transparent" />
              <circle cx={x} cy={BASE + 14} r={on ? 3 : 1.6} fill={b.partner_out ? "#ff5c74" : "#5d6a88"} />
              {b.partner_out && <text x={x} y={BASE + 30} fontSize={9} textAnchor="middle" fill="#ff5c74">✕</text>}</g>;
            const col = b.out ? OUTCOME_COLOR.WICKET : b.six ? OUTCOME_COLOR["6"] : b.four ? OUTCOME_COLOR["4"] : b.dot ? OUTCOME_COLOR.DOT : b.runs ? OUTCOME_COLOR["1"] : "#3a4566";
            const h = b.out ? 34 : b.runs ? 6 + 8 * Math.min(6, b.runs) : 3;
            return <g key={b.seq} onClick={() => onSel(i)} style={{ cursor: "pointer" }}>
              <rect x={x - STEP / 2} y={TOP} width={STEP} height={BASE - TOP} fill="transparent" />
              <rect x={x - 3} y={BASE - h} width={6} height={h} rx={2} fill={col} opacity={on ? 1 : 0.85} />
              {b.out && <text x={x} y={BASE - h - 4} fontSize={11} textAnchor="middle" fill="#ff5c74" fontWeight={900}>W</text>}
            </g>;
          })}
          <line x1={20 + sel * STEP} x2={20 + sel * STEP} y1={TOP - 6} y2={BASE + 20} stroke="#edf2fc" strokeWidth={1.5} className="fade-svg" />
          <text x={8} y={BASE + 46} fontSize={9} fill="#5d6a88">at the other end</text>
        </svg>
      </div>
      <input type="range" className="scrub" min={0} max={n - 1} value={sel} onChange={(e) => onSel(Number(e.target.value))} aria-label="Scrub through the innings" />
      <div className="legend">
        <span><i style={{ borderTopColor: OUTCOME_COLOR.DOT, borderTopWidth: 6 }} />dot</span><span><i style={{ borderTopColor: OUTCOME_COLOR["1"], borderTopWidth: 6 }} />1–3</span>
        <span><i style={{ borderTopColor: OUTCOME_COLOR["4"], borderTopWidth: 6 }} />4</span><span><i style={{ borderTopColor: OUTCOME_COLOR["6"], borderTopWidth: 6 }} />6</span>
        <span><i style={{ borderTopColor: "#edf2fc" }} />cumulative runs</span><span><i style={{ borderTopColor: "#7cc4ff", borderTopStyle: "dashed" }} />new partner</span>
        <span>dots below the line: balls faced by the partner</span>
      </div>
    </div>
  );
}
