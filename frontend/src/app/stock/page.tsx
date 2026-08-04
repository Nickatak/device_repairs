import StockView from "@/components/stock/StockView";
import { getOptions, type Options } from "@/lib/api/options";
import { getOrders, type Order } from "@/lib/api/orders";
import { getStock, type StockItem } from "@/lib/api/stock";

export const dynamic = "force-dynamic";

export default async function StockPage({
  searchParams,
}: {
  searchParams: Promise<{ q?: string }>;
}) {
  const { q } = await searchParams;
  let items: StockItem[] = [];
  let orders: Order[] = [];
  let options: Options = {
    references: [],
    locations: [],
    sources: [],
    people: [],
    orders: [],
    statuses: [],
  };
  let error: string | null = null;
  try {
    [items, orders, options] = await Promise.all([
      getStock(),
      getOrders(),
      getOptions(),
    ]);
  } catch (e) {
    error = e instanceof Error ? e.message : "Unknown error";
  }

  return (
    <StockView
      items={items}
      // Intakes draw from parts orders only — device lots become Device rows.
      partsOrders={orders.filter((p) => p.kind === "parts")}
      options={options}
      error={error}
      initialQuery={q ?? ""}
    />
  );
}
