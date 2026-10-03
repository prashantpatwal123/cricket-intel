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

export async function apiPost<T = any>(path: string, body: unknown): Promise<Envelope<T>> {
  const res = await fetch(`/api${path}`, { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify(body) });
  if (!res.ok) throw new Error(`${res.status} ${await res.text()}`);
  return res.json();
}

export const ordinal = (n: number) => {
  const r = Math.round(n); const s = ["th", "st", "nd", "rd"]; const v = r % 100;
  return r + (s[(v - 20) % 10] || s[v] || s[0]);
};
