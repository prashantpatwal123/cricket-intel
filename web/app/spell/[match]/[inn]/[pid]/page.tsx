"use client";
// Spell Story: a bowler's overs in one innings, over by over and ball by ball. Every ball opens Delivery Replay.
import Link from "next/link";
import { useParams, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useMemo, useState } from "react";
import { api } from "@/lib/api";
import ProvBadge from "@/components/Prov";
import SpellJourney from "@/components/viz/SpellJourney";
import OutcomeMap from "@/components/viz/OutcomeMap";
import { symbolToOutcome } from "@/lib/viz/model";

export default function Page() { return <Suspense fallback={<div className="loading">Loading…</div>}><Spell /></Suspense>; }

function Spell() {
  const { match, inn, pid } = useParams<{ match: string; inn: string; pid: string }>();
  const sp = useSearchParams();
  const [s, setS] = useState<any | null>(null);
  const [err, setErr] = useState(false);
  const [sel, setSel] = useState<any | null>(null);
  useEffect(() => {
    api(`/spells/${match}/${inn}/${pid}`).then((r) => {
      setS(r.data);
      const want = sp.get("ball");
      const all = r.data.overs.flatMap((o: any) => o.balls_list);
      setSel(all.find((b: any) => b.delivery_id === want) || all.find((b: any) => b.wicket) || all[0]);
    }).catch(() => setErr(true));
  }, [match, inn, pid]);
  const counts = useMemo(() => {
    const c: Record<string, number> = {};
    for (const o of s?.overs || []) for (const b of o.balls_list) { const k = b.wicket ? "WICKET" : symbolToOutcome(b.symbol); if (k) c[k] = (c[k] || 0) + 1; }
    return c;
  }, [s]);
  if (err) return <div className="empty" style={{ marginTop: 30 }}>Spell not found.</div>;
  if (!s) return <div className="loading">Loading the spell…</div>;
  const m = s.match, t = s.totals;
  return (
    <div className="fade-in">
      <section className="hero">
        <div className="kicker">Spell story · {m.competition} · {m.start_date} · {m.format_group}</div>
        <h1 className="hero-name" style={{ fontSize: "clamp(36px, 10vw, 64px)" }}>{s.bowler.name}</h1>
        <div className="h2" style={{ fontSize: 26 }}>{t.wickets}/{t.runs} <span className="mini" style={{ fontSize: 16 }}>from {Math.floor(t.balls / 6)}.{t.balls % 6} overs · economy {t.economy} · {t.dots} dots · longest dot run {t.longest_dot_sequence}</span></div>
        <div className="mini" style={{ marginTop: 6 }}>Innings {s.innings_no} · {m.result_line} · {s.spells.length} spell{s.spells.length > 1 ? "s" : ""} <ProvBadge prov="DERIVED" /></div>
      </section>
      <section className="section" style={{ marginTop: 14 }}>
        <div className="section-head"><div><div className="kicker">Over by over</div><div className="h2">The spell</div>
          <div className="sub">Bar = runs conceded in the over; score and required rate at the start of each over. Tap any ball.</div></div></div>
        <div className="card"><SpellJourney story={s} sel={sel?.delivery_id ?? null} onSel={setSel} /></div>
        <div className="mini" style={{ marginTop: 6 }}>{s.spell_definition}</div>
      </section>
      <section className="section" style={{ marginTop: 12 }}>
        <div className="grid2">
          <div className="card">
            {sel && <div className="fade-in" key={sel.delivery_id}>
              <div className="kicker">Ball {sel.ball_label} · to {sel.batter} ({sel.batter_stage} batter)</div>
              <div className="h2" style={{ fontSize: 24, marginTop: 4 }}>{sel.wicket ? `${sel.wicket.player_out}: ${sel.wicket.kind}` : sel.symbol === "•" ? "Dot ball" : sel.symbol}</div>
              <div className="mini">{sel.runs_conceded} run{sel.runs_conceded === 1 ? "" : "s"} conceded{sel.sdx != null ? ` · experimental difficulty ${sel.sdx}` : ""}</div>
              <Link className="btn primary" style={{ display: "inline-block", marginTop: 10 }} href={`/delivery/${encodeURIComponent(sel.delivery_id)}`}>Open delivery replay →</Link>
            </div>}
            <div className="sit-title" style={{ marginTop: 14 }}>Batters faced</div>
            {s.batters.map((b: any) => (
              <Link key={b.batter_id} href={`/battle?bat=${b.batter_id}&bowl=${s.bowler.id}`} className="res" style={{ marginTop: 4 }}>
                <span>{b.batter}</span><span className="num">{b.runs} off {b.balls}{b.dismissed ? <b className="wk"> · out</b> : ""}</span></Link>
            ))}
          </div>
          <div className="card"><OutcomeMap counts={counts} title="Every ball of the spell" unit="deliveries (wides and no-balls not shown)" /></div>
        </div>
      </section>
    </div>
  );
}
