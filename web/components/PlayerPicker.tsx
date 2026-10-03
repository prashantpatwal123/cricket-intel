"use client";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";

export default function PlayerPicker({ label, value, onPick, placeholder }: {
  label: string; value?: { person_id: string; name: string } | null; onPick: (p: { person_id: string; name: string } | null) => void; placeholder?: string;
}) {
  const [q, setQ] = useState("");
  const [res, setRes] = useState<any[]>([]);
  useEffect(() => {
    if (q.trim().length < 2) { setRes([]); return; }
    const t = setTimeout(() => api<any[]>("/players/search", { q, limit: 6 }).then((r) => setRes(r.data)), 140);
    return () => clearTimeout(t);
  }, [q]);
  return (
    <div className="picker">
      <div className="kicker" style={{ marginBottom: 6 }}>{label}</div>
      {value ? (
        <button className="picked" onClick={() => { onPick(null); setQ(""); }} title="Change player">
          <span>{value.name}</span><span className="mini">change</span>
        </button>
      ) : (
        <>
          <input className="input" value={q} onChange={(e) => setQ(e.target.value)} placeholder={placeholder || "Search a player…"} aria-label={label} />
          {res.length > 0 && (
            <div className="results">
              {res.map((p) => (
                <button key={p.person_id} className="res" style={{ border: 0, width: "100%", textAlign: "left" }} onClick={() => { onPick({ person_id: p.person_id, name: p.name }); setRes([]); }}>
                  <span>{p.name}</span><span className="mini">{(p.genders || [])[0] === "female" ? "W" : "M"} · {p.matches} matches · {(p.teams || []).slice(0, 2).join(", ")}</span>
                </button>
              ))}
            </div>
          )}
        </>
      )}
    </div>
  );
}
