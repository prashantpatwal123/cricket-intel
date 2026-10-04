"use client";
// "Useful? 👍 / 👎" and "Something wrong with this stat?". Prototype: saved only in this browser (see lib/feedback.ts).
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { saveFeedback } from "@/lib/feedback";
import { track } from "@/lib/analytics";

let VERSION: string | null = null;

export default function Feedback({ entity, item, model }: { entity?: { type: string; id: string }; item?: string; model?: string }) {
  const [done, setDone] = useState<string | null>(null);
  const [wrong, setWrong] = useState(false);
  const [note, setNote] = useState("");
  useEffect(() => { if (!VERSION) api("/meta").then((r) => { VERSION = r.dataset?.built_at ?? null; }).catch(() => {}); }, []);
  const send = (kind: "useful" | "not_useful" | "stat_wrong") => {
    saveFeedback({ kind, page: window.location.pathname + window.location.search, entity: entity ?? null, item: item ?? null,
      note: kind === "stat_wrong" ? note.slice(0, 500) : null, data_version: VERSION, model_version: model ?? null });
    track("feedback", { kind, entity_type: entity?.type ?? null });
    setDone(kind); setWrong(false);
  };
  if (done) return <div className="fb done" role="status">Thanks. Saved in this browser only (private-beta prototype).</div>;
  return (
    <div className="fb" data-testid="feedback">
      <span className="mini">Useful?</span>
      <button className="fbb" aria-label="Useful" onClick={() => send("useful")}>👍</button>
      <button className="fbb" aria-label="Not useful" onClick={() => send("not_useful")}>👎</button>
      <button className="why-btn" aria-expanded={wrong} onClick={() => setWrong(!wrong)}>Something wrong with a stat?</button>
      {wrong && (
        <form className="fbw" onSubmit={(e) => { e.preventDefault(); send("stat_wrong"); }}>
          <label className="mini" htmlFor="fbnote">What looks wrong? (optional)</label>
          <textarea id="fbnote" className="input" rows={2} value={note} onChange={(e) => setNote(e.target.value)} maxLength={500} />
          <button className="btn sm" type="submit">Save report</button>
        </form>
      )}
    </div>
  );
}
