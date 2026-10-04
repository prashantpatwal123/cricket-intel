"use client";
// Match Centre (Historical Live Lab). The page holds only the state at the current ball, fetched from the server for that
// ball: it never receives later deliveries, so nothing is hidden with CSS. Second-screen order on a phone:
// 1) what is happening (score, batters, bowler, recent balls, partnership, chase), 2) what matters now (ranked, only when
// something changed), 3) current battle, 4) prediction. Evidence links leave the replay and say so.
import Link from "next/link";
import { useParams, useRouter, useSearchParams } from "next/navigation";
import { recordPlay, useRemember } from "@/lib/memory";
import ExploreNext from "@/components/ExploreNext";
import { Suspense, useCallback, useEffect, useRef, useState } from "react";
import { api } from "@/lib/api";
import ProvBadge from "@/components/Prov";
import Worm from "@/components/viz/Worm";

export default function Page() { return <Suspense fallback={<div className="loading">Loading…</div>}><MatchCentre /></Suspense>; }

const SPEEDS: [string, number][] = [["1×", 3000], ["2×", 1500], ["5×", 600]];
const PICKS = ["DOT", "1", "2", "3", "4", "6", "WICKET"];
const TYPE_LABEL: Record<string, string> = {
  battle: "Current battle", batter_stage: "Batter v usual", bowler_spell: "Bowler v usual", partnership: "Partnership", wickets_down: "Wickets down",
  score_rate: "Scoring v average", chase: "Chase", dot_sequence: "Dot-ball run", big_over: "Big over", wicket_burst: "Wicket burst",
};

function Ball({ g }: { g: any }) {
  const c = g.wicket ? "w" : g.boundary === 6 ? "s" : g.boundary === 4 ? "f" : /wd|nb|b|lb/.test(g.g) ? "x" : g.g === "•" ? "d" : "";
  return <span className={`b ${c}`} title={g.label}>{g.g}</span>;
}

function MatchCentre() {
  const { id } = useParams<{ id: string }>();
  const sp = useSearchParams();
  const router = useRouter();
  const [n, setN] = useState<number>(Number(sp.get("n") ?? 0));
  const [d, setD] = useState<any | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [tab, setTab] = useState(sp.get("tab") || "now");
  const [playing, setPlaying] = useState(false);
  const [speed, setSpeed] = useState(3000);
  const [game, setGame] = useState(sp.get("game") === "1");   // deep link from a story: "what happened next?"
  const [pick, setPick] = useState<string | null>(null);
  const [reveal, setReveal] = useState<any | null>(null);
  const [score, setScore] = useState({ pts: 0, n: 0, right: 0, mpts: 0, beat: 0 });
  const busy = useRef(false);
  const jumped = useRef(false);
  useEffect(() => {   // arriving from a story's "what happened next?": bring the picks into view under the sticky score strip
    if (jumped.current || !d || sp.get("game") !== "1") return;
    jumped.current = true;
    setTimeout(() => {
      const el = document.querySelector("[data-testid=whn]"), head = document.querySelector(".mc-sticky");
      if (el) window.scrollTo({ top: el.getBoundingClientRect().top + window.scrollY - (head?.getBoundingClientRect().height ?? 0) - 70 });
    }, 120);
  }, [d, sp]);
  useRemember("replay", id, d?.meta ? `${d.meta.teams?.[0]} v ${d.meta.teams?.[1]} · replay` : null, `/live-lab/${id}`);

  const load = useCallback(async (c: number) => {
    busy.current = true;
    try {
      const r = await api(`/live/${id}`, { cursor: c });
      setD(r.data); setErr(null); setN(c);
      router.replace(`/live-lab/${id}?n=${c}${tab !== "now" ? `&tab=${tab}` : ""}`, { scroll: false });
    } catch (e: any) { setErr(String(e.message || e)); }
    busy.current = false;
  }, [id, router, tab]);

  useEffect(() => { load(n); /* eslint-disable-next-line react-hooks/exhaustive-deps */ }, [id]);
  useEffect(() => {
    if (!playing || game) return;
    const t = setInterval(() => {
      if (busy.current || !d) return;
      if (!d.replay.has_next) { setPlaying(false); return; }
      load(n + 1);
    }, speed);
    return () => clearInterval(t);
  }, [playing, speed, n, d, load, game]);

  const seek = async (to: string) => { setPlaying(false); setReveal(null); const r = await api(`/live/${id}/seek`, { cursor: n, to }); load(r.data.cursor); };
  const step = (k: number) => { setReveal(null); load(Math.max(0, n + k)); };
  const guess = async (p: string) => {
    if (!d?.replay.has_next) return;
    setPick(p);
    const r = await api(`/live/${id}/play`, { cursor: n, pick: p });
    const x = r.data;
    setD(x.state); setN(x.cursor); setReveal(x);
    router.replace(`/live-lab/${id}?n=${x.cursor}&tab=now`, { scroll: false });
    if (x.scored) recordPlay(x.points, x.correct, x.model.points);
    if (x.scored) setScore((s) => ({ pts: s.pts + x.points, n: s.n + 1, right: s.right + (x.correct ? 1 : 0), mpts: s.mpts + x.model.points, beat: s.beat + (x.points > x.model.points ? 1 : 0) }));
    setPick(null);
  };

  if (err) return <div className="empty" style={{ marginTop: 30 }}>Could not load this replay. {err}</div>;
  if (!d) return <div className="loading">Loading the replay…</div>;
  const m = d.meta, now = d.now || {}, sb = d.scoreboard || [];
  const cur = sb[sb.length - 1];
  const chase = now.chase;
  return (
    <div className="fade-in" style={{ marginTop: 10 }}>
      <div className="mc-sticky">
        <div className="replay-flag" role="note" data-testid="replay-flag">Historical replay — not live <small>· {m.date}</small></div>
        <div className="score-strip" data-testid="score-strip">
          <div className="sline">
            <span className="team">{cur ? `${cur.team}${cur.super_over ? " · super over" : ""}` : `${m.teams?.[0]} v ${m.teams?.[1]}`}</span>
            <span className="big">{cur ? `${cur.runs}/${cur.wickets}` : "–"}</span>
            <span className="ov">{cur ? `${cur.overs}${cur.limit_overs ? `/${cur.limit_overs}` : ""} ov` : "yet to start"}{now.run_rate != null ? ` · RR ${now.run_rate}` : ""}</span>
          </div>
          {chase && !chase.reached && chase.balls_remaining > 0 && <div className="need">Need {chase.runs_required} off {chase.balls_remaining} · req {chase.required_rate ?? "–"}{chase.rain_rule ? " · D/L target" : ""}</div>}
          {sb.length > 1 && <div className="prev">{sb.slice(0, -1).map((i: any) => `${i.team} ${i.runs}/${i.wickets} (${i.overs})`).join(" · ")}</div>}
          {d.replay.ended && <div className="need" style={{ color: "var(--accent)" }}>{m.result}</div>}
        </div>
        <div className="ctrl" data-testid="controls">
          <button className="ib" aria-label="Previous over" onClick={() => seek("prev_over")} disabled={!d.replay.has_prev}>«</button>
          <button className="ib" aria-label="Previous ball" onClick={() => step(-1)} disabled={!d.replay.has_prev}>‹</button>
          <button className="ib play" aria-label={playing ? "Pause" : "Play"} data-testid="play" onClick={() => { setGame(false); setPlaying(!playing); }} disabled={!d.replay.has_next}>{playing ? "❚❚" : "▶"}</button>
          <button className="ib" aria-label="Next ball" data-testid="next-ball" onClick={() => step(1)} disabled={!d.replay.has_next}>›</button>
          <button className="ib" aria-label="Next over" data-testid="next-over" onClick={() => seek("next_over")} disabled={!d.replay.has_next}>»</button>
          <button className="ib spd" aria-label={`Speed ${SPEEDS.find(([, ms]) => ms === speed)?.[0]}; tap to change`} data-testid="speed"
            onClick={() => setSpeed(SPEEDS[(SPEEDS.findIndex(([, ms]) => ms === speed) + 1) % SPEEDS.length][1])}>{SPEEDS.find(([, ms]) => ms === speed)?.[0]}</button>
          <select aria-label="Jump to" value="" onChange={(e) => e.target.value && seek(e.target.value)} data-testid="jump">
            <option value="">Go…</option>
            <option value="start">Start of match</option>
            {/* only innings 1–2 plus any already under way: listing later innings would reveal a super over */}
            {Array.from(new Set([1, 2, ...sb.map((i: any) => i.innings)])).map((k) => <option key={k} value={`innings:${k}`}>Innings {k}</option>)}
            <option value="end">End (instant)</option>
          </select>
          <span className="pos" data-testid="position" data-n={n}>{d.replay.position ?? "pre-match"}<span className="only-desktop"> · ball #{n}</span></span>
        </div>
      </div>
      <div className="mc-tabs" role="tablist">
        {[["now", "Now"], ["card", "Scorecard"], ["timeline", "Timeline"], ["ask", "Ask"]].map(([k, l]) => (
          <button key={k} role="tab" aria-selected={tab === k} className={tab === k ? "on" : ""} onClick={() => setTab(k)} data-testid={`tab-${k}`}>{l}</button>))}
      </div>
      <div className="mini" style={{ marginTop: 6 }}>{m.competition}{m.stage ? ` · ${m.stage}` : ""} · {m.venue}{m.toss ? ` · ${m.toss.winner} won the toss and chose to ${m.toss.decision}` : ""}</div>

      {tab === "now" && <Now d={d} n={n} game={game} setGame={(g: boolean) => { setGame(g); setPlaying(false); }} pick={pick} guess={guess} reveal={reveal} score={score} id={id} />}
      {tab === "card" && <Card d={d} />}
      {tab === "timeline" && <TimelineTab d={d} />}
      {tab === "ask" && <AskTab id={id} n={n} d={d} />}
      {/* onward links name results, so they appear only once the replay has reached the end (spoiler safety) */}
      {d.replay.ended && <ExploreNext type="match" id={id} title="After the match" />}
    </div>
  );
}

function Now({ d, n, game, setGame, pick, guess, reveal, score, id }: any) {
  const now = d.now || {};
  if (!now.batters) return <div className="mc-sec"><div className="eyebrow">Before the first ball</div>
    {now.pre_ball && <p>{now.pre_ball.striker.name} and {now.pre_ball.non_striker.name} to open; {now.pre_ball.bowler.name} to bowl.</p>}</div>;
  const [s, ns] = [now.batters.find((b: any) => b.on_strike), now.batters.find((b: any) => !b.on_strike)];
  const bw = now.bowler;
  return (
    <div className="mc-grid">
      <div>
        <section className="mc-sec" aria-label="What is happening">
          <div className="eyebrow">What is happening <ProvBadge prov="DERIVED" title="Derived ball by ball from the deliveries so far" /></div>
          {now.closed && <div className="cmp">Innings closed: {now.close_reason}.</div>}
          <div className="pitch" data-testid="pitch" aria-label="Schematic pitch: who is at each end">
            <div className="end"><span className="tag">striker</span><b className="on">{s?.name ?? "–"}</b>{s ? `${s.runs} (${s.balls})` : ""}</div>
            <div className="strip" />
            <div className="end r"><span className="tag">bowling</span><b>{bw?.name ?? "–"}</b>{bw?.figures ?? ""}</div>
          </div>
          <div className="mini">Non-striker: <b style={{ color: "var(--text)" }}>{ns?.name ?? "–"}</b>{ns ? ` ${ns.runs} (${ns.balls})` : ""}</div>
          <div className="nodata">Positions are schematic. No ball-tracking data: line, length, shot direction and field positions are not recorded, so they are not drawn.</div>
          <div className="eyebrow" style={{ marginTop: 12 }}>Recent balls</div>
          <div className="balls" data-testid="recent">{(now.recent || []).slice(-10).map((g: any, i: number, a: any[]) => (
            <span key={g.event_id} style={{ display: "contents" }}>{i > 0 && a[i - 1].label.split(".")[0] !== g.label.split(".")[0] && <span className="sep" />}<Ball g={g} /></span>))}</div>
          {now.partnership && <Partnership p={now.partnership} />}
        </section>

        <section className="mc-sec" aria-label="What matters now" data-testid="right-now">
          <div className="eyebrow">What matters now</div>
          {d.right_now.nothing_new && <div className="rn-quiet" data-testid="nothing-new">Nothing statistically new on this ball.</div>}
          {d.right_now.items.length === 0 && <div className="mini">No insight clears the evidence bar at this point.</div>}
          {d.right_now.items.map((c: any) => (
            <div key={c.key} className={`rn-item ${c.new ? "" : "old"}`} data-testid="rn-item">
              <div className="t">{c.new && <span className="new">New</span>}{TYPE_LABEL[c.type] || c.type}<ProvBadge prov={c.prov} /></div>
              <p>{c.text}</p>
              <details><summary>Why this is shown (score {c.score})</summary>
                {Object.entries(c.dims).map(([k, v]: any) => <span key={k} style={{ marginRight: 10 }}>{k} {v}</span>)}
                <div>{d.right_now.method}</div>
                {c.href && <Link href={c.href}>Evidence (leaves the replay) →</Link>}</details>
            </div>))}
        </section>
        {now.chase && <section className="mc-sec" aria-label="Chase"><Chase c={now.chase} sdx={d.sdx} /></section>}
      </div>
      <div>
        {d.battle && <BattleBox b={d.battle} />}
        <section className="mc-sec" aria-label="Batters">
          <div className="eyebrow">Batters</div>
          {now.batters.map((b: any) => <BatterRow key={b.id} b={b} />)}
        </section>
        {bw && <BowlerBox w={bw} thisOver={now.this_over} />}
        <section className="mc-sec" aria-label="What happens next" data-testid="whn">
          <div className="eyebrow">What happens next? {d.prediction && <ProvBadge prov="MODELLED" />}</div>
          {!d.prediction ? <div className="mini">{d.replay.has_next ? "No next-ball model for this point (super over or innings break)." : "Match over."}</div> : (
            <>
              {!game ? <button className="btn primary" data-testid="play-this-match" onClick={() => setGame(true)}>Play this match</button> : (
                <>
                  <div className="mini">Predict the next ball, then it is revealed. Session: <b data-testid="session">{score.pts} pts · {score.right}/{score.n} right · model {score.mpts} pts · beat the model {score.beat}×</b></div>
                  <div className="picks">{PICKS.map((p) => <button key={p} data-testid={`pick-${p}`} className={pick === p ? "sel" : reveal?.actual === p ? "act" : ""} onClick={() => guess(p)}>{p === "WICKET" ? "W" : p === "DOT" ? "•" : p}</button>)}</div>
                </>)}
              {reveal && reveal.scored && <div className="cmp" style={{ marginTop: 8 }} data-testid="reveal">Ball was <b>{reveal.actual}</b>. You picked {reveal.pick}: {reveal.correct ? `+${reveal.points}` : "0"} pts. Model picked {reveal.model.pick}: {reveal.model.points} pts (it gave {reveal.actual} {Math.round(100 * reveal.model.p_actual)}%).</div>}
              <div className="eyebrow" style={{ marginTop: 10 }}>Model, next ball</div>
              <div className="probs" aria-label="Model probabilities for the next ball">{d.prediction.probs.map((p: any) => (
                <div key={p.outcome} className={p.outcome === d.prediction.pick ? "hit" : ""}><span>{Math.round(100 * p.p)}%</span><i style={{ height: `${Math.max(2, 100 * p.p)}%` }} />{p.outcome === "WICKET" ? "W" : p.outcome === "DOT" ? "•" : p.outcome}</div>))}</div>
              <div className="mini">Model choice: {d.prediction.pick}. {d.prediction.in_sample_note} {d.prediction.outcome_definition}</div>
            </>)}
        </section>
        <div className="mini" style={{ marginTop: 14 }}>{d.asof.note}</div>
      </div>
    </div>
  );
}

function Partnership({ p }: { p: any }) {
  const ids = [p.a, p.b];
  const r = (x: string) => (x === p.a ? p.runs_a : p.runs_b), bl = (x: string) => (x === p.a ? p.balls_a : p.balls_b);
  const tot = Math.max(1, p.runs_a + p.runs_b);
  return (
    <div style={{ marginTop: 14 }} data-testid="partnership">
      <div className="eyebrow">Partnership · wicket {p.wicket}</div>
      <div className="cmp"><b>{p.runs}</b> off {p.balls} · boundaries {p.boundary_runs} runs · extras {p.extras}</div>
      <div className="pship" aria-hidden><i style={{ width: `${(100 * p.runs_a) / tot}%` }} /></div>
      <div className="mini">{ids.map((x) => `${p.names[x]} ${r(x)} (${bl(x)} balls)`).join(" · ")}</div>
      {p.history ? <div className="mini">Before this match: {p.history.stands} stands together, average {p.history.average}, best {p.history.best}. Observed outcomes only.</div>
        : <div className="mini">No earlier covered stands together in this format.</div>}
    </div>
  );
}

function Chase({ c, sdx }: { c: any; sdx: any }) {
  return (
    <div style={{ marginTop: 14 }} data-testid="chase">
      <div className="eyebrow">Chase</div>
      <div className="battle-mini">
        <div><b>{c.target}</b><span>target</span></div><div><b>{c.runs_required}</b><span>needed</span></div>
        <div><b>{c.balls_remaining}</b><span>balls left</span></div><div><b>{c.required_rate ?? "–"}</b><span>req rate</span></div>
      </div>
      <div className="mini">Current rate {c.current_rate ?? "–"}. {c.note}.</div>
      {sdx && sdx.series?.length > 0 && <Sdx s={sdx} />}
    </div>
  );
}

function Sdx({ s }: { s: any }) {
  const W = 300, H = 60, xs = s.series, mx = Math.max(...xs.map((p: any) => p.legal), 1);
  const pts = xs.map((p: any) => `${(p.legal / mx) * W},${H - (p.sdx / 100) * H}`).join(" ");
  return (
    <div style={{ marginTop: 10, border: "1px dashed #8a6bc9", borderRadius: 10, padding: "8px 10px" }} data-testid="sdx">
      <div className="eyebrow" style={{ color: "#c49bff" }}>{s.label} · now {s.now}</div>
      <svg viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="none" style={{ width: "100%", height: 60 }} aria-label="Situation Difficulty ball by ball (0 = easier, 100 = harder)"><polyline fill="none" stroke="#c49bff" strokeWidth={2} points={pts} /></svg>
      <div className="mini">{s.definition} {s.not} {s.in_sample ? "This match is inside the model's training window (in-sample)." : ""}</div>
    </div>
  );
}

function BattleBox({ b }: { b: any }) {
  const h = b.history, t = b.today;
  return (
    <section className="mc-sec" aria-label="Current battle" data-testid="battle">
      <div className="eyebrow">Current battle <ProvBadge prov="OBSERVED" /></div>
      <div style={{ fontWeight: 900, fontSize: 17 }}>{b.batter.name} <span style={{ color: "var(--muted)" }}>v</span> {b.bowler.name}</div>
      {h ? (<>
        <div className="battle-mini">
          <div><b>{h.balls}</b><span>balls</span></div><div><b>{h.runs}</b><span>runs</span></div>
          <div><b>{h.sr ?? "–"}</b><span>SR (usual {h.usual_sr ?? "–"})</span></div><div><b>{h.outs}</b><span>out (exp {h.expected_outs ?? "–"})</span></div>
        </div>
        <div className="mini">{b.history_scope}. {h.matches} match{h.matches === 1 ? "" : "es"}, {h.first}–{h.last}.{h.small_sample ? " Small sample: under 60 balls." : ""}</div>
      </>) : <div className="mini">No covered meetings before this match ({b.history_scope}).</div>}
      <div className="cmp" style={{ marginTop: 6 }}>Today: <b>{t.runs}</b> off {t.balls}{t.outs ? `, out ${t.outs}` : ""}{t.fours || t.sixes ? ` · ${t.fours}×4 ${t.sixes}×6` : ""} · {t.dots} dots</div>
      <Link className="btn" style={{ marginTop: 8, display: "inline-block" }} href={b.href} data-testid="open-battle">Open battle →</Link>
      <div className="mini" style={{ marginTop: 4 }}>{b.href_note}</div>
    </section>
  );
}

function BatterRow({ b }: { b: any }) {
  const u = b.usual_at_stage;
  return (
    <div className="bat-row" data-testid="batter-state">
      <div className="nm">{b.name}{b.on_strike ? " *" : ""}</div>
      <div className="sc">{b.runs} <small>({b.balls})</small></div>
      <div className="meta">
        <span className="stage" title={b.stage_def}>{b.stage}</span>
        <span>SR {b.sr ?? "–"}</span><span>{b.fours}×4 · {b.sixes}×6 · {b.dots} dots</span>
        {u && <span className="cmp">usually <b>{u.sr}</b> at this stage ({u.balls} balls before this match)</span>}
        {b.last6?.length > 0 && <span>last balls faced: {b.last6.join(" ")}</span>}
      </div>
    </div>
  );
}

function BowlerBox({ w, thisOver }: { w: any; thisOver: any }) {
  const u = w.usual_in_phase, sp = w.spell;
  const his = thisOver && thisOver.bowler === w.name;
  return (
    <section className="mc-sec" aria-label="Bowler" data-testid="bowler-state">
      <div className="eyebrow">Bowler</div>
      <div className="bat-row" style={{ borderBottom: 0 }}>
        <div className="nm">{w.name}</div><div className="sc">{w.wickets ?? 0}-{w.runs ?? 0} <small>({w.overs ?? "0.0"})</small></div>
        <div className="meta">
          {sp && <span className="stage">spell {sp.number} · {sp.overs} over{sp.overs === 1 ? "" : "s"} so far</span>}
          {sp && <span>this spell {sp.overs_label} overs, {sp.runs} runs, {sp.wickets} wkt{sp.wickets === 1 ? "" : "s"} · {sp.dots} dot{sp.dots === 1 ? "" : "s"} · {sp.boundaries} boundar{sp.boundaries === 1 ? "y" : "ies"}</span>}
          {w.economy != null && <span>econ {w.economy}</span>}
          {u && <span className="cmp">usually <b>{u.econ}</b> in the {u.phase} ({u.balls} balls before this match)</span>}
        </div>
      </div>
      {thisOver?.balls?.length > 0 && <>
        <div className="mini" style={{ marginTop: 4 }}>{his ? `This over (${thisOver.over})` : `Last over (${thisOver.over}, ${thisOver.bowler})`}: {thisOver.runs} runs</div>
        <div className="balls" aria-label="Over">{thisOver.balls.map((g: any) => <Ball key={g.event_id} g={g} />)}</div></>}
      {w.links && <div style={{ marginTop: 8, display: "flex", gap: 8, flexWrap: "wrap" }}>
        <Link className="btn" href={w.links.fingerprint}>Bowler fingerprint →</Link>
        <Link className="btn" href={w.links.spell}>Full spell (leaves replay) →</Link></div>}
    </section>
  );
}

function Card({ d }: { d: any }) {
  const now = d.now || {};
  const regular = d.worm.filter((w: any) => !w.super_over);
  const maxOvers = d.meta.format === "ODI" ? 50 : 20;
  return (
    <div className="mc-grid">
      <div>
        <section className="mc-sec"><div className="eyebrow">Worm &amp; Manhattan, so far <ProvBadge prov="DERIVED" /></div>
          <Worm innings={regular.map((w: any) => ({ team: w.team, overs: w.overs.map((o: any) => ({ over: o.over - 1, runs: o.runs, wkts: o.wickets })) }))} maxOvers={maxOvers} /></section>
        <section className="mc-sec"><div className="eyebrow">Batting · {now.batting_team}</div>
          <div className="tablist">{(now.batting_card || []).map((b: any, i: number) => (
            <Link key={b.id} href={`/players/${b.id}`} className="trow"><span className="n">{i + 1}</span>
              <span><b>{b.name}</b><div className="mini">{b.out ? b.how : "not out"} · {b.fours}×4 {b.sixes}×6</div></span><span className="v">{b.runs}<span className="mini"> ({b.balls})</span></span></Link>))}</div>
          {now.extras && <div className="mini">Extras: {Object.entries(now.extras).filter(([, v]: any) => v).map(([k, v]: any) => `${k} ${v}`).join(", ") || "none"}</div>}
        </section>
      </div>
      <div>
        <section className="mc-sec"><div className="eyebrow">Bowling · {now.bowling_team}</div>
          <div className="tablist">{(now.bowling_card || []).map((w: any, i: number) => (
            <div key={w.id} className="trow"><span className="n">{i + 1}</span><span><b>{w.name}</b><div className="mini">{w.overs} ov · {w.maidens} m · {w.dots} dots</div></span>
              <span className="v">{w.wickets}/{w.runs}</span></div>))}</div></section>
        {now.fow?.length > 0 && <section className="mc-sec"><div className="eyebrow">Fall of wickets</div>
          <div className="mini" style={{ lineHeight: 1.7 }}>{now.fow.map((f: any) => `${f.score}/${f.wicket} (${f.player}, ${f.label})`).join(" · ")}</div></section>}
      </div>
    </div>
  );
}

function TimelineTab({ d }: { d: any }) {
  return (
    <div className="mc-grid">
      <section className="mc-sec" data-testid="timeline"><div className="eyebrow">Timeline, newest first <ProvBadge prov="OBSERVED" /></div>
        <ul className="tl">{d.timeline.map((e: any, i: number) => (
          <li key={i} className={e.kind}>{e.label && <span className="lbl">{e.label}</span>}{e.text}
            {e.event_id && <> · <Link href={`/delivery/${e.event_id}`} className="mini">ball →</Link></>}</li>))}</ul>
        <div className="mini">Factual events only, each with its definition: wickets, milestones, partnership and team landmarks, and sequences at or above the
          99th percentile of covered matches before this one. Ball links open the full delivery record, which leaves the replay.</div>
      </section>
      <section className="mc-sec" data-testid="record-watch"><div className="eyebrow">Record watch</div>
        {d.record_watch.length === 0 ? <div className="mini">Nothing is close to a milestone or a covered-data record at this point.</div> :
          d.record_watch.map((r: any) => <div key={r.key} className="rw">{r.text}<span className="note">{r.note}</span></div>)}
      </section>
    </div>
  );
}

function AskTab({ id, n, d }: { id: string; n: number; d: any }) {
  const [q, setQ] = useState("");
  const [a, setA] = useState<any | null>(null);
  const [busy, setBusy] = useState(false);
  const b = d.battle;
  const ex = ["How has this batter done against this bowler?", "How does this partnership compare?", `What usually happens when ${b?.batter?.name?.split(" ").slice(-1)[0] || "this batter"} has faced 30 balls?`,
    "Who has dismissed this batter most?", "Has this pair batted together before?", `Show ${b?.bowler?.name || "this bowler"}'s previous spells against this team`];
  const go = async (text: string) => { setQ(text); setBusy(true); try { setA((await api(`/live/${id}/ask`, { q: text, cursor: n })).data); } finally { setBusy(false); } };
  return (
    <section className="mc-sec" data-testid="match-ask">
      <div className="eyebrow">Ask about this match</div>
      <form onSubmit={(e) => { e.preventDefault(); if (q.trim().length > 2) go(q.trim()); }} style={{ display: "flex", gap: 8, marginTop: 6 }}>
        <input className="input" value={q} onChange={(e) => setQ(e.target.value)} placeholder="Ask about this batter, bowler or pair…" aria-label="Ask" style={{ flex: 1, minWidth: 0 }} />
        <button className="btn primary" disabled={busy}>Ask</button></form>
      <div className="chips" style={{ marginTop: 8 }}>{ex.map((x) => <button key={x} className="chip wrap" onClick={() => go(x)}>{x}</button>)}</div>
      <div className="mini" style={{ marginTop: 6 }}>&quot;This batter&quot;, &quot;this bowler&quot; and &quot;this pair&quot; mean the players at this ball. Answers use only matches before this one.</div>
      {a && (
        <div style={{ marginTop: 12 }} data-testid="ask-answer">
          <div className="chips">{(a.interpretation || a.context_chips || []).map((c: any, i: number) => <span key={i} className="chip">{c.label}</span>)}</div>
          <p style={{ fontSize: 15 }}>{a.answer || a.message}</p>
          {a.items && <div className="tablist">{a.items.slice(0, 6).map((it: any, i: number) => <Link key={i} className="trow" href={it.href}><span className="n">{i + 1}</span><span><b>{it.label}</b><div className="mini">{it.sub}</div></span><span className="v">{it.value}</span></Link>)}</div>}
          {a.caveat && <div className="mini">{a.caveat}</div>}
        </div>)}
    </section>
  );
}
