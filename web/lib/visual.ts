// Visual Cricket Engine V2 contracts (Phase 6). Mirrors pipeline/cricintel/enrich/provenance.py and analytics/visual.py.
// Every visual element may carry a Provenance; every component accepts partial data and renders a truthful sparse state.

export type ProvType = "OBSERVED" | "DERIVED" | "RECONSTRUCTED" | "MODELLED" | "ILLUSTRATIVE";

export interface Provenance {
  provenance_type: ProvType;
  source?: string; source_field?: string; source_event_id?: string; confidence?: number;
  method?: string; model_version?: string; retrieved_at?: string; licence?: string; subject_ids?: string[];
  why: string;                     // "Why am I seeing this?"
}

export type LayerCode = "L0" | "L1" | "L2" | "L3" | "L4" | "L5";

export interface Layer {
  layer: LayerCode; name: string; available: boolean; partial?: boolean;
  data?: any; provenance?: Provenance; why_missing?: string; unlock?: string; describes?: string; missing?: string[];
}

// Canonical coordinates (pitch map): origin at the batter's stumps, x across the pitch in metres (+ = OFF side for the batter,
// so a left-hander's off side is flipped), y down the pitch towards the bowler in metres (0 = batting crease line, 20.12 = bowler's stumps).
export interface BallGeom {
  line?: string; length?: string; pitch_x?: number; pitch_y?: number; speed_kph?: number;
  shot?: string; direction_deg?: number; runs?: number; wicket?: boolean; boundary?: 4 | 6 | null;
  provenance?: Provenance;
}

export const LINES: [string, string][] = [["wide_outside_off", "Wide outside off"], ["outside_off", "Outside off"], ["off_stump", "Off stump"],
  ["middle", "Middle"], ["leg_stump", "Leg stump"], ["down_leg", "Down leg"]];
export const LENGTHS: [string, string][] = [["full_toss", "Full toss"], ["yorker", "Yorker"], ["full", "Full"], ["good_length", "Good length"],
  ["back_of_length", "Back of a length"], ["short", "Short"], ["bouncer", "Bouncer"]];

/** Off side is +x for a right-hander; for a left-hander the same physical point is mirrored. Unknown hand: no transform claimed. */
export function toBatterFrame(x: number, hand: "right" | "left" | null | undefined): number | null {
  if (hand === "right") return x;
  if (hand === "left") return -x;
  return null;
}

export const ILLUSTRATIVE_NOTE = "ILLUSTRATIVE: a generic cricket example, not a real delivery, batter or bowler. CRICINTEL has no line, length, shot or tracking data.";
