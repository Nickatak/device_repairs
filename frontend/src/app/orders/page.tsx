import OrdersCombo from "@/components/orders/OrdersCombo";
import { getCash, type CashSummary } from "@/lib/api/cash";
import { getOptions, type Options } from "@/lib/api/options";
import { getOrders, type Order } from "@/lib/api/orders";

export const dynamic = "force-dynamic";

export default async function OrdersPage({
  searchParams,
}: {
  searchParams: Promise<{ q?: string; tab?: string }>;
}) {
  const { q, tab } = await searchParams;
  let orders: Order[] = [];
  let options: Options = {
    references: [],
    locations: [],
    sources: [],
    people: [],
    orders: [],
    statuses: [],
  };
  let cash: CashSummary | null = null;
  let error: string | null = null;
  try {
    [orders, options, cash] = await Promise.all([
      getOrders(),
      getOptions(),
      getCash(),
    ]);
  } catch (e) {
    error = e instanceof Error ? e.message : "Unknown error";
  }

  return (
    <OrdersCombo
      orders={orders}
      options={options}
      cash={cash}
      error={error}
      initialQuery={q ?? ""}
      initialTab={tab === "parts" || tab === "job" ? tab : "device"}
    />
  );
}
