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
import ExploreNext from "@/components/ExploreNext";
import MomentCard from "@/components/fan/MomentCard";
import { SectionHead, WhyBox } from "@/components/fan/bits";
import Feedback from "@/components/Feedback";
import { useRemember } from "@/lib/memory";

type P = { person_id: string; name: string } | null;
const BREAKS = [["phase", "Phase"], ["innings", "Setting / chasing"], ["year", "Year"], ["format", "Format"]] as const;
const bucketLabel = (by: string, b: any) => by === "innings" ? (b === 1 ? "Setting (1st inns)" : b === 2 ? "Chasing (2nd inns)" : `Innings ${b}`)
  : by === "phase" ? ({ powerplay: "Powerplay", middle: "Middle overs", death: "Death overs" } as any)[b] ?? b : String(b);

export default function Page() { return <Suspense fallback={<div className="loading">Loading…</div>}><Battle /></Suspense>; }

function Battle() {
  const sp = useSearchParams();
  const router = useRouter();
  const batId = sp.get("bat"), bowlId = sp.get("bowl");
  const fl = /^live:(\w+):(\d+)$/.exec(sp.get("from") || "");
  const fromLive = fl ? { mid: fl[1], n: fl[2] } : null;
  const [bat, setBat] = useState<P>(null), [bowl, setBowl] = useState<P>(null);
  const [d, setD] = useState<any | null>(null);
  const [uni, setUni] = useState<any | null>(null);
  const [cat, setCat] = useState("most_balls");
  const [ug, setUg] = useState("male");
  const [sim, setSim] = useState<any | null>(null);
  const [by, setBy] = useState<string>("phase");
  const [mt, setMt] = useState<any | null>(null);
  const [mtAll, setMtAll] = useState(false);
  const [pick, setPick] = useState(false);
  useEffect(() => { setMt(null); if (batId && bowlId) api("/fan/battle/meetings", { bat: batId, bowl: bowlId }).then((r) => setMt(r.data)).catch(() => setMt({ rows: [], count: 0 })); }, [batId, bowlId]);
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
  useEffect(() => { setUni(null); api("/battles/universe", { cat, gender: ug }).then((r) => setUni(r.data)); }, [cat, ug]);
  useEffect(() => { setSim(null); if (batId && bowlId) api("/battles/similar", { bat: batId, bowl: bowlId }).then((r) => setSim(r.data)); }, [batId, bowlId]);
  const onDrill = (title: string, q: any) => { setDrill({ title, q }); setTimeout(() => document.getElementById("evidence")?.scrollIntoView({ behavior: "smooth" }), 60); };
  const t = d?.total;
  useRemember("battle", batId && bowlId ? `${batId}|${bowlId}` : null, d?.met ? `${d.batter.name} v ${d.bowler.name}` : null, `/battle?bat=${batId}&bowl=${bowlId}`);

  return (
    <div className="fade-in">
      {fromLive && (
        <div className="from-live" data-testid="from-live">
          <span>Opened from a historical replay.</span>
          <Link href={`/live-lab/${fromLive.mid}?n=${fromLive.n}`}>← Back to the replay at the same ball</Link>
          <span>This page shows every covered meeting, including any after that match.</span>
        </div>)}
      {!d?.met && <section className="section" style={{ marginTop: 22 }}>
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
      </section>}

      {batId && bowlId && !d && <div className="loading">Loading the battle…</div>}
      {d?.error && <div className="empty">Couldn&apos;t load this battle.</div>}
      {d && !d.error && !d.met && <div className="empty" style={{ marginTop: 16 }}>{d.batter.name} hasn&apos;t faced {d.bowler.name} in covered matches.</div>}

      {d?.met && (<>
        {/* ---- the question: what actually happens when these two meet? */}
        <section className="vs-hero" data-testid="battle-hero" aria-label={`${d.batter.name} v ${d.bowler.name}`}>
          <h1 className="sr-only">{d.batter.name} v {d.bowler.name}</h1>
          <div className="vs-names">
            <Link href={`/players/${d.batter.person_id}`} className="vs-side bat"><span className="vs-role">Batter</span><span className="vs-name">{d.batter.name}</span></Link>
            <div className="vs-pitch" aria-hidden><span className="crease" /><span className="v">v</span><span className="crease" /></div>
            <Link href={`/players/${d.bowler.person_id}`} className="vs-side bowl"><span className="vs-role">Bowler</span><span className="vs-name">{d.bowler.name}</span></Link>
          </div>
          <div className="strip vs-strip">
            <div><b>{t.balls}</b><span>balls</span></div><div><b>{t.runs}</b><span>runs</span></div>
            <div><b>{fmt(t.strike_rate, 1)}</b><span>strike rate</span></div><div className="wk"><b>{t.dismissals}</b><span>dismissals</span></div>
          </div>
          <div className="mini vs-meta">{t.matches} matches · {t.first_date.slice(0, 4)}–{t.last_date.slice(0, 4)} · {t.fours} fours, {t.sixes} sixes, {t.dots} dots <ProvBadge prov="OBSERVED" />
            {" "}<button className="why-btn" onClick={() => setPick(!pick)} aria-expanded={pick}>Change players</button></div>
          {pick && <div className="battle-hero">
            <PlayerPicker label="Batter" value={bat} onPick={(p) => { setBat(p); push(p, bowl); }} placeholder="Search a batter…" />
            <div className="vs">v</div>
            <PlayerPicker label="Bowler" value={bowl} onPick={(p) => { setBowl(p); push(bat, p); }} placeholder="Search a bowler…" />
          </div>}
        </section>

        <section className="section" data-testid="battle-compared">
          <SectionHead kicker="Compared with their normal numbers" title="Is this battle unusual?" />
          <Edge d={d} />
        </section>

        <section className="section" data-testid="battle-changes">
          <SectionHead kicker="How the battle changes" title="Earlier meetings, later meetings" />
          {mt?.change ? (<>
            <div className="halves">
              {(["earlier", "later"] as const).map((k) => { const x = mt.change[k]; return (
                <div key={k} className="half"><span className="tk">{k === "earlier" ? "Earlier" : "Later"} · {x.from}–{x.to}</span>
                  <div className="strip"><div><b>{fmt(x.sr, 0)}</b><span>strike rate</span></div><div className="wk"><b>{x.outs}</b><span>out</span></div><div><b>{x.balls}</b><span>balls</span></div></div></div>); })}
            </div>
            <div className="mini">{mt.change.note} <WhyBox why={{ earlier_out_rate_90: `${mt.change.earlier.out_rate_interval_90?.join("–")} per 100 balls`, later_out_rate_90: `${mt.change.later.out_rate_interval_90?.join("–")} per 100 balls`, split: "meetings in date order, split where half the balls had been faced" }} /></div>
          </>) : <div className="mini">Too few meetings to split.</div>}
          <div className="seg" style={{ flexWrap: "wrap", margin: "14px 0 10px" }}>
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
        </section>

        <section className="section">
          <div className="card">
            <div className="sit-title">How the {t.dismissals} dismissal{t.dismissals === 1 ? "" : "s"} happened</div>
            <BattleScene d={d} onPick={(r: any) => onDrill(`${d.batter.name} ${r.label.toLowerCase()} by ${d.bowler.name}`, { ...d.evidence_query, out_id: d.batter.person_id, route: r.route })} />
          </div>
        </section>

        <section className="section" data-testid="battle-meetings">
          <SectionHead kicker="Every meeting" title={`${mt?.count ?? t.matches} matches`}
            right={<button className="btn sm" onClick={() => onDrill(`Every ball: ${d.batter.name} v ${d.bowler.name}`, d.evidence_query)}>Every ball →</button>} />
          {!mt ? <div className="loading">…</div> : (
            <ol className="meetings">
              {(mtAll ? mt.rows : mt.rows.slice(-8)).map((r: any) => (
                <li key={r.match_id}>
                  <Link href={r.href} className="mt-row">
                    <span className="mt-d">{r.date}<span className="mini">{r.competition}</span></span>
                    <span className="mt-s num">{r.runs}<span className="mini"> ({r.balls})</span></span>
                    <span className={`mt-o ${r.out ? "wk" : ""}`}>{r.out ? r.how : "not out"}</span>
                  </Link>
                </li>
              ))}
            </ol>
          )}
          {mt && mt.rows.length > 8 && <button className="btn sm" style={{ margin: "8px 0" }} aria-expanded={mtAll} onClick={() => setMtAll(!mtAll)} data-testid="meetings-all">
            {mtAll ? "Show the latest 8" : `Show all ${mt.rows.length} meetings (oldest first)`}</button>}
          <div className="mini">{mtAll ? "Oldest first." : `The latest ${Math.min(8, mt?.rows.length ?? 0)}, oldest first.`} Runs (balls) the batter scored off this bowler in each match; "not out" means the bowler did not dismiss them that day.</div>
        </section>

        <MomentCard type="battle" k={`${batId}|${bowlId}`} context="A real ball from their meetings. Make your call before the replay reveals it." />
        {drill && <Deliveries title={drill.title} query={drill.q} onClose={() => setDrill(null)} />}

        <section className="section" data-testid="battle-similar">
          <SectionHead kicker="Similar battles" title="Battles with the same shape" />
          {!sim ? <div className="loading">Finding similar battles…</div> : !sim.available ? <div className="mini">{sim.reason}</div> : (
            <div className="mrows">{sim.rows.slice(0, 5).map((r: any) => (
              <Link key={r.batter_id + r.bowler_id} className="mrow" href={`/battle?bat=${r.batter_id}&bowl=${r.bowler_id}`}>
                <span className="mn"><b>{r.batter} v {r.bowler}</b><span className="mini">{r.balls} balls · strike rate {r.sr} · {r.outs} out</span></span>
                <span className="mv" aria-hidden>→</span></Link>))}
              <div className="mini" style={{ marginTop: 6 }}>Similar in balls, scoring and dismissals relative to each player&apos;s usual numbers. <WhyBox why={sim.method} /></div>
            </div>
          )}
        </section>

        <Knowledge bat={batId!} bowl={bowlId!} />
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginTop: 14 }}>
          <Link className="btn" href={`/share?type=battle&bat=${batId}&bowl=${bowlId}`}>Share card</Link>
          <Link className="btn" href={`/compare?ids=${batId},${bowlId}`}>Compare the two players</Link>
        </div>
        <Feedback entity={{ type: "battle", id: `${batId}|${bowlId}` }} item="battle" />
        <ExploreNext type="battle" id={`${batId}|${bowlId}`} />
      </>)}

      {(!batId || !bowlId) && (
        <section className="rule-section">
          <div className="eyebrow">Battle universe</div>
          <div className="h2" style={{ marginTop: 4 }}>Explore every batter v bowler contest</div>
          <div className="cat-strip">{uni && Object.entries(uni.categories).map(([k, l]) => <button key={k} className={cat === k ? "on" : ""} onClick={() => setCat(k)}>{l as string}</button>)}</div>
          <div className="seg" style={{ marginTop: 10 }}>{[["male", "Men"], ["female", "Women"]].map(([v, l]) => <button key={v} className={ug === v ? "on" : ""} onClick={() => setUg(v)}>{l}</button>)}</div>
          {!uni ? <div className="loading">Loading…</div> : (
            <>
              <div className="def-line"><b>{uni.label}.</b> {uni.definition} <span className="mini">{uni.note}</span></div>
              <div className="tablist">{uni.rows.map((b: any, i: number) => (
                <Link key={b.batter_id + b.bowler_id} href={`/battle?bat=${b.batter_id}&bowl=${b.bowler_id}`} className="trow"><span className="n">{i + 1}</span>
                  <span className="t"><b>{b.batter} v {b.bowler}</b><span className="mini">{b.balls} balls · SR {b.sr} · {b.outs} out (expected {b.expected_outs}) · {b.first_date.slice(0, 4)}–{b.last_date.slice(0, 4)}</span></span>
                  <span className="v num">{cat === "most_dismissals" || cat === "one_sided" ? `${b.outs} out` : cat === "most_runs" ? b.runs : cat.includes("sr") ? b.sr : b.balls}</span></Link>))}</div>
            </>
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
      <div className="sub" style={{ marginTop: 4 }}>The evidence, with its uncertainty. We don&apos;t declare a winner when the evidence is inconclusive. <ProvBadge prov="MODELLED" title="Intervals and expectations are statistical estimates from observed balls" /></div>
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


// "What do we actually know about why this matchup behaves this way?" Known / derived / unavailable, with missing data made explicit.
function Knowledge({ bat, bowl }: { bat: string; bowl: string }) {
  const [k, setK] = useState<any | null>(null);
  useEffect(() => { if (bat && bowl) api("/visual/battle", { bat, bowl }).then((r) => setK(r.data)).catch(() => setK(null)); }, [bat, bowl]);
  if (!k) return null;
  return (
    <section className="rule-section" data-testid="battle-knowledge">
      <div className="eyebrow">What do we actually know about this matchup?</div>
      <div className="know">
        <div className="col k"><b>Known</b> <ProvBadge prov="OBSERVED" /><ul>{k.known.map((x: any) => <li key={x.item}>{x.item}</li>)}</ul></div>
        <div className="col d"><b>Derived</b> <ProvBadge prov="DERIVED" /><ul>{k.derived.map((x: any) => <li key={x.item}>{x.item}</li>)}</ul></div>
        <div className="col u"><b>Not available</b><ul>{k.unavailable.map((x: any) => <li key={x.item}>{x.item}<div className="mini">{x.why}</div></li>)}</ul></div>
      </div>
      <div className="mini" style={{ marginTop: 8 }}>{k.metadata.map((m: any) => `${m.who}: ${m.field.replace("_", " ")} ${m.value ?? "unknown"} (${m.status})`).join(" · ")}</div>
      <p style={{ fontSize: 14, marginTop: 8 }} data-testid="cannot-say">{k.cannot_say}</p>
    </section>
  );
}
