// Glossary: the plain meaning first, the exact definition one tap away.
import Link from "next/link";
import { GLOSSARY } from "@/lib/glossary";

export const metadata = { title: "Glossary · CRICINTEL" };

export default function Glossary() {
  return (
    <div className="fade-in" style={{ maxWidth: 720, margin: "0 auto" }}>
      <div className="kicker">Glossary</div>
      <h1 className="h1" style={{ margin: "4px 0 6px" }}>What the words mean</h1>
      <p className="mini" style={{ marginBottom: 14 }}>Pages use the plain phrase. The exact definition is here and in each WHY box.</p>
      <dl className="glossary" data-testid="glossary">
        {GLOSSARY.map((g) => (
          <div key={g.term} id={g.term.toLowerCase().replace(/[^a-z]+/g, "-")}>
            <dt>{g.term}</dt><dd><b>{g.plain}</b> <span className="mini">{g.detail}</span></dd>
          </div>
        ))}
      </dl>
      <p className="mini" style={{ marginTop: 16 }}>Method detail lives in <Link className="ul" href="/data">Data &amp; methods</Link>.</p>
    </div>
  );
}
