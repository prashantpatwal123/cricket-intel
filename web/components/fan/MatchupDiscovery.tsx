"use client";
// Matchup discovery: biggest battles, nemeses, who they dominated, balanced and unusual battles. Uncertainty stays visible:
// small samples are labelled, "rivalry" is earned (120+ balls across 5+ matches), and each row says what it is compared with.
import Link from "next/link";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { WhyBox } from "./bits";

const LABELS: Record<string, [string, string]> = {
  biggest: ["Biggest battles", "Most balls faced against one bowler"],
  dismissed_most: ["Dismissed most by", "Bowler-credited dismissals, with the number their usual rate would give"],
  dominated: ["Dominated", "Highest strike rate against a bowler compared with their usual (shrunk toward usual)"],
  balanced: ["Most balanced", "Long battles where neither side moved far from usual"],
  unusual: ["Unusual", "Dismissal counts far from what the usual rate would give"],
  dismissed_most_often: ["Dismissed most", "Batters this bowler got out most often"],
  took_apart: ["Took them apart", "Batters who scored much faster than usual against this bowler"],
  kept_quiet: ["Kept quiet", "Batters who scored much slower than usual against this bowler"],
};

export default function MatchupDiscovery({ pid, name }: { pid: string; name: string }) {
  const [d, setD] = useState<any | null>(null);
  const [view, setView] = useState<string | null>(null);
  const [tab, setTab] = useState<string>("biggest");
  useEffect(() => { api(`/fan/player/${pid}/matchups`).then((r) => { setD(r.data); setView(Object.keys(r.data.views)[0] ?? null); }).catch(() => setD({ views: {} })); }, [pid]);
  if (!d) return <div className="loading">Finding their battles…</div>;
  if (!view) return <div className="empty">No battle in covered data reaches 30 balls yet.</div>;
  const v = d.views[view];
  const tabs = Object.keys(v).filter((k) => v[k].length);
  const cur = tabs.includes(tab) ? tab : tabs[0];
  return (
    <div className="mdisc" data-testid="matchup-discovery">
      {Object.keys(d.views).length > 1 && (
        <div className="seg" style={{ marginBottom: 8 }}>
          {Object.keys(d.views).map((k) => <button key={k} className={view === k ? "on" : ""} onClick={() => setView(k)}>{k === "as_batter" ? "Batting" : "Bowling"}</button>)}
        </div>)}
      <div className="mtabs" role="tablist">
        {tabs.map((k) => <button key={k} role="tab" aria-selected={cur === k} className={`mtab ${cur === k ? "on" : ""}`} onClick={() => setTab(k)}>{LABELS[k]?.[0] ?? k}</button>)}
      </div>
      <div className="mini" style={{ margin: "6px 0 4px" }}>{LABELS[cur]?.[1]} <WhyBox why={d.rules} /></div>
      <div className="mrows">
        {v[cur].map((r: any) => (
          <Link key={r.pid} href={r.href} className="mrow">
            <span className="mn"><b>{r.name}</b>{r.label === "rivalry" ? <span className="tag ok">rivalry</span> : r.label === "small sample" ? <span className="tag warn">small sample</span> : null}
              <span className="mini">{r.why}</span></span>
            <span className="mv num"><b>{r.runs}</b><span className="mini">off {r.balls}</span><span className="mini">{r.outs} out</span></span>
          </Link>
        ))}
      </div>
    </div>
  );
}
