// Purchases — the buy events. Money and source live here, never on the device.

import { API_BASE } from "./client";

// A buy event — money and source live here, never on the device.
// kind="parts" rows are the loose parts ledger: ordered-at-some-point +
// has-it-arrived, no stock counts. Nothing hangs off them; label is identity.
export interface Purchase {
  id: number;
  kind: "device" | "parts";
  label: string;
  source: string | null;
  order_ref: string;
  url: string;
  ledger_ref: string;
  total_price: string | null;
  purchased_on: string | null;
  arrived_on: string | null;
  from_who: string;
  expected_units: number | null;
  device_count: number;
  note: string;
  unit_price: string | null;
}

export async function getPurchases(): Promise<Purchase[]> {
  const res = await fetch(`${API_BASE}/purchases/`, { cache: "no-store" });
  if (!res.ok) {
    throw new Error(`Purchases fetch failed: ${res.status} ${res.statusText}`);
  }
  return res.json();
}
