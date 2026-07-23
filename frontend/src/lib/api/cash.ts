// Cash position — the reconcile.py readout, live again now that exits carry money.

import { API_BASE } from "./client";

export interface CashSummary {
  money_out: string;
  money_in: string;
  net: string;
  purchase_count: number;
  exit_count: number;
}

export async function getCash(): Promise<CashSummary> {
  const res = await fetch(`${API_BASE}/cash/`, { cache: "no-store" });
  if (!res.ok) {
    throw new Error(`Cash fetch failed: ${res.status} ${res.statusText}`);
  }
  return res.json();
}
