"use client";
// Small shared pieces for the Phase 7 fan surfaces.
import Link from "next/link";
import { ReactNode, useState } from "react";

/** Progressive disclosure: the method, sample and caveats live behind WHY. */
export function WhyBox({ why, label = "WHY?" }: { why?: Record<string, any> | string | null; label?: string }) {
  const [open, setOpen] = useState(false);
  if (!why) return null;
  return (
    <span className="whybox">
      <button className="why-btn" onClick={(e) => { e.preventDefault(); e.stopPropagation(); setOpen(!open); }} aria-expanded={open}>{label}</button>
      {open && (
        <div className="why-box" onClick={(e) => e.stopPropagation()}>
          {typeof why === "string" ? why : Object.entries(why).filter(([, v]) => v !== null && v !== undefined && v !== "").map(([k, v]) => (
            <div key={k} className="why-kv"><span>{k.replace(/_/g, " ")}</span><b>{typeof v === "object" ? JSON.stringify(v) : String(v)}</b></div>
          ))}
        </div>
      )}
    </span>
  );
}

export function SectionHead({ kicker, title, sub, right, id }: { kicker: string; title: string; sub?: ReactNode; right?: ReactNode; id?: string }) {
  return (
    <div className="section-head" id={id}>
      <div><div className="kicker">{kicker}</div><h2 className="h2">{title}</h2>{sub && <div className="sub">{sub}</div>}</div>
      {right}
    </div>
  );
}

/** A spoiler-safe "what happened next?" card. Only the pre-ball state is shown; the replay reveals the ball after the call. */
export function PlayCard({ m, context }: { m: any; context?: string }) {
  if (!m) return null;
  return (
    <Link href={m.href} className="playcard" data-testid="play-moment">
      <span className="pk">Play · what happened next?</span>
      <span className="pt">{m.title}</span>
      {context && <span className="mini">{context}</span>}
      <span className="pc">Make your call → <span className="mini">nothing after this ball is shown until you pick</span></span>
    </Link>
  );
}

export const SAMPLE_LABEL: Record<string, string> = { rivalry: "rivalry", meeting: "", "small sample": "small sample" };
