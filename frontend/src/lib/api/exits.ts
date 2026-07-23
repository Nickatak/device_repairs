// Exits — the departure events. Money out lives here; the mirror of purchases.
// Type only: exit payloads arrive nested on device/purchase detail; writes go
// through actions.

export interface Exit {
  id: number;
  kind: "sold" | "gifted" | "parted" | "scrapped" | "returned" | "lost";
  kind_display: string;
  happened_on: string | null;
  sale_price: string | null;
  fees: string | null;
  net: string | null;
  to_who: string;
  note: string;
}

// Mirrors Exit.Kind on the backend, in menu order.
export const EXIT_KINDS: { value: Exit["kind"]; label: string }[] = [
  { value: "sold", label: "Sold" },
  { value: "gifted", label: "Gifted" },
  { value: "parted", label: "Parted out" },
  { value: "scrapped", label: "Scrapped" },
  { value: "returned", label: "Returned (refund)" },
  { value: "lost", label: "Lost" },
];
