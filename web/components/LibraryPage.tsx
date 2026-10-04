"use client";
// Shared Innings / Spell library UI: category list, filters, definition, ranked rows that open the story.
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import ProvBadge from "./Prov";

export default function LibraryPage({ kind }: { kind: "innings" | "spells" }) {
  const sp = useSearchParams();
  const router = useRouter();
  const def = kind === "innings" ? "highest" : "best_figures";
  const f = { cat: sp.get("cat") || def, gender: sp.get("gender") || "male", format: sp.get("format") || "T20", competition: sp.get("competition") || "",
              full_members: sp.get("full_members") !== "false" };
  const [d, setD] = useState<any | null>(null);
  const set = (kv: Record<string, string>) => { const n = new URLSearchParams(sp.toString()); for (const [k, v] of Object.entries(kv)) v ? n.set(k, v) : n.delete(k); router.replace(`/${kind}?${n}`, { scroll: false }); };
  useEffect(() => { setD(null); api(`/library/${kind}`, { ...f, full_members: String(f.full_members) }).then((r) => setD(r.data)); }, [sp.toString()]);
  return (
    <div className="fade-in">
      <section style={{ marginTop: 22 }}>
        <div className="eyebrow">{kind === "innings" ? "Innings library" : "Spell library"}</div>
        <h1 className="display-xl">{kind === "innings" ? "Find an innings" : "Find a spell"}</h1>
        <p className="lead">{kind === "innings" ? "Every ranking opens the ball-by-ball Innings Story." : "Every ranking opens the over-by-over Spell Story."} Definitions and minimum samples are shown with each list.</p>
      </section>
      <div className="cat-strip">
        {d && Object.entries(d.categories).map(([k, l]) => <button key={k} className={f.cat === k ? "on" : ""} onClick={() => set({ cat: k })}>{l as string}</button>)}
      </div>
      <div className="filters" style={{ position: "static", flexWrap: "wrap" }}>
        <div className="seg">{[["male", "Men"], ["female", "Women"]].map(([v, l]) => <button key={v} className={f.gender === v ? "on" : ""} onClick={() => set({ gender: v })}>{l}</button>)}</div>
        <div className="seg"><span className="lab">Format</span>{[["T20", "T20"], ["ODI", "ODI"]].map(([v, l]) => <button key={v} className={f.format === v ? "on" : ""} onClick={() => set({ format: v })}>{l}</button>)}</div>
        <div className="seg"><span className="lab">Teams</span>{[["true", "Full members & leagues"], ["false", "All"]].map(([v, l]) => <button key={v} className={String(f.full_members) === v ? "on" : ""} onClick={() => set({ full_members: v })}>{l}</button>)}</div>
        <div className="seg"><span className="lab">Competition</span>{[["", "Any"], [f.gender === "female" ? "Women's Premier League" : "Indian Premier League", f.gender === "female" ? "WPL" : "IPL"]].map(([v, l]) =>
          <button key={l} className={f.competition === v ? "on" : ""} onClick={() => set({ competition: v })}>{l}</button>)}</div>
      </div>
      {!d ? <div className="loading">Ranking…</div> : (
        <section style={{ marginTop: 6 }}>
          <div className="def-line"><b>{d.label}.</b> {d.definition} <span className="mini">{d.scope} · {d.note}</span> <ProvBadge prov="DERIVED" /></div>
          <div className="tablist">
            {d.rows.length === 0 && <div className="empty">Nothing qualifies with these filters.</div>}
            {d.rows.map((r: any, i: number) => kind === "innings" ? (
              <Link key={r.match_id + r.innings_no + r.batter_id} className="trow" href={`/innings/${r.match_id}/${r.innings_no}/${r.batter_id}`}>
                <span className="n">{i + 1}</span>
                <span className="t"><b>{r.name}</b><span className="mini">{r.metric} · v {r.opponent} · {r.competition} · {r.start_date}</span></span>
                <span className="v num">{r.runs}{r.not_out ? "*" : ""}<span className="mini"> ({r.balls})</span></span>
              </Link>
            ) : (
              <Link key={r.match_id + r.innings_no + r.bowler_id} className="trow" href={`/spell/${r.match_id}/${r.innings_no}/${r.bowler_id}`}>
                <span className="n">{i + 1}</span>
                <span className="t"><b>{r.name}</b><span className="mini">{r.metric} · v {r.opponent} · {r.competition} · {r.start_date}</span></span>
                <span className="v num">{r.figures}<span className="mini"> ({r.overs})</span></span>
              </Link>
            ))}
          </div>
        </section>
      )}
    </div>
  );
}
