import StockView from "@/components/stock/StockView";
import { getOptions, type Options } from "@/lib/api/options";
import { getPurchases, type Purchase } from "@/lib/api/purchases";
import { getStock, type StockItem } from "@/lib/api/stock";

export const dynamic = "force-dynamic";

export default async function StockPage({
  searchParams,
}: {
  searchParams: Promise<{ q?: string }>;
}) {
  const { q } = await searchParams;
  let items: StockItem[] = [];
  let purchases: Purchase[] = [];
  let options: Options = {
    references: [],
    locations: [],
    sources: [],
    people: [],
    purchases: [],
    statuses: [],
  };
  let error: string | null = null;
  try {
    [items, purchases, options] = await Promise.all([
      getStock(),
      getPurchases(),
      getOptions(),
    ]);
  } catch (e) {
    error = e instanceof Error ? e.message : "Unknown error";
  }

  return (
    <StockView
      items={items}
      // Intakes draw from parts purchases only — device lots become Device rows.
      partsPurchases={purchases.filter((p) => p.kind === "parts")}
      options={options}
      error={error}
      initialQuery={q ?? ""}
    />
  );
}
