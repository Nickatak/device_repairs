// Price-sheet catalog — reference rows, lanes, comp pulls.

import { API_BASE } from "./client";

// A visual/special variant of the base model — same model number, different
// shell and price band. Pricing arrives via variant-scoped comp pulls.
export interface Variant {
  id: number;
  name: string;
  note: string;
  position: number;
}

// A board/hardware revision — the compatibility axis (JDM-055, BDM-020).
// Variants change the shell; revisions change what parts fit.
export interface Revision {
  id: number;
  name: string;
  note: string;
  position: number;
}

export interface CompPull {
  id: number;
  variant: number | null;
  variant_name: string | null;
  kind: string;
  kind_display: string;
  median: string | null;
  p25: string | null;
  p75: string | null;
  n: number | null;
  window_days: number | null;
  velocity_per_day: string | null;
  verified: string;
  pulled_on: string;
  note: string;
}

// One row of the symptom-decomposition table: seller says <fault>, the cause
// column says what that decodes to, the verdict says buy/avoid/caution.
export interface Issue {
  id: number;
  category: string;
  fault: string;
  cause: string;
  verdict: "buy" | "avoid" | "caution";
  verdict_display: string;
  note: string;
  position: number;
}

export interface ReferenceItem {
  id: number;
  lane: string;
  brand: string;
  name: string;
  sku_prefix: string;
  memory_config: string;
  model_numbers: string;
  release_year: number | null;
  configurations: string;
  stop_price: string | null;
  stop_note: string;
  notes: string;
  comp_pulls: CompPull[];
  issues: Issue[];
  variants: Variant[];
  revisions: Revision[];
  stale: boolean;
  gap: boolean;
}

export async function getReference(): Promise<ReferenceItem[]> {
  const res = await fetch(`${API_BASE}/reference/`, { cache: "no-store" });
  if (!res.ok) {
    throw new Error(`Reference fetch failed: ${res.status} ${res.statusText}`);
  }
  return res.json();
}

export interface Lane {
  id: number;
  name: string;
  policy: string;
}

export async function getLanes(): Promise<Lane[]> {
  const res = await fetch(`${API_BASE}/lanes/`, { cache: "no-store" });
  if (!res.ok) {
    throw new Error(`Lanes fetch failed: ${res.status} ${res.statusText}`);
  }
  return res.json();
}
