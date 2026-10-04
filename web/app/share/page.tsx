"use client";
// Share card generator. Builds a card from the same APIs the product uses; export only (no posting integrations).
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense, useEffect, useRef, useState } from "react";
import { api } from "@/lib/api";
import { CardSpec, ShareCard, svgToPng } from "@/components/ShareCard";

export default function Page() { return <Suspense fallback={<div className="loading">Loading…</div>}><Share /></Suspense>; }

const COV = "Covered data only (Cricsheet ball-by-ball); not official records.";

async function build(sp: URLSearchParams): Promise<{ spec: CardSpec; back: string } | null> {
  const t = sp.get("type");
  if (t === "innings") {
    const [m, i, pid] = [sp.get("m"), sp.get("i"), sp.get("pid")];
    const s = (await api(`/innings/${m}/${i}/${pid}`)).data, sm = s.summary;
    return { back: `/innings/${m}/${i}/${pid}`, spec: { eyebrow: `Innings · ${s.match.competition} · ${s.match.start_date}`, title: `${s.batter.name} v ${s.teams.bowling_team}`,
      big: `${sm.runs}${sm.not_out ? "*" : ""}`, bigLabel: `off ${sm.balls} balls · strike rate ${sm.strike_rate}`,
      stats: [{ label: "fours", value: String(sm.fours) }, { label: "sixes", value: String(sm.sixes) }, { label: "dots", value: String(sm.dots) }, { label: "arrived at", value: sm.arrived }],
      visual: { kind: "bars", values: s.balls.filter((b: any) => b.on_strike).map((b: any) => (b.out ? 7 : b.runs || 0.3)),
                colors: s.balls.filter((b: any) => b.on_strike).map((b: any) => b.out ? "#ff5c74" : b.six ? "#9df26b" : b.four ? "#35e0c2" : b.runs ? "#7cc4ff" : "#5d6a88") },
      lines: [`${s.match.result_line}.`, "Every ball faced, in order: bar height = runs off the bat."], prov: "OBSERVED events, DERIVED totals", coverage: COV } };
  }
  if (t === "spell") {
    const [m, i, pid] = [sp.get("m"), sp.get("i"), sp.get("pid")];
    const s = (await api(`/spells/${m}/${i}/${pid}`)).data, tt = s.totals;
    return { back: `/spell/${m}/${i}/${pid}`, spec: { eyebrow: `Spell · ${s.match.competition} · ${s.match.start_date}`, title: `${s.bowler.name}`,
      big: `${tt.wickets}/${tt.runs}`, bigLabel: `${Math.floor(tt.balls / 6)}.${tt.balls % 6} overs · economy ${tt.economy}`,
      stats: [{ label: "dots", value: String(tt.dots) }, { label: "boundaries", value: String(tt.boundaries) }, { label: "longest dot run", value: String(tt.longest_dot_sequence) }],
      visual: { kind: "bars", values: s.overs.map((o: any) => o.runs || 0.3), colors: s.overs.map((o: any) => (o.wickets ? "#ff5c74" : "#ffb547")) },
      lines: [`${s.match.result_line}.`, "Runs conceded per over; red = an over with a wicket."], prov: "OBSERVED events, DERIVED totals", coverage: COV } };
  }
  if (t === "battle") {
    const b = (await api("/battle", { bat: sp.get("bat"), bowl: sp.get("bowl") })).data, tt = b.total, e = b.edge;
    return { back: `/battle?bat=${sp.get("bat")}&bowl=${sp.get("bowl")}`, spec: { eyebrow: `Battle · ${tt.matches} matches · ${tt.first_date.slice(0, 4)}–${tt.last_date.slice(0, 4)}`,
      title: `${b.batter.name} v ${b.bowler.name}`, big: `${tt.runs}/${tt.dismissals}`, bigLabel: `runs and dismissals from ${tt.balls} balls`,
      stats: [{ label: "strike rate", value: String(tt.strike_rate) }, { label: "batter usual", value: String(e.strike_rate.batter_usual ?? "–") },
              { label: "expected outs", value: String(e.dismissals.expected_from_batter_usual_rate ?? "–") }, { label: "sixes", value: String(tt.sixes) }],
      visual: { kind: "split", a: tt.runs - tt.fours * 4 - tt.sixes * 6, b: tt.fours * 4 + tt.sixes * 6, la: "runs off non-boundaries", lb: "boundary runs" },
      lines: ["Expected outs = balls × the batter's usual dismissal rate (MODELLED).", e.sample_note], prov: "OBSERVED counts, MODELLED expectation", coverage: COV } };
  }
  if (t === "record") {
    const q: any = Object.fromEntries(sp.entries()); delete q.type; delete q.preset;
    const lb = (await api("/records", { ...q, limit: 5 })).data;
    return { back: `/records?${sp.toString().replace(/type=record&?/, "")}`, spec: { eyebrow: `Record · ${lb.entity_label} · ${lb.gender === "female" ? "Women" : "Men"}`,
      title: lb.label, big: lb.rows[0]?.value_fmt ?? "–", bigLabel: lb.rows[0] ? lb.rows[0].names.join(" v ") : "nobody qualifies",
      stats: lb.min_sample ? [{ label: `minimum ${lb.sample_unit}`, value: String(lb.min_sample) }] : [],
      visual: { kind: "rank", rows: lb.rows.map((r: any) => ({ name: r.names.join(" v "), value: r.value_fmt })) },
      lines: [lb.definition], prov: "DERIVED from OBSERVED deliveries", coverage: COV } };
  }
  if (t === "partnership") {
    const d = (await api("/partnerships/pair", { p1: sp.get("p1"), p2: sp.get("p2"), format: sp.get("format") || undefined })).data;
    return { back: `/partnerships?p1=${sp.get("p1")}&p2=${sp.get("p2")}`, spec: { eyebrow: `Partnership · ${d.innings} stands`, title: `${d.p1.name} & ${d.p2.name}`,
      big: String(d.totals.runs), bigLabel: `runs together · ${d.totals.run_rate} an over`,
      stats: [{ label: "average", value: String(d.totals.average ?? "–") }, { label: "best", value: String(d.totals.best) }, { label: "boundaries", value: String(d.totals.boundaries) }],
      visual: { kind: "split", a: d.totals.p1_runs, b: d.totals.p2_runs, la: d.p1.name.split(" ").slice(-1)[0], lb: d.p2.name.split(" ").slice(-1)[0] },
      lines: ["A partnership = every ball bowled while both batters were in."], prov: "DERIVED from OBSERVED deliveries", coverage: COV } };
  }
  if (t === "discovery") {
    const items = (await api("/discover")).data.items; const c = items.find((x: any) => x.id === sp.get("id")) || items[0];
    return { back: c.href, spec: { eyebrow: `${c.type_label} · ${c.gender === "female" ? "Women" : "Men"} · ${c.format}`, title: c.headline, big: String(c.numbers[0]?.value ?? ""),
      bigLabel: c.numbers[0]?.label ?? "", stats: c.numbers.slice(1).map((n: any) => ({ label: n.label, value: String(n.value) })),
      lines: wrapText(c.statement, 60), prov: `Test: ${c.why.test}`.slice(0, 50), coverage: COV } };
  }
  if (t === "fingerprint") {
    const f = (await api(`/players/${sp.get("pid")}/fingerprint`, { role: sp.get("role") || "auto" })).data;
    const p = (await api(`/players/${sp.get("pid")}/profile`)).data;
    const top = [...f.dimensions].filter((d: any) => d.percentile != null).sort((a: any, b: any) => b.percentile - a.percentile)[0];
    return { back: `/players/${sp.get("pid")}`, spec: { eyebrow: `Cricket fingerprint · ${f.format} · ${f.role}`, title: p.name, big: top ? `${Math.round(top.percentile)}th` : "–",
      bigLabel: top ? `percentile: ${top.label.toLowerCase()} v ${f.peer_pool.size} peers` : "", stats: [{ label: "balls", value: String(f.balls) }],
      visual: { kind: "rank", rows: [...f.dimensions].filter((d: any) => d.enough_sample && d.percentile != null).sort((a: any, b: any) => b.percentile - a.percentile)
                .slice(0, 5).map((d: any) => ({ name: d.label, value: `${Math.round(d.percentile)}th` })) },
      lines: [`Peers: ${f.peer_pool.definition}.`.slice(0, 64)], prov: "OBSERVED aggregates, percentile DERIVED", coverage: COV } };
  }
  if (t === "match") {
    const d = (await api(`/match/${sp.get("id")}`)).data, m = d.match;
    return { back: `/match/${sp.get("id")}`, spec: { eyebrow: `${m.competition || "Match"} · ${m.start_date}`, title: `${m.team1} v ${m.team2}`,
      big: d.innings.map((i: any) => `${i.total_runs}/${i.total_wickets}`).join(" · "), bigLabel: m.result_line,
      stats: d.innings.map((i: any) => ({ label: i.batting_team, value: `${i.overs} ov` })),
      visual: { kind: "worm", series: d.innings.map((i: any) => i.overs_list.map((o: any) => o.runs)) },
      lines: [`${m.venue || ""}`], prov: "OBSERVED", coverage: d.coverage.text.slice(0, 86) } };
  }
  if (t === "whn") {
    return { back: "/play", spec: { eyebrow: "What happens next? · historical moments", title: "My session", big: `${sp.get("pts") || 0}`, bigLabel: "points",
      stats: [{ label: "predictions", value: sp.get("n") || "0" }, { label: "accuracy", value: `${sp.get("acc") || 0}%` }, { label: "model points", value: sp.get("mpts") || "0" },
              { label: "beat the model", value: `${sp.get("beat") || 0}×` }],
      lines: ["Real moments from covered matches. The model is an estimate, not a certainty."], prov: "OBSERVED outcomes, MODELLED probabilities", coverage: COV } };
  }
  return null;
}

function wrapText(t: string, n: number) { const w = t.split(" "); const out: string[] = []; let c = ""; for (const x of w) { if ((c + " " + x).length > n) { out.push(c); c = x; } else c = (c + " " + x).trim(); } if (c) out.push(c); return out; }

function Share() {
  const sp = useSearchParams();
  const [res, setRes] = useState<{ spec: CardSpec; back: string } | null>(null);
  const [err, setErr] = useState(false);
  const [story, setStory] = useState(false);
  const [saved, setSaved] = useState<number | null>(null);
  const ref = useRef<SVGSVGElement>(null);
  useEffect(() => { build(new URLSearchParams(sp.toString())).then((r) => (r ? setRes(r) : setErr(true))).catch(() => setErr(true)); }, [sp.toString()]);
  if (err) return <div className="empty" style={{ marginTop: 30 }}>Nothing to share for that link.</div>;
  if (!res) return <div className="loading">Building the card…</div>;
  return (
    <div className="fade-in" style={{ marginTop: 20 }}>
      <div className="eyebrow">Share card · export only</div>
      <div style={{ display: "flex", gap: 8, flexWrap: "wrap", margin: "8px 0 12px" }}>
        <div className="seg"><button className={!story ? "on" : ""} onClick={() => setStory(false)}>1080×1350</button><button className={story ? "on" : ""} onClick={() => setStory(true)}>1080×1920</button></div>
        <button className="btn primary" data-testid="download-png" onClick={async () => ref.current && setSaved(await svgToPng(ref.current, `cricintel-${sp.get("type")}-${story ? "story" : "portrait"}.png`))}>Download PNG</button>
        <Link className="btn" href={res.back}>Back to the source</Link>
      </div>
      {saved && <div className="mini" data-testid="saved">PNG generated ({Math.round(saved / 1024)} KB).</div>}
      <div className="share-frame" style={{ maxWidth: story ? 380 : 480 }}><ShareCard ref={ref} spec={res.spec} story={story} /></div>
      <div className="mini" style={{ marginTop: 8 }}>No posting integrations: the card is generated in your browser. It keeps the internal-preview mark until the data licence is resolved.</div>
    </div>
  );
}
