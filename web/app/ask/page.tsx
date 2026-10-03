"use client";
// Ask Cricket v1. QUESTION → PARSED INTENT → VALIDATED QUERY → DATABASE RESULT → RESPONSE.
// A deterministic parser builds the intent; the shared analytics engines compute every number. No language model writes numbers.
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";
import { api, apiPost, fmt } from "@/lib/api";
import ProvBadge from "@/components/Prov";

const EXAMPLES = ["Who has dismissed Virat Kohli most?", "Most sixes in death overs", "Kohli strike rate chasing in ODIs", "How many times has MS Dhoni been stumped?",
  "Mandhana average in T20Is", "Bumrah v Warner", "Lowest economy in death overs since 2020", "Most times run out"];

export default function Page() { return <Suspense fallback={<div className="loading">Loading…</div>}><Ask /></Suspense>; }

function Ask() {
  const sp = useSearchParams();
  const router = useRouter();
  const [q, setQ] = useState(sp.get("q") || "");
  const [res, setRes] = useState<any | null>(null);
  const [busy, setBusy] = useState(false);
  const [showPipe, setShowPipe] = useState(false);
  const run = async (text: string) => {
    setBusy(true);
    try { setRes((await api("/ask/v1", { q: text })).data); } catch { setRes({ status: "error" }); } finally { setBusy(false); }
  };
  useEffect(() => { const x = sp.get("q"); if (x) { setQ(x); run(x); } }, [sp]);
  const go = (text: string) => { setQ(text); router.replace(`/ask?q=${encodeURIComponent(text)}`, { scroll: false }); };
  const removeChip = async (key: string) => {
    const it = JSON.parse(JSON.stringify(res.intent));
    if (key.startsWith("filters.")) delete it.filters[key.slice(8)]; else it[key] = null;
    setBusy(true);
    try { setRes({ ...(await apiPost("/ask/v1/run", it)).data, question: res.question, edited: true }); } finally { setBusy(false); }
  };
  const pickCandidate = (amb: string, name: string) => go((res.question as string).replace(amb.trim(), name));
  const lbs = res ? (res.leaderboards || (res.leaderboard ? [res.leaderboard] : [])) : [];
  const linkHref = (l: any) => !l ? null : l.kind === "battle" ? `/battle?bat=${l.bat}&bowl=${l.bowl}` : l.kind === "player" ? `/players/${l.id}${l.route ? `?tab=dismissals&route=${l.route}` : ""}`
    : l.kind === "records" ? `/records?${new URLSearchParams({ metric: l.metric, ...Object.fromEntries(Object.entries(l.filters || {}).map(([k, v]) => [k, String(v)])) })}` : null;
  const ambiguous = (res?.notes || []).filter((n: any) => n.ambiguous);
  const assumed = (res?.notes || []).filter((n: any) => n.assumed);

  return (
    <div className="search-hero fade-in" style={{ maxWidth: 780, marginTop: 26 }}>
      <div className="kicker">Ask Cricket · v1</div>
      <h1 className="big-title" style={{ fontSize: "clamp(34px, 8vw, 58px)" }}>Ask. Every number is a query.</h1>
      <p className="sub">Your question is turned into a structured query you can see and edit. The numbers come from the same engines as the rest of the app. No language model writes them.</p>
      <form onSubmit={(e) => { e.preventDefault(); if (q.trim()) go(q.trim()); }} style={{ display: "flex", gap: 8, marginTop: 16 }}>
        <input className="input" value={q} onChange={(e) => setQ(e.target.value)} placeholder="e.g. Who has dismissed Kohli most?" aria-label="Ask a question" />
        <button className="btn primary" type="submit" disabled={busy}>{busy ? "…" : "Ask"}</button>
      </form>
      {!res && <div className="chips" style={{ marginTop: 12 }}>{EXAMPLES.map((e) => <button key={e} className="chip wrap" onClick={() => go(e)}>{e}</button>)}</div>}

      {res && res.status !== "error" && (
        <div className="fade-in" style={{ marginTop: 18, opacity: busy ? 0.5 : 1 }}>
          <div className="card interp">
            <div className="sit-title">How I interpreted your question</div>
            <div className="chips" style={{ marginTop: 8 }}>
              {res.interpretation.map((c: any) => (
                <span key={c.key} className="ichip">{c.label}{c.removable && <button aria-label={`Remove ${c.label}`} title="Remove this condition and re-run" onClick={() => removeChip(c.key)}>×</button>}</span>
              ))}
            </div>
            {assumed.map((n: any, i: number) => <div key={i} className="mini" style={{ marginTop: 6 }}>Assumed: {n.assumed}</div>)}
            {res.edited && <div className="mini" style={{ marginTop: 6 }}>Edited: re-ran the validated query without the removed condition.</div>}
            <button className="btn" style={{ marginTop: 10, fontSize: 12 }} onClick={() => setShowPipe(!showPipe)} aria-expanded={showPipe}>{showPipe ? "Hide the pipeline" : "Show the pipeline"}</button>
            {showPipe && (
              <ol className="pipe fade-in">
                <li><b>Question</b><span>{res.question}</span></li>
                <li><b>Parsed intent</b><code>{JSON.stringify({ kind: res.intent.kind, subject: res.intent.subject?.name, opponent: res.intent.opponent?.name, metric: res.intent.metric, dismissal: res.intent.dismissal, gender: res.intent.gender })}</code></li>
                <li><b>Validated query</b><code>{JSON.stringify(res.intent.filters)}</code><span className="mini">Filter keys are checked against a fixed grammar; unknown keys are rejected.</span></li>
                <li><b>Database result</b><span>{lbs.length ? lbs.map((l: any) => `${l.rows.length} ranked rows (${l.gender === "female" ? "women" : "men"})`).join(", ") : `${(res.numbers || []).length} values`}</span></li>
                <li><b>Response</b><span>{res.generated_by}</span></li>
              </ol>
            )}
          </div>

          {res.status === "needs_clarification" && (
            <div className="card" style={{ marginTop: 12, borderColor: "var(--amber)" }}>
              <div style={{ fontWeight: 700 }}>{res.message}</div>
              {ambiguous.map((a: any, i: number) => (
                <div key={i} style={{ marginTop: 10 }}>
                  <div className="mini">Which “{a.ambiguous.trim()}” did you mean?</div>
                  <div className="chips" style={{ marginTop: 6 }}>
                    {a.candidates.map((c: any) => <button key={c.person_id} className="chip" onClick={() => pickCandidate(a.ambiguous, c.name)}>{c.name} <span className="mini">{c.matches ? `${c.matches} m` : ""}</span></button>)}
                  </div>
                </div>
              ))}
              <div className="chips" style={{ marginTop: 12 }}>{EXAMPLES.slice(0, 4).map((e) => <button key={e} className="chip wrap" onClick={() => go(e)}>{e}</button>)}</div>
            </div>
          )}

          {res.status === "ok" && (
            <div className="card answer" style={{ marginTop: 12 }}>
              <div className="kicker">In our covered data <ProvBadge prov="OBSERVED" /></div>
              <div className="ans">{res.answer}</div>
              {res.numbers?.length > 0 && (
                <div className="statstrip" style={{ gridTemplateColumns: `repeat(${Math.min(4, res.numbers.length)}, minmax(0, 1fr))` }}>
                  {res.numbers.map((n: any, i: number) => {
                    const h = linkHref(n.link);
                    const body = <><b className="num">{typeof n.value === "number" ? fmt(n.value) : n.value}</b><span className="mini">{n.label}{n.n ? ` · ${fmt(n.n)} balls` : ""}</span></>;
                    return h ? <Link key={i} href={h} className="num-link">{body}</Link> : <div key={i}>{body}</div>;
                  })}
                </div>
              )}
              {lbs.map((l: any) => (
                <div key={l.gender + l.metric} style={{ marginTop: 14 }}>
                  <div className="sit-title">{l.gender === "female" ? "Women" : "Men"} · {l.label} · {l.order}{l.min_sample ? ` · min ${l.min_sample} ${l.sample_unit}` : ""}</div>
                  <div className="rec-list">
                    {l.rows.slice(0, 5).map((r: any) => (
                      <Link key={r.ids.join("|")} className="rec-row" href={l.entity === "pair" ? `/battle?bat=${r.ids[0]}&bowl=${r.ids[1]}` : `/players/${r.ids[0]}`}>
                        <span className="rec-rank">{r.rank}</span>
                        <span style={{ minWidth: 0 }}><b style={{ display: "block" }}>{r.names.join(" v ")}</b><span className="mini">{fmt(r.sample)} {l.sample_unit} · {r.matches} matches</span></span>
                        <span className="rec-val num">{r.value_fmt}</span>
                      </Link>
                    ))}
                  </div>
                </div>
              ))}
              <dl className="kv" style={{ marginTop: 14, fontSize: 12.5 }}>
                {res.definition && <><dt>Definition</dt><dd>{res.definition}</dd></>}
                {res.caveat && <><dt>Caveat</dt><dd style={{ fontWeight: 500 }}>{res.caveat}</dd></>}
              </dl>
              {linkHref(res.link) && <Link className="btn primary" style={{ display: "inline-block", marginTop: 12 }} href={linkHref(res.link)!}>
                {res.link.kind === "records" ? "Open in Records explorer →" : res.link.kind === "battle" ? "Open the battle →" : "Open the evidence →"}</Link>}
            </div>
          )}
          <div className="chips" style={{ marginTop: 16 }}>{EXAMPLES.filter((e) => e !== res.question).slice(0, 4).map((e) => <button key={e} className="chip wrap" onClick={() => go(e)}>{e}</button>)}</div>
        </div>
      )}
      {res?.status === "error" && <div className="empty" style={{ marginTop: 14 }}>Something went wrong running that query.</div>}
    </div>
  );
}
