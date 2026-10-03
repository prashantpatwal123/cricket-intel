"use client";
import { useCallback, useEffect, useState } from "react";
import { api } from "@/lib/api";
import ProvBadge from "@/components/Prov";
import { DeliveryModal } from "@/components/Deliveries";

const LABEL: Record<string, string> = { DOT: "DOT", "1": "1", "2": "2", "3": "3", "4": "4", "6": "6", WICKET: "WICKET" };
type Store = { played: string[]; correct: number; points: number; streak: number; best: number };
const EMPTY: Store = { played: [], correct: 0, points: 0, streak: 0, best: 0 };
const load = (): Store => { try { return { ...EMPTY, ...JSON.parse(localStorage.getItem("whn") || "{}") }; } catch { return EMPTY; } };
const save = (s: Store) => { try { localStorage.setItem("whn", JSON.stringify(s)); } catch { /* storage unavailable */ } };

export default function Play() {
  const [st, setSt] = useState<Store>(EMPTY);
  const [m, setM] = useState<any | null>(null);
  const [pts, setPts] = useState<Record<string, number> | null>(null);
  const [rev, setRev] = useState<any | null>(null);
  const [open, setOpen] = useState<string | null>(null);
  const next = useCallback(async (s: Store) => {
    setRev(null); setPts(null);
    const r = await api("/whn/next", { exclude: s.played.slice(-200).join(",") });
    setM(r.data);
    setPts((await api(`/whn/${r.data.moment_id}/points`)).data);
  }, []);
  useEffect(() => { const s = load(); setSt(s); next(s); }, [next]);
  const pick = async (o: string) => {
    if (!m || rev) return;
    const r = (await api(`/whn/${m.moment_id}/reveal`, { pick: o })).data;
    setRev(r);
    const s = { ...st, played: [...st.played, m.moment_id], correct: st.correct + (r.correct ? 1 : 0), points: st.points + r.points,
      streak: r.correct ? st.streak + 1 : 0, best: Math.max(st.best, r.correct ? st.streak + 1 : 0) };
    setSt(s); save(s);
  };
  return (
    <div className="fade-in" style={{ maxWidth: 720, margin: "0 auto" }}>
      <div className="section-head" style={{ marginTop: 22 }}>
        <div><div className="kicker">Historical · What happens next?</div><div className="h2">Call the next ball</div></div>
        <div className="mini" style={{ textAlign: "right" }}>{st.points} pts · {st.correct}/{st.played.length} correct<br />streak {st.streak} · best {st.best}</div>
      </div>
      {!m ? <div className="loading">Loading a moment…</div> : (
        <div className="hero" style={{ marginTop: 6 }}>
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
          <div className="mini" style={{ marginTop: 10 }}>Last balls: {m.recent.length ? m.recent.map((x: string, i: number) => <b key={i} style={{ marginRight: 8, color: x === "W" ? "var(--wicket)" : undefined }}>{x}</b>) : "start of innings"}</div>
        </div>
      )}
      {m && (
        <div className="card" style={{ marginTop: 14 }}>
          <div className="sit-title">What happens next?</div>
          <div className="mini">{m.outcome_definition} Correct picks score the points shown. Rarer calls are worth more, capped at 40.</div>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 8, marginTop: 12 }}>
            {m.options.map((o: string) => {
              const chosen = rev?.pick === o, actual = rev?.actual === o;
              return (
                <button key={o} onClick={() => pick(o)} disabled={!!rev}
                  style={{ gridColumn: o === "WICKET" ? "span 2" : undefined, padding: "14px 6px", borderRadius: 14, fontWeight: 900, fontSize: 18,
                    fontFamily: "var(--display)", border: `2px solid ${actual ? "var(--accent)" : chosen ? "var(--wicket)" : "var(--line-2)"}`,
                    background: actual ? "#35e0c22a" : chosen ? "#ff5c741f" : "var(--surface)", color: o === "WICKET" ? "var(--wicket)" : "var(--text)" }}>
                  {LABEL[o]}<div style={{ fontSize: 11, fontWeight: 700, color: "var(--muted)", fontFamily: "var(--font)" }}>{pts ? `${pts[o]} pts` : ""}</div>
                </button>
              );
            })}
          </div>
        </div>
      )}
      {rev && (
        <div className="card fade-in" style={{ marginTop: 14, borderColor: rev.correct ? "var(--accent)" : "var(--wicket)" }}>
          <div className="h2" style={{ color: rev.correct ? "var(--accent)" : "var(--wicket)" }}>{rev.correct ? `CORRECT · +${rev.points}` : "NOT THIS TIME"}</div>
          <div style={{ marginTop: 6, fontSize: 16 }}>It was <b>{rev.actual}</b>{rev.delivery.wickets?.[0] ? `: ${rev.delivery.wickets[0].player_out} ${rev.delivery.wickets[0].kind}` : ""}. <ProvBadge prov="OBSERVED" /></div>
          <div className="sit-title" style={{ marginTop: 14 }}>What the model expected <ProvBadge prov="MODELLED" /></div>
          <div className="mini">Model {rev.model.version}, trained only on matches before {rev.model.trained_before}. It&apos;s an estimate, not a fact.</div>
          <div style={{ marginTop: 8 }}>
            {rev.model.probs.map(({ outcome: k, p: v }: any) => (
              <div key={k} style={{ display: "grid", gridTemplateColumns: "70px 1fr 50px", gap: 8, alignItems: "center", marginTop: 4, fontSize: 13 }}>
                <span style={{ fontWeight: 800, color: k === rev.actual ? "var(--accent)" : undefined }}>{k}</span>
                <span className="bar" style={{ height: 8, gridColumn: "auto" }}><span style={{ width: `${v * 100}%`, background: k === rev.actual ? "var(--accent)" : "var(--mod)" }} /></span>
                <span className="num mini">{(v * 100).toFixed(1)}%</span>
              </div>
            ))}
          </div>
          <div className="mini" style={{ marginTop: 8 }}>Drivers: {rev.model.drivers.map((d: any) => `${d.factor}: ${d.effect}`).join(" · ")}</div>
          <div className="mini" style={{ marginTop: 8 }}>Next balls: {rev.next_balls.map((x: string, i: number) => <b key={i} style={{ marginRight: 8 }}>{x}</b>)}</div>
          <div style={{ display: "flex", gap: 8, marginTop: 14 }}>
            <button className="btn" onClick={() => setOpen(rev.delivery.delivery_id)}>Inspect the delivery</button>
            <button className="btn primary" onClick={() => next(st)}>Next moment →</button>
          </div>
        </div>
      )}
      {open && <DeliveryModal id={open} onClose={() => setOpen(null)} />}
    </div>
  );
}
