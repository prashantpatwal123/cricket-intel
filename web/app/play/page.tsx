"use client";
// What Happens Next? v1: real historical moments, Model vs You. No accounts: stats live in this browser only.
import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "@/lib/api";
import ProvBadge from "@/components/Prov";
import { DeliveryModal } from "@/components/Deliveries";

const KEYS: Record<string, string> = { "0": "DOT", ".": "DOT", d: "DOT", "1": "1", "2": "2", "3": "3", "4": "4", "6": "6", w: "WICKET" };
const KEY_HINT: Record<string, string> = { DOT: "0", "1": "1", "2": "2", "3": "3", "4": "4", "6": "6", WICKET: "W" };
const RARITY: Record<string, string> = { expected: "Expected", plausible: "Plausible", rare: "Rare", "very rare": "Very rare" };
type Store = { played: string[]; n: number; correct: number; points: number; streak: number; best: number; modelPoints: number; modelCorrect: number; beat: number };
const EMPTY: Store = { played: [], n: 0, correct: 0, points: 0, streak: 0, best: 0, modelPoints: 0, modelCorrect: 0, beat: 0 };
const load = (): Store => { try { const s = { ...EMPTY, ...JSON.parse(localStorage.getItem("whn1") || "{}") }; return s; } catch { return EMPTY; } };
const save = (s: Store) => { try { localStorage.setItem("whn1", JSON.stringify(s)); } catch { /* storage unavailable: stats last for this visit only */ } };
type Moment = { m: any; pts: Record<string, number> };

export default function Play() {
  const [st, setSt] = useState<Store>(EMPTY);
  const [cur, setCur] = useState<Moment | null>(null);
  const [rev, setRev] = useState<any | null>(null);
  const [open, setOpen] = useState<string | null>(null);
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
    const youRight = !!r.correct, modelRight = !!r.model.correct;
    const s: Store = { ...st, played: [...st.played, m.moment_id].slice(-500), n: st.n + 1, correct: st.correct + (youRight ? 1 : 0), points: st.points + r.points,
      streak: youRight ? st.streak + 1 : 0, best: Math.max(st.best, youRight ? st.streak + 1 : 0),
      modelPoints: st.modelPoints + (r.model.points || 0), modelCorrect: st.modelCorrect + (modelRight ? 1 : 0), beat: st.beat + (youRight && !modelRight ? 1 : 0) };
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

  return (
    <div className="fade-in" style={{ maxWidth: 720, margin: "0 auto" }}>
      <div className="section-head" style={{ marginTop: 20, marginBottom: 8 }}>
        <div><div className="kicker">Play · historical moments</div><div className="h2">What happens next?</div></div>
      </div>
      <div className="mvy" aria-label="Model versus you">
        <div className="mvy-side you"><div className="l">You</div><div className="v num">{st.points}</div><div className="mini">{st.correct}/{st.n} right{acc != null ? ` · ${acc}%` : ""}</div></div>
        <div className="mvy-mid"><div className="mini">streak</div><b className="num">{st.streak}</b><div className="mini">best {st.best}</div>
          <div className="mini" style={{ marginTop: 4 }}>beat the model <b className="num" style={{ color: "var(--accent-2)" }}>{st.beat}</b>×</div></div>
        <div className="mvy-side model"><div className="l">Model · modelled</div><div className="v num">{st.modelPoints}</div><div className="mini">{st.modelCorrect}/{st.n} right{macc != null ? ` · ${macc}%` : ""}</div></div>
      </div>
      <div className="mini" style={{ marginTop: 6 }}>The model always picks the outcome it rates most likely and scores by the same rules. A favourite is not a certainty: most balls, the most likely outcome still has well under a 50% chance.</div>

      {!m ? <div className="loading">Loading a moment…</div> : (
        <div className="hero fade-in" key={m.moment_id} style={{ marginTop: 12 }}>
          <div className="kicker">{m.competition} · {m.date} · {m.gender === "female" ? "Women" : "Men"} · {m.format}</div>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-end", marginTop: 8, gap: 10, flexWrap: "wrap" }}>
            <div>
              <div className="mini">{m.batting_team} v {m.bowling_team} · innings {m.innings_no}</div>
              <div className="hero-name" style={{ fontSize: "clamp(44px, 12vw, 72px)", margin: "4px 0" }}>{m.score}</div>
              <div className="mini">after {m.overs_completed} overs · next ball <b>{m.next_ball}</b> · {m.phase}</div>
            </div>
            {m.chase && <div className="hstat" style={{ minWidth: 150 }}><div className="v num">{m.chase.runs_required}</div><div className="l">needed off {m.chase.balls_remaining} · RRR {m.chase.required_rate}</div></div>}
          </div>
          <div className="grid2" style={{ marginTop: 14, gridTemplateColumns: "1fr 1fr" }}>
            <div className="hstat"><div className="l">On strike</div><div style={{ fontWeight: 800, fontSize: 17 }}>{m.batter.name}</div><div className="mini">{m.batter.runs} ({m.batter.balls}){m.batter.hand ? ` · ${m.batter.hand}-handed` : ""}</div></div>
            <div className="hstat"><div className="l">Bowling</div><div style={{ fontWeight: 800, fontSize: 17 }}>{m.bowler.name}</div><div className="mini">{m.bowler.figures}{m.bowler.style ? ` · ${m.bowler.style}` : ""}</div></div>
          </div>
          <div className="recent" aria-label="Previous balls">{m.recent.length ? m.recent.map((x: string, i: number) => <span key={i} className={`rb ${x === "W" ? "w" : x === "4" || x === "6" ? "b" : ""}`}>{x}</span>) : <span className="mini">start of the innings</span>}</div>
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
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", gap: 10, flexWrap: "wrap" }}>
            <div className="h2" style={{ color: rev.correct ? "var(--accent)" : "var(--text)" }}>{rev.correct ? `+${rev.points}` : "Not this time"}</div>
            <span className={`rar ${rev.rarity.label.replace(" ", "_")}`}>{RARITY[rev.rarity.label] ?? rev.rarity.label} · model gave it {(rev.rarity.p_actual * 100).toFixed(1)}%</span>
          </div>
          <div style={{ marginTop: 6, fontSize: 16 }}>It was <b>{rev.actual}</b>{rev.delivery.wickets?.[0] ? `: ${rev.delivery.wickets[0].player_out} ${rev.delivery.wickets[0].kind}` : ""}. <ProvBadge prov="OBSERVED" /></div>
          <div className="mini" style={{ marginTop: 4 }}>{rev.match_line} · {rev.delivery.venue}</div>
          <div className="vs-line">
            <span>You: <b>{rev.pick}</b> {rev.correct ? `✓ +${rev.points}` : "✗"}</span>
            <span>Model: <b>{rev.model.pick}</b> {rev.model.correct ? `✓ +${rev.model.points}` : "✗"}</span>
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
          <div className="mini" style={{ marginTop: 8 }}>An estimate from model {rev.model.version}, trained only on matches before {rev.model.trained_before}. Drivers: {rev.model.drivers.map((d: any) => `${d.factor}: ${d.effect}`).join(" · ")}</div>
          <div className="mini" style={{ marginTop: 6 }}>What followed: {rev.next_balls.map((x: string, i: number) => <b key={i} style={{ marginRight: 8 }}>{x}</b>)}</div>
          <div style={{ display: "flex", gap: 8, marginTop: 14, flexWrap: "wrap" }}>
            <button className="btn primary big" onClick={() => advance(st)} autoFocus>NEXT BALL →</button>
            <button className="btn" onClick={() => setOpen(rev.delivery.delivery_id)}>Inspect the delivery</button>
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
