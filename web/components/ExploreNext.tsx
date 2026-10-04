"use client";
// Rabbit-Hole engine UI: the most interesting next destinations from the entity on screen, ranked by the deterministic
// engine (/api/fan/next) and pushed away from anything already opened in this browser session (local memory only).
import Link from "next/link";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { markShown, remember, seenIds, shownIds } from "@/lib/memory";

const KIND_ICON: Record<string, string> = { innings: "▮", spell: "◎", battle: "⚔", partnership: "∞", competition: "🏆", match: "▣", story: "¶",
  delivery: "•", player: "●", rivalry: "⇄", record: "≡", finding: "✦", moment: "▶", team: "⚑" };
const REL_LABEL: Record<string, string> = { dismissed_by: "Nemesis", victim: "Victim", dominated: "Dominated", punished_by: "Took them apart",
  best_innings: "Big innings", best_spell: "Best spell", finding: "Finding", record: "Record", similar: "Similar player", partner: "Partner",
  play: "Play", compare: "Compare", how_out: "Dismissals", story: "Story", match: "Match", top_innings: "Top innings", top_spell: "Top spell",
  big_stand: "Big stand", player: "Player", dismissal: "Wicket", biggest_meeting: "Big meeting", similar_battle: "Similar battle",
  other_rival: "Another battle", rivalry: "Rivalry", competition: "Competition", next_match: "Next match", latest_match: "Latest match",
  replay: "Replay", edition: "Edition", faced_most: "Battle", teammate: "Team-mate", related_record: "Record", records: "Records" };

export default function ExploreNext({ type, id, title = "Explore next" }: { type: string; id: string; title?: string }) {
  const [d, setD] = useState<any | null>(null);
  const [why, setWhy] = useState(false);
  useEffect(() => {
    setD(null);
    api("/fan/next", { type, key: id, seen: seenIds().join(","), shown: shownIds().join(","), k: 7 })
      .then((r) => {
        const here = window.location.pathname + window.location.search;
        const items = r.data.items.filter((x: any) => x.href !== here).slice(0, 6);
        setD({ ...r.data, items });
        markShown(items.map((x: any) => x.id));
      })
      .catch(() => setD({ items: [] }));
  }, [type, id]);
  if (d && !d.items.length) return null;
  return (
    <section className="xnext" aria-label={title} data-testid="explore-next">
      <div className="xnext-head">
        <span className="eyebrow">{title}</span>
        <button className="why-btn" onClick={() => setWhy(!why)} aria-expanded={why}>WHY these?</button>
      </div>
      {why && d?.method && <div className="mini why-box">{d.method}</div>}
      {!d ? <div className="loading">…</div> : (
        <div className="xnext-list">
          {d.items.map((r: any) => (
            <Link key={r.id} href={r.href} className="xnext-row" data-rel={r.relation} data-type={r.type}
              onClick={() => remember({ id: r.id, type: r.type, label: r.label, href: r.href })}>
              <span className={`sicon ${r.type}`}>{KIND_ICON[r.type] ?? "→"}</span>
              <span className="sl"><span className="rel">{REL_LABEL[r.relation] ?? r.relation}</span><b>{r.label}</b><span className="mini">{r.reason}</span></span>
              <span className="sgo">→</span>
            </Link>
          ))}
        </div>
      )}
    </section>
  );
}
