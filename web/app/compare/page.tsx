"use client";
// Compare 2–4 players. Coverage differences are shown next to the numbers; warnings come from the engine.
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";
import { api, fmt } from "@/lib/api";
import PlayerPicker from "@/components/PlayerPicker";
import ProvBadge from "@/components/Prov";

const COLS = ["#35e0c2", "#ffb547", "#7cc4ff", "#c49bff"];
const SEGS = [{ key: "format", label: "Format", opts: [["", "All"], ["T20", "T20"], ["ODI", "ODI"]] },
  { key: "team_type", label: "Level", opts: [["", "All"], ["international", "Intl"], ["club", "League"]] }] as const;
const METRICS: [string, string, number, string][] = [
  ["strike_rate", "Strike rate", 1, "Runs per 100 balls faced"], ["average", "Average", 1, "Runs per dismissal"],
  ["balls_per_dismissal", "Balls per dismissal", 1, "Higher = survives longer"], ["boundary_pct", "Boundary %", 1, "Balls faced hit for 4 or 6"],
  ["dot_pct", "Dot-ball %", 1, "Balls faced with no run off the bat"], ["runs", "Runs", 0, "Depends on how much of the career is covered"],
];

export default function Page() { return <Suspense fallback={<div className="loading">Loading…</div>}><Compare /></Suspense>; }

function Compare() {
  const sp = useSearchParams();
  const router = useRouter();
  const ids = (sp.get("ids") || "").split(",").filter(Boolean).slice(0, 4);
  const f = { format: sp.get("format") || "", team_type: sp.get("team_type") || "" };
  const [d, setD] = useState<any | null>(null);
  const [names, setNames] = useState<Record<string, string>>({});
  const set = (nextIds: string[], nf = f) => {
    const n = new URLSearchParams();
    if (nextIds.length) n.set("ids", nextIds.join(","));
    for (const [k, v] of Object.entries(nf)) if (v) n.set(k, v);
    router.replace(`/compare?${n}`, { scroll: false });
  };
  useEffect(() => {
    if (!ids.length) { setD(null); return; }
    api("/compare", { ids: ids.join(","), ...f }).then((r) => {
      setD(r.data);
      setNames((o) => ({ ...o, ...Object.fromEntries(r.data.players.map((p: any) => [p.player.person_id, p.player.name])) }));
    }).catch(() => setD({ error: true }));
  }, [sp.toString()]);
  const ps = (d?.players || []) as any[];
  const slots = [...ids, ...(ids.length < 4 ? [""] : [])];

  return (
    <div className="fade-in">
      <section className="section" style={{ marginTop: 22 }}>
        <div className="kicker">Compare</div>
        <h1 className="big-title" style={{ fontSize: "clamp(34px, 8vw, 58px)", margin: "6px 0 14px" }}>Side by side</h1>
        <div className="cmp-pickers">
          {slots.map((id, i) => (
            <div key={i} className="cmp-slot" style={{ borderTopColor: COLS[i] }}>
              <PlayerPicker label={`Player ${i + 1}`} value={id ? { person_id: id, name: names[id] || "…" } : null}
                onPick={(p) => set(p ? [...ids.slice(0, i), p.person_id, ...ids.slice(i + 1)].filter((x, j, a) => a.indexOf(x) === j) : ids.filter((x) => x !== id))} />
            </div>
          ))}
        </div>
        <div className="filters" style={{ position: "static" }}>
          {SEGS.map((s) => (
            <div className="seg" key={s.key}><span className="lab">{s.label}</span>
              {s.opts.map(([v, l]) => <button key={v} className={(f as any)[s.key] === v ? "on" : ""} onClick={() => set(ids, { ...f, [s.key]: v })}>{l}</button>)}
            </div>
          ))}
        </div>
      </section>

      {!ids.length && <div className="empty">Pick two to four players. Batting numbers are compared; use the format and level filters to compare like with like.</div>}
      {ids.length > 0 && !d && <div className="loading">Comparing…</div>}
      {d?.warnings?.length > 0 && (
        <div className="cmp-warn">
          <div className="sit-title" style={{ color: "var(--amber)" }}>Before you compare</div>
          <ul className="edge-list">{d.warnings.map((w: string) => <li key={w}>{w}</li>)}</ul>
        </div>
      )}

      {ps.length > 0 && (<>
        <section className="section">
          <div className="cmp-cards">
            {ps.map((p, i) => (
              <div key={p.player.person_id} className="card" style={{ borderTop: `3px solid ${COLS[i]}` }}>
                <Link href={`/players/${p.player.person_id}`} className="pcard-n" style={{ color: COLS[i] }}>{p.player.name} →</Link>
                <div className="mini">{(p.player.genders || []).map((g: string) => g === "female" ? "Women" : "Men").join(", ")} · {(p.player.teams || []).slice(0, 2).join(", ")}</div>
                {p.stats?.balls ? <div className="mini" style={{ marginTop: 6 }}><b style={{ color: "var(--text)" }}>{fmt(p.stats.balls)}</b> balls faced in {p.stats.matches} matches · {String(p.stats.first_date).slice(0, 4)}–{String(p.stats.last_date).slice(0, 4)}<br />{p.stats.formats.join(" + ")} · {p.stats.levels.join(", ")}</div>
                  : <div className="mini" style={{ marginTop: 6 }}>No batting in this selection.</div>}
                <div style={{ marginTop: 8, display: "flex", flexDirection: "column", gap: 4 }}>
                  {p.coverage.map((c: any) => (
                    <div key={c.label + c.team} className="cmp-cov"><span>{c.label} · {c.matches}m</span>
                      <span className={`covstat ${c.status}`}>{{ COMPLETE: "complete", COMPLETE_FOR_TEAM: "no known gaps", PARTIAL: "gaps known", UNKNOWN: "unknown" }[c.status as string] ?? c.status}</span></div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </section>

        <section className="section">
          <div className="section-head"><div><div className="kicker">Batting, in covered data <ProvBadge prov="OBSERVED" /></div><div className="h2">The numbers</div></div></div>
          <div className="ex-cards">
            {METRICS.map(([k, l, dp, help]) => {
              const max = Math.max(1, ...ps.map((p) => p.stats?.[k] ?? 0));
              return (
                <div key={k} className="card">
                  <div className="sit-title">{l}</div><div className="mini">{help}</div>
                  {ps.map((p, i) => (
                    <div key={p.player.person_id} className="cmp-bar">
                      <span className="mini" style={{ color: COLS[i] }}>{p.player.name}</span>
                      <span className="cmp-track"><i style={{ width: `${(100 * (p.stats?.[k] ?? 0)) / max}%`, background: COLS[i] }} /></span>
                      <b className="num">{p.stats?.[k] != null ? fmt(p.stats[k], dp) : "–"}</b>
                    </div>
                  ))}
                </div>
              );
            })}
            <OutRate ps={ps} />
          </div>
        </section>
      </>)}
    </div>
  );
}

/** Dismissals per 100 balls with 90% intervals: overlapping intervals are not presented as a difference. */
function OutRate({ ps }: { ps: any[] }) {
  const ivs = ps.map((p) => p.stats?.out_rate_interval_90).filter(Boolean) as number[][];
  if (!ivs.length) return null;
  const hi = Math.max(...ivs.map((x) => x[1])) * 1.15;
  return (
    <div className="card">
      <div className="sit-title">Dismissals per 100 balls, with uncertainty <ProvBadge prov="MODELLED" title="90% Wilson interval around an observed rate" /></div>
      <div className="mini">Bars are 90% intervals. Where they overlap, the data can&apos;t separate the players.</div>
      {ps.map((p, i) => {
        const iv = p.stats?.out_rate_interval_90, r = p.stats?.balls ? (100 * p.stats.outs) / p.stats.balls : null;
        return (
          <div key={p.player.person_id} className="cmp-bar">
            <span className="mini" style={{ color: COLS[i] }}>{p.player.name}</span>
            <span className="cmp-track" style={{ position: "relative", background: "#ffffff08" }}>
              {iv && <i style={{ position: "absolute", left: `${(100 * iv[0]) / hi}%`, width: `${(100 * (iv[1] - iv[0])) / hi}%`, background: COLS[i], opacity: 0.55 }} />}
              {r != null && <i style={{ position: "absolute", left: `${(100 * r) / hi}%`, width: 2, background: "#fff" }} />}
            </span>
            <b className="num">{r != null ? fmt(r, 2) : "–"}</b>
          </div>
        );
      })}
    </div>
  );
}
