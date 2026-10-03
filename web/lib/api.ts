// Thin client for the cricintel API. All responses arrive in an envelope with dataset attribution.
export type Prov = "OBSERVED" | "DERIVED" | "RECONSTRUCTED" | "MODELLED" | "ILLUSTRATIVE" | "UNKNOWN";

export interface Dataset { name: string; synthetic: boolean; source_id: string; attribution: string; built_at: string }
export interface Envelope<T> { data: T; dataset: Dataset; ms: number }

export type Params = Record<string, string | number | boolean | null | undefined>;

export async function api<T = any>(path: string, params: Params = {}): Promise<Envelope<T>> {
  const qs = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) if (v !== undefined && v !== null && v !== "") qs.set(k, String(v));
  const res = await fetch(`/api${path}${qs.toString() ? "?" + qs : ""}`);
  if (!res.ok) throw new Error(`${res.status} ${await res.text()}`);
  return res.json();
}

export const fmt = (v: number | null | undefined, d = 0) =>
  v === null || v === undefined || Number.isNaN(v) ? "–" : Number(v).toLocaleString("en-GB", { minimumFractionDigits: d, maximumFractionDigits: d });

export const pct = (v: number | null | undefined) => (v === null || v === undefined ? "–" : `${fmt(v, 1)}%`);
