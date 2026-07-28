// Note templates — the (model × phase) prefill layer. List fetch for the
// authoring page; writes go through actions.

import { API_BASE } from "./client";
import type { NoteTemplate } from "./repairlog";

export async function getTemplates(): Promise<NoteTemplate[]> {
  const res = await fetch(`${API_BASE}/templates/`, { cache: "no-store" });
  if (!res.ok) {
    throw new Error(`Templates fetch failed: ${res.status} ${res.statusText}`);
  }
  return res.json();
}
