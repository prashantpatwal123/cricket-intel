"use client";
// Player × Player battle. Evidence and uncertainty, never a winner label.
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";
import { api, fmt } from "@/lib/api";
import PlayerPicker from "@/components/PlayerPicker";
import Deliveries from "@/components/Deliveries";
import ProvBadge from "@/components/Prov";
import { C, Crease, Defs, Figure, Pitch, Stumps } from "@/components/cricket/primitives";
import OutcomeMap from "@/components/viz/OutcomeMap";

type P = { person_id: string; name: string } | null;
const BREAKS = [["phase", "Phase"], ["innings", "Setting / chasing"], ["year", "Year"], ["format", "Format"]] as const;
const bucketLabel = (by: string, b: any) => by === "innings" ? (b === 1 ? "Setting (1st inns)" : b === 2 ? "Chasing (2nd inns)" : `Innings ${b}`)
  : by === "phase" ? ({ powerplay: "Powerplay", middle: "Middle overs", death: "Death overs" } as any)[b] ?? b : String(b);

export default function Page() { return <Suspense fallback={<div className="loading">Loading…</div>}><Battle /></Suspense>; }

function Battle() {
  const sp = useSearchParams();
  const router = useRouter();
  const batId = sp.get("bat"), bowlId = sp.get("bowl");
  const [bat, setBat] = useState<P>(null), [bowl, setBowl] = useState<P>(null);
  const [d, setD] = useState<any | null>(null);
  const [notable, setNotable] = useState<any[] | null>(null);
  const [by, setBy] = useState<string>("phase");
  const [drill, setDrill] = useState<{ title: string; q: any } | null>(null);

  const push = (b: P, w: P) => {
    const n = new URLSearchParams();
    if (b) n.set("bat", b.person_id); if (w) n.set("bowl", w.person_id);
    router.replace(`/battle${n.toString() ? "?" + n : ""}`, { scroll: false });
  };
  useEffect(() => {
    setDrill(null);
    if (batId && bowlId) { setD(null); api("/battle", { bat: batId, bowl: bowlId }).then((r) => { setD(r.data); setBat(r.data.batter); setBowl(r.data.bowler); }).catch(() => setD({ error: true })); }
    else setD(null);
  }, [batId, bowlId]);
  useEffect(() => { api<any[]>("/battles/notable", { limit: 16 }).then((r) => setNotable(r.data)); }, []);
  const onDrill = (title: string, q: any) => { setDrill({ title, q }); setTimeout(() => document.getElementById("evidence")?.scrollIntoView({ behavior: "smooth" }), 60); };
  const t = d?.total;

  return (
    <div className="fade-in">
      <section className="section" style={{ marginTop: 22 }}>
        <div className="kicker">Battles</div>
        <h1 className="big-title" style={{ fontSize: "clamp(34px, 8vw, 58px)", margin: "6px 0 14px" }}>Batter v bowler</h1>
        <div className="battle-hero">
          <PlayerPicker label="Batter" value={bat} onPick={(p) => { setBat(p); push(p, bowl); }} placeholder="Search a batter…" />
          <div className="vs">v</div>
          <PlayerPicker label="Bowler" value={bowl} onPick={(p) => { setBowl(p); push(bat, p); }} placeholder="Search a bowler…" />
        </div>
        <div className="mini" style={{ marginTop: 8 }}>
          <Link href="/compare" style={{ textDecoration: "underline" }}>Compare 2–4 players side by side →</Link>{" · "}
          <Link href="/partnerships" style={{ textDecoration: "underline" }}>Best partnerships →</Link>
        </div>
      </section>

      {batId && bowlId && !d && <div className="loading">Loading the battle…</div>}
      {d?.error && <div className="empty">Couldn&apos;t load this battle.</div>}
      {d && !d.error && !d.met && <div className="empty" style={{ marginTop: 16 }}>{d.batter.name} hasn&apos;t faced {d.bowler.name} in our covered data.</div>}

      {d?.met && (<>
        <section className="hero">
          <div className="kicker">{t.matches} matches · {t.first_date} → {t.last_date} <ProvBadge prov="OBSERVED" /></div>
          <div className="h2" style={{ fontSize: "clamp(26px, 7vw, 40px)", marginTop: 6 }}>
            <Link href={`/players/${d.batter.person_id}`}>{d.batter.name}</Link> <span style={{ color: "var(--muted)" }}>v</span> <Link href={`/players/${d.bowler.person_id}`}>{d.bowler.name}</Link></div>
          <div className="statstrip">
            {[["Balls", t.balls], ["Runs", t.runs], ["Dots", t.dots], ["Singles", t.singles], ["4s", t.fours], ["6s", t.sixes], ["Outs", t.dismissals], ["SR", fmt(t.strike_rate, 1)]].map(([l, v]) => (
              <div key={l as string}><b className={`num ${l === "Outs" ? "wk" : ""}`}>{v as any}</b><span className="mini">{l}</span></div>
            ))}
          </div>
          <div className="mini" style={{ marginTop: 8 }}>Runs per dismissal: <b>{t.runs_per_dismissal != null ? fmt(t.runs_per_dismissal, 1) : "no dismissals"}</b> · dot balls {fmt(t.dot_pct, 1)}% · boundaries {fmt(t.boundary_pct, 1)}% of balls faced. 2s and 3s: {t.twos_threes}.</div>
        </section>

        <section className="section">
          <div className="grid2">
            <div className="card">
              <div className="sit-title">How the {t.dismissals} dismissal{t.dismissals === 1 ? "" : "s"} happened</div>
              <BattleScene d={d} onPick={(r: any) => onDrill(`${d.batter.name} ${r.label.toLowerCase()} by ${d.bowler.name}`, { ...d.evidence_query, out_id: d.batter.person_id, route: r.route })} />
            </div>
            <Edge d={d} />
          </div>
        </section>

        <section className="section">
          <div className="card">
            <OutcomeMap title="Every ball faced in this battle" counts={{ DOT: Math.max(0, t.dots - t.dismissals), "1": t.singles, "2": t.twos, "3": t.threes,
              "4": t.fours, "6": t.sixes, WICKET: t.dismissals }} />
            <div className="mini" style={{ marginTop: 4 }}>DOT excludes balls on which the batter was dismissed (shown as WICKET).{t.fives ? ` ${t.fives} ball(s) with 5 runs are not shown.` : ""}</div>
          </div>
        </section>

        <section className="section">
          <div className="section-head"><div><div className="kicker">Breakdown</div><div className="h2">Where the battle was fought</div></div></div>
          <div className="seg" style={{ flexWrap: "wrap", marginBottom: 10 }}>
            {BREAKS.map(([k, l]) => <button key={k} className={by === k ? "on" : ""} onClick={() => setBy(k)}>{l}</button>)}
          </div>
          <div className="card">
            <div className="brk brk-head"><span>{d.by[by].label}</span><span>Balls</span><span>Runs</span><span>SR</span><span>Outs</span></div>
            {d.by[by].rows.map((r: any) => {
              const q = { ...d.evidence_query, ...(by === "phase" ? { phase: r.bucket } : by === "format" ? { format: r.bucket } : by === "year" ? { year_from: r.bucket, year_to: r.bucket } : { innings_no: r.bucket }) };
              return (
                <button key={String(r.bucket)} className="brk" onClick={() => onDrill(`${bucketLabel(by, r.bucket)}: every ball`, q)}>
                  <span className="strong">{bucketLabel(by, r.bucket)}{r.balls < 30 && <span className="mini"> *</span>}</span>
                  <span className="num">{r.balls}</span><span className="num">{r.runs}</span><span className="num">{fmt(r.strike_rate, 0)}</span><span className="num wk">{r.dismissals}</span>
                  <span className="brk-bar"><i style={{ width: `${Math.min(100, (r.strike_rate ?? 0) / 2.5)}%` }} /></span>
                </button>
              );
            })}
            <div className="mini" style={{ marginTop: 8 }}>Bar = strike rate (0–250). * = under 30 balls, a small sample. Tap a row for its deliveries.</div>
          </div>
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginTop: 12 }}>
            <button className="btn primary" onClick={() => onDrill(`Every ball: ${d.batter.name} v ${d.bowler.name}`, d.evidence_query)}>Every ball they&apos;ve faced →</button>
          </div>
          <div className="mini" style={{ marginTop: 10 }}>Not shown, because the data doesn&apos;t record it: {d.not_available.join(" · ")}.</div>
        </section>
        {drill && <Deliveries title={drill.title} query={drill.q} onClose={() => setDrill(null)} />}
      </>)}

      {(!batId || !bowlId) && (
        <section className="section">
          <div className="section-head"><div><div className="kicker">Most-played battles</div><div className="h2">Pick one, or choose your own</div></div></div>
          {!notable ? <div className="loading">Loading…</div> : (
            <div className="ex-cards three">
              {notable.map((b) => (
                <Link key={b.batter_id + b.bowler_id} href={`/battle?bat=${b.batter_id}&bowl=${b.bowler_id}`} className="bcard">
                  <div className="gender-tag">{b.gender === "female" ? "Women" : "Men"}</div>
                  <div className="who">{b.batter}<span>v</span>{b.bowler}</div>
                  <div className="mini" style={{ marginTop: 6 }}>{b.balls} balls · {b.runs} runs · SR {fmt((100 * b.runs) / b.balls, 0)} · <span className="wk">{b.dismissals} out</span></div>
                </Link>
              ))}
            </div>
          )}
        </section>
      )}
    </div>
  );
}

/** Schematic: bowler's end → batter's end, with one count node per observed dismissal route. No ball path is drawn. */
function BattleScene({ d, onPick }: { d: any; onPick: (r: any) => void }) {
  const routes = (d.dismissals_by_kind as any[]).filter((r) => r.n > 0);
  const W = 360, H = 132, max = Math.max(1, ...routes.map((r) => r.n));
  return (
    <div>
      <svg viewBox={`0 0 ${W} ${H}`} style={{ width: "100%" }} role="img" aria-label="Dismissal routes in this battle">
        <Defs />
        <rect x={0} y={0} width={W} height={130} rx={14} fill="url(#ci-turf)" />
        <g transform={`rotate(-90 ${W / 2} 65)`}><Pitch x={W / 2} top={65 - 120} bottom={65 + 120} width={34} /></g>
        <g transform={`rotate(-90 ${W / 2} 65)`}><Crease x={W / 2} y={65 - 100} /><Crease x={W / 2} y={65 + 100} /></g>
        <Stumps x={W / 2 - 112} y={62} /><Stumps x={W / 2 + 112} y={62} broken={routes.some((r) => ["BOWLED", "STUMPED", "HIT_WICKET"].includes(r.route))} />
        <Figure x={W / 2 - 92} y={74} role="bowler" label={d.bowler.name.split(" ").slice(-1)[0]} />
        <Figure x={W / 2 + 96} y={82} role="batter" label={d.batter.name.split(" ").slice(-1)[0]} unknownHand />
      </svg>
      {routes.length === 0 ? <div className="empty" style={{ marginTop: 10 }}>No dismissals in this battle.</div> : (
        <div className="broutes">
          {routes.map((r) => (
            <button key={r.route} className="broute" onClick={() => onPick(r)} aria-label={`${r.label}: ${r.n}`}>
              <span className="bnode" style={{ width: 30 + 16 * Math.sqrt(r.n / max), height: 30 + 16 * Math.sqrt(r.n / max) }}>{r.n}</span>
              <span className="mini">{r.label}</span>
            </button>
          ))}
        </div>
      )}
      <div className="mini" style={{ marginTop: 8 }}>Tap a count to see those dismissals. Schematic only: no ball path, line, length or field position is shown.</div>
    </div>
  );
}
const shortRoute = (l: string) => l.replace("Caught by wicketkeeper", "Caught by keeper").replace("Caught by a fielder", "Caught (field)").replace("Caught and bowled", "C & B");

/** WHO HAS THE EDGE? Evidence and uncertainty only. */
function Edge({ d }: { d: any }) {
  const e = d.edge, sr = e.strike_rate, ds = e.dismissals;
  const [lo, hi] = sr.matchup_interval_90 || [sr.matchup, sr.matchup];
  const vals = [lo, hi, sr.batter_usual, sr.bowler_usual_conceded].filter((v) => v != null);
  const a = Math.max(0, Math.min(...vals) * 0.8), b = Math.max(...vals) * 1.15;
  const X = (v: number) => `${(100 * (v - a)) / (b - a)}%`;
  const cmp = (usual: number | null) => usual == null ? null : usual < lo ? "above" : usual > hi ? "below" : "within";
  const vB = cmp(sr.batter_usual), vW = cmp(sr.bowler_usual_conceded);
  const [dlo, dhi] = ds.observed_interval_90 || [ds.observed, ds.observed];
  const dB = ds.expected_from_batter_usual_rate, dW = ds.expected_from_bowler_usual_rate;
  const dv = (x: number | null) => x == null ? null : x < dlo ? "more" : x > dhi ? "fewer" : "consistent";
  return (
    <div className="card">
      <div className="kicker">Who has the edge?</div>
      <div className="sub" style={{ marginTop: 4 }}>The evidence, with its uncertainty. We don&apos;t declare a winner. <ProvBadge prov="MODELLED" title="Intervals and expectations are statistical estimates from observed balls" /></div>
      <div className="sit-title" style={{ marginTop: 12 }}>Strike rate in this battle</div>
      <div className="numline" aria-label="Strike rate comparison">
        <div className="axis" />
        <div className="band" style={{ left: X(lo), width: `calc(${X(hi)} - ${X(lo)})` }} title="90% interval" />
        <div className="mark" style={{ left: X(sr.matchup), background: C.accent }} />
        <div className="lbl top" style={{ left: X(sr.matchup), color: C.accent, fontWeight: 800 }}>{fmt(sr.matchup, 1)} here</div>
        {sr.batter_usual != null && <><div className="mark" style={{ left: X(sr.batter_usual), background: C.text }} /><div className="lbl" style={{ left: X(sr.batter_usual) }}>batter usual {fmt(sr.batter_usual, 0)}</div></>}
        {sr.bowler_usual_conceded != null && <><div className="mark" style={{ left: X(sr.bowler_usual_conceded), background: C.amber }} /><div className="lbl row3" style={{ left: X(sr.bowler_usual_conceded), color: C.amber }}>bowler usually concedes {fmt(sr.bowler_usual_conceded, 0)}</div></>}
      </div>
      <ul className="edge-list">
        <li>90% interval for the strike rate here: <b>{fmt(lo, 0)}–{fmt(hi, 0)}</b>.</li>
        {vB && <li>The batter&apos;s usual rate ({fmt(sr.batter_usual, 1)}) is {vB === "within" ? <b>inside that range</b> : <>{vB === "above" ? "below" : "above"} it: <b>{d.batter.name} scores {vB === "above" ? "faster" : "slower"} against this bowler than usual</b></>}.</li>}
        {vW && <li>Batters usually score at {fmt(sr.bowler_usual_conceded, 1)} off this bowler: {vW === "within" ? <b>inside the range</b> : <b>{vW === "above" ? "this batter scores faster than most" : "this batter scores slower than most"}</b>}.</li>}
      </ul>
      <div className="sit-title" style={{ marginTop: 12 }}>Dismissals</div>
      <ul className="edge-list">
        <li>Observed: <b className="wk">{ds.observed}</b> (90% interval {fmt(dlo, 1)}–{fmt(dhi, 1)}).</li>
        {dB != null && <li>At the batter&apos;s usual dismissal rate we&apos;d expect <b>{fmt(dB, 1)}</b>: {dv(dB) === "consistent" ? "consistent with what happened" : dv(dB) === "more" ? "this bowler has dismissed the batter more often than that" : "fewer dismissals than that happened"}.</li>}
        {dW != null && <li>At the bowler&apos;s usual wicket rate we&apos;d expect <b>{fmt(dW, 1)}</b>: {dv(dW) === "consistent" ? "consistent with what happened" : dv(dW) === "more" ? "more dismissals happened than that" : "the batter has survived better than most against this bowler"}.</li>}
      </ul>
      <div className="note">{e.sample_note}</div>
      <div className="mini" style={{ marginTop: 8 }}>{e.explain}</div>
    </div>
  );
}
