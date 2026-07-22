"use client";

import { useState } from "react";

const PAGE_SIZES = [10, 25, 50];

// Client-side pagination over an already-filtered list. The page index is
// CLAMPED rather than reset when the list shrinks (filter/search changes), so
// there's no effect-juggling; changing the page size returns to page one.
export function usePagination<T>(items: T[]) {
  const [rawPage, setPage] = useState(0);
  const [size, setSizeState] = useState(10);
  const pageCount = Math.max(1, Math.ceil(items.length / size));
  const page = Math.min(rawPage, pageCount - 1);
  const paged = items.slice(page * size, (page + 1) * size);

  function setSize(n: number) {
    setSizeState(n);
    setPage(0);
  }

  return { paged, page, pageCount, size, total: items.length, setPage, setSize };
}

export function Pagination({
  page,
  pageCount,
  size,
  total,
  setPage,
  setSize,
}: {
  page: number;
  pageCount: number;
  size: number;
  total: number;
  setPage: (page: number) => void;
  setSize: (size: number) => void;
}) {
  // Short lists still get the count along the bottom — just no controls.
  if (total <= PAGE_SIZES[0]) {
    return (
      <div className="pagination">
        <span className="page-info">{total} total</span>
      </div>
    );
  }
  const start = page * size + 1;
  const end = Math.min((page + 1) * size, total);
  return (
    <div className="pagination">
      <span className="page-info">
        {start}–{end} of {total} total
      </span>
      <button
        className="btn-edit"
        disabled={page === 0}
        onClick={() => setPage(page - 1)}
      >
        ‹ Prev
      </button>
      <span className="page-info">
        {page + 1} / {pageCount}
      </span>
      <button
        className="btn-edit"
        disabled={page >= pageCount - 1}
        onClick={() => setPage(page + 1)}
      >
        Next ›
      </button>
      <select value={size} onChange={(e) => setSize(Number(e.target.value))}>
        {PAGE_SIZES.map((n) => (
          <option key={n} value={n}>
            {n} / page
          </option>
        ))}
      </select>
    </div>
  );
}
