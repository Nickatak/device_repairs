"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

// Tab order mirrors the pipeline: research it → buy it → work it.
// Purchases is a combo page (device lots + stock purchases as in-page tabs);
// Stock trails the pipeline — buckets feed repairs, not inventory.
const LINKS = [
  { href: "/reference", label: "Reference" },
  { href: "/purchases", label: "Purchases" },
  { href: "/", label: "Inventory" },
  { href: "/stock", label: "Stock" },
];

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
        </div>
      </div>
    </nav>
  );
}
