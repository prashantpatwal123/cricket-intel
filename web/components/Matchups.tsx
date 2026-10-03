"use client";
import { useEffect, useState } from "react";
import { api, fmt, Params } from "@/lib/api";
import ProvBadge from "./Prov";

const GROUPS = [["bowler", "Bowlers"], ["bowler_family", "Pace / Spin"], ["bowler_style", "Style"], ["bowler_arm", "Arm"]] as const;

export default function Matchups({ pid, filters, onDrill }: { pid: string; filters: Params; onDrill: (title: string, q: Params) => void }) {
  const [by, setBy] = useState<string>("bowler");
  const [q, setQ] = useState("");
  const [data, setData] = useState<any | null>(null);
  const [all, setAll] = useState(false);
  useEffect(() => {
    const t = setTimeout(() => api(`/players/${pid}/matchups`, { ...filters, by, q: by === "bowler" ? q : "", limit: 40 }).then((r) => setData(r.data)), 120);
    return () => clearTimeout(t);
  }, [pid, by, q, JSON.stringify(filters)]);
  const base = data?.baseline;
  const unknownRow = data?.rows.find((r: any) => r.k === null);
  return (
    <div className="card">
      <div className="seg" style={{ marginBottom: 12, flexWrap: "wrap" }}>
        {GROUPS.map(([k, l]) => <button key={k} className={by === k ? "on" : ""} onClick={() => setBy(k)}>{l}</button>)}
      </div>
      {by === "bowler" && <input className="input" placeholder="Find a bowler…" value={q} onChange={(e) => setQ(e.target.value)} style={{ marginBottom: 10 }} />}
      {by !== "bowler" && (
        <div className="mini" style={{ marginBottom: 8 }}>
          Groups come from bowler metadata <ProvBadge prov="DERIVED" title="Bowling style from a metadata source; arm/family parsed from the style" />.
          {unknownRow ? ` ${fmt(unknownRow.balls)} balls are against bowlers whose type we don't know. They're shown as "unknown", not guessed.` : ""}
        </div>
      )}
      <div className="scroll-x">
        <table className="mtable">
          <thead><tr><th>{by === "bowler" ? "Bowler" : "Group"}</th><th>Balls</th><th>Runs</th><th>SR</th><th>Outs</th><th>R/Out</th><th>Dot%</th><th>Bdry%</th><th>0s</th><th>1s</th><th>2s</th><th>3s</th><th>4s</th><th>6s</th></tr></thead>
          <tbody>
            {base && (
              <tr><td className="strong">All bowlers</td><td>{fmt(base.balls)}</td><td>{fmt(base.runs)}</td><td>{fmt(base.strike_rate, 1)}</td><td className="wk">{base.dismissals}</td>
                <td>{fmt(base.runs_per_dismissal, 1)}</td><td>{fmt(base.dot_pct, 1)}</td><td>{fmt(base.boundary_pct, 1)}</td><td>{base.dots}</td><td>{base.ones}</td><td>{base.twos}</td><td>{base.threes}</td><td>{base.fours}</td><td>{base.sixes}</td></tr>
            )}
            {data?.rows.slice(0, all ? undefined : 12).map((r: any) => (
              <tr key={String(r.k)} className="click" onClick={() => onDrill(
                `${r.label ?? "Unknown type"}: every ball faced`,
                by === "bowler" ? { batter_id: pid, bowler_id: r.k, ...filters } : { batter_id: pid, ...filters, ...(r.k ? { [by]: r.k } : {}) })}>
                <td className="strong">{r.label ?? <span className="mini">unknown</span>}{r.balls < 30 && <span className="mini" title="Small sample"> · small n</span>}</td>
                <td>{fmt(r.balls)}</td><td>{fmt(r.runs)}</td><td>{fmt(r.strike_rate, 1)}</td><td className="wk">{r.dismissals}</td>
                <td>{fmt(r.runs_per_dismissal, 1)}</td><td>{fmt(r.dot_pct, 1)}</td><td>{fmt(r.boundary_pct, 1)}</td><td>{r.dots}</td><td>{r.ones}</td><td>{r.twos}</td><td>{r.threes}</td><td>{r.fours}</td><td>{r.sixes}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {data && data.rows.length > 12 && <button className="btn" style={{ marginTop: 10 }} onClick={() => setAll(!all)}>{all ? "Show top 12" : `Show all ${data.rows.length}`}</button>}
      <div className="mini" style={{ marginTop: 8 }}>Outs = wickets credited to the bowler (run-outs excluded). Tap a row to see the deliveries. Rows under 30 balls are flagged as small samples.</div>
    </div>
  );
}
