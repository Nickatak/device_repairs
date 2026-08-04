"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";

// Tab order mirrors the pipeline: research it → buy it → work it.
// Orders is a combo page (device lots + stock orders as in-page tabs);
// Stock trails the pipeline — buckets feed repairs, not inventory.
const LINKS = [
  { href: "/reference", label: "Reference" },
  { href: "/orders", label: "Orders" },
  { href: "/", label: "Inventory" },
  { href: "/stock", label: "Stock" },
];

// Config/meta pages live behind the top-right menu, off the main pipeline tabs.
const META_LINKS = [{ href: "/templates", label: "Note templates" }];

function MetaMenu({ pathname }: { pathname: string }) {
  const [open, setOpen] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    function onDown(e: MouseEvent) {
      if (!rootRef.current?.contains(e.target as Node)) setOpen(false);
    }
    window.addEventListener("mousedown", onDown);
    return () => window.removeEventListener("mousedown", onDown);
  }, [open]);

  const active = META_LINKS.some((l) => pathname.startsWith(l.href));

  return (
    <div className="meta-menu" ref={rootRef}>
      <button
        className={`navbar-link meta-menu-button${active ? " active" : ""}`}
        onClick={() => setOpen((o) => !o)}
        title="Config pages"
      >
        ⋯
      </button>
      {open && (
        <div className="meta-menu-list">
          {META_LINKS.map((link) => (
            <Link
              key={link.href}
              href={link.href}
              className="meta-menu-item"
              onClick={() => setOpen(false)}
            >
              {link.label}
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}

export default function Navbar() {
  const pathname = usePathname();

  return (
    <nav className="navbar">
      <div className="navbar-inner">
        <span className="navbar-brand">Repair Log</span>
        <div className="navbar-links">
          {LINKS.map((link) => {
            // Exact match for the inventory root; prefix match for sections.
            const active =
              link.href === "/"
                ? pathname === "/"
                : pathname.startsWith(link.href);
            return (
              <Link
                key={link.href}
                href={link.href}
                className={active ? "navbar-link active" : "navbar-link"}
              >
                {link.label}
              </Link>
            );
          })}
          <MetaMenu pathname={pathname} />
        </div>
      </div>
    </nav>
  );
}
