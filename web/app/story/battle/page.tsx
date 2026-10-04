"use client";
import { useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";
import { api } from "@/lib/api";
import StoryView from "@/components/StoryView";
import ExploreNext from "@/components/ExploreNext";

export default function Page() { return <Suspense fallback={<div className="loading">Loading…</div>}><B /></Suspense>; }
function B() {
  const sp = useSearchParams();
  const bat = sp.get("bat") || "", bowl = sp.get("bowl") || "";
  const [s, setS] = useState<any | null>(null);
  const [err, setErr] = useState(false);
  useEffect(() => { api("/story/battle", { bat, bowl }).then((r) => setS(r.data)).catch(() => setErr(true)); }, [bat, bowl]);
  if (err) return <div className="empty" style={{ marginTop: 30 }}>These players haven&apos;t met in covered data.</div>;
  if (!s) return <div className="loading">Assembling the story…</div>;
  return <div className="fade-in"><StoryView s={s} share={`/share?type=battle&bat=${bat}&bowl=${bowl}`} /><ExploreNext type="battle" id={`${bat}|${bowl}`} /></div>;
}
