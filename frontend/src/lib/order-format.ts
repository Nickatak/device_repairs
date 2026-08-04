// Order display helpers, shared across inventory rows, the device card,
// the order page, and the form comboboxes. (Moved out of InventoryView /
// DeviceForm 2026-07-22 when the order page landed.)

import type { Order } from "@/lib/api/orders";

// Compact handle for a buy event: ledger id ("0004") first, then order ref.
export function orderShort(p: Order): string {
  const ref = p.ledger_ref || p.order_ref;
  return [ref, p.source].filter(Boolean).join(" · ") || `#${p.id}`;
}

// Every order now has a real page.
export function orderHref(p: Order): string {
  return `/orders/${p.id}`;
}

export function orderLabel(p: Order): string {
  const parts = [p.label || p.source, p.label ? null : p.order_ref].filter(Boolean);
  if (p.total_price !== null) parts.push(`$${p.total_price}`);
  return parts.join(" ") || `order #${p.id}`;
}
