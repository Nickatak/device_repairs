"use client";

import { useMemo, useState, useTransition } from "react";
import { useRouter } from "next/navigation";
import { updateStockItem } from "@/app/actions";
import type { Options } from "@/lib/api/options";
import type { Purchase } from "@/lib/api/purchases";
import type { StockItem } from "@/lib/api/stock";
import { formatDate } from "@/lib/format";
import { Pagination, usePagination } from "@/components/ui/Pagination";
import { SortTh, applySort, useSort } from "@/components/ui/sorting";
import { IntakeModal, RecountModal, StockModal } from "./StockModals";

type ModalState =
  | { mode: "create" }
  | { mode: "edit"; item: StockItem }
  | { mode: "intake"; item: StockItem }
  | { mode: "recount"; item: StockItem }
  | null;

function matches(it: StockItem, query: string): boolean {
  if (!query) return true;
  const haystack = [
    it.name,
    it.category,
    it.note,
    it.mode,
    it.state,
    ...it.fits_references.map((f) => f.name),
    ...it.fits_revisions.map((f) => f.name),
  ]
    .join(" ")
    .toLowerCase();
  return query
    .toLowerCase()
    .split(/\s+/)
    .every((term) => haystack.includes(term));
}

// A bucket that needs eyes: presence low/out, or a counted bucket at zero /
// never counted.
function needsAttention(it: StockItem): boolean {
  if (it.mode === "presence") return it.state !== "in_stock";
  return it.count === null || it.count <= 0;
}

type SortKey = "name" | "category" | "onhand" | "counted";

function sortValue(it: StockItem, key: SortKey): string | number | null {
  switch (key) {
    case "name":
      return it.name;
    case "category":
      return it.category || null;
    case "onhand":
      // Counted buckets sort by number; presence in_stock/low/out map high→low.
      if (it.mode === "counted") return it.count;
      return it.state === "in_stock" ? 2 : it.state === "low" ? 1 : 0;
    case "counted":
      return it.counted_at;
  }
}

// Presence states cycle by eyeball — clicking the badge is the whole workflow.
const NEXT_STATE = { in_stock: "low", low: "out", out: "in_stock" } as const;

function stateBand(state: StockItem["state"]): string {
  return state === "in_stock" ? "band-fixed" : state === "low" ? "band-holding" : "band-exited";
}

function PresenceBadge({ item }: { item: StockItem }) {
  const router = useRouter();
  const [pending, startTransition] = useTransition();

  function cycle() {
    startTransition(async () => {
      await updateStockItem(item.id, {
        name: item.name,
        category: item.category,
        note: item.note,
        mode: item.mode,
        state: NEXT_STATE[item.state],
        fits_references: item.fits_references.map((f) => f.id),
        fits_revisions: item.fits_revisions.map((f) => f.id),
      });
      router.refresh();
    });
  }

  return (
    <button
      className={`badge ${stateBand(item.state)}`}
      style={{ cursor: "pointer" }}
      disabled={pending}
      title="Click to cycle: in stock → low → out"
      onClick={cycle}
    >
      {pending ? "…" : item.state_display}
    </button>
  );
}

function OnHand({ item }: { item: StockItem }) {
  if (item.mode === "presence") return <PresenceBadge item={item} />;
  if (item.count === null) {
    return (
      <span className="badge band-holding" title="Counted bucket with no recount yet — record the first count to start the ledger">
        uncounted
      </span>
    );
  }
  return (
    <strong
      title={
        item.counted_at
          ? `base ${item.last_count} @ ${formatDate(item.counted_at.slice(0, 10))} + intakes − draws`
          : undefined
      }
    >
      {item.count}
    </strong>
  );
}

export default function StockView({
  items,
  partsPurchases,
  options,
  error,
  initialQuery = "",
}: {
  items: StockItem[];
  partsPurchases: Purchase[];
  options: Options;
  error: string | null;
  initialQuery?: string;
}) {
  const [modal, setModal] = useState<ModalState>(null);
  const [query, setQuery] = useState(initialQuery);
  const [categoryFilter, setCategoryFilter] = useState<string | null>(null);
  const [modeFilter, setModeFilter] = useState<StockItem["mode"] | null>(null);
  const [attentionOnly, setAttentionOnly] = useState(false);
  const { sort, toggle } = useSort<SortKey>();

  const categories = useMemo(
    () => [...new Set(items.map((it) => it.category || "—"))].sort(),
    [items],
  );

  const visible = items.filter(
    (it) =>
      matches(it, query) &&
      (categoryFilter === null || (it.category || "—") === categoryFilter) &&
      (modeFilter === null || it.mode === modeFilter) &&
      (!attentionOnly || needsAttention(it)),
  );
  applySort(visible, sort, sortValue);
  const pager = usePagination(visible);
  const filtered = visible.length !== items.length;

  return (
    <main className="wide">
      <header className="page-head">
        <div>
          <h1>Stock</h1>
          <p className="subtitle">
            {filtered
              ? `${visible.length} of ${items.length} buckets`
              : `${items.length} bucket${items.length === 1 ? "" : "s"}`}{" "}
            — counted forcefully or presence by eyeball
          </p>
        </div>
        <button className="btn-primary" onClick={() => setModal({ mode: "create" })}>
          + Add bucket
        </button>
      </header>

      <div className="ref-controls">
        <input
          className="ref-search"
          placeholder="Search name, category, fits, note…"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
        />
        <div className="ref-filters">
          <button
            className={`ref-chip${categoryFilter === null ? " active" : ""}`}
            onClick={() => setCategoryFilter(null)}
          >
            All
          </button>
          {categories.map((c) => (
            <button
              key={c}
              className={`ref-chip${categoryFilter === c ? " active" : ""}`}
              onClick={() => setCategoryFilter(categoryFilter === c ? null : c)}
            >
              {c}
            </button>
          ))}
          <span className="chip-divider" aria-hidden />
          <button
            className={`ref-chip${modeFilter === "counted" ? " active" : ""}`}
            title="Buckets with transactional counts"
            onClick={() => setModeFilter(modeFilter === "counted" ? null : "counted")}
          >
            counted
          </button>
          <button
            className={`ref-chip${modeFilter === "presence" ? " active" : ""}`}
            title="Have/low/out buckets"
            onClick={() => setModeFilter(modeFilter === "presence" ? null : "presence")}
          >
            presence
          </button>
          <span className="chip-divider" aria-hidden />
          <button
            className={`ref-chip flag-stale${attentionOnly ? " active" : ""}`}
            title="Low/out presence buckets + counted buckets at zero or never counted"
            onClick={() => setAttentionOnly(!attentionOnly)}
          >
            needs attention
          </button>
        </div>
      </div>

      {error ? (
        <p className="error">Could not load stock: {error}</p>
      ) : items.length === 0 ? (
        <p className="empty">
          No stock buckets yet — mint your first SKU with “+ Add bucket”.
        </p>
      ) : visible.length === 0 ? (
        <p className="empty">No buckets match.</p>
      ) : (
        <table>
          <thead>
            <tr>
              <SortTh label="Bucket" k="name" sort={sort} onToggle={toggle} />
              <SortTh label="Category" k="category" sort={sort} onToggle={toggle} />
              <th>Fits</th>
              <SortTh label="On hand" k="onhand" sort={sort} onToggle={toggle} className="num" />
              <SortTh label="Counted" k="counted" sort={sort} onToggle={toggle} />
              <th>Note</th>
              <th aria-label="actions"></th>
            </tr>
          </thead>
          <tbody>
            {pager.paged.map((item) => {
              const fits = [
                ...item.fits_references.map((f) => f.name),
                ...item.fits_revisions.map((f) => f.name),
              ];
              return (
                <tr key={item.id}>
                  <td className="device">{item.name}</td>
                  <td>{item.category || "—"}</td>
                  <td>
                    <span className="purchase-note" title={fits.join(" · ") || undefined}>
                      {fits.length > 0 ? fits.join(" · ") : "—"}
                    </span>
                  </td>
                  <td className="num">
                    <OnHand item={item} />
                  </td>
                  <td>
                    {item.mode === "counted" && item.counted_at
                      ? formatDate(item.counted_at.slice(0, 10))
                      : "—"}
                  </td>
                  <td>
                    <span className="purchase-note" title={item.note || undefined}>
                      {item.note || "—"}
                    </span>
                  </td>
                  <td className="num">
                    <span className="row-actions">
                      {item.mode === "counted" && (
                        <>
                          <button
                            className="btn-edit"
                            onClick={() => setModal({ mode: "recount", item })}
                          >
                            Recount
                          </button>
                          <button
                            className="btn-edit"
                            onClick={() => setModal({ mode: "intake", item })}
                          >
                            + Intake
                          </button>
                        </>
                      )}
                      <button
                        className="btn-edit"
                        onClick={() => setModal({ mode: "edit", item })}
                      >
                        Edit
                      </button>
                    </span>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      )}
      <Pagination {...pager} />

      {modal?.mode === "create" || modal?.mode === "edit" ? (
        <StockModal
          item={modal.mode === "edit" ? modal.item : null}
          options={options}
          categories={categories.filter((c) => c !== "—")}
          onClose={() => setModal(null)}
        />
      ) : modal?.mode === "intake" ? (
        <IntakeModal
          item={modal.item}
          partsPurchases={partsPurchases}
          onClose={() => setModal(null)}
        />
      ) : modal?.mode === "recount" ? (
        <RecountModal item={modal.item} onClose={() => setModal(null)} />
      ) : null}
    </main>
  );
}
