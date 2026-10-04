"use client";
// EXPERIMENTAL lab: Situation Difficulty (SDX v0.1) and performance in difficult chases. Only reachable when the API is
// started with CRICINTEL_EXPERIMENTAL=1. Not called "Pressure" until validated and approved.
import Link from "next/link";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import ProvBadge from "@/components/Prov";
import MatchSituation from "@/components/viz/MatchSituation";

export default function Lab() {
  const [on, setOn] = useState<boolean | null>(null);
  const [val, setVal] = useState<any | null>(null);
  const [st, setSt] = useState({ format: "T20", gender: "male", runs_required: 40, balls_left: 24, wickets_lost: 5 });
  const [score, setScore] = useState<any | null>(null);
  const [lb, setLb] = useState<any | null>(null);
  const [lbq, setLbq] = useState({ format: "T20", gender: "male", role: "batting" });
  useEffect(() => { api("/meta").then((r) => setOn(!!r.data.experimental)); }, []);
  useEffect(() => { if (on) api("/exp/situation/validation").then((r) => setVal(r.data)).catch(() => setVal(null)); }, [on]);
  useEffect(() => { if (on) api("/exp/situation", st).then((r) => setScore(r.data)).catch(() => setScore(null)); }, [on, JSON.stringify(st)]);
  useEffect(() => { if (on) { setLb(null); api("/exp/difficulty", lbq).then((r) => setLb(r.data)); } }, [on, JSON.stringify(lbq)]);
  if (on === null) return <div className="loading">Loading…</div>;
  if (!on) return <div className="empty" style={{ marginTop: 30 }}>Experimental features are switched off on this server.</div>;
  const total = st.format === "T20" ? 120 : 300;
  const key = `${st.format}|${st.gender}`;
  const h = val?.holdout?.[key];
  const num = (k: keyof typeof st, lab: string, min: number, max: number) => (
    <label className="lab-in"><span className="mini">{lab}</span>
      <input type="range" min={min} max={max} value={st[k] as number} onChange={(e) => setSt({ ...st, [k]: Number(e.target.value) })} />
      <b className="num">{st[k]}</b></label>
  );
  return (
    <div className="fade-in">
      <div className="exp-box" style={{ marginTop: 18 }}>
        <div className="exp-tag">Experimental lab · internal only · not launched</div>
        <div className="sub" style={{ marginTop: 4 }}>These are research prototypes behind a flag. They are MODELLED estimates, validated below, and deliberately not called &ldquo;Pressure&rdquo; or &ldquo;clutch&rdquo;.</div>
      </div>
      <section className="section">
        <div className="kicker">Situation Difficulty — Experimental · {score?.version}</div>
        <h1 className="h2" style={{ fontSize: "clamp(26px, 7vw, 40px)" }}>How hard is this chase?</h1>
        <p className="sub">{score?.definition}</p>
        <div className="grid2" style={{ marginTop: 10 }}>
          <div className="card">
            <div className="seg" style={{ marginBottom: 10 }}>{["T20", "ODI"].map((f) => <button key={f} className={st.format === f ? "on" : ""} onClick={() => setSt({ ...st, format: f, balls_left: Math.min(st.balls_left, f === "T20" ? 120 : 300) })}>{f}</button>)}
              {[["male", "Men"], ["female", "Women"]].map(([g, l]) => <button key={g} className={st.gender === g ? "on" : ""} onClick={() => setSt({ ...st, gender: g })}>{l}</button>)}</div>
            {num("runs_required", "Runs required", 1, st.format === "T20" ? 250 : 400)}
            {num("balls_left", "Balls left", 1, total)}
            {num("wickets_lost", "Wickets lost", 0, 9)}
            <div style={{ marginTop: 10 }}>
              <MatchSituation compact s={{ format: st.format, innings_no: 2, score: NaN, wickets: st.wickets_lost, legal_balls: total - st.balls_left, limit_balls: total,
                target: null, runs_required: st.runs_required, balls_left: st.balls_left, rrr: (6 * st.runs_required) / st.balls_left, crr: null }} />
            </div>
          </div>
          <div className="card">
            {score?.score && <>
              <div className="sdx-big num">{Math.round(score.score.sdx)}<span className="mini"> / 100</span> <ProvBadge prov="MODELLED" /></div>
              <div style={{ fontSize: 14 }}>Of training-era chases facing this demand, <b>{Math.round(score.score.sdx)}%</b> failed.</div>
              <dl className="kv" style={{ marginTop: 10 }}>
                <dt>Expected runs</dt><dd>{score.score.expected_runs} from {st.balls_left} balls with {10 - st.wickets_lost} wickets (DLS-style resource table fitted on first innings)</dd>
                <dt>Demand</dt><dd>{st.runs_required} ÷ {score.score.expected_runs} = {score.score.demand}</dd>
                <dt>Swing</dt><dd>{score.swing} points between a wicket and a four on the next ball</dd>
                <dt>Not used</dt><dd>player quality, venue, toss, momentum</dd>
              </dl>
            </>}
          </div>
        </div>
      </section>
      {val && h && (
        <section className="section">
          <div className="section-head"><div><div className="kicker">Validation · holdout {val.cutoff} onwards</div><div className="h2">Does it work?</div></div>
            <Link className="btn" href="/context">Context Engine →</Link></div>
          <div className="grid2">
            <div className="card">
              <div className="sit-title">Holdout skill ({key}: {h.deliveries.toLocaleString()} balls, {h.matches} chases)</div>
              <table className="mtable" style={{ marginTop: 6 }}><thead><tr><th>Model</th><th>Log loss</th><th>Brier</th></tr></thead><tbody>
                <tr><td className="strong">SDX v0.1</td><td>{h.log_loss.sdx}</td><td>{h.brier.sdx}</td></tr>
                <tr><td>Required rate only</td><td>{h.log_loss.rrr}</td><td>{h.brier.rrr}</td></tr>
                <tr><td>Base rate</td><td>{h.log_loss.base}</td><td>{h.brier.base}</td></tr></tbody></table>
              <div className="mini" style={{ marginTop: 6 }}>Lower is better. Monotonicity: {val.monotonicity.violations} violations in {val.monotonicity.states_checked.toLocaleString()} states; {val.monotonicity.out_of_bounds} out of bounds.</div>
            </div>
            <div className="card">
              <div className="sit-title">Calibration (predicted v observed failure %)</div>
              <div className="calib">
                {val.calibration[key].map((c: any) => (
                  <div key={c.band} className="calib-row"><span className="mini">{c.band}</span>
                    <span className="calib-t"><i style={{ width: `${c.predicted}%` }} /><b style={{ left: `${c.observed}%` }} /></span>
                    <span className="mini num">{c.predicted} v {c.observed}</span></div>
                ))}
              </div>
              <div className="mini">Bar = predicted, tick = observed. Known issue: in recent men&apos;s T20 chases mid-range states succeed ~5 points more often than predicted.</div>
            </div>
          </div>
        </section>
      )}
      <section className="section">
        <div className="section-head"><div><div className="kicker">Research question</div><div className="h2">Do some players do better when the chase is hard?</div>
          <div className="sub">Balls in chases with difficulty ≥ 70, compared with each player&apos;s own baseline and the league shift. Full members and leagues only.</div></div></div>
        <div className="seg" style={{ marginBottom: 10, flexWrap: "wrap" }}>
          {["T20", "ODI"].map((f) => <button key={f} className={lbq.format === f ? "on" : ""} onClick={() => setLbq({ ...lbq, format: f })}>{f}</button>)}
          {[["male", "Men"], ["female", "Women"]].map(([g, l]) => <button key={g} className={lbq.gender === g ? "on" : ""} onClick={() => setLbq({ ...lbq, gender: g })}>{l}</button>)}
          {[["batting", "Batters"], ["bowling", "Bowlers"]].map(([g, l]) => <button key={g} className={lbq.role === g ? "on" : ""} onClick={() => setLbq({ ...lbq, role: g })}>{l}</button>)}
        </div>
        {!lb ? <div className="loading">Testing…</div> : (
          <>
            <div className={`note`} style={lb.trait_test.use_word_clutch ? {} : { borderColor: "#c49bff66", color: "#e5d4ff", background: "#c49bff10" }}>
              <b>Is it a stable trait?</b> Split-half correlation across {lb.trait_test.players} players: r = {lb.trait_test.split_half_r} (90% interval {lb.trait_test.interval_90?.join(" to ")}).
              Verdict: <b>{lb.trait_test.verdict}</b>. {lb.trait_test.use_word_clutch ? "" : "So we don't use the word \"clutch\"."}
              <div className="mini" style={{ marginTop: 4 }}>{lb.leaderboard.passing_fdr} of {lb.leaderboard.qualified} players pass the false-discovery test.</div>
            </div>
            <div className="rec-list">
              {lb.leaderboard.rows.slice(0, 10).map((r: any, i: number) => (
                <Link key={r.person_id} className="rec-row" href={`/players/${r.person_id}`}>
                  <span className="rec-rank">{i + 1}</span>
                  <span style={{ minWidth: 0 }}><b style={{ display: "block" }}>{r.name}</b><span className="mini">{r.balls} balls · {r.observed} v {r.expected} expected (own overall {r.own_overall}) · interval {r.interval.join(" to ")}{r.passes_fdr ? " · passes FDR" : ""}</span></span>
                  <span className="rec-val num">{r.shrunk_diff > 0 ? "+" : ""}{r.shrunk_diff}</span>
                </Link>
              ))}
            </div>
            <div className="mini" style={{ marginTop: 6 }}>{lb.leaderboard.definition} Descriptive only: with no evidence of a stable trait, these differences are best read as variation.</div>
          </>
        )}
      </section>
    </div>
  );
}
