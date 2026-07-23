// Inventory — the device list and single-device detail payloads.

import { API_BASE } from "./client";
import type { Exit } from "./exits";
import type { Purchase } from "./purchases";
import type { ReferenceItem } from "./reference";
import type { RepairWithNotes } from "./repairlog";

export interface InventoryItem {
  id: number;
  label: string;
  ledger_ref: string;
  reference: number | null;
  serial: string;
  location: string | null;
  purchase: Purchase | null;
  notes: string;
  status: string;
  status_display: string;
  repair_count: number;
  cost_override: string | null;
  unit_cost: string | null;
}

export async function getInventory(): Promise<InventoryItem[]> {
  const res = await fetch(`${API_BASE}/inventory/`, { cache: "no-store" });
  if (!res.ok) {
    throw new Error(`Inventory fetch failed: ${res.status} ${res.statusText}`);
  }
  return res.json();
}

export interface DeviceDetail {
  id: number;
  label: string;
  ledger_ref: string;
  serial: string;
  location: string | null;
  purchase: Purchase | null;
  notes: string;
  status: string;
  status_display: string;
  reference: ReferenceItem | null;
  repairs: RepairWithNotes[];
  exits: Exit[];
  cost_override: string | null;
  unit_cost: string | null;
}

export async function getDevice(id: number): Promise<DeviceDetail> {
  const res = await fetch(`${API_BASE}/inventory/${id}/`, { cache: "no-store" });
  if (!res.ok) {
    throw new Error(`Device fetch failed: ${res.status} ${res.statusText}`);
  }
  return res.json();
}
