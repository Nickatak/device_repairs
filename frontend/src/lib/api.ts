// API client for the Django backend. Fetches run server-side (Server Components),
// so we hit the in-cluster backend host and never touch browser CORS.

const API_BASE =
  process.env.SERVER_API_BASE_URL ?? "http://localhost:8000/api/v1";

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

export interface InventoryItem {
  id: number;
  label: string;
  ledger_ref: string;
  reference: number | null;
  serial: string;
  location: string | null;
  purchase: Purchase | null;
  to_who: string;
  notes: string;
  status: string;
  status_display: string;
  repair_count: number;
}

export async function getInventory(): Promise<InventoryItem[]> {
  const res = await fetch(`${API_BASE}/inventory/`, { cache: "no-store" });
  if (!res.ok) {
    throw new Error(`Inventory fetch failed: ${res.status} ${res.statusText}`);
  }
  return res.json();
}

export interface Measurement {
  id: number;
  what: string;
  value: string;
  comment: string;
}

export interface Note {
  id: number;
  position: number;
  title: string;
  text: string;
  comment: string;
  parent: number | null;
  measurements: Measurement[];
  subnotes: Note[];
}

// Mirrors Repair.PHASES on the backend — the fixed bench pipeline.
export const REPAIR_PHASES = [
  { key: "teardown", label: "Teardown" },
  { key: "wash", label: "Wash" },
  { key: "repair", label: "Repair" },
  { key: "reassemble", label: "Re-assemble" },
  { key: "verify", label: "Verify" },
] as const;

export type PhaseKey = (typeof REPAIR_PHASES)[number]["key"];

export type PhaseFields = {
  [K in PhaseKey as `${K}_done_at`]: string | null;
} & {
  [K in PhaseKey as `${K}_note`]: string;
};

export interface RepairWithNotes extends PhaseFields {
  id: number;
  current_phase: PhaseKey | "completion" | "complete";
  created_at: string;
  completed_at: string | null;
  comment: string;
  notes: Note[];
}

export interface DeviceDetail {
  id: number;
  label: string;
  ledger_ref: string;
  serial: string;
  location: string | null;
  purchase: Purchase | null;
  to_who: string;
  notes: string;
  status: string;
  status_display: string;
  reference: ReferenceItem | null;
  repairs: RepairWithNotes[];
}

export async function getDevice(id: number): Promise<DeviceDetail> {
  const res = await fetch(`${API_BASE}/inventory/${id}/`, { cache: "no-store" });
  if (!res.ok) {
    throw new Error(`Device fetch failed: ${res.status} ${res.statusText}`);
  }
  return res.json();
}

export interface StatusOption {
  value: string;
  label: string;
}

// Light catalog projection for the device form's reference combobox.
export interface ReferenceOption {
  id: number;
  brand: string;
  name: string;
  sku_prefix: string;
  model_numbers: string;
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
