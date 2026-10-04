"use client";
// Visual Lab (Phase 6): progressive enhancement, demonstrated honestly. Real deliveries show AVAILABLE DATA next to the
// VISUAL RESULT, and stay sparse where data is absent. Future layers are shown only as ILLUSTRATIVE examples built from
// generic, unnamed data: they are never attached to a real delivery or player.
import Link from "next/link";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { BallGeom } from "@/lib/visual";
import { DismissalTheatre, EdgeMap, LayerLadder, LineLengthMap, PitchMap, ShotAtlas, WagonMap, Why } from "@/components/visual";

// Generic illustration data: no ids, no names, provenance ILLUSTRATIVE. Values are chosen to show what each layer would encode.
const ILL: BallGeom[] = [
  { line: "outside_off", length: "good_length", pitch_x: 0.35, pitch_y: 6.4, runs: 0, shot: "leave" },
  { line: "outside_off", length: "full", pitch_x: 0.3, pitch_y: 3.6, runs: 4, boundary: 4, shot: "cover_drive", direction_deg: 62 },
  { line: "off_stump", length: "good_length", pitch_x: 0.12, pitch_y: 6.0, runs: 0, shot: "forward_defence" },
  { line: "middle", length: "short", pitch_x: 0.0, pitch_y: 9.5, runs: 6, boundary: 6, shot: "pull", direction_deg: 255 },
  { line: "outside_off", length: "back_of_length", pitch_x: 0.4, pitch_y: 7.8, runs: 0, wicket: true, shot: "cut" },
  { line: "leg_stump", length: "full", pitch_x: -0.1, pitch_y: 3.2, runs: 1, shot: "flick", direction_deg: 230 },
  { line: "wide_outside_off", length: "yorker", pitch_x: 0.7, pitch_y: 1.6, runs: 1, shot: "square_drive", direction_deg: 95 },
  { line: "middle", length: "good_length", pitch_x: 0.02, pitch_y: 6.2, runs: 2, shot: "straight_drive", direction_deg: 5 },
];

export default function VisualLab() {
  const [d, setD] = useState<any | null>(null);
  const [pilot, setPilot] = useState<any | null>(null);
  useEffect(() => { api("/visual/lab").then((r) => setD(r.data)); api("/metadata/pilot").then((r) => setPilot(r.data)).catch(() => setPilot(null)); }, []);
  return (
    <div className="fade-in" style={{ marginTop: 18 }}>
      <div className="eyebrow">Visual Lab</div>
      <h1 className="display-xl" style={{ marginTop: 4 }}>Sparse and true beats rich and invented</h1>
      <p className="mini" style={{ fontSize: 14, maxWidth: 720 }}>Every CRICINTEL graphic is built in layers. Real deliveries only show the layers we actually hold;
        the rest is marked "not recorded". The illustrations at the bottom show what future licensed data could unlock. They are generic, not real deliveries.</p>
      {d && <section className="rule-section"><div className="eyebrow">The six layers</div>
        <div className="tablist">{d.layers.map((l: any) => <div key={l.code} className="trow"><span className="n">{l.code}</span><span><b>{l.name}</b><div className="mini">{l.describes}</div></span><span /></div>)}</div></section>}

      <section className="rule-section" data-testid="lab-real">
        <div className="eyebrow">Real deliveries · available data → visual result</div>
        {!d ? <div className="loading">Loading…</div> : d.examples.map((ex: any) => {
          const L0 = ex.layers[0].data;
          return (
            <div key={ex.delivery_id} className="rule-section" data-testid="lab-example">
              <div style={{ fontWeight: 900 }}>{L0.bowler.name} to {L0.batter.name} · {ex.match.competition} · {ex.match.start_date}</div>
              <div className="mini">{ex.why_chosen} · highest layer present: L{ex.fidelity}</div>
              <div className="av-split" style={{ marginTop: 10 }}>
                <div><div className="eyebrow">Available data</div><LayerLadder layers={ex.layers} />
                  {ex.layers[1].available && <div className="mini" style={{ marginTop: 6 }}>Layer 1 values: {Object.entries(ex.layers[1].data.bowler).filter(([k]) => k.startsWith("bowling")).map(([k, v]: any) => `${k.replace("_", " ")} ${v.value}`).join(" · ")}
                    {Object.values(ex.layers[1].data.bowler).slice(0, 1).map((v: any, i) => <Why key={i} p={v.provenance} />)}</div>}</div>
                <div><div className="eyebrow">Visual result</div>
                  {L0.dismissal.length ? <DismissalTheatre d={L0.dismissal[0]} keeperNote="Keeper identified by inference for this match; not the same as 'caught behind'." /> : null}
                  <div style={{ marginTop: 10 }}><PitchMap balls={[]} /></div>
                  <p className="mini" style={{ marginTop: 8 }} aria-live="polite">Text equivalent: {ex.text}</p>
                  <Link className="btn" href={`/delivery/${ex.delivery_id}`}>Open the delivery →</Link></div>
              </div>
            </div>);
        })}
      </section>

      <section className="rule-section" data-testid="lab-pilot">
        <div className="eyebrow">Player metadata pilot · 8 players, joined by stable ids</div>
        {!pilot ? <div className="mini">Pilot report not available.</div> : (<>
          <p className="mini" style={{ fontSize: 13 }}>{pilot.summary.verdict}</p>
          <div style={{ overflowX: "auto" }}><table className="capm"><thead><tr><th>Player</th><th>Join</th><th>Batting hand</th><th>Bowling style</th><th>Role</th></tr></thead>
            <tbody>{Object.entries(pilot.players).map(([pid, p]: any) => (
              <tr key={pid}><td><Link href={`/players/${pid}`}>{p.name}</Link></td><td>{p.join.join_ok ? "✓ id" : "✕"}</td>
                {(["batting_hand", "bowling_style", "role"] as const).map((f) => { const x = p.fields[f]; const wp = x.candidates.find((c: any) => c.source === "wikipedia");
                  return <td key={f}>{x.value ? <><b>{x.value}</b><div className="mini">{x.used_source}</div></>
                    : <span className="mini">{wp ? "withheld: only in CC BY-SA source" : "no source"}</span>}</td>; })}</tr>))}</tbody></table></div>
          <div className="mini">&quot;Withheld&quot;: Wikipedia infoboxes hold this value, but their CC BY-SA licence needs review before CRICINTEL may store or show it, so it is neither used nor displayed.</div>
          <div className="mini">Wikidata (CC0) coverage across all {pilot.wikidata_coverage.P2697_total.toLocaleString()} cricketer items: bowling style {pilot.wikidata_coverage.P2545},
            handedness {pilot.wikidata_coverage.P552} (generic handedness, not batting hand). Retrieved {pilot.retrieved.pilot}.</div></>)}
      </section>

      <section className="rule-section" data-testid="lab-illustrative">
        <div className="eyebrow">What future layers could enable · illustrative only</div>
        <p className="mini" style={{ fontSize: 13 }}>None of this is CRICINTEL data. It is a generic example (no real batter, bowler or ball) showing what each component
          would draw if a licensed source supplied the layer. With today&apos;s data each of these renders as &quot;not recorded&quot;.</p>
        <div className="vgrid">
          <div><div className="eyebrow">L2 · Pitch map</div><PitchMap balls={ILL} hand="right" illustrative /></div>
          <div><div className="eyebrow">L2 · Line &amp; length</div><LineLengthMap balls={ILL} illustrative /></div>
          <div><div className="eyebrow">L3 · Wagon wheel</div><WagonMap balls={ILL} illustrative /></div>
          <div><div className="eyebrow">L3 · Shot atlas</div><ShotAtlas balls={ILL} illustrative /></div>
          <div><div className="eyebrow">L4 · Contact</div><EdgeMap illustrative /></div>
          <div><div className="eyebrow">The same components on real data today</div><LineLengthMap balls={[]} /><div style={{ height: 8 }} /><WagonMap balls={[]} /><div style={{ height: 8 }} /><ShotAtlas balls={[]} /></div>
        </div>
      </section>
      <section className="rule-section"><Link className="btn" href="/data">Field-by-field data capability →</Link></section>
    </div>
  );
}
