"use client";
import Link from "next/link";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";

export default function InningsList({ pid, format }: { pid: string; format?: string }) {
  const [sort, setSort] = useState("runs");
  const [rows, setRows] = useState<any[] | null>(null);
  useEffect(() => { setRows(null); api<any[]>(`/players/${pid}/innings`, { sort, format, limit: 24 }).then((r) => setRows(r.data)); }, [pid, sort, format]);
  return (
    <div>
      <div className="seg" style={{ marginBottom: 10 }}>{[["runs", "Most runs"], ["recent", "Most recent"], ["sr", "Fastest (15+ balls)"]].map(([k, l]) =>
        <button key={k} className={sort === k ? "on" : ""} onClick={() => setSort(k)}>{l}</button>)}</div>
      {!rows ? <div className="loading">Loading innings…</div> : (
        <div className="dcard-list">
          {rows.map((r) => (
            <Link key={r.match_id + r.innings_no} href={`/innings/${r.match_id}/${r.innings_no}/${pid}`} className="rec-row">
              <span className="rec-rank" style={{ fontSize: 15 }}>{r.format_group}</span>
              <span style={{ minWidth: 0 }}><b style={{ display: "block", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>v {r.opponent}</b>
                <span className="mini">{r.start_date} · {r.competition} · {r.result}</span></span>
              <span className="rec-val num">{r.runs}{r.not_out ? "*" : ""}<span className="mini" style={{ fontSize: 12 }}> ({r.balls})</span></span>
            </Link>
          ))}
        </div>
      )}
      <div className="mini" style={{ marginTop: 6 }}>Open any innings to replay it ball by ball.</div>
    </div>
  );
}
