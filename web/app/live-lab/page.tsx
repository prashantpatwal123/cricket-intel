"use client";
// Historical Live Lab: completed matches replayed ball by ball through the live event pipeline. Nothing here is live.
// The list deliberately shows no results, scores or "famous finish" descriptions: choosing a match must not spoil it.
import Link from "next/link";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";

export default function LiveLab() {
  const [d, setD] = useState<any | null>(null);
  useEffect(() => { api("/live/featured").then((r) => setD(r.data)).catch(() => setD({ matches: [] })); }, []);
  return (
    <div className="fade-in" style={{ marginTop: 18 }}>
      <div className="replay-flag" role="note">Historical replay — not live</div>
      <div className="eyebrow" style={{ marginTop: 18 }}>Historical Live Lab</div>
      <h1 className="display-xl" style={{ marginTop: 4 }}>Watch a finished match arrive ball by ball</h1>
      <p className="mini" style={{ fontSize: 14, maxWidth: 680 }}>
        Each replay feeds a completed Cricsheet match through the same event pipeline a live feed would use. At every ball the Match Centre knows only
        what had happened so far: the server never sends later deliveries, and every historical comparison uses only matches played before this one.
      </p>
      <div className="eyebrow" style={{ marginTop: 22 }}>Choose a match</div>
      {!d ? <div className="loading">Loading…</div> : (
        <div className="lab-list">
          {d.matches.map((m: any) => (
            <Link key={m.match_id} href={`/live-lab/${m.match_id}`} data-testid="lab-match">
              <b>{m.title}</b>
              <span className="mini">{m.competition}{m.stage ? ` · ${m.stage}` : ""} · {m.date} · {m.city || m.venue} · {m.tags.join(" · ")}</span>
              <span className="go">Replay →</span>
            </Link>
          ))}
        </div>
      )}
      <div className="rule-section">
        <div className="eyebrow">What this is, and is not</div>
        <ul className="mini" style={{ fontSize: 13, lineHeight: 1.6, paddingLeft: 18 }}>
          <li>Not live, and never presented as live. Every screen carries the replay label.</li>
          <li>No ball-tracking: line, length, shot direction and field positions are not in the data and are never drawn.</li>
          <li>Next-ball probabilities come from a model (MODELLED). For matches inside its training window they are in-sample, and say so.</li>
          <li>Play along: predict each ball before it is revealed (What Happens Next).</li>
        </ul>
        <Link className="btn" href="/data">How the replay works →</Link>
      </div>
    </div>
  );
}
