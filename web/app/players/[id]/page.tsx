"use client";
import { useParams, useRouter, useSearchParams } from "next/navigation";
import { Suspense, useCallback, useEffect, useMemo, useState } from "react";
import { api, fmt, Params } from "@/lib/api";
import ProvBadge from "@/components/Prov";
import HowOut from "@/components/HowOut";
import Matchups from "@/components/Matchups";
import Situations from "@/components/Situations";
import Deliveries from "@/components/Deliveries";
import Fingerprint from "@/components/Fingerprint";
import InsightCard from "@/components/InsightCard";
import DismissalStory from "@/components/DismissalStory";
import Timeline from "@/components/Timeline";
import Link from "next/link";
import StateAnalysis from "@/components/StateAnalysis";
import Partners from "@/components/Partners";
import InningsList from "@/components/InningsList";
import SpellsList from "@/components/SpellsList";
import CareerExplorer from "@/components/CareerExplorer";
import ExploreNext from "@/components/ExploreNext";
import PlayerHome from "@/components/fan/PlayerHome";
import { useRemember } from "@/lib/memory";

const FILTERS: { key: string; label: string; opts: [string, string][] }[] = [
  { key: "format", label: "Format", opts: [["", "All"], ["T20", "T20"], ["ODI", "ODI"]] },
  { key: "team_type", label: "Level", opts: [["", "All"], ["international", "Intl"], ["club", "League"]] },
  { key: "phase", label: "Phase", opts: [["", "All"], ["powerplay", "Powerplay"], ["middle", "Middle"], ["death", "Death"]] },
  { key: "bowler_family", label: "Bowler", opts: [["", "All"], ["pace", "Pace"], ["spin", "Spin"]] },
];

const TABS = [["overview", "Overview"], ["strengths", "Strengths & weaknesses"], ["states", "When they change"], ["dismissals", "Dismissals"],
  ["matchups", "Matchups"], ["partners", "Partners"], ["innings", "Innings"], ["bowling", "Bowling"], ["career", "Career"], ["numbers", "Numbers"]] as const;
// Phase and bowler-type filters only make sense where every number is ball-level.
const BALL_LEVEL_TABS = new Set(["dismissals", "matchups"]);

export default function Page() {
  return <Suspense fallback={<div className="loading">Loading…</div>}><PlayerPage /></Suspense>;
}

function PlayerPage() {
  const { id } = useParams<{ id: string }>();
  const sp = useSearchParams();
  const router = useRouter();
  const tab = sp.get("tab") || "overview";
  const shown = tab === "overview" ? [] : FILTERS.filter((f) => BALL_LEVEL_TABS.has(tab) || f.key === "format" || f.key === "team_type");
  const filters: Params = useMemo(() => Object.fromEntries(shown.map((f) => [f.key, sp.get(f.key) || ""]).filter(([, v]) => v)), [sp, tab]);
  const route = sp.get("route");
  const [prof, setProf] = useState<any | null>(null);
  const [dis, setDis] = useState<any | null>(null);
  const [ins, setIns] = useState<any | null>(null);
  const [drill, setDrill] = useState<{ title: string; q: Params } | null>(null);
  const [covOpen, setCovOpen] = useState(false);
  const [fan, setFan] = useState<any | null>(null);
  useEffect(() => { setFan(null); api(`/fan/player/${id}`).then((r) => setFan(r.data)).catch(() => setFan({ error: true })); }, [id]);
  useRemember("player", id, fan?.hero?.name, `/players/${id}`);

  const setParams = useCallback((kv: Record<string, string | null>) => {
    const n = new URLSearchParams(sp.toString());
    for (const [k, v] of Object.entries(kv)) { if (v) n.set(k, v); else n.delete(k); }
    router.replace(`?${n.toString()}`, { scroll: false });
  }, [sp, router]);
  const setParam = (k: string, v: string | null) => setParams({ [k]: v });

  const base = { format: filters.format, team_type: filters.team_type };
  useEffect(() => { api(`/players/${id}/profile`, filters).then((r) => setProf(r.data)).catch(() => setProf({ error: true })); }, [id, JSON.stringify(filters)]);
  useEffect(() => { api(`/players/${id}/dismissals`, filters).then((r) => setDis(r.data)); }, [id, JSON.stringify(filters)]);
  useEffect(() => {
    if (tab !== "strengths") return;   // the fan home gets its findings from /fan/player; the full engine output loads on its tab
    setIns(null); api(`/players/${id}/insights`, base).then((r) => setIns(r.data)).catch(() => setIns({ cards: [], reason: "unavailable" }));
  }, [id, base.format, base.team_type, tab]);
  useEffect(() => { setDrill(null); }, [tab]);

  const onDrill = (title: string, q: Params) => {
    setDrill({ title, q });
    setTimeout(() => document.getElementById("evidence")?.scrollIntoView({ behavior: "smooth", block: "start" }), 60);
  };
  const pickRoute = (r: string | null) => { setParams({ route: r, tab: "dismissals" }); setDrill(null); };
  const goTab = (t: string) => { setParams({ tab: t === "overview" ? null : t, route: t === "dismissals" ? route : null }); window.scrollTo({ top: 0 }); };

  if (!prof) return <div className="loading">Loading player…</div>;
  if (prof.error) return <div className="empty" style={{ marginTop: 40 }}>Player not found.</div>;
  const m = prof.metadata, bat = prof.batting, bowl = prof.bowling;
  const isBowler = bowl && (!bat?.balls || bowl.balls > bat.balls * 1.3);
  const total = dis?.total ?? 0;
  const cards = (ins?.cards || []) as any[];
  const partial = (prof.coverage.breakdown || []).filter((c: any) => c.status !== "COMPLETE" && c.status !== "COMPLETE_FOR_TEAM").length;

  return (
    <div className="fade-in">
      {/* ---------------- HERO: who is this, in one screen */}
      <section className="hero fan-hero">
        <div className="kicker">{(prof.genders || []).map((g: string) => (g === "female" ? "Women's cricket" : "Men's cricket")).join(" · ")} · {prof.teams.slice(0, 3).join(" · ")}{prof.teams.length > 3 ? ` +${prof.teams.length - 3}` : ""}</div>
        <h1 className="hero-name">{prof.name}</h1>
        {fan?.hero && <div className="hero-line">
          <span className="kind">{fan.hero.kind}</span>
          {fan.hero.formats.map((f: any) => <span key={f.format} className="fmtpill">{f.format} · {f.matches}</span>)}
          {fan.hero.span.from && <span className="mini">{fan.hero.span.from.slice(0, 4)}–{fan.hero.span.to.slice(0, 4)} in covered data</span>}
        </div>}
        {/* known metadata only; unknown fields are explained behind WHY, not shown as hero chips */}
        <div className="chips">
          {[["Role", m.role], ["Bats", m.batting_hand], ["Bowls", m.bowling_style], ["Keeper", m.wicketkeeper]].filter(([, f]: any) => f?.value).map(([l, f]: any) =>
            <MetaChip key={l} label={l} f={f} fmtv={l === "Bats" ? (v) => `${v}-handed` : undefined} />)}
        </div>
        <div className="hero-stats">
          {fan?.hero?.numbers?.length ? fan.hero.numbers.slice(0, 3).map((n: any) => <HStat key={n.l} v={n.v} l={n.l} />) : isBowler ? (<>
            <HStat v={fmt(bowl.wickets)} l="Wickets" /><HStat v={fmt(bowl.economy, 2)} l="Economy" /><HStat v={fmt(bowl.strike_rate, 1)} l="Balls / wkt" />
          </>) : (<>
            <HStat v={fmt(bat?.runs)} l="Runs" /><HStat v={fmt(bat?.average, 1)} l="Average" /><HStat v={fmt(bat?.strike_rate, 1)} l="Strike rate" />
          </>)}
        </div>
        <div className="hero-foot">
          <span className="mini">Covered matches only, not official totals.</span>
          <button className="why-btn" onClick={() => setCovOpen(!covOpen)} aria-expanded={covOpen}>{covOpen ? "Hide" : "WHY? Coverage & metadata"}</button>
          <Link className="btn sm" href={`/compare?ids=${id}`}>Compare</Link>
        </div>
        {covOpen && <div className="fade-in" style={{ marginTop: 10 }}>
          <div className="mini" style={{ marginBottom: 6 }}>{prof.coverage.statement}</div>
          <div className="chips">
            <MetaChip label="Role" f={m.role} />
            <MetaChip label="Bats" f={m.batting_hand} fmtv={(v) => `${v}-handed`} />
            <MetaChip label="Bowls" f={m.bowling_style} />
            {m.wicketkeeper.value && <MetaChip label="Keeper" f={m.wicketkeeper} />}
          </div>
          <div className="covgrid">
            {(prof.coverage.breakdown || []).map((c: any) => (
              <div key={c.label} className="covrow">
                <div><b>{c.label}</b> <span className="mini">{c.matches} matches · {String(c.first_date).slice(0, 4)}–{String(c.last_date).slice(0, 4)}</span></div>
                <span className={`covstat ${c.status}`}>{{ COMPLETE: "complete", COMPLETE_FOR_TEAM: "no known gaps", PARTIAL: "gaps known", UNKNOWN: "completeness unknown" }[c.status as string] ?? c.status}</span>
                <div className="mini" style={{ gridColumn: "1 / -1" }}>{c.note}</div>
              </div>
            ))}
          </div>
          {prof.coverage.notes.filter((n: any) => n.kind !== "source_exclusion").map((n: any, i: number) => <div key={i} className="note">{n.text}</div>)}
          {partial > 0 && <div className="mini">{partial} competition{partial > 1 ? "s" : ""} with gaps or unknown completeness.</div>}
        </div>}
      </section>

      {/* ---------------- TABS + FILTERS */}
      <nav className="tabs" aria-label="Player sections">
        {TABS.filter(([k]) => k !== "bowling" || bowl?.balls).map(([k, l]) => <button key={k} className={tab === k ? "on" : ""} onClick={() => goTab(k)} aria-current={tab === k}>{l}</button>)}
      </nav>
      {shown.length > 0 && <div className="filters" style={{ position: "static" }}>
        {shown.map((f) => (
          <div className="seg" key={f.key}>
            <span className="lab">{f.label}</span>
            {f.opts.map(([v, l]) => <button key={v} className={(filters[f.key] || "") === v ? "on" : ""} onClick={() => setParam(f.key, v || null)}>{l}</button>)}
          </div>
        ))}
      </div>}

      {tab === "overview" && (fan?.hero ? <PlayerHome pid={id} fan={fan} dis={dis} hand={m.batting_hand.value} onDrill={onDrill} />
        : fan?.error ? <div className="empty">Could not load this player's home.</div> : <div className="loading">Reading {prof.name}&apos;s cricket…</div>)}

      {tab === "strengths" && (
        <section className="section" style={{ marginTop: 12 }}>
          <div className="section-head"><div><div className="kicker">Strength & weakness engine</div>
            <div className="h2">{ins?.format ? `${ins.format}${ins.position_band ? ` · ${ins.position_band}` : ""}` : "Findings"}</div>
            <div className="sub">{ins?.baseline ? <>Every split of {prof.name}&apos;s batting is compared with the same split for {ins.baseline}. {ins.tested} splits tested; only findings that survive the sample, effect-size and false-discovery thresholds are shown. Tap WHY for the working.</> : null}</div></div></div>
          <InsightList ins={ins} cards={cards} onDrill={onDrill} />
          {ins?.method && <details className="card" style={{ marginTop: 12 }}><summary className="sit-title" style={{ cursor: "pointer" }}>Method</summary>
            <div className="mini" style={{ whiteSpace: "pre-wrap", marginTop: 8 }}>{ins.method}</div></details>}
        </section>
      )}

      {tab === "dismissals" && (
        <section className="section" style={{ marginTop: 12 }}>
          <div className="section-head"><div><div className="kicker">Dismissal DNA</div><div className="h2">How {prof.name} gets out</div>
            <div className="sub">{total ? <>{total} dismissals in {fmt(dis.innings)} innings · one every {fmt(dis.balls_per_dismissal, 1)} balls faced. Tap a route for its full story.</> : "No dismissals in this selection."}</div></div></div>
          <Link className="btn primary" href={`/how-out/${id}`} data-testid="explore-how-out" style={{ display: "inline-block", marginBottom: 10 }}>Explore how {prof.name} gets out, step by step →</Link>
          <div className="grid2">
            <div className="card">{dis && <HowOut routes={dis.routes} hand={m.batting_hand.value} selected={route} onSelect={pickRoute} name={prof.name} />}</div>
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
            </div>
          </div>
          {route ? <DismissalStory pid={id} route={route} filters={filters} onDrill={onDrill} />
            : <div className="empty" style={{ marginTop: 12 }}>Pick a route above to see when, where in the innings and to whom it happens.</div>}
        </section>
      )}

      {tab === "matchups" && (<>
        <section className="section" style={{ marginTop: 12 }}>
          <div className="section-head"><div><div className="kicker">Matchup lab</div><div className="h2">Against whom?</div>
            <div className="sub">{prof.name} batting against individual bowlers. Open any bowler as a full battle from the Battles tab.</div></div></div>
          <Matchups pid={id} filters={filters} onDrill={onDrill} />
        </section>
        <section className="section">
          <div className="section-head"><div><div className="kicker">Situation map</div><div className="h2">When does it happen?</div>
            <div className="sub">Scoring and dismissal patterns by match situation. Tap an over to see its deliveries.</div></div></div>
          <Situations pid={id} filters={filters} onDrill={onDrill} />
        </section>
      </>)}

      {tab === "states" && (
        <section className="section" style={{ marginTop: 12 }}>
          <div className="section-head"><div><div className="kicker">Batter state analysis</div><div className="h2">When does {prof.name} change?</div>
            <div className="sub">Scoring through the innings and the match situation, against {prof.name}&apos;s own average and against similar batters in the same state.</div></div></div>
          <StateAnalysis pid={id} role="batting" format={filters.format as string} teamType={filters.team_type as string} onDrill={onDrill} />
        </section>
      )}

      {tab === "partners" && (
        <section className="section" style={{ marginTop: 12 }}>
          <div className="section-head"><div><div className="kicker">Partnership intelligence</div><div className="h2">Who {prof.name} bats with</div>
            <div className="sub">Partnerships and whether {prof.name}&apos;s own scoring changes with the partner, adjusted for phase and season.</div></div>
            <Link className="btn" href="/partnerships">Best partnerships →</Link></div>
          <Partners pid={id} format={filters.format as string} teamType={filters.team_type as string} onDrill={onDrill} />
        </section>
      )}

      {tab === "innings" && (
        <section className="section" style={{ marginTop: 12 }}>
          <div className="section-head"><div><div className="kicker">Innings stories</div><div className="h2">Replay an innings</div></div></div>
          <InningsList pid={id} format={filters.format as string} />
        </section>
      )}

      {tab === "bowling" && bowl?.balls > 0 && (<>
        <section className="section" style={{ marginTop: 12 }}>
          <div className="section-head"><div><div className="kicker">Bowler fingerprint</div><div className="h2">How {prof.name} bowls, against peers</div>
            <div className="sub">Built only from what the data records: runs, dots, boundaries, wickets, phases and the batter&apos;s stage. No pace, spin, line or length.</div></div></div>
          <div className="card"><Fingerprint pid={id} format={filters.format as string} teamType={filters.team_type as string} onDrill={onDrill} initialRole="bowling" /></div>
        </section>
        <section className="section">
          <div className="section-head"><div><div className="kicker">Bowler state analysis</div><div className="h2">When does {prof.name}&apos;s bowling change?</div></div></div>
          <StateAnalysis pid={id} role="bowling" format={filters.format as string} teamType={filters.team_type as string} onDrill={onDrill} />
        </section>
        <section className="section">
          <div className="section-head"><div><div className="kicker">Spell stories</div><div className="h2">Replay a spell</div></div></div>
          <SpellsList pid={id} format={filters.format as string} />
        </section>
      </>)}

      {tab === "career" && (
        <section className="section" style={{ marginTop: 12 }}>
          <div className="section-head"><div><div className="kicker">Career explorer</div><div className="h2">{prof.name} through covered data</div>
            <div className="sub">Tap a year to turn the page into that season. Gaps are years with no covered matches.</div></div></div>
          <CareerExplorer pid={id} year={sp.get("year") ? Number(sp.get("year")) : null} setYear={(y) => setParams({ year: y ? String(y) : null })} filters={filters} onDrill={onDrill} />
        </section>
      )}

      {tab === "timeline" && (
        <section className="section" style={{ marginTop: 12 }}>
          <div className="section-head"><div><div className="kicker">Career timeline</div><div className="h2">Year by year, in covered data</div>
            <div className="sub">One line per format and level. Lines break where there is no covered data; nothing is interpolated across a gap.</div></div></div>
          <Timeline pid={id} filters={filters} onDrill={onDrill} />
        </section>
      )}

      {tab === "numbers" && (
        <section className="section" style={{ marginTop: 12 }}>
          <div className="section-head"><div><div className="kicker">The numbers</div><div className="h2">In our dataset</div></div></div>
          <div className="grid2">
            {bat?.innings > 0 && (
              <div className="card"><div className="sit-title">Batting <ProvBadge prov="OBSERVED" /></div>
                <StatGrid items={[["Inns", bat.innings], ["Runs", bat.runs], ["Balls", bat.balls], ["Avg", fmt(bat.average, 2)], ["SR", fmt(bat.strike_rate, 1)],
                  ["Not out", bat.not_outs], ["HS", `${bat.hs}${bat.hs_not_out ? "*" : ""}`], ["50s", bat.fifties], ["100s", bat.hundreds], ["Ducks", bat.ducks], ["4s", bat.fours], ["6s", bat.sixes]]} />
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
          <div style={{ marginTop: 12, display: "flex", gap: 8, flexWrap: "wrap" }}>
            <Link className="btn" href={`/compare?ids=${id}`}>Compare with others →</Link>
          </div>
        </section>
      )}

      {drill && <Deliveries title={drill.title} query={drill.q} onClose={() => setDrill(null)} />}
      <ExploreNext type="player" id={id} />
    </div>
  );
}

function InsightList({ ins, cards, onDrill }: { ins: any; cards: any[]; onDrill: (t: string, q: Params) => void }) {
  if (!ins) return <div className="loading">Testing every split against similar players…</div>;
  if (!cards.length) return <div className="empty">{ins.reason ? `No findings: ${ins.reason}.` : `Nothing in this player's ${ins.format ?? ""} batting differs clearly enough from similar batters to pass our thresholds. That is a result, not a gap.`}</div>;
  return <div className="icards">{cards.map((c) => <InsightCard key={c.id} c={c} onDrill={onDrill} />)}</div>;
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
