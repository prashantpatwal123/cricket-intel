"use client";
// Delivery Replay v1: one real delivery, using only what the data records. ← / → walk through the innings.
import Link from "next/link";
import { useRemember } from "@/lib/memory";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import { api } from "@/lib/api";
import { deliveryModel } from "@/lib/viz/model";
import ProvBadge from "@/components/Prov";
import ExploreNext from "@/components/ExploreNext";
import DeliveryScene from "@/components/viz/DeliveryScene";
import MatchSituation from "@/components/viz/MatchSituation";
import { DismissalTheatre, LayerLadder, NotRecorded } from "@/components/visual";

export default function Replay() {
  const { id } = useParams<{ id: string }>();
  const did = decodeURIComponent(id);
  const router = useRouter();
  const [r, setR] = useState<any | null>(null);
  useRemember("delivery", decodeURIComponent(id), r?.batter ? `${r.batter.name} v ${r.bowler.name} · ball ${r.over_ball}` : null, `/delivery/${id}`);
  const [err, setErr] = useState(false);
  useEffect(() => { setErr(false); api(`/deliveries/${encodeURIComponent(did)}/replay`).then((x) => setR(x.data)).catch(() => setErr(true)); }, [did]);
  const model = useMemo(() => (r ? deliveryModel(r) : null), [r]);
  const go = (to: string | null) => to && router.push(`/delivery/${encodeURIComponent(to)}`);
  useEffect(() => {
    const h = (e: KeyboardEvent) => { if (!r) return; if (e.key === "ArrowLeft") go(r.prev_id); if (e.key === "ArrowRight") go(r.next_id); };
    window.addEventListener("keydown", h); return () => window.removeEventListener("keydown", h);
  }, [r]);
  if (err) return <div className="empty" style={{ marginTop: 30 }}>Delivery not found.</div>;
  if (!r || !model) return <div className="loading">Loading the delivery…</div>;
  const m = r.match, w = r.wicket_detail?.[0], c = r.context_v1;
  const fact = (l: string, v: any, prov = "OBSERVED") => <div className="fact" key={l}><div className="l"><span>{l}</span><span className={`pdot ${prov}`} title={prov} /></div><div className="v">{v ?? "–"}</div></div>;
  return (
    <div className="fade-in">
      <section className="hero" style={{ paddingBottom: 14 }}>
        <div className="kicker">Delivery replay · {m.competition} · {m.start_date} · {r.gender === "female" ? "Women" : "Men"} · {r.format}</div>
        <h1 className="h2" style={{ fontSize: "clamp(26px, 7vw, 40px)", marginTop: 6 }}>
          {w ? <>{w.player_out} <span style={{ color: "var(--wicket)" }}>{w.kind === "caught" ? `c ${w.fielder ?? "?"}` : w.kind}</span> b {r.bowler.name}</> :
            <>{r.batter.name} <span className="mini" style={{ fontSize: 20 }}>v</span> {r.bowler.name}</>}
        </h1>
        <div className="mini" style={{ marginTop: 6 }}>{r.batting_team} v {r.bowling_team} · {m.venue} · innings {r.innings_no} · over {r.over_ball}
          {m.result_line ? <> · <b style={{ color: "var(--text)" }}>{m.result_line}</b> <ProvBadge prov="OBSERVED" /></> : null}</div>
        <div className="replay-nav">
          <button className="btn" onClick={() => go(r.prev_id)} disabled={!r.prev_id}>← Previous ball</button>
          <span className={`reveal-ball`} style={{ minWidth: 46, height: 46, fontSize: 18, background: w ? "#ff5c74" : r.runs.six ? "#9df26b55" : r.runs.four ? "#35e0c255" : "#ffffff14" }}>{r.symbol}</span>
          <button className="btn" onClick={() => go(r.next_id)} disabled={!r.next_id}>Next ball →</button>
        </div>
      </section>

      <section className="section" style={{ marginTop: 14 }}>
        <MatchSituation s={{ ...r.situation, recent: r.recent.map((x: any) => x.symbol), next_ball: r.over_ball, batting: r.batting_team }} />
      </section>

      <section className="section" style={{ marginTop: 14 }}>
        <div className="card"><DeliveryScene model={model} /></div>
      </section>

      <Layers did={did} />

      <section className="section">
        <div className="section-head"><div><div className="kicker">The record</div><div className="h2">What the data says about this ball</div></div></div>
        <div className="facts">
          {fact("Over.ball", r.over_ball)}{fact("Score before", r.score_before, "DERIVED")}{fact("Score after", r.score_after, "DERIVED")}
          {fact("Batter", r.batter.name)}{fact("Bowler", r.bowler.name)}{fact("Non-striker", r.non_striker.name)}
          {fact("Runs off bat", r.runs.batter)}{fact("Extras", r.runs.extras ? `${r.runs.extras}${r.runs.wides ? " wd" : r.runs.noballs ? " nb" : r.runs.byes ? " b" : r.runs.legbyes ? " lb" : ""}` : 0)}
          {fact("Batter's innings", `${r.batter_innings.before} → ${r.batter_innings.after}`, "DERIVED")}
          {fact("Wicket", w ? `${w.player_out}: ${w.kind}` : "no")}
          {w && fact(w.route === "CAUGHT_KEEPER" ? "Keeper credited" : "Fielder", w.kind === "caught and bowled" ? r.bowler.name : w.fielder ?? "—", w.route === "CAUGHT_KEEPER" ? "DERIVED" : "OBSERVED")}
          {r.situation.target && fact("Needed", `${r.situation.runs_required} off ${r.situation.balls_left}`, "DERIVED")}
          {fact("Partnership", `${c.partnership_runs_before} (${c.partnership_balls_before})`, "DERIVED")}
          {fact("Batter stage", `${c.batter_stage} · ${r.batter_innings.before.split("(")[1]?.replace(")", "")} balls`, "DERIVED")}
          {fact("Since boundary", `batter ${c.batter_balls_since_boundary} · team ${c.team_balls_since_boundary}`, "DERIVED")}
          {fact(`Last ${c.recent_window} balls`, `${c.recent_runs} runs, ${c.recent_wickets} wkts`, "DERIVED")}
        </div>
        <div className="mini" style={{ marginTop: 6 }}>White dot = observed in the data · blue = derived by calculation. Context definitions: <Link href="/context" style={{ textDecoration: "underline" }}>Context Engine</Link>.</div>
      </section>

      {r.experimental && (
        <section className="section">
          <div className="exp-box">
            <div className="exp-tag">Experimental · not validated for release</div>
            <div style={{ fontWeight: 800, marginTop: 4 }}>Situation Difficulty {r.experimental.sdx.sdx} / 100 <ProvBadge prov="MODELLED" /></div>
            <div className="mini" style={{ marginTop: 4 }}>Historically {Math.round(r.experimental.sdx.sdx)}% of chases facing this demand failed (needing {r.situation.runs_required} where a typical side
              scores {r.experimental.sdx.expected_runs} from {r.situation.balls_left} balls and {10 - r.situation.wickets} wickets). Swing on this ball: {r.experimental.swing}. {r.experimental.version}.
              <Link href="/lab" style={{ textDecoration: "underline", marginLeft: 4 }}>How it works</Link></div>
          </div>
        </section>
      )}

      <section className="section">
        <div className="grid2">
          <div className="card">
            <div className="sit-title">Before this ball</div>
            <div className="balls-row" style={{ marginTop: 8 }}>
              {r.recent.map((x: any) => <Link key={x.delivery_id} href={`/delivery/${encodeURIComponent(x.delivery_id)}`} title={`${x.ball_label} ${x.batter}`}
                style={{ background: x.symbol === "W" ? "#ff5c74" : undefined }}>{x.symbol}</Link>)}
              <span className="cur" style={{ minWidth: 34, height: 34, borderRadius: 10, display: "inline-grid", placeItems: "center", border: "1px solid #fff", fontWeight: 800 }}>{r.symbol}</span>
            </div>
            <div className="sit-title" style={{ marginTop: 12 }}>What followed</div>
            <div className="balls-row" style={{ marginTop: 8 }}>
              {r.following.map((x: any) => <Link key={x.delivery_id} href={`/delivery/${encodeURIComponent(x.delivery_id)}`} title={`${x.ball_label} ${x.batter}`}
                style={{ background: x.symbol === "W" ? "#ff5c74" : undefined }}>{x.symbol}</Link>)}
            </div>
          </div>
          <div className="card">
            <div className="sit-title">Walk through it</div>
            <div style={{ display: "flex", flexDirection: "column", gap: 8, marginTop: 8 }}>
              <Link className="btn" href={`/innings/${r.links.innings.match_id}/${r.links.innings.innings_no}/${r.links.innings.batter_id}?ball=${encodeURIComponent(r.delivery_id)}`}>{r.batter.name}&apos;s innings story →</Link>
              <Link className="btn" href={`/spell/${r.links.spell.match_id}/${r.links.spell.innings_no}/${r.links.spell.bowler_id}?ball=${encodeURIComponent(r.delivery_id)}`}>{r.bowler.name}&apos;s spell story →</Link>
              <Link className="btn" href={`/battle?bat=${r.batter.id}&bowl=${r.bowler.id}`}>{r.batter.name} v {r.bowler.name}: every meeting →</Link>
            </div>
            <div className="mini" style={{ marginTop: 10 }}>Keys: ← previous ball · → next ball. Source: {r.source.source_ref}.</div>
          </div>
        </div>
      </section>
      <div className="mini" style={{ marginTop: 12 }}>Match: {m.innings.map((i: any) => `${i.batting_team} ${i.total_runs}/${i.total_wickets} (${i.overs} ov)`).join(" · ")}</div>
      <ExploreNext type="delivery" id={did} />
    </div>
  );
}


// Delivery Replay V2: progressive fidelity. Each layer is shown only if a source records it; the rest say so.
function Layers({ did }: { did: string }) {
  const [v, setV] = useState<any | null>(null);
  useEffect(() => { api(`/visual/delivery/${did}`).then((r) => setV(r.data)).catch(() => setV(null)); }, [did]);
  if (!v) return null;
  const L0 = v.layers[0].data;
  return (
    <section className="section" data-testid="delivery-layers">
      <div className="section-head"><div><div className="kicker">Progressive replay · layer {v.fidelity} of 5</div><div className="h2">What we can draw, and what we can&apos;t</div></div></div>
      <div className="av-split">
        <div><LayerLadder layers={v.layers} /></div>
        <div>
          {L0.dismissal.length > 0 && <DismissalTheatre d={L0.dismissal[0]} keeperNote="Keeper identified by inference for this match; not the same as 'caught behind'." />}
          <div style={{ marginTop: 10 }}><NotRecorded what="Pitch point, shot, edge and ball path" why="Layers 2–5 are not recorded for this ball (see the ladder), so none of them is drawn." /></div>
          <p className="mini" style={{ marginTop: 8 }}>Text equivalent: {v.text}</p>
        </div>
      </div>
    </section>
  );
}
