"use client";
// Ask Cricket v1. QUESTION → PARSED INTENT → VALIDATED QUERY → DATABASE RESULT → RESPONSE.
// A deterministic parser builds the intent; the shared analytics engines compute every number. No language model writes numbers.
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";
import { api, apiPost, fmt } from "@/lib/api";
import ProvBadge from "@/components/Prov";
import Deliveries from "@/components/Deliveries";
import ExploreNext from "@/components/ExploreNext";

const EXAMPLES = ["Who dismisses Kohli most?", "Who has Kohli scored fastest against?", "What changes after Kohli faces 30 balls?",
  "Who are the best death-over bowlers since 2020?", "Which players are most similar to Rohit?", "What is Bumrah's best spell?",
  "Compare Kohli and Rohit in chases", "Show India's biggest successful T20 chases", "Which Kohli-Zampa dismissals happened in death overs?",
  "Show Kohli's best covered innings while chasing", "What happened in India v Pakistan in Melbourne in 2022?", "Who partners Mandhana best?",
  "Show Bumrah's best death-over spells", "Which bowlers have troubled Kohli most?", "Compare Kohli before and after 2020", "Who improved their strike rate most after 30 balls?",
  "Show me unusual India-Australia battles", "How does Kohli score after facing 30 balls?", "Who is best while chasing 10+ an over?", "Which bowler has dismissed Rohit most?",
  "How does Bumrah perform in overs 17-20?", "Who has the highest boundary rate after 30 balls?", "Which partnerships score fastest in the death overs?",
  "Show Kohli's dismissals between balls 20 and 30", "Who improves most from middle overs to death overs?", "Most sixes in death overs", "Bumrah v Warner"];

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
  const linkHref = (l: any) => !l ? null : l.kind === "compare" ? `/compare?ids=${l.ids.join(",")}` : l.kind === "record" ? `/records/${l.id}` : l.kind === "how_out" ? `/how-out/${l.id}` : l.kind === "battle" ? `/battle?bat=${l.bat}&bowl=${l.bowl}` : l.kind === "player" ? `/players/${l.id}${l.route ? `?tab=dismissals&route=${l.route}` : l.tab ? `?tab=${l.tab}` : ""}`
    : l.kind === "match" ? `/match/${l.id}` : l.kind === "rivalry" ? `/rivalry?a=${encodeURIComponent(l.a)}&b=${encodeURIComponent(l.b)}&gender=${l.gender}`
    : l.kind === "partnerships" ? `/partnerships?sort=${l.sort}${l.phase ? `&phase=${l.phase}` : ""}${l.format ? `&format=${l.format}` : ""}`
    : l.kind === "records" ? `/records?${new URLSearchParams({ metric: l.metric, ...Object.fromEntries(Object.entries(l.filters || {}).map(([k, v]) => [k, String(v)])) })}` : null;
  const ambiguous = (res?.notes || []).filter((n: any) => n.ambiguous);
  const assumed = (res?.notes || []).filter((n: any) => n.assumed);

  return (
    <div className="search-hero fade-in" style={{ maxWidth: 780, marginTop: 26 }}>
      <div className="kicker">Ask Cricket · v3</div>
      <h1 className="big-title" style={{ fontSize: "clamp(34px, 8vw, 58px)" }}>Ask cricket.</h1>
      <div className="sub">Who dismisses whom, who scores fastest against whom, best spells, chases, comparisons. You&apos;ll see exactly how your question was read. <details className="why" style={{ display: "inline-block", marginTop: 4 }}><summary>WHY trust it?</summary>Your question becomes a structured query you can see and edit; the numbers come from the same engines as the rest of the app. No language model writes them. To find a player or match by name, use <Link href="/search" className="ul">Search</Link>.</details></div>
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
              <div className="ans" data-testid="ask-answer">{res.answer}</div>
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
              {(res.pairs || []).map((g: any) => (
                <div key={g.gender} style={{ marginTop: 14 }}>
                  <div className="sit-title">{g.gender === "female" ? "Women" : "Men"} · {g.thresholds}</div>
                  <div className="rec-list">
                    {g.rows.slice(0, 5).map((r: any) => (
                      <Link key={r.p1 + r.p2} className="rec-row" href={`/partnerships?p1=${r.p1}&p2=${r.p2}`}>
                        <span className="rec-rank">{r.rank}</span>
                        <span style={{ minWidth: 0 }}><b style={{ display: "block" }}>{r.p1_name} & {r.p2_name}</b><span className="mini">{r.innings} stands · {r.runs} runs off {r.balls}</span></span>
                        <span className="rec-val num">{r[g.sort]}</span>
                      </Link>
                    ))}
                  </div>
                </div>
              ))}
              {(res.changes || []).map((g: any) => (
                <div key={g.gender} style={{ marginTop: 14 }}>
                  <div className="sit-title">{g.gender === "female" ? "Women" : "Men"} · typical change {g.typical_change > 0 ? "+" : ""}{g.typical_change}</div>
                  <div className="rec-list">
                    {g.rows.slice(0, 5).map((r: any) => (
                      <Link key={r.person_id} className="rec-row" href={`/players/${r.person_id}?tab=states`}>
                        <span className="rec-rank">{r.rank}</span>
                        <span style={{ minWidth: 0 }}><b style={{ display: "block" }}>{r.name}</b><span className="mini">{res.change_labels?.[0] ?? "middle"} {r.middle_sr} ({r.middle_balls} balls) → {res.change_labels?.[1] ?? "death"} {r.death_sr} ({r.death_balls})</span></span>
                        <span className="rec-val num">+{r.change}</span>
                      </Link>
                    ))}
                  </div>
                </div>
              ))}
              {res.items?.length > 0 && (
                <div className="tablist" style={{ marginTop: 12 }}>{res.items.map((it: any, i: number) => (
                  <Link key={i} className="trow" href={it.href}><span className="n">{i + 1}</span>
                    <span className="t"><b>{it.label}</b>{it.sub && <span className="mini">{it.sub}</span>}</span><span className="v num" style={{ fontSize: 15 }}>{it.value}</span></Link>))}</div>
              )}
              {res.story && <Link className="btn" style={{ display: "inline-block", marginTop: 10 }} href={res.story}>How the match unfolded (story) →</Link>}
              {res.deliveries_query && <Deliveries title="The dismissals" query={res.deliveries_query} onClose={() => {}} />}
              <dl className="kv" style={{ marginTop: 14, fontSize: 12.5 }}>
                {res.definition && <><dt>Definition</dt><dd>{res.definition}</dd></>}
                {res.caveat && <><dt>Caveat</dt><dd style={{ fontWeight: 500 }}>{res.caveat}</dd></>}
              </dl>
              {linkHref(res.link) && <Link className="btn primary" style={{ display: "inline-block", marginTop: 12 }} href={linkHref(res.link)!}>
                {res.link.kind === "compare" ? "Open the full comparison →" : res.link.kind === "record" ? "Open the record →" : res.link.kind === "records" ? "Open in Records explorer →" : res.link.kind === "battle" ? "Open the battle →" : res.link.kind === "partnerships" ? "Open Partnerships →"
                  : res.link.kind === "match" ? "Open the match →" : res.link.kind === "rivalry" ? "Open the rivalry →" : res.link.kind === "how_out" ? "Explore every dismissal →" : "Open the evidence →"}</Link>}
            </div>
          )}
          {res.status === "ok" && (() => {
            const l = res.link || {}, sub = res.intent?.subject, opp = res.intent?.opponent;
            const t = l.kind === "battle" ? ["battle", `${l.bat}|${l.bowl}`] : l.kind === "match" ? ["match", l.id]
              : sub && opp && res.intent.kind !== "compare_players" ? ["battle", `${sub.person_id}|${opp.person_id}`] : sub ? ["player", sub.person_id] : null;
            return t ? <ExploreNext type={t[0]} id={t[1]} title="Keep exploring" /> : null;
          })()}
          <div className="chips" style={{ marginTop: 16 }}>{EXAMPLES.filter((e) => e !== res.question).slice(0, 4).map((e) => <button key={e} className="chip wrap" onClick={() => go(e)}>{e}</button>)}</div>
        </div>
      )}
      {res?.status === "error" && <div className="empty" style={{ marginTop: 14 }}>Something went wrong running that query.</div>}
    </div>
  );
}
