"use client";
// Innings Story: a real innings from first ball to the end, scrubbable. Every ball opens Delivery Replay.
import Link from "next/link";
import { useParams, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useMemo, useState } from "react";
import { api, fmt } from "@/lib/api";
import ProvBadge from "@/components/Prov";
import ExploreNext from "@/components/ExploreNext";
import InningsJourney from "@/components/viz/InningsJourney";
import MatchSituation from "@/components/viz/MatchSituation";
import OutcomeMap from "@/components/viz/OutcomeMap";
import { symbolToOutcome } from "@/lib/viz/model";

export default function Page() { return <Suspense fallback={<div className="loading">Loading…</div>}><Story /></Suspense>; }

function Story() {
  const { match, inn, pid } = useParams<{ match: string; inn: string; pid: string }>();
  const sp = useSearchParams();
  const [s, setS] = useState<any | null>(null);
  const [err, setErr] = useState(false);
  const [sel, setSel] = useState(0);
  useEffect(() => {
    api(`/innings/${match}/${inn}/${pid}`).then((r) => {
      setS(r.data);
      const want = sp.get("ball");
      const i = want ? r.data.balls.findIndex((b: any) => b.delivery_id === want) : -1;
      setSel(i >= 0 ? i : Math.max(0, r.data.balls.findIndex((b: any) => b.out) >= 0 ? r.data.balls.findIndex((b: any) => b.out) : r.data.balls.length - 1));
    }).catch(() => setErr(true));
  }, [match, inn, pid]);
  useEffect(() => {
    const h = (e: KeyboardEvent) => { if (!s) return; if (e.key === "ArrowLeft") setSel((x) => Math.max(0, x - 1)); if (e.key === "ArrowRight") setSel((x) => Math.min(s.balls.length - 1, x + 1)); };
    window.addEventListener("keydown", h); return () => window.removeEventListener("keydown", h);
  }, [s]);
  const counts = useMemo(() => {
    const c: Record<string, number> = {};
    for (const b of s?.balls || []) if (b.on_strike) { const o = b.out ? "WICKET" : symbolToOutcome(b.symbol); if (o) c[o] = (c[o] || 0) + 1; }
    return c;
  }, [s]);
  if (err) return <div className="empty" style={{ marginTop: 30 }}>Innings not found.</div>;
  if (!s) return <div className="loading">Loading the innings…</div>;
  const m = s.match, sm = s.summary, b = s.balls[sel];
  const [sc, wk] = String(b.score_before).split("/").map(Number);
  const limit = (m.format_group === "T20" ? 120 : 300);
  const lb = (() => { const [o, bl] = String(b.ball_label).split(".").map(Number); return o * 6 + Math.max(0, bl - 1); })();
  return (
    <div className="fade-in">
      <section className="hero">
        <div className="kicker">Innings story · {m.competition} · {m.start_date} · {m.format_group}</div>
        <h1 className="hero-name" style={{ fontSize: "clamp(36px, 10vw, 64px)" }}>{s.batter.name}</h1>
        <div className="h2" style={{ fontSize: 26 }}>{sm.runs}{sm.not_out ? "*" : ""} <span className="mini" style={{ fontSize: 16 }}>off {sm.balls} balls · SR {sm.strike_rate} · {sm.fours}×4 · {sm.sixes}×6 · {sm.dots} dots</span></div>
        <div className="mini" style={{ marginTop: 6 }}>{s.teams.batting_team} v {s.teams.bowling_team} · innings {s.innings_no} · in at {sm.arrived} ({sm.arrived_over}) ·
          {sm.not_out ? " not out" : ` out: ${sm.how_out.kind}`} · {m.result_line} <ProvBadge prov="OBSERVED" /></div>
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginTop: 10 }}>
          <Link className="btn primary" href={`/story/innings/${match}/${inn}/${pid}`}>How it unfolded (story) →</Link>
          <Link className="btn" href={`/match/${match}`}>The match →</Link>
          <Link className="btn" href={`/share?type=innings&m=${match}&i=${inn}&pid=${pid}`}>Share card</Link>
        </div>
      </section>

      <section className="section" style={{ marginTop: 14 }}>
        <div className="section-head"><div><div className="kicker">The journey</div><div className="h2">Ball by ball</div>
          <div className="sub">Scrub, use ← →, or tap a ball. Balls at the other end appear as small marks below the line.</div></div></div>
        <div className="card"><InningsJourney story={s} sel={sel} onSel={setSel} /></div>
      </section>

      <section className="section" style={{ marginTop: 12 }}>
        <div className="grid2">
          <div className="card fade-in" key={b.seq}>
            <div className="kicker">Ball {b.ball_label} · {b.on_strike ? `${s.batter.name} on strike` : `${b.partner} on strike`}</div>
            <div className="h2" style={{ fontSize: 24, marginTop: 4 }}>{b.symbol === "•" ? "Dot ball" : b.symbol === "W" ? "Wicket" : b.symbol} <span className="mini">from {b.bowler}</span></div>
            <div className="mini" style={{ marginTop: 4 }}>{s.batter.name}: {b.cum_runs} ({b.cum_balls}) after this ball{b.rolling_sr != null ? ` · last-10-ball SR ${b.rolling_sr}` : ""} · partner {b.partner}</div>
            {(b.out || b.partner_out) && <div className="note" style={{ borderColor: "#ff5c7466", color: "#ffd0d8", background: "#ff5c740f" }}>{(b.out || b.partner_out).player_out} out: {(b.out || b.partner_out).kind}{(b.out || b.partner_out).fielder ? ` (${(b.out || b.partner_out).fielder})` : ""}</div>}
            {b.sdx != null && <div className="mini" style={{ marginTop: 6 }}><span className="exp-tag">Experimental</span> Situation Difficulty {b.sdx}</div>}
            <Link className="btn primary" style={{ display: "inline-block", marginTop: 10 }} href={`/delivery/${encodeURIComponent(b.delivery_id)}`}>Open delivery replay →</Link>
            <div style={{ marginTop: 12 }}>
              <MatchSituation compact s={{ format: m.format_group, innings_no: s.innings_no, score: sc, wickets: wk, legal_balls: lb, limit_balls: limit,
                target: b.runs_required != null ? sc + b.runs_required : null, runs_required: b.runs_required, balls_left: b.balls_left,
                rrr: b.required_rate, crr: lb ? (6 * sc) / lb : null, phase: b.phase }} />
            </div>
          </div>
          <div className="card">
            <OutcomeMap counts={counts} title="How the balls faced turned out" />
            <div className="sit-title" style={{ marginTop: 14 }}>Partnerships</div>
            {s.partnerships.map((p: any) => (
              <div key={p.partnership_id} className="part-row">
                <span><b>{p.partner}</b> <span className="mini">for the {p.wicket_no + 1}{["st", "nd", "rd"][p.wicket_no] ?? "th"} wkt</span></span>
                <span className="num">{p.runs} <span className="mini">({p.balls})</span></span>
                <span className="part-split" title={`${s.batter.name} ${p.my_runs}, ${p.partner} ${p.partner_runs}`}>
                  <i style={{ width: `${p.runs ? (100 * p.my_runs) / p.runs : 0}%` }} /></span>
              </div>
            ))}
            <div className="mini" style={{ marginTop: 6 }}>Bar = {s.batter.name}&apos;s share of each partnership (extras excluded from the split). <ProvBadge prov="DERIVED" /></div>
          </div>
        </div>
      </section>

      <section className="section">
        <div className="section-head"><div><div className="kicker">Moments</div><div className="h2">How it unfolded</div></div></div>
        <div className="card">
          {s.events.map((e: any, i: number) => (
            <button key={i} className="ev-row" onClick={() => setSel(Math.max(0, s.balls.findIndex((x: any) => x.seq >= e.seq)))}>
              <span className="mini num">{e.ball_label}</span><span className={`ev-k ${e.kind}`}>{e.kind.replace("_", " ")}</span><span>{e.label}</span>
            </button>
          ))}
          <div className="mini" style={{ marginTop: 8 }}>Strike changed {sm.strike_changes} times. {fmt(sm.team_deliveries_at_crease)} deliveries were bowled while {s.batter.name} was in.</div>
        </div>
      </section>
      <ExploreNext type="innings" id={`${match}|${inn}|${pid}`} />
    </div>
  );
}
