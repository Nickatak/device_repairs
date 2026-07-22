// Price-sheet catalog — reference rows, lanes, comp pulls.

import { API_BASE } from "./client";

export interface CompPull {
  id: number;
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
