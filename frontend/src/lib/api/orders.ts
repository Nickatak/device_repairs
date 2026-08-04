// Orders — the buy events. Money and source live here, never on the device.

import { API_BASE } from "./client";

// An intake event — money and source live here, never on the device.
// kind="parts" rows are the loose parts ledger: ordered-at-some-point +
// has-it-arrived, no stock counts. Nothing hangs off them; label is identity.
// kind="job" rows are customer work orders: device-shaped (units hang off
// them) but the units are customer property and total_price is 0.
export interface Order {
  id: number;
  kind: "device" | "parts" | "job";
  label: string;
  source: string | null;
  order_ref: string;
  url: string;
  ledger_ref: string;
  total_price: string | null;
  ordered_on: string | null;
  arrived_on: string | null;
  from_who: string;
  expected_units: number | null;
  device_count: number;
  note: string;
  unit_price: string | null;
}

export async function getOrders(): Promise<Order[]> {
  const res = await fetch(`${API_BASE}/orders/`, { cache: "no-store" });
  if (!res.ok) {
    throw new Error(`Orders fetch failed: ${res.status} ${res.statusText}`);
  }
  return res.json();
}

// Slim device row on the order page's units table — no order echo.
export interface OrderUnit {
  id: number;
  label: string;
  ledger_ref: string;
  serial: string;
  status: string;
  status_display: string;
  location: string | null;
  repair_count: number;
  cost_override: string | null;
  unit_cost: string | null;
}

export interface OrderDetail extends Order {
  devices: OrderUnit[];
}

export async function getOrder(id: number): Promise<OrderDetail> {
  const res = await fetch(`${API_BASE}/orders/${id}/`, { cache: "no-store" });
  if (!res.ok) {
    throw new Error(`Order fetch failed: ${res.status} ${res.statusText}`);
  }
  return res.json();
}
