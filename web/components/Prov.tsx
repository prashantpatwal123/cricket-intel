import type { Prov } from "@/lib/api";

const LABEL: Record<string, string> = {
  OBSERVED: "Observed", DERIVED: "Derived", RECONSTRUCTED: "Reconstructed", MODELLED: "Model", ILLUSTRATIVE: "Illustration", UNKNOWN: "Unknown",
};
const HELP: Record<string, string> = {
  OBSERVED: "Stated directly by the source record.",
  DERIVED: "Computed or classified from observed data by a documented rule.",
  RECONSTRUCTED: "Approximate drawing from incomplete event data. Not ball-tracking.",
  MODELLED: "A statistical estimate, not a fact.",
  ILLUSTRATIVE: "Generic illustration of a concept.",
  UNKNOWN: "Not present in our data.",
};

export default function ProvBadge({ prov, title }: { prov?: Prov | string | null; title?: string }) {
  if (!prov) return null;
  const p = String(prov).toUpperCase();
  return <span className={`prov ${p}`} title={title || HELP[p]}>{LABEL[p] ?? p}</span>;
}
