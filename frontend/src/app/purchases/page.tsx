import PurchasesView from "@/components/purchases/PurchasesView";
import { getCash, type CashSummary } from "@/lib/api/cash";
import { getOptions, type Options } from "@/lib/api/options";
import { getPurchases, type Purchase } from "@/lib/api/purchases";

export const dynamic = "force-dynamic";

export default async function PurchasesPage({
  searchParams,
}: {
  searchParams: Promise<{ q?: string }>;
}) {
  const { q } = await searchParams;
  let purchases: Purchase[] = [];
  let options: Options = {
    references: [],
    locations: [],
    sources: [],
    people: [],
    purchases: [],
    statuses: [],
  };
  let cash: CashSummary | null = null;
  let error: string | null = null;
  try {
    [purchases, options, cash] = await Promise.all([
      getPurchases(),
      getOptions(),
      getCash(),
    ]);
  } catch (e) {
    error = e instanceof Error ? e.message : "Unknown error";
  }

  return (
    <PurchasesView
      purchases={purchases}
      options={options}
      error={error}
      initialQuery={q ?? ""}
      cash={cash}
    />
  );
}
