"use client";
// Match Situation: score, wickets, innings progress, phases, target and rates drawn spatially. All DERIVED from events.
import { OUTCOME_COLOR, symbolToOutcome } from "@/lib/viz/model";

export interface Situation {
  format: string; innings_no: number; score: number; wickets: number; legal_balls: number; limit_balls: number;
  target?: number | null; runs_required?: number | null; balls_left?: number | null; rrr?: number | null; crr?: number | null;
  phase?: string; recent?: string[]; batting?: string; bowling?: string; next_ball?: string;
}

export default function MatchSituation({ s, compact = false }: { s: Situation; compact?: boolean }) {
  const phases = s.format === "T20" ? [36, 54, 30] : [60, 180, 60];
  const total = s.limit_balls || phases.reduce((a, b) => a + b, 0);
  const prog = Math.min(1, s.legal_balls / total);
  const scale = s.format === "T20" ? 18 : 12;
  const chase = s.runs_required != null;
  return (
    <div className={`msit ${compact ? "compact" : ""}`} aria-label="Match situation">
      <div className="msit-top">
        <div><span className="msit-score num">{Number.isFinite(s.score) ? `${s.score}/${s.wickets}` : `${s.wickets} down`}</span>
          <span className="mini"> {Math.floor(s.legal_balls / 6)}.{s.legal_balls % 6} ov{s.phase ? ` · ${s.phase}` : ""}</span></div>
        {chase && <div className="msit-need"><b className="num">{s.runs_required}</b> <span className="mini">needed off</span> <b className="num">{s.balls_left}</b></div>}
      </div>
      <div className="msit-bar" title={`${s.legal_balls} of ${total} legal balls bowled`}>
        {phases.map((p, i) => <span key={i} className={`ph ph${i}`} style={{ width: `${(100 * p) / phases.reduce((a, b) => a + b, 0)}%` }} />)}
        <i className="done" style={{ width: `${100 * prog}%` }} />
        <i className="now" style={{ left: `${100 * prog}%` }} />
      </div>
      <div className="msit-legend mini"><span>powerplay</span><span>middle</span><span>death</span></div>
      <div className="msit-row">
        <div className="wk-pips" aria-label={`${s.wickets} wickets lost`}>
          {Array.from({ length: 10 }).map((_, i) => <span key={i} className={i < s.wickets ? "lost" : ""} />)}
        </div>
        <span className="mini">{10 - s.wickets} wickets in hand</span>
      </div>
      {chase && (
        <div className="msit-chase">
          {s.target != null && Number.isFinite(s.score) && <div className="msit-runs" title={`${s.score} of ${s.target}`}><i style={{ width: `${Math.min(100, (100 * s.score) / (s.target || 1))}%` }} /><span className="mini">target {s.target}</span></div>}
          {s.rrr != null && (
            <div className="rate-gauge" aria-label={`Required rate ${s.rrr?.toFixed(2)}, current rate ${s.crr?.toFixed(2)}`}>
              <div className="rg-axis" />
              {s.crr != null && <span className="rg crr" style={{ left: `${Math.min(100, (100 * s.crr) / scale)}%` }}><em>now {s.crr.toFixed(1)}</em></span>}
              <span className="rg rrr" style={{ left: `${Math.min(100, (100 * s.rrr) / scale)}%` }}><em>need {s.rrr.toFixed(1)}</em></span>
            </div>
          )}
        </div>
      )}
      {s.recent && s.recent.length > 0 && (
        <div className="recent" aria-label="Previous deliveries">
          {s.recent.map((x, i) => { const o = symbolToOutcome(x); return <span key={i} className={o === "WICKET" ? "rb w" : "rb"} style={o === "WICKET" ? undefined : { background: o ? OUTCOME_COLOR[o] + "33" : "#ffffff10" }}>{x}</span>; })}
          {s.next_ball && <span className="rb next">{s.next_ball}?</span>}
        </div>
      )}
    </div>
  );
}
