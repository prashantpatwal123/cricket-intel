"use client";
import Link from "next/link";

export default function Leader({ title, rows, value, sub, href, note }: { title: string; rows: any[]; value: (r: any) => any; sub?: (r: any) => string; href: (r: any) => string; note?: string }) {
  return (
    <div>
      <div className="eyebrow" style={{ marginTop: 14 }}>{title}</div>
      <div className="tablist">
        {rows.map((r, i) => (
          <Link key={i} className="trow" href={href(r)}><span className="n">{i + 1}</span>
            <span className="t"><b>{r.name ?? r.label}</b>{sub && <span className="mini">{sub(r)}</span>}</span><span className="v num">{value(r)}</span></Link>
        ))}
      </div>
      {note && <div className="mini" style={{ marginTop: 4 }}>{note}</div>}
    </div>
  );
}
