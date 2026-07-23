// The cross-domain combobox aggregate — mirrors the backend's views/options.py.

import { API_BASE } from "./client";
import type { Purchase } from "./purchases";

export interface StatusOption {
  value: string;
  label: string;
}

// Light catalog projection for the device form's reference combobox.
// Revisions ride along so the form's revision picker filters to the reference.
export interface ReferenceOption {
  id: number;
  brand: string;
  name: string;
  sku_prefix: string;
  model_numbers: string;
  revisions: { id: number; name: string }[];
}

export interface Options {
  references: ReferenceOption[];
  locations: string[];
  sources: string[];
  people: string[];
  purchases: Purchase[];
  statuses: StatusOption[];
}

export async function getOptions(): Promise<Options> {
  const res = await fetch(`${API_BASE}/options/`, { cache: "no-store" });
  if (!res.ok) {
    throw new Error(`Options fetch failed: ${res.status} ${res.statusText}`);
  }
  return res.json();
}
