// CRICINTEL Visual Cricket Engine v1: the visual model.
// Renderers draw VizElements; they never invent geometry. Every element carries provenance in the model itself,
// so a user can tap any element and see what it is, where it came from and what is NOT known.
//
//   OBSERVED       directly in the source data (who bowled, runs, the dismissal kind, the fielder credited)
//   DERIVED        deterministic calculation from observed data (score after the ball, keeper inferred from history)
//   RECONSTRUCTED  arrangement inferred from reliable event information
//   MODELLED       statistical estimate (model probabilities, Situation Difficulty)
//   ILLUSTRATIVE   generic cricket graphic used to explain (pitch geometry, standard figure slots). NOT the real event
//   UNKNOWN        not in the data: drawn as a hatched zone or listed, never as a point or path

export type Prov = "OBSERVED" | "DERIVED" | "RECONSTRUCTED" | "MODELLED" | "ILLUSTRATIVE" | "UNKNOWN";

export const PROV_MEANING: Record<Prov, string> = {
  OBSERVED: "Directly recorded in the source data.",
  DERIVED: "Calculated deterministically from recorded data.",
  RECONSTRUCTED: "Arrangement inferred from reliable event information.",
  MODELLED: "A statistical estimate, not a fact.",
  ILLUSTRATIVE: "A generic cricket graphic to aid understanding. Not a reconstruction of this delivery.",
  UNKNOWN: "Not recorded in the data. Shown as unknown, never guessed.",
};

export interface VizElement {
  id: string;
  kind: "pitch" | "stumps" | "crease" | "figure" | "event" | "outcome" | "score" | "zone" | "fact" | "connector";
  role?: "bowler" | "striker" | "non_striker" | "keeper" | "fielder";
  prov: Prov;
  label: string;
  detail?: string;   // what it means / caveat
  source?: string;   // e.g. "Cricsheet match 1298150, delivery 17.6"
  emphasis?: boolean;
}

export interface DeliveryModel {
  elements: VizElement[];
  chain: VizElement[];          // the event chain drawn beside (not across) the pitch
  dismissal?: { kind: string; route?: string; theatre: string; involved: string[] };
  unknowns: string[];
}

type Replay = any;

const src = (r: Replay) => `Cricsheet match ${r.match_id}, innings ${r.innings_no}, ball ${r.over_ball}`;

/** Law-based explanation of what each dismissal kind means: what the data tells us, and what it does not. */
export const THEATRE: Record<string, { text: string; involved: string[] }> = {
  bowled: { text: "Bowled: the delivery broke the striker's wicket. The data records that it happened, not where the ball pitched or what it hit first.", involved: ["bowler", "striker", "stumps_striker"] },
  lbw: { text: "LBW: the umpire (or review) judged the ball would have hit the stumps after striking the batter. Impact point and projected path are not recorded.", involved: ["bowler", "striker"] },
  stumped: { text: "Stumped: the keeper broke the wicket with the batter out of their ground, off a legal delivery that wasn't a no-ball.", involved: ["bowler", "striker", "keeper", "stumps_striker"] },
  "run out": { text: "Run out: a fielder broke the wicket while a batter was out of their ground. Which end, and where the throw came from, are not recorded.", involved: ["fielder", "striker", "non_striker"] },
  "caught and bowled": { text: "Caught and bowled: the bowler took the catch. Where, and off which part of the bat, is not recorded.", involved: ["bowler", "striker"] },
  caught: { text: "Caught: a fielder took the catch. The data names the fielder but not where they were standing or how the ball came off the bat.", involved: ["bowler", "striker", "fielder"] },
  caught_keeper: { text: "Caught by wicketkeeper: the credited fielder was keeping wicket. Whether the ball was edged is not recorded.", involved: ["bowler", "striker", "keeper"] },
  "hit wicket": { text: "Hit wicket: the batter broke their own wicket while playing the ball or setting off for a run.", involved: ["striker", "stumps_striker"] },
};

export function deliveryModel(r: Replay): DeliveryModel {
  const w = (r.wicket_detail || [])[0];
  const keeperKnown = !!w?.keeper_id;
  const isKeeperCatch = w?.route === "CAUGHT_KEEPER";
  const E: VizElement[] = [
    { id: "pitch", kind: "pitch", prov: "ILLUSTRATIVE", label: "Pitch", detail: "Standard pitch geometry. Not this ground's measurements." },
    { id: "stumps_bowler", kind: "stumps", prov: "ILLUSTRATIVE", label: "Stumps (bowler's end)" },
    { id: "stumps_striker", kind: "stumps", prov: w && ["bowled", "stumped", "hit wicket"].includes(w.kind) ? "OBSERVED" : "ILLUSTRATIVE",
      label: w && ["bowled", "stumped", "hit wicket"].includes(w.kind) ? "Wicket broken" : "Stumps (striker's end)",
      detail: w && ["bowled", "stumped", "hit wicket"].includes(w.kind) ? `The dismissal kind (${w.kind}) means the striker's wicket was broken.` : undefined,
      emphasis: !!w && ["bowled", "stumped", "hit wicket"].includes(w.kind) },
    { id: "bowler", kind: "figure", role: "bowler", prov: "OBSERVED", label: r.bowler.name, detail: "Bowler identity is recorded. Figure position is a standard slot (illustrative); run-up and release are not recorded.", source: src(r) },
    { id: "striker", kind: "figure", role: "striker", prov: "OBSERVED", label: r.batter.name,
      detail: `Striker identity is recorded. ${r.batter.hand ? `${r.batter.hand}-handed.` : "Batting hand unknown, so the figure is neutral."} Stance and movement are not recorded.`, source: src(r) },
    { id: "non_striker", kind: "figure", role: "non_striker", prov: "OBSERVED", label: r.non_striker.name, detail: "Non-striker identity is recorded. Position is a standard slot.", source: src(r) },
    { id: "keeper", kind: "figure", role: "keeper", prov: keeperKnown ? "DERIVED" : "UNKNOWN",
      label: keeperKnown ? `Keeper${isKeeperCatch && w?.fielder ? `: ${w.fielder}` : ""}` : "Keeper (identity not established)",
      detail: keeperKnown ? `Keeper identity is inferred from career keeping records (confidence ${w.keeper_conf ?? "–"}).` : "The data does not say who kept wicket on this ball." },
  ];
  const chain: VizElement[] = [
    { id: "c_bowler", kind: "event", role: "bowler", prov: "OBSERVED", label: r.bowler.name, detail: "Bowled this delivery." },
    { id: "c_ball", kind: "event", prov: "OBSERVED", label: `Ball ${r.over_ball}`, detail: r.legal ? "Legal delivery." : "Not a legal delivery (wide or no-ball).", source: src(r) },
    { id: "c_outcome", kind: "outcome", prov: "OBSERVED", emphasis: true,
      label: w ? `OUT · ${w.kind}` : r.runs.wides ? `${r.runs.total} wide${r.runs.total > 1 ? "s" : ""}` : r.runs.six ? "SIX" : r.runs.four ? "FOUR" : r.runs.total === 0 ? "No run" : `${r.runs.total} run${r.runs.total > 1 ? "s" : ""}`,
      detail: `Batter ${r.runs.batter}, extras ${r.runs.extras}${r.runs.byes ? ` (byes ${r.runs.byes})` : ""}${r.runs.legbyes ? ` (leg-byes ${r.runs.legbyes})` : ""}${r.runs.noballs ? " (no-ball)" : ""}.` },
  ];
  if (w) {
    const stumping = w.kind === "stumped";
    const credited = w.route === "CAUGHT_KEEPER" || stumping ? "keeper" : w.kind === "caught and bowled" ? "bowler" : w.fielder ? "fielder" : null;
    if (credited)
      chain.push({ id: "c_credit", kind: "event", role: credited as any, prov: w.route === "CAUGHT_KEEPER" ? "DERIVED" : "OBSERVED",
        label: credited === "bowler" ? `Caught by ${r.bowler.name}` : stumping ? `Stumped by keeper ${w.fielder}` : `${w.route === "CAUGHT_KEEPER" ? "Keeper" : "Fielder"}: ${w.fielder}${w.substitute ? " (sub)" : ""}`,
        detail: w.route === "CAUGHT_KEEPER" ? "Fielder named in the data; that they were keeping is inferred (DERIVED)."
          : stumping ? "Only the wicketkeeper can make a stumping (Laws of Cricket), so the named fielder was keeping." : "Fielder named in the data. Their position is not recorded." });
    chain.push({ id: "c_out", kind: "event", role: w.striker_out ? "striker" : "non_striker", prov: "OBSERVED", label: `${w.player_out} out`, detail: `${w.striker_out ? "Striker" : "Non-striker"} dismissed.` });
  }
  chain.push({ id: "c_score", kind: "score", prov: "DERIVED", label: `${r.score_before} → ${r.score_after}`, detail: "Team score before and after, summed from recorded runs and wickets." });
  const key = w ? (w.route === "CAUGHT_KEEPER" ? "caught_keeper" : w.kind) : null;
  const th = key ? THEATRE[key] : undefined;
  if (w && th) {
    for (const e of E) if (th.involved.includes(e.id === "keeper" ? "keeper" : e.id)) e.emphasis = true;
    if (w.kind === "caught" && !isKeeperCatch)
      E.push({ id: "fielder_zone", kind: "zone", role: "fielder", prov: "UNKNOWN", emphasis: true, label: `${w.fielder ?? "Fielder"}: position not recorded`,
        detail: "Catches are recorded with the fielder's name only. Drawn as a ring, not a point." });
    if (w.kind === "run out")
      E.push({ id: "runout_zone", kind: "zone", prov: "UNKNOWN", emphasis: true, label: "Run-out end not recorded", detail: "The data says who was run out, not at which end." });
  }
  return { elements: E, chain, dismissal: w && th ? { kind: w.kind, route: w.route, theatre: th.text, involved: th.involved } : undefined, unknowns: r.not_recorded || [] };
}

/** Outcome categories used across Outcome Maps and WHN. */
export const OUTCOMES = ["DOT", "1", "2", "3", "4", "6", "WICKET"] as const;
export const OUTCOME_COLOR: Record<string, string> = { DOT: "#5d6a88", "1": "#7cc4ff", "2": "#7cc4ff", "3": "#7cc4ff", "4": "#35e0c2", "6": "#9df26b", WICKET: "#ff5c74" };

/** Map a scorebook symbol ('•', '4', 'W', '1wd'…) to an outcome category, or null for extras-only balls. */
export function symbolToOutcome(s: string): string | null {
  if (s === "W") return "WICKET";
  if (s === "•") return "DOT";
  if (/wd|nb|lb|b$/.test(s)) return null;
  return ["1", "2", "3", "4", "6"].includes(s) ? s : s === "5" ? null : null;
}
