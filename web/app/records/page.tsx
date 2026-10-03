"use client";
// Records Explorer: one generic engine. Every leaderboard shows its definition, filters, threshold and coverage.
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useMemo, useState } from "react";
import { api, fmt } from "@/lib/api";
import ProvBadge from "@/components/Prov";

const SEGS: { key: string; label: string; opts: [string, string][] }[] = [
  { key: "gender", label: "", opts: [["male", "Men"], ["female", "Women"]] },
  { key: "format", label: "Format", opts: [["", "All"], ["T20", "T20"], ["ODI", "ODI"]] },
  { key: "team_type", label: "Level", opts: [["", "All"], ["international", "Intl"], ["club", "League"]] },
  { key: "phase", label: "Phase", opts: [["", "All"], ["powerplay", "Powerplay"], ["middle", "Middle"], ["death", "Death"]] },
  { key: "chasing", label: "Innings", opts: [["", "Both"], ["false", "Setting"], ["true", "Chasing"]] },
  { key: "full_members", label: "Teams", opts: [["", "All"], ["true", "Full members & leagues"]] },
];
const FKEYS = ["format", "team_type", "phase", "chasing", "full_members", "year_from", "year_to"];

export default function Page() { return <Suspense fallback={<div className="loading">Loading…</div>}><Records /></Suspense>; }

function Records() {
  const sp = useSearchParams();
  const router = useRouter();
  const [cat, setCat] = useState<any | null>(null);
  const [lb, setLb] = useState<any | null>(null);
  const [err, setErr] = useState<string | null>(null);
  useEffect(() => { api("/records/catalog").then((r) => setCat(r.data)); }, []);

  // A preset in the URL expands into metric + filters once the catalog is known.
  useEffect(() => {
    const pid = sp.get("preset");
    if (!cat || !pid) return;
    const p = cat.presets.find((x: any) => x.id === pid);
    if (!p) return;
    const n = new URLSearchParams({ metric: p.metric, gender: sp.get("gender") || "male" });
    for (const [k, v] of Object.entries(p.filters)) n.set(k, String(v));
    if (p.min) n.set("min", String(p.min));
    router.replace(`/records?${n}`, { scroll: false });
  }, [cat, sp]);

  const metric = sp.get("metric") || "runs";
  const gender = sp.get("gender") || "male";
  const min = sp.get("min");
  const filt = useMemo(() => Object.fromEntries(FKEYS.map((k) => [k, sp.get(k) || ""]).filter(([, v]) => v)), [sp]);
  const set = (kv: Record<string, string | null>, dropMin = false) => {
    const n = new URLSearchParams(sp.toString());
    n.delete("preset");
    for (const [k, v] of Object.entries(kv)) { if (v) n.set(k, v); else n.delete(k); }
    if (dropMin) n.delete("min");
    router.replace(`/records?${n}`, { scroll: false });
  };
  useEffect(() => {
    if (sp.get("preset")) return;
    setLb(null); setErr(null);
    api("/records", { metric, gender, min_sample: min, limit: 25, ...filt }).then((r) => setLb(r.data)).catch((e) => setErr(String(e.message)));
  }, [sp.toString()]);
  const m = cat?.metrics.find((x: any) => x.key === metric);
  const href = (r: any) => lb.entity === "pair" ? `/battle?bat=${r.ids[0]}&bowl=${r.ids[1]}` : `/players/${r.ids[0]}`;
  const activePreset = cat?.presets.find((p: any) => p.metric === metric && Object.entries(p.filters).every(([k, v]) => String(filt[k] ?? "") === String(v))
    && Object.keys(filt).length === Object.keys(p.filters).length);

  return (
    <div className="fade-in">
      <section className="section" style={{ marginTop: 22 }}>
        <div className="kicker">Records explorer</div>
        <h1 className="big-title" style={{ fontSize: "clamp(34px, 8vw, 58px)", margin: "6px 0 10px" }}>Leaderboards</h1>
        <p className="sub">Covered data only, so these are not official records. Pick a ready-made question or build your own.</p>
        <div className="chips" style={{ marginTop: 10 }}>
          {cat?.presets.map((p: any) => (
            <button key={p.id} className="chip wrap" style={activePreset?.id === p.id ? { borderColor: "var(--accent)", color: "var(--accent)" } : undefined}
              onClick={() => set({ preset: p.id, gender })}>{p.title}</button>
          ))}
        </div>
      </section>

      <section className="section">
        <div className="rec-ctrl">
          <label className="mini" htmlFor="metric">Statistic</label>
          <select id="metric" className="input" value={metric} onChange={(e) => set({ metric: e.target.value }, true)}>
            {["batter", "bowler", "fielder", "dismissed", "pair"].map((ent) => (
              <optgroup key={ent} label={{ batter: "Batting", bowler: "Bowling", fielder: "Fielding", dismissed: "Dismissals", pair: "Batter v bowler" }[ent]}>
                {cat?.metrics.filter((x: any) => x.entity === ent).map((x: any) => <option key={x.key} value={x.key}>{x.label}</option>)}
              </optgroup>
            ))}
          </select>
        </div>
        <div className="filters" style={{ position: "static", flexWrap: "wrap" }}>
          {SEGS.map((s) => (
            <div className="seg" key={s.key}>{s.label && <span className="lab">{s.label}</span>}
              {s.opts.map(([v, l]) => {
                const cur = s.key === "gender" ? gender : (filt[s.key] ?? "");
                return <button key={v} className={cur === v ? "on" : ""} onClick={() => set({ [s.key]: v || null })}>{l}</button>;
              })}
            </div>
          ))}
          <div className="seg"><span className="lab">Years</span>
            <input className="yr" inputMode="numeric" placeholder="from" defaultValue={filt.year_from || ""} key={"f" + filt.year_from} onBlur={(e) => set({ year_from: e.target.value || null })} aria-label="From year" />
            <input className="yr" inputMode="numeric" placeholder="to" defaultValue={filt.year_to || ""} key={"t" + filt.year_to} onBlur={(e) => set({ year_to: e.target.value || null })} aria-label="To year" />
          </div>
          <div className="seg"><span className="lab">Min sample</span>
            <input className="yr" inputMode="numeric" defaultValue={min ?? (m?.min || "")} key={"m" + min + metric} onBlur={(e) => set({ min: e.target.value || null })} aria-label="Minimum sample" />
          </div>
        </div>
      </section>

      {err && <div className="empty">{err}</div>}
      {!lb && !err && <div className="loading">Ranking…</div>}
      {lb && (
        <section className="section" style={{ marginTop: 8 }}>
          <div className="rec-def">
            <div><div className="kicker">{lb.entity_label} · {gender === "female" ? "Women" : "Men"} · {lb.order}</div>
              <div className="h2">{lb.label}</div></div>
            <dl className="kv" style={{ marginTop: 8 }}>
              <dt>Definition</dt><dd>{lb.definition} <ProvBadge prov={metric === "keeper_catches" ? "DERIVED" : "OBSERVED"} /></dd>
              <dt>Filters</dt><dd>{Object.entries(lb.filters).filter(([k]) => k !== "gender").map(([k, v]) => `${k.replace(/_/g, " ")}: ${v}`).join(" · ") || "none"}</dd>
              <dt>Threshold</dt><dd>{lb.min_sample ? `at least ${fmt(lb.min_sample)} ${lb.sample_unit}` : "none (counting statistic)"}</dd>
              <dt>Coverage</dt><dd style={{ fontWeight: 500 }}>{lb.coverage}</dd>
            </dl>
          </div>
          {lb.rows.length === 0 ? <div className="empty" style={{ marginTop: 10 }}>Nobody meets this threshold with these filters.</div> : (
            <div className="rec-list">
              {lb.rows.map((r: any) => (
                <Link key={r.ids.join("|")} href={href(r)} className="rec-row">
                  <span className="rec-rank">{r.rank}</span>
                  <span style={{ minWidth: 0 }}>
                    <span style={{ fontWeight: 800, display: "block", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{r.names.join(" v ")}</span>
                    <span className="mini">{fmt(r.sample)} {lb.sample_unit} · {r.matches} matches · {String(r.first_date).slice(0, 4)}–{String(r.last_date).slice(0, 4)}</span>
                  </span>
                  <span className="rec-val num">{r.value_fmt}</span>
                </Link>
              ))}
            </div>
          )}
          <div className="mini" style={{ marginTop: 8 }}>Tap a row to open the {lb.entity === "pair" ? "battle" : "player"}.</div>
        </section>
      )}
    </div>
  );
}
