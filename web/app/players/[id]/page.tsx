"use client";
import { useParams, useRouter, useSearchParams } from "next/navigation";
import { Suspense, useCallback, useEffect, useMemo, useState } from "react";
import { api, fmt, Params } from "@/lib/api";
import ProvBadge from "@/components/Prov";
import HowOut from "@/components/HowOut";
import Matchups from "@/components/Matchups";
import Situations from "@/components/Situations";
import Deliveries from "@/components/Deliveries";

const FILTERS: { key: string; label: string; opts: [string, string][] }[] = [
  { key: "format", label: "Format", opts: [["", "All"], ["T20", "T20"], ["ODI", "ODI"]] },
  { key: "team_type", label: "Level", opts: [["", "All"], ["international", "Intl"], ["club", "League"]] },
  { key: "phase", label: "Phase", opts: [["", "All"], ["powerplay", "Powerplay"], ["middle", "Middle"], ["death", "Death"]] },
  { key: "bowler_family", label: "Bowler", opts: [["", "All"], ["pace", "Pace"], ["spin", "Spin"]] },
];

export default function Page() {
  return <Suspense fallback={<div className="loading">Loading…</div>}><PlayerPage /></Suspense>;
}

function PlayerPage() {
  const { id } = useParams<{ id: string }>();
  const sp = useSearchParams();
  const router = useRouter();
  const filters: Params = useMemo(() => Object.fromEntries(FILTERS.map((f) => [f.key, sp.get(f.key) || ""]).filter(([, v]) => v)), [sp]);
  const route = sp.get("route");
  const [prof, setProf] = useState<any | null>(null);
  const [dis, setDis] = useState<any | null>(null);
  const [drill, setDrill] = useState<{ title: string; q: Params } | null>(null);

  const setParam = useCallback((k: string, v: string | null) => {
    const n = new URLSearchParams(sp.toString());
    if (v) n.set(k, v); else n.delete(k);
    router.replace(`?${n.toString()}`, { scroll: false });
  }, [sp, router]);

  useEffect(() => { api(`/players/${id}/profile`, filters).then((r) => setProf(r.data)).catch(() => setProf({ error: true })); }, [id, JSON.stringify(filters)]);
  useEffect(() => { api(`/players/${id}/dismissals`, filters).then((r) => setDis(r.data)); }, [id, JSON.stringify(filters)]);
  useEffect(() => {
    if (route && dis) {
      const r = dis.routes.find((x: any) => x.route === route);
      setDrill({ title: `${r?.label ?? route}: ${r?.n ?? 0} dismissal${r?.n === 1 ? "" : "s"}`, q: { out_id: id, route, ...filters } });
    }
  }, [route, dis]);

  const onDrill = (title: string, q: Params) => {
    setDrill({ title, q });
    setTimeout(() => document.getElementById("evidence")?.scrollIntoView({ behavior: "smooth", block: "start" }), 60);
  };
  const pickRoute = (r: string | null) => {
    setParam("route", r);
    if (!r) setDrill(null);
    else setTimeout(() => document.getElementById("evidence")?.scrollIntoView({ behavior: "smooth", block: "start" }), 250);
  };

  if (!prof) return <div className="loading">Loading player…</div>;
  if (prof.error) return <div className="empty" style={{ marginTop: 40 }}>Player not found.</div>;
  const m = prof.metadata, bat = prof.batting, bowl = prof.bowling;
  const isBowler = bowl && (!bat?.balls || bowl.balls > bat.balls * 1.3);
  const total = dis?.total ?? 0;
  const topRoute = dis?.routes?.slice().sort((a: any, b: any) => b.n - a.n)[0];

  return (
    <div className="fade-in">
      {/* ---------------- HERO */}
      <section className="hero">
        <div className="kicker">{(prof.genders || []).map((g: string) => (g === "female" ? "Women's cricket" : "Men's cricket")).join(" · ")} · {prof.teams.slice(0, 3).join(" · ")}{prof.teams.length > 3 ? ` +${prof.teams.length - 3}` : ""}</div>
        <h1 className="hero-name">{prof.name}</h1>
        <div className="chips">
          <MetaChip label="Role" f={m.role} />
          <MetaChip label="Bats" f={m.batting_hand} fmtv={(v) => `${v}-handed`} />
          <MetaChip label="Bowls" f={m.bowling_style} />
          {m.wicketkeeper.value && <MetaChip label="Keeper" f={m.wicketkeeper} />}
        </div>
        <div className="hero-stats">
          {isBowler ? (<>
            <HStat v={fmt(bowl.wickets)} l="Wickets" /><HStat v={fmt(bowl.economy, 2)} l="Economy" /><HStat v={fmt(bowl.strike_rate, 1)} l="Balls / wkt" />
          </>) : (<>
            <HStat v={fmt(bat?.runs)} l="Runs" /><HStat v={fmt(bat?.average, 1)} l="Average" /><HStat v={fmt(bat?.strike_rate, 1)} l="Strike rate" />
          </>)}
        </div>
        <div className="coverage"><span className="ico">i</span><span><b>Data coverage:</b> {prof.coverage.statement}</span></div>
        {prof.coverage.notes.map((n: any, i: number) => <div key={i} className="note">{n.text}</div>)}
      </section>

      {/* ---------------- FILTERS */}
      <div className="filters">
        {FILTERS.map((f) => (
          <div className="seg" key={f.key}>
            <span className="lab">{f.label}</span>
            {f.opts.map(([v, l]) => <button key={v} className={(filters[f.key] || "") === v ? "on" : ""} onClick={() => setParam(f.key, v || null)}>{l}</button>)}
          </div>
        ))}
      </div>

      {/* ---------------- HOW THEY GET OUT */}
      <section className="section">
        <div className="section-head">
          <div>
            <div className="kicker">Dismissal DNA</div>
            <div className="h2">How {prof.name} gets out</div>
            <div className="sub">
              {total ? <>{total} dismissals in {fmt(dis.innings)} innings · one every {fmt(dis.balls_per_dismissal, 1)} balls faced.
                {topRoute?.n ? <> Most common: <b>{topRoute.label.toLowerCase()}</b> ({topRoute.pct}%).</> : null}</> : "No dismissals in this selection."}
            </div>
          </div>
        </div>
        <div className="grid2">
          <div className="card">
            {dis && <HowOut routes={dis.routes} hand={m.batting_hand.value} selected={route} onSelect={pickRoute} name={prof.name} />}
          </div>
          <div className="card">
            <div className="routes">
              {dis?.routes.map((r: any) => (
                <button key={r.route} className={`route ${route === r.route ? "on" : ""} ${r.n ? "" : "zero"}`} onClick={() => pickRoute(route === r.route ? null : r.route)} title={r.explain}>
                  <span className="name">{r.label} <ProvBadge prov={r.prov} title={r.explain} /></span>
                  <span className="cnt num">{r.n}<span className="mini"> {r.pct != null ? `${r.pct}%` : ""}</span></span>
                  <span className="bar"><span style={{ width: `${total ? (100 * r.n) / total : 0}%` }} /></span>
                </button>
              ))}
            </div>
            <div className="mini" style={{ marginTop: 10 }}>{dis?.position_note}{dis?.catch_route_mean_confidence ? ` Keeper-vs-fielder split relies on keeper inference (mean confidence ${dis.catch_route_mean_confidence}).` : ""}</div>
            {dis?.top_bowlers?.length > 0 && (
              <div style={{ marginTop: 14 }}>
                <div className="sit-title">Dismissed most often by</div>
                {dis.top_bowlers.map((b: any) => (
                  <button key={b.bowler_id} className="res" style={{ width: "100%", border: 0, marginTop: 4 }}
                          onClick={() => onDrill(`Dismissals by ${b.bowler}`, { out_id: id, bowler_id: b.bowler_id, ...filters })}>
                    <span>{b.bowler}</span><span className="wk">{b.n}</span>
                  </button>
                ))}
              </div>
            )}
            {dis?.by_bowler_family?.length > 0 && (
              <div className="mini" style={{ marginTop: 12 }}>By bowler type: {dis.by_bowler_family.map((x: any) => `${x.family} ${x.n}`).join(" · ")}</div>
            )}
          </div>
        </div>
        {drill && <Deliveries title={drill.title} query={drill.q} onClose={() => { setDrill(null); setParam("route", null); }} />}
      </section>

      {/* ---------------- MATCHUPS */}
      <section className="section">
        <div className="section-head"><div><div className="kicker">Matchup lab</div><div className="h2">Against whom?</div>
          <div className="sub">{prof.name} batting against individual bowlers and bowling types.</div></div></div>
        <Matchups pid={id} filters={filters} onDrill={onDrill} />
      </section>

      {/* ---------------- SITUATIONS */}
      <section className="section">
        <div className="section-head"><div><div className="kicker">Situation map</div><div className="h2">When does it happen?</div>
          <div className="sub">Scoring and dismissal patterns by match situation. Tap an over to see its deliveries.</div></div></div>
        <Situations pid={id} filters={filters} onDrill={onDrill} />
      </section>

      {/* ---------------- NUMBERS */}
      <section className="section">
        <div className="section-head"><div><div className="kicker">The numbers</div><div className="h2">In our dataset</div></div></div>
        <div className="grid2">
          {bat?.innings > 0 && (
            <div className="card"><div className="sit-title">Batting <ProvBadge prov="OBSERVED" /></div>
              <StatGrid items={[["Inns", bat.innings], ["Runs", bat.runs], ["Balls", bat.balls], ["Avg", fmt(bat.average, 2)], ["SR", fmt(bat.strike_rate, 1)],
                ["Not out", bat.not_outs], ["HS", `${bat.hs}${bat.hs_not_out ? "*" : ""}`], ["50s", bat.fifties], ["100s", bat.hundreds], ["Ducks", bat.ducks], ["4s", bat.fours], ["6s", bat.sixes]]} />
              {filters.phase || filters.bowler_family ? <div className="mini" style={{ marginTop: 8 }}>Innings, milestones and averages use format/level filters only. Phase and bowler filters apply to the ball-level sections.</div> : null}
            </div>
          )}
          {bowl && (
            <div className="card"><div className="sit-title">Bowling <ProvBadge prov="OBSERVED" /></div>
              <StatGrid items={[["Inns", bowl.innings], ["Balls", bowl.balls], ["Runs", bowl.runs], ["Wkts", bowl.wickets], ["Econ", fmt(bowl.economy, 2)], ["Avg", fmt(bowl.average, 2)],
                ["SR", fmt(bowl.strike_rate, 1)], ["Best", bowl.best_wickets_innings], ["4w+", bowl.four_plus]]} />
            </div>
          )}
          {prof.fielding && (
            <div className="card"><div className="sit-title">Fielding <ProvBadge prov="OBSERVED" /></div>
              <StatGrid items={[["Catches", prof.fielding.catches], ["As keeper", prof.fielding.catches_as_keeper], ["Stumpings", prof.fielding.stumpings], ["Run-out involvements", prof.fielding.run_out_involvements]]} />
            </div>
          )}
          <div className="card"><div className="sit-title">Where the data comes from</div>
            {prof.coverage.competitions.map((c: any) => (
              <div key={c.competition + c.format_group} className="mini" style={{ marginTop: 4 }}>{c.competition} ({c.format_group}): <b>{c.matches}</b> matches · {c.first_date} → {c.last_date}</div>
            ))}
          </div>
        </div>
      </section>
    </div>
  );
}

function MetaChip({ label, f, fmtv }: { label: string; f: any; fmtv?: (v: string) => string }) {
  if (!f?.value) return <span className="chip unknown" title="Not available in our metadata sources. Not guessed.">{label}: unknown</span>;
  return <span className="chip" title={`${f.source} · confidence ${f.confidence ?? "–"}`}>{label}: <b>{fmtv ? fmtv(f.value) : f.value}</b> <ProvBadge prov={f.prov} /></span>;
}
function HStat({ v, l }: { v: string; l: string }) {
  return <div className="hstat"><div className="v num">{v}</div><div className="l">{l}</div></div>;
}
function StatGrid({ items }: { items: [string, any][] }) {
  return (
    <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(78px, 1fr))", gap: 10, marginTop: 10 }}>
      {items.map(([l, v]) => <div key={l}><div className="num" style={{ fontWeight: 800, fontSize: 19 }}>{typeof v === "number" ? fmt(v) : v ?? "–"}</div><div className="mini">{l}</div></div>)}
    </div>
  );
}
