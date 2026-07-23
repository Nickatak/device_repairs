"use client";

import { useState } from "react";
import type { CashSummary } from "@/lib/api/cash";
import type { Options } from "@/lib/api/options";
import type { Purchase } from "@/lib/api/purchases";
import PurchasesView from "./PurchasesView";

// One Purchases page, two money-in ledgers: device lots (split into Device
// rows) and stock purchases (feed /stock buckets). Tab state is client-side;
// ?tab=parts deep-links the stock tab. key= remounts the view per tab so
// filters/sort/pagination start fresh — the two ledgers share no filter state.
export default function PurchasesCombo({
  purchases,
  options,
  cash,
  error,
  initialQuery = "",
  initialTab = "device",
}: {
  purchases: Purchase[];
  options: Options;
  cash: CashSummary | null;
  error: string | null;
  initialQuery?: string;
  initialTab?: Purchase["kind"];
}) {
  const [tab, setTab] = useState<Purchase["kind"]>(initialTab);

  return (
    <PurchasesView
      key={tab}
      purchases={purchases}
      options={options}
      error={error}
      initialQuery={initialQuery}
      kind={tab}
      cash={cash}
      title="Purchases"
      tabs={
        <div className="page-tabs">
          <button
            className={`page-tab${tab === "device" ? " active" : ""}`}
            onClick={() => setTab("device")}
          >
            Device Purchases
          </button>
          <button
            className={`page-tab${tab === "parts" ? " active" : ""}`}
            onClick={() => setTab("parts")}
          >
            Stock Purchases
          </button>
        </div>
      }
    />
  );
}
