"use server";

import { revalidatePath } from "next/cache";

const API_BASE =
  process.env.SERVER_API_BASE_URL ?? "http://localhost:8000/api/v1";

export interface DeviceWrite {
  reference: number | null;
  revision: number | null;
  serial: string;
  location: string;
  purchase: number | null;
  notes: string;
  status: string;
  cost_override: string | null;
}

// One homogeneous slice of a lot: N units of one catalog model.
export interface BulkLine {
  reference: number | null;
  quantity: number;
}

export interface BulkDeviceWrite {
  purchase: number | null;
  location: string;
  notes: string;
  status: string;
  lines: BulkLine[];
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

// Purchases render on two tabs (device lots / parts orders), their own detail
// pages, AND inside inventory rows — refresh all of them.
export async function createPurchase(data: PurchaseWrite): Promise<WriteResult> {
  return send(`${API_BASE}/purchases/`, "POST", data, ["/purchases", "/parts", "/"]);
}

export async function updatePurchase(
  id: number,
  data: PurchaseWrite,
): Promise<WriteResult> {
  return send(`${API_BASE}/purchases/${id}/`, "PATCH", data, [
    "/purchases",
    `/purchases/${id}`,
    "/parts",
    "/",
  ]);
}

// The lot landed: stamp arrived_on (default today) and flip its shipped units
// to acquired in one stroke — the ledger's on-arrival rule.
export async function markArrived(
  id: number,
  date: string | null,
): Promise<WriteResult> {
  return send(`${API_BASE}/purchases/${id}/arrive/`, "POST", date ? { date } : {}, [
    "/purchases",
    `/purchases/${id}`,
    "/",
  ]);
}

export interface ExitWrite {
  kind: string;
  happened_on: string | null;
  sale_price: string | null;
  fees: string | null;
  to_who: string;
  note: string;
}

// Recording an exit also flips the device to exited (backend rule), so the
// device page, inventory, and cash strip all change.
export async function createExit(
  deviceId: number,
  data: ExitWrite,
): Promise<WriteResult> {
  return send(`${API_BASE}/exits/`, "POST", { device: deviceId, ...data }, [
    `/devices/${deviceId}`,
    "/purchases",
    "/",
  ]);
}

export async function updateExit(
  deviceId: number,
  exitId: number,
  data: ExitWrite,
): Promise<WriteResult> {
  return send(`${API_BASE}/exits/${exitId}/`, "PATCH", data, [
    `/devices/${deviceId}`,
    "/purchases",
    "/",
  ]);
}

export interface StockItemWrite {
  name: string;
  category: string;
  note: string;
  mode: "counted" | "presence";
  state: "in_stock" | "low" | "out";
  fits_references: number[];
  fits_revisions: number[];
}

export async function createStockItem(data: StockItemWrite): Promise<WriteResult> {
  return send(`${API_BASE}/stock/`, "POST", data, "/stock");
}

export async function updateStockItem(
  id: number,
  data: StockItemWrite,
): Promise<WriteResult> {
  return send(`${API_BASE}/stock/${id}/`, "PATCH", data, "/stock");
}

// The physical recount: new base + server-side counted_at stamp. The count is
// never written directly — it moves via intakes, draws, and this.
export async function recountStockItem(
  id: number,
  count: number,
): Promise<WriteResult> {
  return send(`${API_BASE}/stock/${id}/recount/`, "POST", { count }, "/stock");
}

export interface StockIntakeWrite {
  purchase: number;
  stock_item: number;
  quantity: number;
  note: string;
}

export async function createStockIntake(
  data: StockIntakeWrite,
): Promise<WriteResult> {
  return send(`${API_BASE}/stock/intakes/`, "POST", data, "/stock");
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

// Photo upload: forwards the browser's files to the backend as one multipart
// POST per file (Media = one image per row). GPS-strip + EXIF taken_at happen
// backend-side. `formData` carries `files` entries from the note's file input.
export async function uploadNoteMedia(
  deviceId: number,
  noteId: number,
  formData: FormData,
): Promise<WriteResult> {
  const files = formData.getAll("files") as File[];
  if (files.length === 0) return { ok: false, error: "No files selected." };

  for (const file of files) {
    const body = new FormData();
    body.append("note", String(noteId));
    body.append("image", file);
    let res: Response;
    try {
      res = await fetch(`${API_BASE}/media/`, { method: "POST", body });
    } catch (e) {
      return { ok: false, error: e instanceof Error ? e.message : "Network error" };
    }
    if (!res.ok) {
      const text = await res.text();
      return { ok: false, error: `${file.name}: ${res.status}: ${text.slice(0, 300)}` };
    }
  }

  revalidatePath(`/devices/${deviceId}`);
  return { ok: true };
}
