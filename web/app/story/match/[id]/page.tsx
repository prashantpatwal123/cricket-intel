"use client";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import StoryView from "@/components/StoryView";
import ExploreNext from "@/components/ExploreNext";

export default function Page() {
  const { id } = useParams<{ id: string }>();
  const [s, setS] = useState<any | null>(null);
  const [err, setErr] = useState(false);
  useEffect(() => { api(`/story/match/${id}`).then((r) => setS(r.data)).catch(() => setErr(true)); }, [id]);
  if (err) return <div className="empty" style={{ marginTop: 30 }}>Story not available.</div>;
  if (!s) return <div className="loading">Assembling the story…</div>;
  return <div className="fade-in"><StoryView s={s} share={`/share?type=match&id=${id}`} /><ExploreNext type="match" id={id} /></div>;
}
