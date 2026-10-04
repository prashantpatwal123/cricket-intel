"use client";
// Player home (Phase 8, compressed + role-adaptive). Target: 3–5 phone screens before deeper exploration.
//   above the fold: defining insight + obvious next actions (the hero card sits above this component)
//   then: what makes them different (top 3) · how they get out / take wickets · biggest battles · best performances · explore more
// Layout adapts to the defensible role: batter, bowler, all-rounder, wicketkeeper-batter, or neutral when the covered
// sample is too small to say. The fingerprint, similar players, full lists and methodology live in purposeful tabs.
import Link from "next/link";
import { useEffect, useState } from "react";
import { api, fmt, Params } from "@/lib/api";
import { PlayCard, SectionHead, WhyBox } from "./bits";
import Feedback from "@/components/Feedback";
import { track } from "@/lib/analytics";

const ROUTE_ORDER = (routes: any[]) => routes.filter((r: any) => r.n).sort((a: any, b: any) => b.n - a.n);

export default function PlayerHome({ pid, fan, dis, onDrill, goTab }: { pid: string; fan: any; dis: any; onDrill: (t: string, q: Params) => void; goTab: (t: string) => void }) {
  const h = fan.hero, name = h.name, L = h.layout as "batter" | "bowler" | "allrounder" | "keeper" | "neutral";
  const bowlerFirst = L === "bowler";
  const diff = (fan.different?.items || []) as any[];
  const stories = (fan.stories?.cards || []) as any[];
  const [mu, setMu] = useState<any | null>(null);
  useEffect(() => { api(`/fan/player/${pid}/matchups`).then((r) => setMu(r.data)).catch(() => setMu({ views: {} })); }, [pid]);
  const defining = diff[0];
  const routes = dis?.routes ? ROUTE_ORDER(dis.routes) : [];
  const total = dis?.total ?? 0;
  const view = mu?.views?.[bowlerFirst ? "as_bowler" : "as_batter"] || mu?.views?.as_batter || mu?.views?.as_bowler;
  const nemesis = view?.dismissed_most?.[0] || view?.dismissed_most_often?.[0];
  const biggest = (view?.biggest || []).slice(0, 3);
  const best = stories.filter((c) => c.id === "best_innings" || c.id === "best_spell");
  const others = stories.filter((c) => c.id !== "best_innings" && c.id !== "best_spell");
  const [allStories, setAllStories] = useState(false);
  const rest = allStories ? others : others.slice(0, 2);

  return (
    <>
      {/* -------- above the fold: one defining insight + the obvious next actions */}
      {defining ? (
        <section className="defining" data-testid="defining-insight" aria-label="Defining insight">
          <div className="tk">What stands out</div>
          <p className="dh">{defining.headline}</p>
          <div className="dm"><span className="mini">{defining.sample}</span><WhyBox why={defining.why} />
            {defining.evidence?.query ? <button className="btn sm" onClick={() => onDrill(defining.evidence.label, defining.evidence.query)}>Deliveries →</button>
              : defining.evidence?.href ? <Link className="btn sm" href={defining.evidence.href}>Evidence →</Link> : null}</div>
        </section>
      ) : (
        <section className="defining neutral" data-testid="defining-insight">
          <div className="tk">In covered matches</div>
          <p className="dh">{L === "neutral" ? `Not enough covered balls yet to say what kind of player ${name} is (${fmt(h.role.balls_faced)} faced, ${fmt(h.role.balls_bowled)} bowled).`
            : `Nothing in ${name}'s numbers clears our bar for "unusual" yet. That is a result, not a gap.`}</p>
        </section>
      )}
      <nav className="actions" aria-label={`Explore ${name}`} data-testid="player-actions">
        {(L !== "bowler" && total > 0) && <Link href={`/how-out/${pid}`} data-testid="explore-how-out-home"><b>How {name.split(" ").slice(-1)[0]} gets out</b><span>{total} dismissals</span></Link>}
        {(L === "bowler" || L === "allrounder") && fan.wickets?.total > 0 && <a href="#wickets"><b>How the wickets come</b><span>{fan.wickets.total} wickets</span></a>}
        {biggest[0] && <Link href={biggest[0].href} onClick={() => track("battle_open", { from: "player_action" })}><b>Biggest battle</b><span>v {biggest[0].name}</span></Link>}
        {fan.moment && <Link href={fan.moment.href}><b>Play a moment</b><span>Call the next ball</span></Link>}
        <Link href={`/compare?ids=${pid}`}><b>Compare</b><span>with anyone</span></Link>
      </nav>

      {/* -------- what makes them different (top 3 after the defining one) */}
      {diff.length > 1 && (
        <section className="section" data-testid="what-different">
          <SectionHead kicker="What makes them different" title="Also unusual" right={<button className="btn sm" onClick={() => goTab("style")}>All findings →</button>} />
          <ul className="plainlist">
            {diff.slice(1, 4).map((it: any) => (
              <li key={it.id}><span className="pl-h">{it.headline}</span>
                <span className="dm"><WhyBox why={{ detail: it.body, sample: it.sample, ...(typeof it.why === "object" ? it.why : { method: it.why }) }} />
                  {it.evidence?.query ? <button className="why-btn" onClick={() => onDrill(it.evidence.label, it.evidence.query)}>Deliveries</button>
                    : it.evidence?.href ? <Link className="why-btn" href={it.evidence.href}>Evidence</Link> : null}</span></li>
            ))}
          </ul>
        </section>
      )}

      {/* -------- how they get out / take wickets (role-adaptive) */}
      <div className={L === "allrounder" ? "grid2" : ""}>
        {L !== "bowler" && total > 0 && (
          <section className="section" data-testid="how-out-summary">
            <SectionHead kicker="Dismissals" title={`How ${name} gets out`} right={<Link className="btn sm" href={`/how-out/${pid}`}>Step by step →</Link>} />
            <RouteBars rows={routes.slice(0, 4).map((r: any) => ({ k: r.route, label: r.label, n: r.n, pct: r.pct }))} total={total} unit="dismissals" />
            <div className="mini">One dismissal every {fmt(dis.balls_per_dismissal, 1)} balls faced. Where the ball pitched and the shot played are not recorded.</div>
          </section>
        )}
        {(L === "bowler" || L === "allrounder") && fan.wickets?.total > 0 && (
          <section className="section" id="wickets" data-testid="how-wickets">
            <SectionHead kicker="Wickets" title={`How ${name} takes wickets`} />
            <RouteBars rows={fan.wickets.routes.slice(0, 4).map((r: any) => ({ k: r.route, label: r.label, n: r.n, pct: r.pct }))} total={fan.wickets.total} unit="wickets" />
            <div className="mini">To new batters (0–9 balls): {fan.wickets.stage.new} · to set batters (30+): {fan.wickets.stage.set}. <WhyBox why={fan.wickets.note} /></div>
          </section>
        )}
      </div>
      {L === "keeper" && h.keeping && (
        <section className="section">
          <div className="strip" aria-label="Keeping in covered matches">
            <div><b>{fmt(h.keeping.ct)}</b><span>catches as keeper</span></div><div><b>{fmt(h.keeping.st)}</b><span>stumpings</span></div>
          </div>
          <div className="mini">Keeper identity is derived per match from the scorecards. <WhyBox why="A catch counts as a keeper catch when the fielder is the side's identified wicketkeeper for that match (DERIVED from Cricsheet scorecards; unresolved matches are excluded)." /></div>
        </section>
      )}

      {/* -------- biggest battles (top 3 + nemesis) */}
      {biggest.length > 0 && (
        <section className="section" data-testid="biggest-battles">
          <SectionHead kicker="Battles" title={`${name}'s biggest battles`} right={<button className="btn sm" onClick={() => goTab("matchups")}>All battles →</button>} />
          <div className="mrows">
            {biggest.map((r: any) => (
              <Link key={r.pid} href={r.href} className="mrow" onClick={() => track("battle_open", { from: "player_biggest" })}>
                <span className="mn"><b>{bowlerFirst ? `bowling to ${r.name}` : `v ${r.name}`}</b><span className="mini">{r.balls} balls · {r.matches} matches{r.label === "small sample" ? " · small sample" : ""}</span></span>
                <span className="mv num"><b>{r.runs}</b><span className="mini">{r.outs} out</span></span>
              </Link>
            ))}
          </div>
          {nemesis && <p className="mini" style={{ marginTop: 8 }}>{bowlerFirst ? "Dismissed most often" : "Dismissed most by"}: <Link className="ul" href={nemesis.href}>{nemesis.name}</Link>, {nemesis.outs} times in {nemesis.balls} balls (about {nemesis.expected_outs} at the usual rate).</p>}
        </section>
      )}

      {/* -------- best performances */}
      {(best.length > 0 || fan.moment || rest.length > 0) && (
        <section className="section" data-testid="player-stories">
          <SectionHead kicker="Best performances" title="The days that stand out" />
          <div className="perfs">
            {best.map((c: any) => (
              <Link key={c.id} href={c.link.href} className="perf"><span className="tk">{c.id === "best_spell" ? "Best spell" : "Best innings"}</span><b>{c.headline}</b><span className="mini">{c.evidence}</span></Link>
            ))}
            {rest.map((c: any) => (
              <div key={c.id} className="perf storycard"><span className="tk">{c.title}</span><b>{c.headline}</b><span className="mini">{c.comparison}</span>
                <span className="dm"><WhyBox why={c.why} />{c.link?.query && <button className="why-btn" onClick={() => onDrill(c.link.label, c.link.query)}>Deliveries</button>}
                  <Link className="why-btn" href={`/share?type=story&pid=${pid}&id=${encodeURIComponent(c.id)}`}>Share</Link></span></div>
            ))}
          </div>
          {others.length > 2 && <button className="btn sm" style={{ marginTop: 8 }} aria-expanded={allStories} onClick={() => setAllStories(!allStories)} data-testid="more-stories">
            {allStories ? "Fewer stories" : `${others.length - 2} more stories`}</button>}
          {fan.moment && <PlayCard m={fan.moment} />}
        </section>
      )}

      {/* -------- explore more: everything else, one tap away */}
      <section className="section" data-testid="explore-more">
        <div className="kicker">Explore more</div>
        <div className="more-links">
          <button onClick={() => goTab("style")}><b>Style & similar players</b><span>Fingerprint against peers</span></button>
          {fan.partners?.length > 0 && <button onClick={() => goTab("partners")}><b>Partnerships</b><span>{fan.partners[0].name} and others</span></button>}
          {fan.records?.length > 0 && <Link href={`/records/${fan.records[0].id}`}><b>Record book</b><span>#{fan.records[0].rank} · {fan.records[0].title}</span></Link>}
          <button onClick={() => goTab("career")}><b>Career</b><span>Year by year</span></button>
          {L !== "bowler" && <button onClick={() => goTab("innings")}><b>Every innings</b><span>Replay any of them</span></button>}
          {(L === "bowler" || L === "allrounder") && <button onClick={() => goTab("bowling")}><b>Every spell</b><span>Bowling in detail</span></button>}
        </div>
      </section>
      <Feedback entity={{ type: "player", id: pid }} item="player_home" />
    </>
  );
}

function RouteBars({ rows, total, unit }: { rows: { k: string; label: string; n: number; pct: number }[]; total: number; unit: string }) {
  return (
    <div className="rbars" role="list" aria-label={`Top ${rows.length} of ${total} ${unit}`}>
      {rows.map((r) => (
        <div key={r.k} className="rbar" role="listitem">
          <span className="rl">{r.label}</span>
          <span className="rt" aria-hidden><span style={{ width: `${Math.max(2, r.pct)}%` }} /></span>
          <span className="rn num">{r.n} <span className="mini">{r.pct}%</span></span>
        </div>
      ))}
    </div>
  );
}
