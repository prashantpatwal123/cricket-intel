"use client";
import Link from "next/link";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";

export default function SpellsList({ pid, format }: { pid: string; format?: string }) {
  const [sort, setSort] = useState("wickets");
  const [rows, setRows] = useState<any[] | null>(null);
  useEffect(() => { setRows(null); api<any[]>(`/players/${pid}/spells`, { sort, format, limit: 20 }).then((r) => setRows(r.data)); }, [pid, sort, format]);
  return (
    <div>
      <div className="seg" style={{ marginBottom: 10 }}>{[["wickets", "Most wickets"], ["economy", "Tightest (3+ overs)"], ["recent", "Most recent"]].map(([k, l]) =>
        <button key={k} className={sort === k ? "on" : ""} onClick={() => setSort(k)}>{l}</button>)}</div>
      {!rows ? <div className="loading">Loading spells…</div> : (
        <div className="dcard-list">
          {rows.map((r) => (
            <Link key={r.match_id + r.innings_no + r.spell_no} href={`/spell/${r.match_id}/${r.innings_no}/${pid}`} className="rec-row">
              <span className="rec-rank" style={{ fontSize: 15 }}>{r.format_group}</span>
              <span style={{ minWidth: 0 }}><b style={{ display: "block", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>v {r.opponent}</b>
                <span className="mini">{r.start_date} · {r.competition} · spell {r.spell_no}: overs {r.from_over + 1}–{r.to_over + 1}</span></span>
              <span className="rec-val num">{r.wickets}/{r.runs}<span className="mini" style={{ fontSize: 12 }}> ({r.overs} ov)</span></span>
            </Link>
          ))}
        </div>
      )}
      <div className="mini" style={{ marginTop: 6 }}>A spell = overs bowled from one end without a break of more than one over. Open any spell to replay the whole innings&apos; bowling.</div>
    </div>
  );
}
