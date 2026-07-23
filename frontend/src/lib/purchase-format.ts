// Purchase display helpers, shared across inventory rows, the device card,
// the purchase page, and the form comboboxes. (Moved out of InventoryView /
// DeviceForm 2026-07-22 when the purchase page landed.)

import type { Purchase } from "@/lib/api/purchases";

// Compact handle for a buy event: ledger id ("0004") first, then order ref.
export function purchaseShort(p: Purchase): string {
  const ref = p.ledger_ref || p.order_ref;
  return [ref, p.source].filter(Boolean).join(" · ") || `#${p.id}`;
}

// Every purchase now has a real page.
export function purchaseHref(p: Purchase): string {
  return `/purchases/${p.id}`;
}

export function purchaseLabel(p: Purchase): string {
  const parts = [p.label || p.source, p.label ? null : p.order_ref].filter(Boolean);
  if (p.total_price !== null) parts.push(`$${p.total_price}`);
  return parts.join(" ") || `purchase #${p.id}`;
}
