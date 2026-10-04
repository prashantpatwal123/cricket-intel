"use client";
// WHEN DOES THIS PLAYER CHANGE? Each state shows the player's rate (with 90% interval), the peer rate in that state, and the
// value expected if the player changed exactly as peers do (dashed). Tap a state for the deliveries.
import { useEffect, useState } from "react";
import { api, fmt, Params } from "@/lib/api";
import ProvBadge from "./Prov";

export default function StateAnalysis({ pid, role, format, teamType, onDrill }: { pid: string; role: "batting" | "bowling"; format?: string; teamType?: string; onDrill: (t: string, q: Params) => void }) {
  const [d, setD] = useState<any | null>(null);
  useEffect(() => { setD(null); api(`/players/${pid}/states`, { role, format, team_type: teamType }).then((r) => setD(r.data)); }, [pid, role, format, teamType]);
  if (!d) return <div className="loading">Comparing every state…</div>;
  if (!d.available) return <div className="empty">{d.reason}.</div>;
  const main = d.main_metric, bat = role === "batting";
  const unit = bat ? "strike rate" : "economy";
  const all = d.groups.flatMap((g: any) => g.rows.flatMap((r: any) => [r.player?.[main], r.peer?.[main], r.expected_if_typical, ...(r.player?.[bat ? "sr_interval" : "econ_interval"] || [])])).filter((v: any) => v != null);
  const lo = Math.max(0, Math.min(...all) * 0.9), hi = Math.max(...all) * 1.05;
  const X = (v: number) => `${(100 * (v - lo)) / (hi - lo)}%`;
  const better = (x: number) => bat ? x > 0 : x < 0;
  return (
    <div>
      <div className="mini">{d.format} · {d.peer_definition} · player overall {unit} <b>{d.baseline[main]}</b> v peers {d.peer_baseline[main]} <ProvBadge prov="OBSERVED" /></div>
      {d.biggest_changes.length > 0 ? (
        <div className="icards" style={{ marginTop: 10 }}>
          {d.biggest_changes.slice(0, 2).map((c: any) => (
            <div key={c.group + c.bucket} className={`icard ${better(c.relative) ? "strength" : "weakness"}`}>
              <span className={`ikind ${better(c.relative) ? "strength" : "weakness"}`}>Changes more than peers</span>
              <div className="ihead">{bat ? "Scores" : "Concedes"} {Math.abs(c.relative)} {bat ? "strike-rate points" : "runs an over"} {c.relative > 0 ? "more" : "less"} than expected {c.phrase}</div>
              <div className="mini" style={{ marginTop: 4 }}>{fmt(c.balls)} balls. Expected = their overall {unit} shifted by how much peers change in that state. Clear at 99%.</div>
            </div>
          ))}
        </div>
      ) : <div className="note">No state differs clearly from what peers would predict (99% test, enough sample). That is a finding: this player changes the way typical {bat ? "batters" : "bowlers"} do.</div>}
      {d.groups.map((g: any) => (
        <div key={g.key} className="card state-grp">
          <div className="sit-title">{g.label}</div>
          {g.rows.map((r: any) => {
            const p = r.player, iv = p?.[bat ? "sr_interval" : "econ_interval"];
            return (
              <button key={r.bucket} className="state-row" disabled={!r.evidence} onClick={() => r.evidence && onDrill(`${g.label}: ${r.bucket}`, r.evidence)}>
                <span><b>{r.bucket}</b>{p ? <span className="mini"><br />{fmt(p.balls)} balls{r.small_sample ? " · small" : ""}</span> : <span className="mini"><br />none</span>}</span>
                <span className="state-track" aria-label={p ? `${unit} ${p[main]}, peers ${r.peer?.[main]}` : "no data"}>
                  <span className="axis" />
                  {iv && <span className="ci" style={{ left: X(iv[0]), width: `calc(${X(iv[1])} - ${X(iv[0])})` }} />}
                  {r.peer && <span className="pe" style={{ left: X(r.peer[main]) }} title={`peers ${r.peer[main]}`} />}
                  {r.expected_if_typical != null && <span className="ex" style={{ left: X(r.expected_if_typical) }} title={`expected if typical ${r.expected_if_typical}`} />}
                  {p && <span className="me" style={{ left: X(p[main]) }} title={`${p[main]}`} />}
                </span>
                <span className={`state-delta num ${r.clear ? (better(r.relative_change[main]) ? "pos" : "neg") : ""}`}>
                  {p ? p[main] : "–"}<span className="mini"><br />{r.relative_change ? `${r.relative_change[main] > 0 ? "+" : ""}${r.relative_change[main]} rel.` : ""}{r.clear ? " ●" : ""}</span>
                </span>
              </button>
            );
          })}
        </div>
      ))}
      <div className="legend" style={{ marginTop: 8 }}>
        <span><i style={{ borderTopColor: "var(--accent)", borderTopWidth: 3 }} />player (band = 90% interval)</span>
        <span><i style={{ borderTopColor: "#ffb547", borderTopWidth: 3 }} />peers in that state</span>
        <span><i style={{ borderTopStyle: "dashed" }} />expected if the player changed like peers</span><span>● clear at 99%</span>
      </div>
      <div className="mini" style={{ marginTop: 6 }}>{d.method}</div>
    </div>
  );
}
