"use client";

import { useMemo, useState } from "react";

// The site's two picker flavors. Both render our own styled dropdown — native
// <datalist> popups are unstylable and misposition inside modals.
//
// Combobox<T>:    picks a ROW — free text is only ever a search query; an entry
//                 that isn't picked from the list doesn't survive blur, so the
//                 stored value is always a real row id or null.
// TextCombobox:   picks or TYPES a string — for free-text-via-lookup fields
//                 (source, location) where a brand-new value is legitimate.

export function Combobox<T extends { id: number }>({
  value,
  items,
  onChange,
  label,
  sublabel,
  haystack,
  placeholder,
}: {
  value: number | null;
  items: T[];
  onChange: (id: number | null) => void;
  label: (item: T) => string;
  sublabel: (item: T) => string;
  haystack: (item: T) => string;
  placeholder: string;
}) {
  const selected = items.find((r) => r.id === value) ?? null;
  const [query, setQuery] = useState(selected ? label(selected) : "");
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState(0);

  const matches = useMemo(() => {
    const tokens = query.toLowerCase().split(/\s+/).filter(Boolean);
    if (tokens.length === 0) return items.slice(0, 10);
    return items
      .filter((r) => {
        const hay = haystack(r).toLowerCase();
        return tokens.every((t) => hay.includes(t));
      })
      .slice(0, 10);
  }, [query, items, haystack]);

  function pick(item: T) {
    onChange(item.id);
    setQuery(label(item));
    setOpen(false);
  }

  function handleBlur() {
    if (query.trim() === "") {
      onChange(null);
      setQuery("");
    } else {
      setQuery(selected ? label(selected) : "");
    }
    setOpen(false);
  }

  return (
    <div className="combobox">
      <input
        value={query}
        placeholder={placeholder}
        onChange={(e) => {
          setQuery(e.target.value);
          setOpen(true);
          setActive(0);
        }}
        onFocus={() => setOpen(true)}
        onBlur={handleBlur}
        onKeyDown={(e) => {
          if (!open) return;
          if (e.key === "ArrowDown") {
            e.preventDefault();
            setActive((a) => Math.min(a + 1, matches.length - 1));
          } else if (e.key === "ArrowUp") {
            e.preventDefault();
            setActive((a) => Math.max(a - 1, 0));
          } else if (e.key === "Enter") {
            e.preventDefault();
            if (matches[active]) pick(matches[active]);
          } else if (e.key === "Escape") {
            setOpen(false);
          }
        }}
      />
      {open && matches.length > 0 && (
        <ul className="combobox-list">
          {matches.map((r, i) => (
            <li key={r.id}>
              <button
                type="button"
                className={`combobox-item${i === active ? " active" : ""}`}
                // mousedown, not click: it fires before the input's blur.
                onMouseDown={(e) => {
                  e.preventDefault();
                  pick(r);
                }}
              >
                <span className="combobox-label">{label(r)}</span>
                {sublabel(r) && <span className="combobox-sub">{sublabel(r)}</span>}
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

export function TextCombobox({
  value,
  items,
  onChange,
  placeholder,
}: {
  value: string;
  items: string[];
  onChange: (value: string) => void;
  placeholder?: string;
}) {
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState(0);

  const matches = useMemo(() => {
    const q = value.toLowerCase().trim();
    const pool = q ? items.filter((i) => i.toLowerCase().includes(q)) : items;
    return pool.slice(0, 10);
  }, [value, items]);

  function pick(item: string) {
    onChange(item);
    setOpen(false);
  }

  return (
    <div className="combobox">
      <input
        value={value}
        placeholder={placeholder}
        onChange={(e) => {
          onChange(e.target.value);
          setOpen(true);
          setActive(0);
        }}
        onFocus={() => setOpen(true)}
        // Typed text is a legitimate new value — keep it, just close the list.
        onBlur={() => setOpen(false)}
        onKeyDown={(e) => {
          if (!open) return;
          if (e.key === "ArrowDown") {
            e.preventDefault();
            setActive((a) => Math.min(a + 1, matches.length - 1));
          } else if (e.key === "ArrowUp") {
            e.preventDefault();
            setActive((a) => Math.max(a - 1, 0));
          } else if (e.key === "Enter" && matches.length > 0) {
            e.preventDefault();
            if (matches[active]) pick(matches[active]);
          } else if (e.key === "Escape") {
            setOpen(false);
          }
        }}
      />
      {open && matches.length > 0 && (
        <ul className="combobox-list">
          {matches.map((item, i) => (
            <li key={item}>
              <button
                type="button"
                className={`combobox-item${i === active ? " active" : ""}`}
                onMouseDown={(e) => {
                  e.preventDefault();
                  pick(item);
                }}
              >
                <span className="combobox-label">{item}</span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
