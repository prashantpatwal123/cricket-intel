"use client";
// Fetches a spoiler-safe Play moment for an innings, match or battle and shows it as a "what happened next?" card.
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { PlayCard } from "./bits";

export default function MomentCard({ type, k, context }: { type: string; k: string; context?: string }) {
  const [m, setM] = useState<any | null>(null);
  useEffect(() => { api("/fan/moment", { type, key: k }).then((r) => setM(r.data)).catch(() => setM(null)); }, [type, k]);
  return m ? <PlayCard m={m} context={context} /> : null;
}
