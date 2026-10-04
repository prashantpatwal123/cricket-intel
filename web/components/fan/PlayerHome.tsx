"use client";
// Fan player home (Phase 7): what kind of cricketer is this, what makes them unusual, where to go next.
// Order: fingerprint → what makes them different → how they get out / take wickets → biggest battles → best stories →
// partnerships → records → career journey → similar players. Methodology lives behind WHY.
import Link from "next/link";
import { Params, fmt } from "@/lib/api";
import Fingerprint from "@/components/Fingerprint";
import HowOut from "@/components/HowOut";
import MatchupDiscovery from "./MatchupDiscovery";
import SimilarPlayers from "./SimilarPlayers";
import { PlayCard, SectionHead, WhyBox } from "./bits";

export default function PlayerHome({ pid, fan, dis, hand, onDrill }: { pid: string; fan: any; dis: any; hand?: string | null; onDrill: (t: string, q: Params) => void }) {
  const h = fan.hero, name = h.name;
  const bowler = h.role.primary === "bowler";
  const diff = fan.different?.items || [];
  const stories = fan.stories?.cards || [];
  const total = dis?.total ?? 0;
  const topRoute = dis?.routes?.slice().sort((a: any, b: any) => b.n - a.n)[0];
  return (
    <>
      <section className="section" style={{ marginTop: 12 }}>
        <SectionHead kicker="Fingerprint" title={`What kind of ${h.kind} is ${name}?`}
          sub="Each petal compares one habit with peers in the same format. Tap a trait below; WHY shows the definition and peer pool." />
        <div className="card"><Fingerprint pid={pid} onDrill={onDrill} compact scope="major" initialRole={bowler ? "bowling" : "auto"} /></div>
      </section>

      <section className="section" data-testid="what-different">
        <SectionHead kicker="What makes them different" title="Unusual, and backed by evidence"
          sub={diff.length ? fan.different.note : undefined} />
        {diff.length ? (
          <div className="diffs">
            {diff.map((it: any) => (
              <div key={it.id} className={`diff ${it.kind}`}>
                <div className="dh">{it.headline}</div>
                <div className="db">{it.body}</div>
                <div className="dm">
                  <span className="mini">{it.sample}{it.stable ? " · holds in both halves of the covered period" : ""}</span>
                  <WhyBox why={it.why} />
                  {it.evidence?.query ? <button className="btn sm" onClick={() => onDrill(it.evidence.label, it.evidence.query)}>Deliveries →</button>
                    : it.evidence?.href ? <Link className="btn sm" href={it.evidence.href}>{it.evidence.label} →</Link> : null}
                  <Link className="why-btn" href={`/share?type=story&pid=${pid}&id=${encodeURIComponent(it.id)}`}>Share</Link>
                </div>
              </div>
            ))}
          </div>
        ) : <div className="empty">Not enough covered balls yet to say what is unusual about {name} ({fmt(h.role.balls_faced)} faced, {fmt(h.role.balls_bowled)} bowled; findings need at least 300 and must pass the tests). That is a result, not a gap.</div>}
      </section>

      {!bowler && total > 0 && (
        <section className="section">
          <SectionHead kicker="Dismissal DNA" title={`How ${name} gets out`}
            sub={<>{total} dismissals · one every {fmt(dis.balls_per_dismissal, 1)} balls.{topRoute?.n ? <> Most often <b>{topRoute.label.toLowerCase()}</b> ({topRoute.pct}%).</> : null}</>}
            right={<Link className="btn" href={`/how-out/${pid}`} data-testid="explore-how-out-home">Step by step →</Link>} />
          <div className="card" style={{ maxWidth: 520 }}><HowOut routes={dis.routes} hand={hand} selected={null} onSelect={(r) => r && (window.location.href = `/how-out/${pid}?route=${r}`)} name={name} /></div>
        </section>
      )}
      {fan.wickets && fan.wickets.total > 0 && (
        <section className="section" data-testid="how-wickets">
          <SectionHead kicker="Wicket DNA" title={`How ${name} takes wickets`} sub={<>{fan.wickets.total} bowler-credited wickets in covered matches. <WhyBox why={fan.wickets.note} /></>} />
          <div className="routes">
            {fan.wickets.routes.map((r: any) => (
              <div key={r.route} className="route static"><span className="name">{r.label}</span><span className="cnt num">{r.n}<span className="mini"> {r.pct}%</span></span>
                <span className="bar"><span style={{ width: `${r.pct}%` }} /></span></div>))}
          </div>
          <div className="mini" style={{ marginTop: 8 }}>
            By phase: {fan.wickets.phases.map((p: any) => `${p.phase} ${p.n}`).join(" · ")} · to new batters (0–9 balls) {fan.wickets.stage.new} · to set batters (30+) {fan.wickets.stage.set}
          </div>
        </section>
      )}

      <section className="section">
        <SectionHead kicker="Matchups" title={bowler ? `${name}'s biggest battles` : `${name}'s biggest battles`} />
        <MatchupDiscovery pid={pid} name={name} />
      </section>

      {(stories.length > 0 || fan.moment) && (
        <section className="section" data-testid="player-stories">
          <SectionHead kicker="Player stories" title="Best stories" sub={fan.stories?.note} />
          {fan.moment && <PlayCard m={fan.moment} />}
          <div className="stories">
            {stories.map((c: any) => (
              <div key={c.id} className="storycard">
                <div className="st">{c.title}</div>
                <div className="sh">{c.headline}</div>
                <div className="sc">{c.comparison}</div>
                <div className="dm"><span className="mini">{c.sample}</span><WhyBox why={c.why} />
                  {c.link?.query ? <button className="btn sm" onClick={() => onDrill(c.link.label, c.link.query)}>Deliveries →</button>
                    : c.link?.href ? <Link className="btn sm" href={c.link.href}>{c.link.label} →</Link> : null}
                  <Link className="why-btn" href={`/share?type=story&pid=${pid}&id=${encodeURIComponent(c.id)}`}>Share</Link></div>
              </div>
            ))}
          </div>
        </section>
      )}

      {fan.partners?.length > 0 && (
        <section className="section">
          <SectionHead kicker="Partnerships" title={`Who ${name} bats with`} right={<Link className="btn" href={`/players/${pid}?tab=partners`}>All partners →</Link>} />
          <div className="mrows">
            {fan.partners.map((p: any) => (
              <Link key={p.pid} href={p.href} className="mrow"><span className="mn"><b>{p.name}</b><span className="mini">{p.stands} stands · best {p.best} · average {p.avg}</span></span>
                <span className="mv num"><b>{fmt(p.runs)}</b><span className="mini">runs together</span></span></Link>))}
          </div>
        </section>
      )}

      {fan.records?.length > 0 && (
        <section className="section" data-testid="player-records">
          <SectionHead kicker="Record book" title="Where they appear in the records" sub="Covered matches only; these are not official records." />
          <div className="mrows">
            {fan.records.map((r: any) => (
              <Link key={r.id} href={`/records/${r.id}`} className="mrow"><span className="mn"><b>{r.title}</b><span className="mini">{r.category}</span></span>
                <span className="mv num"><b>#{r.rank}</b><span className="mini">{r.value_fmt}</span></span></Link>))}
          </div>
        </section>
      )}

      {fan.career?.points?.length > 0 && (
        <section className="section">
          <SectionHead kicker="Career journey" title={`${name}, year by year`} sub={`${fan.career.metric} per covered year; gaps are years without covered matches.`}
            right={<Link className="btn" href={`/players/${pid}?tab=career`}>Career explorer →</Link>} />
          <CareerBars c={fan.career} />
        </section>
      )}

      <section className="section">
        <SectionHead kicker="Similar players" title={`Players who play like ${name}`} />
        <SimilarPlayers pid={pid} name={name} />
      </section>
    </>
  );
}

function CareerBars({ c }: { c: any }) {
  const fmts = Array.from(new Set(c.points.map((p: any) => p.format))) as string[];
  const years = Array.from(new Set(c.points.map((p: any) => p.year))).sort() as number[];
  const max = Math.max(...c.points.map((p: any) => p.value || 0), 1);
  const y0 = years[0], y1 = years[years.length - 1];
  const all = Array.from({ length: y1 - y0 + 1 }, (_, i) => y0 + i);
  return (
    <div className="cbars" role="img" aria-label={`${c.metric} by year`}>
      {fmts.map((f) => (
        <div key={f} className="cbrow">
          <div className="mini" style={{ width: 34 }}>{f}</div>
          <div className="cbtrack">
            {all.map((y) => {
              const p = c.points.find((x: any) => x.year === y && x.format === f);
              return <div key={y} className="cb" title={p ? `${y}: ${p.value} ${c.metric}, ${c.rate} ${p.rate}` : `${y}: no covered matches`}>
                <span style={{ height: p ? `${Math.max(4, (100 * p.value) / max)}%` : 0 }} className={p ? "" : "gap"} /></div>;
            })}
          </div>
        </div>
      ))}
      <div className="cbyears mini"><span>{y0}</span><span>{y1}</span></div>
    </div>
  );
}
