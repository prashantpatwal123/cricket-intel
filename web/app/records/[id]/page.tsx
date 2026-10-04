"use client";
// One record: definition, minimum sample, filters, coverage, and every row linked to its evidence.
import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import ExploreNext from "@/components/ExploreNext";
import { WhyBox } from "@/components/fan/bits";
import { useRemember } from "@/lib/memory";

export default function RecordPage() {
  const { id } = useParams<{ id: string }>();
  const rid = decodeURIComponent(id);
  const [d, setD] = useState<any | null>(null);
  useEffect(() => { setD(null); api(`/fan/records/${encodeURIComponent(rid)}`).then((r) => setD(r.data)).catch(() => setD({ error: true })); }, [rid]);
  useRemember("record", rid, d?.title ? `${d.title} · ${d.scope}` : null, `/records/${rid}`);
  if (!d) return <div className="loading">Opening the record…</div>;
  if (d.error) return <div className="empty" style={{ marginTop: 30 }}>Record not found. <Link href="/records">Back to the record book</Link></div>;
  return (
    <div className="fade-in" data-testid="record-page">
      <section className="section" style={{ marginTop: 20 }}>
        <Link href="/records" className="mini">← Record book · {d.category}</Link>
        <h1 className="h2" style={{ fontSize: "clamp(28px, 7vw, 44px)", marginTop: 6 }}>{d.title}</h1>
        <div className="mtabs" style={{ marginTop: 10 }}>
          {d.scopes.map((s: any) => <Link key={s.id} href={`/records/${s.id}`} className={`mtab ${s.id === rid ? "on" : ""}`}>{s.scope}</Link>)}
        </div>
        <div className="mini" style={{ marginTop: 10 }}>{d.definition}{d.min_sample ? ` Minimum: ${d.min_sample}.` : ""}{" "}
          <WhyBox why={{ definition: d.definition, minimum_sample: d.min_sample || "none", filters: d.filters.join(" · "), coverage: d.coverage, provenance: d.prov }} /> <Link className="why-btn" href={`/share?type=rec2&id=${encodeURIComponent(rid)}`}>Share card</Link></div>
      </section>
      <section className="section" data-testid="record-rows">
        {d.rows.map((r: any) => (
          <Link key={r.rank} href={r.href} className="mrow rec-row">
            <span className="mn"><b>{r.rank}. {r.label}</b><span className="mini">{r.detail}</span></span>
            <span className="mv num"><b>{r.value_fmt.split(" (")[0]}</b>{r.value_fmt.includes(" (") && <span className="mini">({r.value_fmt.split(" (")[1]}</span>}</span>
          </Link>
        ))}
      </section>
      {d.related?.length > 0 && <section className="section">
        <div className="eyebrow">More {d.category.toLowerCase()} records</div>
        <div className="scope-row">{d.related.map((x: any) => <Link key={x.id} href={`/records/${x.id}`} className="chip">{x.title}</Link>)}</div>
      </section>}
      <ExploreNext type="record" id={rid} />
    </div>
  );
}
