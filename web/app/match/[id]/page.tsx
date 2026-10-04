"use client";
// Match Intelligence: the canonical match object. Factual events only; no turning points are claimed.
import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import ProvBadge from "@/components/Prov";
import ExploreNext from "@/components/ExploreNext";
import MomentCard from "@/components/fan/MomentCard";
import { useRemember } from "@/lib/memory";
import Worm from "@/components/viz/Worm";

export default function MatchPage() {
  const { id } = useParams<{ id: string }>();
  const [d, setD] = useState<any | null>(null);
  const [err, setErr] = useState(false);
  const [inn, setInn] = useState(0);
  useRemember("match", id, d?.match ? `${d.match.team1} v ${d.match.team2}` : null, `/match/${id}`);
  useEffect(() => { setD(null); api(`/match/${id}`).then((r) => setD(r.data)).catch(() => setErr(true)); }, [id]);
  if (err) return <div className="empty" style={{ marginTop: 30 }}>Match not found.</div>;
  if (!d) return <div className="loading">Loading the match…</div>;
  const m = d.match, I = d.innings, cur = I[inn];
  const maxOv = m.format_group === "T20" ? 20 : 50;
  return (
    <div className="fade-in">
      <section className="match-head">
        <div className="eyebrow">{m.competition ? <Link href={`/competition?name=${encodeURIComponent(m.competition)}&gender=${m.gender}${m.season ? `&season=${encodeURIComponent(m.season)}` : ""}`} className="ul">{m.competition}</Link> : "Match"}{m.event_stage ? ` · ${m.event_stage}` : ""} · {m.season} · {m.gender === "female" ? "Women" : "Men"} · {m.format_group}</div>
        <div className="scoreboard">
          {I.map((i: any) => (
            <div key={i.innings_no} className={`sb-row ${m.winner === i.batting_team ? "won" : ""}`}>
              <span className="sb-team">{i.batting_team}</span>
              <span className="sb-score num">{i.total_runs}/{i.total_wickets}</span>
              <span className="sb-ov mini">{i.overs} ov · RR {i.run_rate}</span>
            </div>
          ))}
        </div>
        <div className="sb-result">{m.result_line} <ProvBadge prov="OBSERVED" /></div>
        <div className="mini" style={{ marginTop: 4 }}>{m.venue}{m.city ? `, ${m.city}` : ""} · {m.start_date}
          {m.toss_winner ? ` · ${m.toss_winner} won the toss and chose to ${m.toss_decision}` : ""}
          {m.player_of_match_names?.length ? ` · Player of the match: ${m.player_of_match_names.join(", ")}` : ""}</div>
        <div className="cov-line"><span className={`covstat ${d.coverage.status}`}>{d.coverage.status === "COMPLETE" ? "complete" : d.coverage.status === "PARTIAL" ? "gaps known" : "completeness unknown"}</span><span>{d.coverage.text}</span></div>
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginTop: 12 }}>
          <Link className="btn primary" href={`/story/match/${id}`}>How the match unfolded →</Link>
          <Link className="btn" href={`/share?type=match&id=${id}`}>Share card</Link>
        </div>
      </section>

      <MomentCard type="match" k={id} context="A real pre-ball moment from this match. Replay opens at that ball; nothing after it is shown until you pick." />
      <section className="rule-section">
        <div className="eyebrow">Worm & Manhattan <ProvBadge prov="DERIVED" /></div>
        <Worm innings={I.map((i: any) => ({ team: i.batting_team, overs: i.overs_list }))} maxOvers={maxOv} />
        <div className="legend">{I.map((i: any, k: number) => <span key={k}><i style={{ borderTopColor: ["#35e0c2", "#ffb547"][k], borderTopWidth: 3 }} />{i.batting_team}</span>)}
          <span>bars = runs per over · red dots = wickets</span></div>
      </section>

      <section className="rule-section">
        <div className="eyebrow">Key events (factual)</div>
        <div className="mini">{d.turning_points}</div>
        <div className="tablist" style={{ marginTop: 6 }}>
          {d.events.map((e: any, i: number) => (
            <div key={i} className="ev-line">
              <span className={`ev-k ${e.kind === "collapse" ? "dismissed" : e.kind}`}>{e.kind.replace("_", " ")}</span>
              {e.delivery_id ? <Link href={`/delivery/${encodeURIComponent(e.delivery_id)}`}>{e.label} →</Link> : <span>{e.label}</span>}
            </div>
          ))}
        </div>
        {d.experimental && (
          <div className="exp-box" style={{ marginTop: 12 }}>
            <div className="exp-tag">{d.experimental.label}</div>
            {d.experimental.rows.map((r: any) => <div key={r.delivery_id} className="mini" style={{ marginTop: 4 }}>
              <Link href={`/delivery/${encodeURIComponent(r.delivery_id)}`} className="ul">{r.ball_label}</Link> {r.batter} v {r.bowler}: {r.event} · difficulty {r.from} → {r.to} ({r.change > 0 ? "+" : ""}{r.change})</div>)}
            <div className="mini" style={{ marginTop: 4 }}>{d.experimental.note}</div>
          </div>
        )}
      </section>

      <section className="rule-section">
        <div className="tabs" style={{ position: "static", margin: 0, padding: 0 }}>
          {I.map((i: any, k: number) => <button key={k} className={inn === k ? "on" : ""} onClick={() => setInn(k)}>{i.batting_team} innings</button>)}
        </div>
        {cur && (
          <div className="cols2" style={{ marginTop: 10 }}>
            <div>
              <div className="eyebrow" style={{ marginTop: 8 }}>Batting <ProvBadge prov="OBSERVED" /></div>
              <div className="tablist">
                {cur.batting.map((b: any) => (
                  <Link key={b.batter_id} className="sc-row" href={`/innings/${id}/${cur.innings_no}/${b.batter_id}`}>
                    <span className="t"><b>{b.name}</b><span className="mini">{b.not_out ? "not out" : `${b.out_kind}${b.out_bowler ? ` b ${b.out_bowler}` : ""}`}</span></span>
                    <span className="num v">{b.runs}{b.not_out ? "*" : ""}</span><span className="num mini">({b.balls}) {b.fours}×4 {b.sixes}×6</span>
                  </Link>
                ))}
              </div>
              <div className="mini" style={{ marginTop: 6 }}>Extras {cur.extras}. Tap a batter for the ball-by-ball Innings Story.</div>
              <div className="eyebrow" style={{ marginTop: 14 }}>Fall of wickets</div>
              <div className="fow">{cur.fall_of_wickets.map((f: any) => <Link key={f.delivery_id} href={`/delivery/${encodeURIComponent(f.delivery_id)}`}><b>{f.score}/{f.wkt}</b> <span className="mini">{f.player_out}, {f.ball_label}</span></Link>)}</div>
            </div>
            <div>
              <div className="eyebrow" style={{ marginTop: 8 }}>Bowling <ProvBadge prov="OBSERVED" /></div>
              <div className="tablist">
                {cur.bowling.map((b: any) => (
                  <Link key={b.bowler_id} className="sc-row" href={`/spell/${id}/${cur.innings_no}/${b.bowler_id}`}>
                    <span className="t"><b>{b.name}</b><span className="mini">{Math.floor(b.balls / 6)}.{b.balls % 6} ov · {b.dots} dots</span></span>
                    <span className="num v">{b.wickets}/{b.runs}</span><span className="num mini">econ {(6 * b.runs / b.balls).toFixed(2)}</span>
                  </Link>
                ))}
              </div>
              <div className="eyebrow" style={{ marginTop: 14 }}>By phase</div>
              <div className="statline">{["powerplay", "middle", "death"].filter((p) => cur.phases[p]).map((p) => <div key={p}><b className="num">{cur.phases[p].runs}/{cur.phases[p].wkts}</b><span>{p}</span></div>)}</div>
            </div>
          </div>
        )}
      </section>

      <section className="rule-section cols2">
        <div>
          <div className="eyebrow">Biggest partnerships</div>
          <div className="tablist">{d.partnerships.map((p: any, i: number) => (
            <Link key={p.partnership_id} className="trow" href={`/innings/${id}/${p.innings_no}/${p.p1}`}><span className="n">{i + 1}</span>
              <span className="t"><b>{p.p1_name} & {p.p2_name}</b><span className="mini">for the {p.wicket_no + 1}{["st", "nd", "rd"][p.wicket_no] ?? "th"} wicket</span></span><span className="v num">{p.runs} <span className="mini">({p.balls})</span></span></Link>))}</div>
        </div>
        <div>
          <div className="eyebrow">Battles in this match</div>
          <div className="tablist">{d.battles.map((b: any) => (
            <Link key={b.batter_id + b.bowler_id} className="trow" href={`/battle?bat=${b.batter_id}&bowl=${b.bowler_id}`}><span className="n">⚔</span>
              <span className="t"><b>{b.batter} v {b.bowler}</b><span className="mini">{b.career_balls ? `career: ${b.career_runs} off ${b.career_balls}, ${b.career_outs} out` : "first meetings in covered data"}</span></span>
              <span className="v num">{b.runs}<span className="mini">/{b.balls}{b.outs ? " · out" : ""}</span></span></Link>))}</div>
        </div>
      </section>

      {d.records.length > 0 && (
        <section className="rule-section">
          <div className="eyebrow">Where this match ranks <ProvBadge prov="DERIVED" /></div>
          {d.records.map((r: any, i: number) => <div key={i} style={{ marginTop: 6, fontSize: 14.5 }}>{r.label}.</div>)}
          <div className="mini" style={{ marginTop: 4 }}>Covered data only; not official records.</div>
        </section>
      )}
      <ExploreNext type="match" id={id} />
    </div>
  );
}
