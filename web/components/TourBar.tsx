"use client";
// One-line tour hint on the real page. Never blocks the page; ✕ ends the tour at any step.
import Link from "next/link";
import { usePathname, useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { STEPS, setTour, tourState } from "@/lib/tour";
import { track } from "@/lib/analytics";

export default function TourBar() {
  const path = usePathname();
  const sp = useSearchParams();
  const n = Number(sp.get("tour") || 0);
  const [hidden, setHidden] = useState(false);
  const [moment, setMoment] = useState<string | null>(null);
  const step = STEPS.find((s) => s.n === n && s.match(path));
  useEffect(() => { setHidden(tourState() === "dismissed"); }, [n]);
  useEffect(() => {
    if (step?.next?.href !== "moment") return;
    api("/fan/moment", { type: "innings", key: "1298150|2|ba607b88" }).then((r) => setMoment(r.data?.href ? `${r.data.href}&tour=5` : null)).catch(() => {});
  }, [step]);
  useEffect(() => { if (step?.n === 5) { setTour("done"); track("tour", { action: "complete" }); } }, [step]);
  if (!step || hidden) return null;
  const href = step.next?.href === "moment" ? moment : step.next?.href;
  return (
    <div className="tourbar" role="status" aria-live="polite" data-testid="tourbar">
      <span className="tn">{step.n}/5</span>
      <span className="tt">{step.text}</span>
      {step.next && href && <Link className="btn sm primary" href={href} data-testid="tour-next" onClick={() => track("tour", { action: "next", step: step.n })}>{step.next.label} →</Link>}
      {step.n === 5 && <Link className="btn sm" href="/">Done</Link>}
      <button className="tx" aria-label="End the tour" onClick={() => { setTour("dismissed"); setHidden(true); track("tour", { action: "dismiss", step: step.n }); }}>✕</button>
    </div>
  );
}
