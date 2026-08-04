"use client";

import { useState } from "react";
import type { CashSummary } from "@/lib/api/cash";
import type { Options } from "@/lib/api/options";
import type { Order } from "@/lib/api/orders";
import OrdersView from "./OrdersView";

// One Orders page, three ledgers: device lots (split into Device rows),
// stock orders (feed /stock buckets), and customer jobs (units in for
// service). Tab state is client-side; ?tab=parts / ?tab=job deep-link.
// key= remounts the view per tab so filters/sort/pagination start fresh —
// the ledgers share no filter state.
export default function OrdersCombo({
  orders,
  options,
  cash,
  error,
  initialQuery = "",
  initialTab = "device",
}: {
  orders: Order[];
  options: Options;
  cash: CashSummary | null;
  error: string | null;
  initialQuery?: string;
  initialTab?: Order["kind"];
}) {
  const [tab, setTab] = useState<Order["kind"]>(initialTab);

  return (
    <OrdersView
      key={tab}
      orders={orders}
      options={options}
      error={error}
      initialQuery={initialQuery}
      kind={tab}
      cash={cash}
      title="Orders"
      tabs={
        <div className="page-tabs">
          <button
            className={`page-tab${tab === "device" ? " active" : ""}`}
            onClick={() => setTab("device")}
          >
            Device Orders
          </button>
          <button
            className={`page-tab${tab === "parts" ? " active" : ""}`}
            onClick={() => setTab("parts")}
          >
            Stock Orders
          </button>
          <button
            className={`page-tab${tab === "job" ? " active" : ""}`}
            onClick={() => setTab("job")}
          >
            Jobs
          </button>
        </div>
      }
    />
  );
}
