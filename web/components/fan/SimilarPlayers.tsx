"use client";
// Similar Players: nearest neighbours on fingerprint dimensions (style, not quality), with why and a holdout validation.
import Link from "next/link";
import { useEffect, useState } from "react";
import { api, ordinal } from "@/lib/api";
import { WhyBox } from "./bits";

export default function SimilarPlayers({ pid, name }: { pid: string; name: string }) {
  const [d, setD] = useState<any | null>(null);
  useEffect(() => { api(`/fan/player/${pid}/similar`).then((r) => setD(r.data)).catch(() => setD({ available: false, reason: "unavailable" })); }, [pid]);
  if (!d) return <div className="loading">Finding similar players…</div>;
  if (!d.available) return <div className="empty">No similar players shown: {d.reason}.</div>;
  const v = d.validation;
  return (
    <div data-testid="similar-players">
      <div className="mini" style={{ marginBottom: 6 }}>
        {d.format} {d.role}, against {d.pool_size} peers. {d.note}{" "}
        <WhyBox why={{ method: d.method, holdout_self_match_top5: `${Math.round(v.self_top5 * 100)}% (chance ${(v.chance_top5 * 100).toFixed(1)}%)`,
          neighbour_overlap: `${Math.round(v.neighbour_overlap_top5 * 100)}% (chance ${(v.chance_overlap * 100).toFixed(1)}%)`, players_tested: v.players, verdict: v.status }} />
      </div>
      <div className="simrows">
        {d.rows.map((r: any) => (
          <div key={r.pid} className="simrow">
            <Link href={`/players/${r.pid}`} className="sn"><b>{r.name}</b>
              <span className="mini">Alike: {r.alike.map((a: any) => `${a.label.toLowerCase()} (${ordinal(a.a_pct)} v ${ordinal(a.b_pct)})`).join(" · ")}</span>
              {r.differ?.[0] && <span className="mini">Differ most: {r.differ[0].label.toLowerCase()} ({ordinal(r.differ[0].a_pct)} v {ordinal(r.differ[0].b_pct)})</span>}
            </Link>
            <Link className="btn sm" href={`/compare?ids=${pid},${r.pid}`} aria-label={`Compare ${name} with ${r.name}`}>Compare</Link>
          </div>
        ))}
      </div>
    </div>
  );
}
