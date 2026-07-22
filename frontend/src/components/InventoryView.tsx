"use client";

import { useState } from "react";
import Link from "next/link";
import type { InventoryItem, Options, Purchase } from "@/lib/api";
import { bandClass, formatDate, formatPrice } from "@/lib/format";
import DeviceModal from "./DeviceModal";
import { purchaseLabel } from "./DeviceForm";
import { Pagination, usePagination } from "./Pagination";
import { SortTh, applySort, useSort } from "./sorting";

// Compact handle for a buy event: ledger id ("0004") first, then order ref.
export function purchaseShort(p: Purchase): string {
  const ref = p.ledger_ref || p.order_ref;
  return [ref, p.source].filter(Boolean).join(" · ") || `#${p.id}`;
}

export function purchaseHref(p: Purchase): string {
  const key = p.ledger_ref || p.order_ref;
  return key ? `/purchases?q=${encodeURIComponent(key)}` : "/purchases";
}

function StatusBadge({ item }: { item: InventoryItem }) {
  return (
    <>
      <span className={`badge ${bandClass(item.status)}`}>
        {item.status_display}
      </span>
    </>
  );
}

type ModalState = { mode: "create" } | { mode: "edit"; item: InventoryItem } | null;

type SortKey = "ref" | "device" | "purchase" | "acquired" | "arrived";

function sortValue(item: InventoryItem, key: SortKey): string | number | null {
  switch (key) {
    case "ref":
      return item.ledger_ref || null;
    case "device":
      return item.label;
    case "purchase":
      return item.purchase ? purchaseShort(item.purchase) : null;
    case "acquired":
      return item.purchase?.unit_price != null
        ? Number(item.purchase.unit_price)
        : null;
    case "arrived":
      return item.purchase?.arrived_on ?? null;
  }
}

function matches(item: InventoryItem, query: string): boolean {
  if (!query) return true;
  const haystack = [
    item.label,
    item.ledger_ref,
    item.serial,
    item.location ?? "",
    item.notes,
    item.status,
    item.status_display,
    item.purchase?.ledger_ref ?? "",
    item.purchase?.order_ref ?? "",
    item.purchase?.source ?? "",
    item.to_who,
  ]
    .join(" ")
    .toLowerCase();
  // Every whitespace-separated term must appear (AND search).
  return query
    .toLowerCase()
    .split(/\s+/)
    .every((term) => haystack.includes(term));
}

export default function InventoryView({
  items,
  options,
  error,
  initialQuery = "",
}: {
  items: InventoryItem[];
  options: Options;
  error: string | null;
  initialQuery?: string;
}) {
  const [modal, setModal] = useState<ModalState>(null);
  // Deep-linkable: /?q=0004 lands with the search prefilled.
  const [query, setQuery] = useState(initialQuery);
  const [statusFilter, setStatusFilter] = useState<string | null>(null);
  const { sort, toggle } = useSort<SortKey>();

  // Status chips in lifecycle order, only for statuses actually present.
  const presentStatuses = options.statuses.filter((s) =>
    items.some((it) => it.status === s.value),
  );

  const visible = items.filter(
    (it) =>
      matches(it, query) && (statusFilter === null || it.status === statusFilter),
  );
  const filtered = visible.length !== items.length;
  applySort(visible, sort, sortValue);
  const pager = usePagination(visible);

  // Sum PURCHASES, not rows: a 4-unit lot's $20 counts once, not four times.
  const purchaseTotals = new Map<number, number>();
  for (const it of visible) {
    if (it.purchase?.total_price != null) {
      purchaseTotals.set(it.purchase.id, Number(it.purchase.total_price));
    }
  }
  const totalSpent = [...purchaseTotals.values()].reduce((a, b) => a + b, 0);

  return (
    <main>
      <header className="page-head">
        <div>
          <h1>Inventory</h1>
          <p className="subtitle">
            {filtered
              ? `${visible.length} of ${items.length} devices`
              : `${items.length} device${items.length === 1 ? "" : "s"} on the bench`}
          </p>
        </div>
        <button className="btn-primary" onClick={() => setModal({ mode: "create" })}>
          + Add device
        </button>
      </header>

      <div className="ref-controls">
        <input
          className="ref-search"
          placeholder="Search model, serial, location, purchase, notes…"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
        />
        <div className="ref-filters">
          <button
            className={`ref-chip${statusFilter === null ? " active" : ""}`}
            onClick={() => setStatusFilter(null)}
          >
            All
          </button>
          {presentStatuses.map((s) => (
            <button
              key={s.value}
              className={`ref-chip${statusFilter === s.value ? " active" : ""}`}
              onClick={() =>
                setStatusFilter(statusFilter === s.value ? null : s.value)
              }
            >
              {s.label}
            </button>
          ))}
        </div>
      </div>

      {error ? (
        <p className="error">Could not load inventory: {error}</p>
      ) : items.length === 0 ? (
        <p className="empty">No devices yet — add your first.</p>
      ) : visible.length === 0 ? (
        <p className="empty">No devices match.</p>
      ) : (
        <table>
          <thead>
            <tr>
              <SortTh label="ID" k="ref" sort={sort} onToggle={toggle} />
              <SortTh label="Device" k="device" sort={sort} onToggle={toggle} />
              <th>Location</th>
              <SortTh label="Purchase" k="purchase" sort={sort} onToggle={toggle} />
              <SortTh label="Acquired" k="acquired" sort={sort} onToggle={toggle} className="num" />
              <SortTh label="Arrived" k="arrived" sort={sort} onToggle={toggle} />
              <th>Status</th>
              <th aria-label="actions"></th>
            </tr>
          </thead>
          <tbody>
            {pager.paged.map((item) => (
              <tr key={item.id} className="row-link">
                {/* Unit's ledger id; site-created rows fall back to the DB id. */}
                <td>{item.ledger_ref || `#${item.id}`}</td>
                <td className="device">
                  <Link href={`/devices/${item.id}`} className="row-link-anchor">
                    {item.label}
                  </Link>
                </td>
                <td>{item.location ?? "—"}</td>
                <td>
                  {item.purchase ? (
                    <Link
                      href={purchaseHref(item.purchase)}
                      className="cell-link"
                      title={purchaseLabel(item.purchase)}
                    >
                      {purchaseShort(item.purchase)}
                    </Link>
                  ) : (
                    "—"
                  )}
                </td>
                <td className="num" title={item.purchase ? `lot: ${formatPrice(item.purchase.total_price)}` : undefined}>
                  {formatPrice(item.purchase?.unit_price ?? null)}
                </td>
                <td>
                  {item.purchase?.arrived_on
                    ? formatDate(item.purchase.arrived_on)
                    : "—"}
                </td>
                <td>
                  <StatusBadge item={item} />
                </td>
                <td className="num">
                  <button
                    className="btn-edit"
                    onClick={() => setModal({ mode: "edit", item })}
                  >
                    Edit
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
          <tfoot>
            <tr className="total-row">
              <td colSpan={4}>{filtered ? "Total (filtered)" : "Total spent"}</td>
              <td className="num">${totalSpent.toFixed(2)}</td>
              <td colSpan={3}></td>
            </tr>
          </tfoot>
        </table>
      )}
      <Pagination {...pager} />

      {modal && (
        <DeviceModal
          item={modal.mode === "edit" ? modal.item : null}
          options={options}
          onClose={() => setModal(null)}
        />
      )}
    </main>
  );
}
