"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import type { CashSummary } from "@/lib/api/cash";
import type { Options } from "@/lib/api/options";
import type { Purchase } from "@/lib/api/purchases";
import { formatDate, formatPrice } from "@/lib/format";
import PurchaseModal from "./PurchaseModal";
import BulkAddModal from "@/components/inventory/BulkAddModal";
import { Pagination, usePagination } from "@/components/ui/Pagination";
import { SortTh, applySort, useSort } from "@/components/ui/sorting";

type ModalState =
  | { mode: "create" }
  | { mode: "edit"; item: Purchase }
  | { mode: "bulk"; item: Purchase }
  | null;

function matches(p: Purchase, query: string): boolean {
  if (!query) return true;
  const haystack = [
    p.kind,
    p.label,
    p.source ?? "",
    p.order_ref,
    p.url,
    p.ledger_ref,
    p.from_who,
    p.note,
    p.total_price ?? "",
    p.purchased_on ?? "",
    p.arrived_on ?? "",
  ]
    .join(" ")
    .toLowerCase();
  // Every whitespace-separated term must appear (AND search).
  return query
    .toLowerCase()
    .split(/\s+/)
    .every((term) => haystack.includes(term));
}

// Entered device rows disagree with the lot's expected count — under (4/5)
// or over (6/5). The reconcile-audit signal. Device lots only: parts
// purchases never hold device rows, so 0-of-N is their normal state.
function mismatched(p: Purchase): boolean {
  return (
    p.kind === "device" &&
    p.expected_units !== null &&
    p.device_count !== p.expected_units
  );
}

// Display handle for order-less rows: the listing id off the URL's tail
// ("…/itm/168422045256" → "168422045256").
function refFromUrl(url: string): string {
  const tail = url.split("/").filter(Boolean).pop() ?? "";
  return tail.includes("=") ? (tail.split("=").pop() ?? "") : tail;
}

type SortKey = "source" | "units" | "purchased" | "arrived";

function sortValue(p: Purchase, key: SortKey): string | number | null {
  switch (key) {
    case "source":
      return p.source;
    case "units":
      return p.expected_units ?? p.device_count;
    case "purchased":
      return p.purchased_on;
    case "arrived":
      return p.arrived_on;
  }
}

// One component, two tabs: /purchases renders kind="device" (lots that split
// into device rows), /parts renders kind="parts" (the loose parts ledger).
// Signed money display for the net line: -$75.50, not $-75.50.
function signedPrice(value: string): string {
  const n = Number(value);
  return `${n < 0 ? "−" : ""}$${Math.abs(n).toFixed(2)}`;
}

export default function PurchasesView({
  purchases: allPurchases,
  options,
  error,
  initialQuery = "",
  kind = "device",
  cash = null,
  title = null,
  tabs = null,
}: {
  purchases: Purchase[];
  options: Options;
  error: string | null;
  initialQuery?: string;
  kind?: Purchase["kind"];
  // Whole-project cash position (money in vs out) — /purchases only.
  cash?: CashSummary | null;
  // Combo-page hooks: a stable h1 override + the tab bar rendered above the header.
  title?: string | null;
  tabs?: React.ReactNode;
}) {
  const parts = kind === "parts";
  const purchases = useMemo(
    () => allPurchases.filter((p) => p.kind === kind),
    [allPurchases, kind],
  );
  const [modal, setModal] = useState<ModalState>(null);
  // Deep-linkable: /purchases?q=0004 lands with the search prefilled.
  const [query, setQuery] = useState(initialQuery);
  const [sourceFilter, setSourceFilter] = useState<string | null>(null);
  const [arrival, setArrival] = useState<"all" | "onhand" | "inbound">("all");
  const [mismatchOnly, setMismatchOnly] = useState(false);
  // Default view: most recently arrived first (unknown arrivals at the bottom).
  const { sort, toggle } = useSort<SortKey>({ key: "arrived", dir: -1 });

  const sources = useMemo(
    () => [...new Set(purchases.map((p) => p.source ?? "—"))].sort(),
    [purchases],
  );
  const visible = purchases.filter(
    (p) =>
      matches(p, query) &&
      (sourceFilter === null || (p.source ?? "—") === sourceFilter) &&
      (arrival === "all" ||
        (arrival === "onhand" ? p.arrived_on !== null : p.arrived_on === null)) &&
      (!mismatchOnly || mismatched(p)),
  );

  applySort(visible, sort, sortValue);

  const pager = usePagination(visible);

  const filtered = visible.length !== purchases.length;
  const totalSpent = visible.reduce(
    (sum, p) => sum + (p.total_price ? Number(p.total_price) : 0),
    0,
  );

  return (
    <main className="wide">
      {tabs}
      <header className="page-head">
        <div>
          <h1>{title ?? (parts ? "Parts Orders" : "Purchases")}</h1>
          <p className="subtitle">
            {filtered
              ? `${visible.length} of ${purchases.length} ${parts ? "parts orders" : "buy events"}`
              : `${purchases.length} ${parts ? "parts order" : "buy event"}${purchases.length === 1 ? "" : "s"}`}{" "}
            {parts
              ? "— ordered at some point; arrival is the state"
              : "— money lives here; devices split the lot"}
          </p>
          {cash && (
            <p className="subtitle" title={`${cash.purchase_count} purchases · ${cash.exit_count} exits`}>
              Cash position: {signedPrice(cash.money_out)} out ·{" "}
              {signedPrice(cash.money_in)} in · net {signedPrice(cash.net)}
            </p>
          )}
        </div>
        <button className="btn-primary" onClick={() => setModal({ mode: "create" })}>
          {parts ? "+ Parts order" : "+ Purchase"}
        </button>
      </header>

      <div className="ref-controls">
        <input
          className="ref-search"
          placeholder="Search source, order #, ledger id, note…"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
        />
        <div className="ref-filters">
          <button
            className={`ref-chip${sourceFilter === null ? " active" : ""}`}
            onClick={() => setSourceFilter(null)}
          >
            All
          </button>
          {sources.map((s) => (
            <button
              key={s}
              className={`ref-chip${sourceFilter === s ? " active" : ""}`}
              onClick={() => setSourceFilter(sourceFilter === s ? null : s)}
            >
              {s}
            </button>
          ))}
          <span className="chip-divider" aria-hidden />
          <button
            className={`ref-chip flag-good${arrival === "onhand" ? " active" : ""}`}
            title="Lots with an arrival date — here and unboxed"
            onClick={() => setArrival(arrival === "onhand" ? "all" : "onhand")}
          >
            on hand
          </button>
          <button
            className={`ref-chip flag-stale${arrival === "inbound" ? " active" : ""}`}
            title="Lots with no arrival date — not yet here and unboxed"
            onClick={() => setArrival(arrival === "inbound" ? "all" : "inbound")}
          >
            inbound
          </button>
          {!parts && (
            <button
              className={`ref-chip flag-gap${mismatchOnly ? " active" : ""}`}
              title="Entered device rows ≠ expected units — under (4/5) or over (6/5)"
              onClick={() => setMismatchOnly(!mismatchOnly)}
            >
              mismatched units
            </button>
          )}
        </div>
      </div>

      {error ? (
        <p className="error">Could not load purchases: {error}</p>
      ) : purchases.length === 0 ? (
        <p className="empty">
          {parts
            ? "No parts orders yet — record your first."
            : "No purchases yet — record your first buy."}
        </p>
      ) : visible.length === 0 ? (
        <p className="empty">No purchases match.</p>
      ) : (
        <table>
          <thead>
            <tr>
              <SortTh label="Source" k="source" sort={sort} onToggle={toggle} />
              <th>Order #</th>
              <th>Item</th>
              <th className="num">Total</th>
              <SortTh label={parts ? "Qty" : "Units"} k="units" sort={sort} onToggle={toggle} className="num" />
              <SortTh label="Purchased" k="purchased" sort={sort} onToggle={toggle} />
              <SortTh label="Arrived" k="arrived" sort={sort} onToggle={toggle} />
              <th>Note</th>
              <th aria-label="actions"></th>
            </tr>
          </thead>
          <tbody>
            {pager.paged.map((p) => (
              <tr key={p.id} className="row-link">
                <td className="device">
                  <Link href={`/purchases/${p.id}`} className="row-link-anchor">
                    {p.source ?? "—"}
                  </Link>
                </td>
                <td>
                  {p.url ? (
                    <a
                      href={p.url}
                      target="_blank"
                      rel="noreferrer"
                      className="order-ref"
                      title={p.url}
                    >
                      {p.order_ref || refFromUrl(p.url)}
                    </a>
                  ) : (
                    <span className="order-ref" title={p.order_ref}>
                      {p.order_ref || "—"}
                    </span>
                  )}
                </td>
                <td>
                  <span className="purchase-note" title={p.label || undefined}>
                    {p.label || "—"}
                  </span>
                </td>
                <td className="num" title={p.unit_price ? `$${p.unit_price}/unit` : undefined}>
                  {formatPrice(p.total_price)}
                </td>
                {p.kind === "parts" ? (
                  // Parts are counts, not device rows — show the piece count alone.
                  <td className="num" title="piece count (no device rows for parts)">
                    {p.expected_units ?? "—"}
                  </td>
                ) : (
                  <td
                    className="num"
                    title={
                      p.expected_units !== null
                        ? `${p.device_count} device row${p.device_count === 1 ? "" : "s"} entered of ${p.expected_units} expected`
                        : `${p.device_count} device row${p.device_count === 1 ? "" : "s"} linked`
                    }
                  >
                    {p.expected_units !== null
                      ? `${p.device_count} / ${p.expected_units}`
                      : p.device_count}
                  </td>
                )}
                <td>{p.purchased_on ? formatDate(p.purchased_on) : "—"}</td>
                <td>
                  {p.arrived_on ? (
                    formatDate(p.arrived_on)
                  ) : (
                    <span
                      className="badge band-holding"
                      title="No arrival date — not yet here and unboxed"
                    >
                      inbound
                    </span>
                  )}
                </td>
                <td>
                  <span className="purchase-note" title={p.note}>
                    {p.note || "—"}
                  </span>
                </td>
                <td className="num">
                  <span className="row-actions">
                    {p.kind === "device" && (
                      <button
                        className="btn-edit"
                        onClick={() => setModal({ mode: "bulk", item: p })}
                      >
                        + Devices
                      </button>
                    )}
                    <button
                      className="btn-edit"
                      onClick={() => setModal({ mode: "edit", item: p })}
                    >
                      Edit
                    </button>
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
          <tfoot>
            <tr className="total-row">
              <td colSpan={3}>{filtered ? "Total (filtered)" : "Total spent"}</td>
              <td className="num">${totalSpent.toFixed(2)}</td>
              <td colSpan={5}></td>
            </tr>
          </tfoot>
        </table>
      )}
      <Pagination {...pager} />

      {modal && modal.mode === "bulk" ? (
        <BulkAddModal
          purchase={modal.item}
          options={options}
          onClose={() => setModal(null)}
        />
      ) : modal ? (
        <PurchaseModal
          item={modal.mode === "edit" ? modal.item : null}
          options={options}
          defaultKind={kind}
          onClose={() => setModal(null)}
        />
      ) : null}
    </main>
  );
}
