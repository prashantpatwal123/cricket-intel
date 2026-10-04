"use client";
// What Happens Next? v2: real historical moments, Model vs You, a visual match situation, known-outcome-only reveal
// animation and session analytics. No accounts: stats live in this browser only.
import Link from "next/link";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { api } from "@/lib/api";
import ProvBadge from "@/components/Prov";
import { DeliveryModal } from "@/components/Deliveries";
import MatchSituation from "@/components/viz/MatchSituation";
import { Stumps } from "@/components/cricket/primitives";
import { OUTCOME_COLOR } from "@/lib/viz/model";

const KEYS: Record<string, string> = { "0": "DOT", ".": "DOT", d: "DOT", "1": "1", "2": "2", "3": "3", "4": "4", "6": "6", w: "WICKET" };
const KEY_HINT: Record<string, string> = { DOT: "0", "1": "1", "2": "2", "3": "3", "4": "4", "6": "6", WICKET: "W" };
const RARITY: Record<string, string> = { expected: "Expected", plausible: "Plausible", rare: "Rare", "very rare": "Very rare" };
type H = { pick: string; actual: string; p_pick: number; model_pick: string; ok: boolean; mok: boolean; pts: number; mpts: number };
type Store = { played: string[]; n: number; correct: number; points: number; streak: number; best: number; modelPoints: number; modelCorrect: number; beat: number; hist: H[] };
const EMPTY: Store = { played: [], n: 0, correct: 0, points: 0, streak: 0, best: 0, modelPoints: 0, modelCorrect: 0, beat: 0, hist: [] };
const load = (): Store => { try { return { ...EMPTY, ...JSON.parse(localStorage.getItem("whn1") || "{}") }; } catch { return EMPTY; } };
const save = (s: Store) => { try { localStorage.setItem("whn1", JSON.stringify(s)); } catch { /* storage unavailable: stats last for this visit only */ } };
type Moment = { m: any; pts: Record<string, number> };

export default function Play() {
  const [st, setSt] = useState<Store>(EMPTY);
  const [cur, setCur] = useState<Moment | null>(null);
  const [rev, setRev] = useState<any | null>(null);
  const [open, setOpen] = useState<string | null>(null);
  const [showStats, setShowStats] = useState(false);
  const nextRef = useRef<Promise<Moment> | null>(null);
  const fetchMoment = useCallback(async (played: string[]): Promise<Moment> => {
    const r = await api("/whn/next", { exclude: played.slice(-200).join(",") });
    const p = await api(`/whn/${r.data.moment_id}/points`);
    return { m: r.data, pts: p.data };
  }, []);
  const advance = useCallback(async (s: Store) => {
    setRev(null);
    const pending = nextRef.current; nextRef.current = null;
    setCur(null);
    setCur(await (pending ?? fetchMoment(s.played)));
  }, [fetchMoment]);
  useEffect(() => { const s = load(); setSt(s); advance(s); }, [advance]);

  const pick = useCallback(async (o: string) => {
    if (!cur || rev) return;
    const m = cur.m;
    const r = (await api(`/whn/${m.moment_id}/reveal`, { pick: o })).data;
    setRev(r);
    const ok = !!r.correct, mok = !!r.model.correct;
    const pPick = r.model.probs.find((x: any) => x.outcome === o)?.p ?? 0;
    const h: H = { pick: o, actual: r.actual, p_pick: pPick, model_pick: r.model.pick, ok, mok, pts: r.points, mpts: r.model.points || 0 };
    const s: Store = { ...st, played: [...st.played, m.moment_id].slice(-500), n: st.n + 1, correct: st.correct + (ok ? 1 : 0), points: st.points + r.points,
      streak: ok ? st.streak + 1 : 0, best: Math.max(st.best, ok ? st.streak + 1 : 0), modelPoints: st.modelPoints + (r.model.points || 0),
      modelCorrect: st.modelCorrect + (mok ? 1 : 0), beat: st.beat + (ok && !mok ? 1 : 0), hist: [...(st.hist || []), h].slice(-500) };
    setSt(s); save(s);
    nextRef.current = fetchMoment(s.played); // prefetch so NEXT BALL is instant
  }, [cur, rev, st, fetchMoment]);

  useEffect(() => {
    const h = (e: KeyboardEvent) => {
      if (e.target instanceof HTMLInputElement || open) return;
      const k = e.key.toLowerCase();
      if (!rev && KEYS[k]) { e.preventDefault(); pick(KEYS[k]); }
      else if (rev && (k === "enter" || k === "n" || k === " ")) { e.preventDefault(); advance(st); }
    };
    window.addEventListener("keydown", h);
    return () => window.removeEventListener("keydown", h);
  }, [pick, rev, st, advance, open]);

  const m = cur?.m, pts = cur?.pts;
  const acc = st.n ? Math.round((100 * st.correct) / st.n) : null;
  const macc = st.n ? Math.round((100 * st.modelCorrect) / st.n) : null;
  const reset = () => { const s = { ...EMPTY, played: st.played }; setSt(s); save(s); };
  const sess = useMemo(() => analytics(st.hist || []), [st.hist]);
  const after = rev ? afterScore(rev) : null;

  return (
    <div className="fade-in" style={{ maxWidth: 720, margin: "0 auto" }}>
      <div className="section-head" style={{ marginTop: 20, marginBottom: 8 }}>
        <div><div className="kicker">Play · historical moments</div><div className="h2">What happens next?</div></div>
        <button className="btn" onClick={() => setShowStats(!showStats)} aria-expanded={showStats}>{showStats ? "Hide" : "Session"} stats</button>
      </div>
      <div className="mvy" aria-label="Model versus you">
        <div className="mvy-side you"><div className="l">You</div><div className="v num">{st.points}</div><div className="mini">{st.correct}/{st.n} right{acc != null ? ` · ${acc}%` : ""}</div></div>
        <div className="mvy-mid"><div className="mini">streak</div><b className="num">{st.streak}</b><div className="mini">best {st.best}</div>
          <div className="mini" style={{ marginTop: 4 }}>beat the model <b className="num" style={{ color: "var(--accent-2)" }}>{st.beat}</b>×</div></div>
        <div className="mvy-side model"><div className="l">Model · modelled</div><div className="v num">{st.modelPoints}</div><div className="mini">{st.modelCorrect}/{st.n} right{macc != null ? ` · ${macc}%` : ""}</div></div>
      </div>
      {showStats && <SessionStats s={sess} st={st} />}

      {!m ? <div className="loading">Loading a moment…</div> : (
        <div className="hero fade-in" key={m.moment_id} style={{ marginTop: 12 }}>
          <div className="kicker">{m.competition} · {m.date} · {m.gender === "female" ? "Women" : "Men"} · {m.format}</div>
          <div className="mini" style={{ marginTop: 4 }}>{m.batting_team} v {m.bowling_team} · innings {m.innings_no}</div>
          <div style={{ marginTop: 10 }}>
            <MatchSituation s={{ ...m.situation, recent: m.recent, next_ball: m.next_ball,
              score: rev && after ? after.score : m.situation.score, wickets: rev && after ? after.wickets : m.situation.wickets }} />
          </div>
          <div className="grid2" style={{ marginTop: 12, gridTemplateColumns: "1fr 1fr" }}>
            <div className="hstat"><div className="l">On strike</div><div style={{ fontWeight: 800, fontSize: 17 }}>{m.batter.name}</div><div className="mini">{m.batter.runs} ({m.batter.balls}){m.batter.hand ? ` · ${m.batter.hand}-handed` : ""}</div></div>
            <div className="hstat"><div className="l">Bowling</div><div style={{ fontWeight: 800, fontSize: 17 }}>{m.bowler.name}</div><div className="mini">{m.bowler.figures}{m.bowler.style ? ` · ${m.bowler.style}` : ""}</div></div>
          </div>
        </div>
      )}

      {m && (
        <div className="card" style={{ marginTop: 12 }}>
          <div className="mini">{m.outcome_definition} Rarer calls score more (capped at 40).</div>
          <div className="picks">
            {m.options.map((o: string) => {
              const chosen = rev?.pick === o, actual = rev?.actual === o, modelPick = rev?.model.pick === o;
              return (
                <button key={o} onClick={() => pick(o)} disabled={!!rev} className={`pick ${o === "WICKET" ? "wkt" : ""} ${actual ? "actual" : ""} ${chosen && !actual ? "wrong" : ""}`}>
                  {o}
                  <span className="pp">{pts ? `${pts[o]} pts` : ""}{!rev && <span className="kbd"> · {KEY_HINT[o]}</span>}</span>
                  {modelPick && <span className="mtag">model</span>}
                </button>
              );
            })}
          </div>
        </div>
      )}

      {rev && (
        <div className="card fade-in" style={{ marginTop: 12, borderColor: rev.correct ? "var(--accent)" : "var(--line-2)" }}>
          <div className="reveal-banner">
            <span className="reveal-ball" style={{ background: OUTCOME_COLOR[rev.actual] + (rev.actual === "WICKET" ? "" : "55"), color: rev.actual === "WICKET" ? "#0b1020" : undefined }}>
              {rev.actual === "DOT" ? "•" : rev.actual === "WICKET" ? "W" : rev.actual}</span>
            {rev.actual === "WICKET" && <svg width="40" height="40" viewBox="0 0 40 40" aria-label="Wicket"><Stumps x={20} y={18} broken size={1.6} /></svg>}
            <div style={{ minWidth: 0 }}>
              <div className="h2" style={{ fontSize: 24, color: rev.correct ? "var(--accent)" : "var(--text)" }}>{rev.correct ? `+${rev.points}` : "Not this time"}</div>
              <div style={{ fontSize: 14 }}>It was <b>{rev.actual}</b>{rev.delivery.wickets?.[0] ? `: ${rev.delivery.wickets[0].player_out} ${rev.delivery.wickets[0].kind}` : ""}.
                {after && <> Score <span className="score-flip num" key={after.text}><b>{after.text}</b></span>.</>} <ProvBadge prov="OBSERVED" /></div>
            </div>
          </div>
          <div className="mini" style={{ marginTop: 6 }}>{rev.match_line} · {rev.delivery.venue} · only the recorded outcome is shown; how the ball was played is not in the data.</div>
          <div className="vs-line">
            <span>You: <b>{rev.pick}</b> {rev.correct ? `✓ +${rev.points}` : "✗"}</span>
            <span>Model: <b>{rev.model.pick}</b> {rev.model.correct ? `✓ +${rev.model.points}` : "✗"}</span>
            <span className={`rar ${rev.rarity.label.replace(" ", "_")}`}>{RARITY[rev.rarity.label] ?? rev.rarity.label} · model gave it {(rev.rarity.p_actual * 100).toFixed(1)}%</span>
            {rev.correct && !rev.model.correct && <span style={{ color: "var(--accent-2)", fontWeight: 800 }}>You beat the model</span>}
          </div>
          <div className="sit-title" style={{ marginTop: 14 }}>How likely the model thought each outcome was <ProvBadge prov="MODELLED" /></div>
          <div style={{ marginTop: 6 }}>
            {rev.model.probs.map(({ outcome: k, p: v }: any) => (
              <div key={k} className="prow">
                <span style={{ fontWeight: 800, color: k === rev.actual ? "var(--accent)" : undefined }}>{k}{k === rev.pick ? " ·you" : ""}</span>
                <span className="bar" style={{ height: 8, gridColumn: "auto" }}><span style={{ width: `${v * 100}%`, background: k === rev.actual ? "var(--accent)" : "var(--mod)" }} /></span>
                <span className="num mini">{(v * 100).toFixed(1)}%</span>
              </div>
            ))}
          </div>
          <div className="mini" style={{ marginTop: 8 }}>An estimate from model {rev.model.version}, trained only on matches before {rev.model.trained_before}. Even its favourite usually has well under a 50% chance. Drivers: {rev.model.drivers.map((d: any) => `${d.factor}: ${d.effect}`).join(" · ")}</div>
          <div className="mini" style={{ marginTop: 6 }}>What followed: {rev.next_balls.map((x: string, i: number) => <b key={i} style={{ marginRight: 8 }}>{x}</b>)}</div>
          <div style={{ display: "flex", gap: 8, marginTop: 14, flexWrap: "wrap" }}>
            <button className="btn primary big" onClick={() => advance(st)} autoFocus>NEXT BALL →</button>
            <button className="btn" onClick={() => setOpen(rev.delivery.delivery_id)}>Inspect the delivery</button>
            <Link className="btn" href={`/delivery/${encodeURIComponent(rev.delivery.delivery_id)}`}>Full replay</Link>
          </div>
          <div className="kbd" style={{ marginTop: 8 }}>Keys: 0 1 2 3 4 6 W to pick · Enter for the next ball</div>
        </div>
      )}
      <div style={{ marginTop: 18, textAlign: "center" }}><button className="btn" style={{ fontSize: 12 }} onClick={reset}>Reset my score</button>
        <div className="mini" style={{ marginTop: 6 }}>No account: your score is kept in this browser only.</div></div>
      {open && <DeliveryModal id={open} onClose={() => setOpen(null)} />}
    </div>
  );
}

function afterScore(rev: any) {
  const sa = rev.delivery?.score_after;
  if (!sa) return null;
  const [s, w] = String(sa).split("/").map(Number);
  return { score: s, wickets: w, text: `${rev.delivery.score_before} → ${sa}` };
}

function analytics(h: H[]) {
  const n = h.length;
  const bands = [[0, 0.1], [0.1, 0.25], [0.25, 0.5], [0.5, 1.01]].map(([a, b]) => {
    const x = h.filter((r) => r.p_pick >= a && r.p_pick < b);
    return { band: `${Math.round(100 * a)}–${Math.min(100, Math.round(100 * b))}%`, n: x.length, hit: x.length ? x.filter((r) => r.ok).length / x.length : null,
             p: x.length ? x.reduce((t, r) => t + r.p_pick, 0) / x.length : null };
  });
  const cats: Record<string, { n: number; ok: number; p: number }> = {};
  for (const r of h) { const c = (cats[r.pick] ||= { n: 0, ok: 0, p: 0 }); c.n++; c.ok += r.ok ? 1 : 0; c.p += r.p_pick; }
  const rated = Object.entries(cats).filter(([, c]) => c.n >= 3).map(([k, c]) => ({ k, n: c.n, hit: c.ok / c.n, edge: c.ok / c.n - c.p / c.n }));
  rated.sort((a, b) => b.edge - a.edge);
  return { n, pts: h.reduce((t, r) => t + r.pts, 0), mpts: h.reduce((t, r) => t + r.mpts, 0), acc: n ? h.filter((r) => r.ok).length / n : null,
           macc: n ? h.filter((r) => r.mok).length / n : null, bands, strongest: rated[0], weakest: rated.length > 1 ? rated[rated.length - 1] : null };
}

function SessionStats({ s, st }: { s: ReturnType<typeof analytics>; st: Store }) {
  if (!s.n) return <div className="empty" style={{ marginTop: 10 }}>Make a few predictions to see your session analytics.</div>;
  const pc = (x: number | null) => (x == null ? "–" : `${Math.round(100 * x)}%`);
  return (
    <div className="card fade-in" style={{ marginTop: 10 }}>
      <div className="sess">
        <div><b className="num">{s.n}</b><span className="mini">predictions</span></div>
        <div><b className="num">{pc(s.acc)}</b><span className="mini">your accuracy</span></div>
        <div><b className="num">{pc(s.macc)}</b><span className="mini">model accuracy</span></div>
        <div><b className="num">{st.points}</b><span className="mini">your points</span></div>
        <div><b className="num">{st.modelPoints}</b><span className="mini">model points</span></div>
        <div><b className="num" style={{ color: st.points >= st.modelPoints ? "var(--accent)" : "var(--wicket)" }}>{st.points - st.modelPoints > 0 ? "+" : ""}{st.points - st.modelPoints}</b><span className="mini">you v model</span></div>
      </div>
      <div className="sit-title" style={{ marginTop: 12 }}>Calibration: when the model rated your pick at…</div>
      <div className="calib">
        {s.bands.filter((b) => b.n).map((b) => (
          <div key={b.band} className="calib-row"><span className="mini">{b.band}</span>
            <span className="calib-t"><i style={{ width: `${100 * (b.hit ?? 0)}%`, background: "#35e0c266" }} /><b style={{ left: `${100 * (b.p ?? 0)}%` }} /></span>
            <span className="mini num">you {pc(b.hit)} · n={b.n}</span></div>
        ))}
      </div>
      <div className="mini">Bar = how often you were right; tick = the model&apos;s average probability for those picks. Bar beyond the tick = you did better than the model expected.</div>
      {s.strongest && <div className="mini" style={{ marginTop: 8 }}>Strongest call: <b style={{ color: "var(--accent)" }}>{s.strongest.k}</b> (right {pc(s.strongest.hit)} of {s.strongest.n}){s.weakest && s.weakest.k !== s.strongest.k ? <> · weakest: <b style={{ color: "var(--wicket)" }}>{s.weakest.k}</b> (right {pc(s.weakest.hit)} of {s.weakest.n})</> : null}. Ranked against what the model expected for those picks; needs 3+ picks per outcome.</div>}
    </div>
  );
}
