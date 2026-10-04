// Standard coverage language (Phase 8). Every user-facing statement about scope uses one of these phrases so a fan
// always reads the same words for the same limitation. Spec: docs/product/terminology-and-coverage.md
export const COVERAGE = {
  scope: "Within CRICINTEL's covered matches",            // sentence opener
  scopeShort: "In covered matches",                        // kicker / label
  notOfficial: "Covered matches only, not official totals.", // beside any career-style number
  notOfficialRecord: "Covered matches only, not official records.", // beside any record / ranking
  span: (from: string, to: string) => `${from}–${to} in covered matches`,
  none: (what: string) => `${what} in covered matches.`,  // e.g. none("Kohli hasn't faced Starc") → "... in covered matches."
  notRecorded: "Not recorded in the data",                 // field missing from every source (line, length, shot)
  replay: "Historical replay, not live",
} as const;
