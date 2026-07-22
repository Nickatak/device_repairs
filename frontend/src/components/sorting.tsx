"use client";

import { useState } from "react";

// Shared column-sort machinery for the list views (purchases, inventory).
// Click cycle per column: ascending → descending → off. Unknown values
// (null) always sort last, whichever the direction.

export type Sort<K extends string> = { key: K; dir: 1 | -1 } | null;

export function useSort<K extends string>(initial: Sort<K> = null) {
  const [sort, setSort] = useState<Sort<K>>(initial);

  function toggle(key: K) {
    setSort(
      sort?.key !== key
        ? { key, dir: 1 }
        : sort.dir === 1
          ? { key, dir: -1 }
          : null,
    );
  }

  return { sort, toggle };
}

// In-place sort of `rows` by the active column; no-op when sort is off.
export function applySort<T, K extends string>(
  rows: T[],
  sort: Sort<K>,
  value: (row: T, key: K) => string | number | null,
) {
  if (!sort) return;
  const { key, dir } = sort;
  rows.sort((a, b) => {
    let av = value(a, key);
    let bv = value(b, key);
    if (av === null && bv === null) return 0;
    if (av === null) return 1; // unknowns last, either direction
    if (bv === null) return -1;
    if (typeof av === "string") av = av.toLowerCase();
    if (typeof bv === "string") bv = bv.toLowerCase();
    return (av < bv ? -1 : av > bv ? 1 : 0) * dir;
  });
}

export function SortTh<K extends string>({
  label,
  k,
  sort,
  onToggle,
  className,
}: {
  label: string;
  k: K;
  sort: Sort<K>;
  onToggle: (key: K) => void;
  className?: string;
}) {
  const active = sort?.key === k;
  return (
    <th className={className}>
      <button
        className={`th-sort${active ? " active" : ""}`}
        onClick={() => onToggle(k)}
      >
        {label}
        <span className="sort-glyph">
          {active ? (sort.dir === 1 ? "▲" : "▼") : "⇅"}
        </span>
      </button>
    </th>
  );
}
