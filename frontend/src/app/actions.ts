"use server";

import { revalidatePath } from "next/cache";

const API_BASE =
  process.env.SERVER_API_BASE_URL ?? "http://localhost:8000/api/v1";

export interface DeviceWrite {
  reference: number | null;
  serial: string;
  location: string;
  purchase: number | null;
  to_who: string;
  notes: string;
  status: string;
}

export interface BulkDeviceWrite {
  purchase: number | null;
  reference: number | null;
  location: string;
  notes: string;
  status: string;
  quantity: number;
}

export interface PurchaseWrite {
  kind: "device" | "parts";
  label: string;
  source: string;
  order_ref: string;
  url: string;
  total_price: string | null;
  purchased_on: string | null;
  arrived_on: string | null;
  from_who: string;
  expected_units: number | null;
  note: string;
}

export type WriteResult = { ok: true } | { ok: false; error: string };

// Both run on the Next server, so writes to the backend never touch browser CORS.

export async function updateDevice(
  id: number,
  data: DeviceWrite,
): Promise<WriteResult> {
  return send(`${API_BASE}/inventory/${id}/`, "PATCH", data, "/");
}

export async function createDevice(data: DeviceWrite): Promise<WriteResult> {
  return send(`${API_BASE}/inventory/`, "POST", data, "/");
}

export async function bulkCreateDevices(data: BulkDeviceWrite): Promise<WriteResult> {
  return send(`${API_BASE}/inventory/bulk/`, "POST", data, ["/purchases", "/"]);
}

// Purchases render on two tabs (device lots / parts orders) AND inside
// inventory rows — refresh all three.
export async function createPurchase(data: PurchaseWrite): Promise<WriteResult> {
  return send(`${API_BASE}/purchases/`, "POST", data, ["/purchases", "/parts", "/"]);
}

export async function updatePurchase(
  id: number,
  data: PurchaseWrite,
): Promise<WriteResult> {
  return send(`${API_BASE}/purchases/${id}/`, "PATCH", data, ["/purchases", "/parts", "/"]);
}

async function send(
  url: string,
  method: "PATCH" | "POST",
  data: unknown,
  revalidate: string | string[],
): Promise<WriteResult> {
  let res: Response;
  try {
    res = await fetch(url, {
      method,
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    });
  } catch (e) {
    return { ok: false, error: e instanceof Error ? e.message : "Network error" };
  }

  if (!res.ok) {
    const body = await res.text();
    return { ok: false, error: `${res.status}: ${body.slice(0, 300)}` };
  }

  for (const path of Array.isArray(revalidate) ? revalidate : [revalidate]) {
    revalidatePath(path);
  }
  return { ok: true };
}

// Partial phase-track / notes update; keys match RepairWriteSerializer.
export type RepairWrite = Partial<Record<string, string | null>>;

export async function createRepair(deviceId: number): Promise<WriteResult> {
  return send(`${API_BASE}/repairs/`, "POST", { device: deviceId }, `/devices/${deviceId}`);
}

export async function updateRepair(
  deviceId: number,
  repairId: number,
  data: RepairWrite,
): Promise<WriteResult> {
  return send(`${API_BASE}/repairs/${repairId}/`, "PATCH", data, `/devices/${deviceId}`);
}

export interface NoteWrite {
  repair: number;
  position: number;
  title: string;
  text: string;
  comment: string;
}

export async function createNote(
  deviceId: number,
  data: NoteWrite,
): Promise<WriteResult> {
  return send(`${API_BASE}/notes/`, "POST", data, `/devices/${deviceId}`);
}

export async function updateNote(
  deviceId: number,
  noteId: number,
  data: Omit<NoteWrite, "repair">,
): Promise<WriteResult> {
  return send(`${API_BASE}/notes/${noteId}/`, "PATCH", data, `/devices/${deviceId}`);
}

export interface MeasurementWrite {
  what: string;
  value: string;
  comment: string;
}

export async function createMeasurement(
  deviceId: number,
  noteId: number,
  data: MeasurementWrite,
): Promise<WriteResult> {
  return send(
    `${API_BASE}/measurements/`,
    "POST",
    { note: noteId, ...data },
    `/devices/${deviceId}`,
  );
}

export async function updateMeasurement(
  deviceId: number,
  measurementId: number,
  data: MeasurementWrite,
): Promise<WriteResult> {
  return send(
    `${API_BASE}/measurements/${measurementId}/`,
    "PATCH",
    data,
    `/devices/${deviceId}`,
  );
}
