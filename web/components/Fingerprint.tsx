"use client";
// Cricket Fingerprint: polar view of percentile ranks vs peers. Tap a petal → statistic → deliveries.
import { useEffect, useState } from "react";
import { api, fmt, ordinal, Params } from "@/lib/api";

const GROUP_COLORS: Record<string, string> = {
  Tempo: "#35e0c2", Survival: "#ff5c74", Phase: "#ffb547", Situation: "#7cc4ff", "Innings stage": "#c49bff", Concentration: "#b8c4dd",
  Control: "#35e0c2", Threat: "#ff5c74",
};

export default function Fingerprint({ pid, format, teamType, onDrill, initialRole = "auto", compact = false, scope }: {
  pid: string; format?: string; teamType?: string; onDrill: (title: string, q: Params) => void; initialRole?: "auto" | "batting" | "bowling";
  compact?: boolean; // fan home: no tiny petal labels; readable trait chips; method behind WHY
  scope?: "major";   // fan home: leagues + full-member internationals for the player and the peers
}) {
  const [role, setRole] = useState<"auto" | "batting" | "bowling">(initialRole);
  const [fp, setFp] = useState<any | null>(null);
  const [sel, setSel] = useState<string | null>(null);
  useEffect(() => {
    setFp(null);
    api(`/players/${pid}/fingerprint`, { role, format, team_type: teamType, scope }).then((r) => {
      setFp(r.data);
      const first = (r.data.dimensions || []).find((d: any) => d.enough_sample);
      setSel(first?.key ?? null);
    });
  }, [pid, role, format, teamType, scope]);
  if (!fp) return <div className="loading">Building fingerprint…</div>;
  if (!fp.available) return <div className="empty">No fingerprint: {fp.reason}.</div>;
  const dims = fp.dimensions as any[];
  const N = dims.length, S = 360, cx = S / 2, cy = S / 2, r0 = 46, R = 150;
  const d = dims.find((x) => x.key === sel);
  const arc = (i: number, frac: number) => {
    const a0 = (i / N) * 2 * Math.PI - Math.PI / 2 + 0.03, a1 = ((i + 1) / N) * 2 * Math.PI - Math.PI / 2 - 0.03;
    const r = r0 + (R - r0) * frac;
    const p = (a: number, rr: number) => `${cx + rr * Math.cos(a)} ${cy + rr * Math.sin(a)}`;
    return `M ${p(a0, r0)} L ${p(a0, r)} A ${r} ${r} 0 0 1 ${p(a1, r)} L ${p(a1, r0)} A ${r0} ${r0} 0 0 0 ${p(a0, r0)} Z`;
  };
  const isBowl = fp.role === "bowling";
  return (
    <div className="fp">
      <div className="fp-head">
        <div className="seg">
          {(["auto", "batting", "bowling"] as const).map((r) => <button key={r} className={role === r ? "on" : ""} onClick={() => setRole(r)}>{r === "auto" ? "Main role" : r[0].toUpperCase() + r.slice(1)}</button>)}
        </div>
        <span className="mini">{fp.format}{fp.scope === "major" ? " · leagues & full-member internationals" : ""} · {fmt(fp.balls)} {isBowl ? "legal balls bowled" : "balls faced"} · vs {fp.peer_pool.size} peers</span>
      </div>
      {fp.below_peer_threshold && <div className="note">This player is below the peer-pool sample threshold for {fp.format}. Percentiles are shown but carry more uncertainty.</div>}
      <div className="fp-grid">
        <svg viewBox={compact ? `-6 -6 ${S + 12} ${S + 12}` : `-78 -16 ${S + 156} ${S + 32}`} className={`fp-svg${compact ? " compact" : ""}`} role="img" aria-label="Cricket fingerprint">
          {[0.25, 0.5, 0.75, 1].map((f) => <circle key={f} cx={cx} cy={cy} r={r0 + (R - r0) * f} fill="none" stroke="#ffffff14" strokeDasharray={f === 0.5 ? "0" : "2 4"} />)}
          {dims.map((x, i) => {
            const col = GROUP_COLORS[x.group] || "#8d9ab8";
            const on = sel === x.key;
            return (
              <g key={x.key} onClick={() => setSel(x.key)} style={{ cursor: "pointer" }} role="button" aria-label={`${x.label}: ${x.percentile ?? "insufficient sample"}`}>
                <path d={arc(i, 1)} fill="#ffffff04" stroke="none" />
                {x.enough_sample && x.percentile != null
                  ? <path d={arc(i, Math.max(0.03, x.percentile / 100))} fill={col} opacity={on ? 1 : sel ? 0.45 : 0.85} className="petal" />
                  : <path d={arc(i, 0.5)} fill="none" stroke="#5d6a88" strokeDasharray="2 3" />}
                {on && <path d={arc(i, 1)} fill="none" stroke="#edf2fc" strokeWidth={1.5} />}
              </g>
            );
          })}
          {!compact && dims.map((x, i) => {
            const a = ((i + 0.5) / N) * 2 * Math.PI - Math.PI / 2;
            const rr = R + 14;
            const tx = cx + rr * Math.cos(a), ty = cy + rr * Math.sin(a);
            const lines = wrap(x.label);
            const on = sel === x.key;
            return <text key={x.key + "t"} x={tx} y={ty - (lines.length - 1) * 5} fontSize={12} fill={on ? "#edf2fc" : "#8d9ab8"} fontWeight={on ? 800 : 500}
                         textAnchor={Math.cos(a) > 0.2 ? "start" : Math.cos(a) < -0.2 ? "end" : "middle"} dominantBaseline="middle"
                         onClick={() => setSel(x.key)} style={{ cursor: "pointer" }}>
              {lines.map((l, j) => <tspan key={j} x={tx} dy={j ? 10.5 : 0}>{l}</tspan>)}</text>;
          })}
          <circle cx={cx} cy={cy} r={r0 - 4} fill="#0b1324" stroke="#233154" />
          <text x={cx} y={cy - 4} textAnchor="middle" fontSize={20} fontWeight={900} fill="#edf2fc" style={{ fontFamily: "var(--display)" }}>
            {d?.percentile != null ? ordinal(d.percentile) : "–"}</text>
          <text x={cx} y={cy + 12} textAnchor="middle" fontSize={14} fill="#8d9ab8">percentile</text>
        </svg>
        {d && (
          <div className="fp-detail fade-in" key={d.key}>
            <div className="kicker" style={{ color: GROUP_COLORS[d.group] }}>{d.group}</div>
            <div className="h2" style={{ fontSize: 24 }}>{d.label}</div>
            <div className="fp-value num">{d.value != null ? fmt(d.value, d.unit === "runs/over" ? 2 : 1) : "–"} <span className="mini">{d.unit}</span></div>
            {d.enough_sample ? (
              <div className="sub">
                {d.percentile != null && <>Higher than <b>{Math.round(d.percentile)}%</b> of peers. </>}Peer median {fmt(d.peer_median, d.unit === "runs/over" ? 2 : 1)}.
                <div className="mini" style={{ marginTop: 4 }}>A percentile describes style, not quality: for dot-ball rate or dismissal frequency, lower is usually better.</div>
              </div>
            ) : <div className="note">Not enough data: {d.n} {d.n_unit} (minimum {d.min_sample}). No percentile shown.</div>}
            {(() => {
              const kv = (<dl className="kv" style={{ marginTop: 10 }}>
                <dt>Definition</dt><dd>{d.description}</dd>
                <dt>Sample</dt><dd>{fmt(d.n)} {d.n_unit}{d.detail ? ` · most common: ${d.detail.replace(/_/g, " ").toLowerCase()}` : ""}</dd>
                <dt>Peers</dt><dd>{fp.peer_pool.definition} ({d.peer_n} with enough sample)</dd>
              </dl>);
              return compact ? <details className="why" style={{ marginTop: 8 }}><summary>WHY? Definition, sample and peers</summary>{kv}
                <div className="mini" style={{ marginTop: 6 }}>Solid ring = peer median; outer ring = 100th percentile. Dashed outline = not enough sample.</div>
                <div className="mini" style={{ marginTop: 6 }}>Not measured (the data doesn&apos;t record it): {fp.not_available.join(" · ")}.</div></details> : kv;
            })()}
            <button className="btn primary" style={{ marginTop: 12 }} onClick={() => onDrill(`${d.label}: the deliveries`, { [isBowl ? "bowler_id" : "batter_id"]: pid, ...d.evidence })}>
              See the deliveries →
            </button>
          </div>
        )}
      </div>
      {compact && (
        <div className="fp-chips" role="list" aria-label="Traits, most distinctive first">
          {dims.filter((x) => x.enough_sample && x.percentile != null && x.group !== "Concentration").sort((a, b) => Math.abs(b.percentile - 50) - Math.abs(a.percentile - 50)).slice(0, 8).map((x) => (
            <button key={x.key} role="listitem" className={`fp-chip ${sel === x.key ? "on" : ""}`} onClick={() => setSel(x.key)}
              style={{ borderColor: (GROUP_COLORS[x.group] || "#8d9ab8") + "88" }}>
              <span>{x.label}</span><b className="num">{ordinal(x.percentile)}</b></button>))}
        </div>
      )}
      {!compact && <div className="mini" style={{ marginTop: 6 }}>Solid ring = peer median (50th percentile); outer ring = 100th. Dashed outline = not enough sample, no percentile shown.</div>}
      <a className="btn" style={{ display: "inline-block", marginTop: 10 }} href={`/share?type=fingerprint&pid=${pid}&role=${role}`}>Share fingerprint card</a>
      {!compact && <div className="mini" style={{ marginTop: 8 }}>Not in this fingerprint (the data doesn&apos;t support it): {fp.not_available.join(" · ")}.</div>}
    </div>
  );
}

/** Split a label into at most two balanced lines so petal labels fit at phone width. */
function wrap(label: string): string[] {
  if (label.length <= 12) return [label];
  const w = label.split(" ");
  let best = [label], score = Infinity;
  for (let i = 1; i < w.length; i++) {
    const a = w.slice(0, i).join(" "), b = w.slice(i).join(" ");
    const sc = Math.max(a.length, b.length);
    if (sc < score) { score = sc; best = [a, b]; }
  }
  return best;
}
