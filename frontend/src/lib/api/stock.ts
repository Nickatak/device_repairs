// Stock — minted SKU buckets (counted vs presence tiers) and intake events.

import { API_BASE } from "./client";

export interface StockIntake {
  id: number;
  order: number;
  order_label: string;
  quantity: number;
  note: string;
  created_at: string;
}

export interface FitsLink {
  id: number;
  name: string;
}

export interface StockItem {
  id: number;
  name: string;
  category: string;
  note: string;
  mode: "counted" | "presence";
  mode_display: string;
  state: "in_stock" | "low" | "out";
  state_display: string;
  last_count: number | null;
  counted_at: string | null;
  // Derived live number: last recount + intakes − draws. Null for presence
  // items and for counted items that have never had a recount.
  count: number | null;
  fits_references: FitsLink[];
  fits_revisions: FitsLink[];
  intakes: StockIntake[];
  draw_count: number;
}

export const STOCK_STATES = [
  { value: "in_stock", label: "In stock" },
  { value: "low", label: "Low" },
  { value: "out", label: "Out" },
] as const;

export async function getStock(): Promise<StockItem[]> {
  const res = await fetch(`${API_BASE}/stock/`, { cache: "no-store" });
  if (!res.ok) {
    throw new Error(`Stock fetch failed: ${res.status} ${res.statusText}`);
  }
  return res.json();
}
