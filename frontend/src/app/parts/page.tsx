import PurchasesView from "@/components/PurchasesView";
import { getOptions, getPurchases, type Options, type Purchase } from "@/lib/api";

export const dynamic = "force-dynamic";

export default async function PartsPage({
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
  let error: string | null = null;
  try {
    [purchases, options] = await Promise.all([getPurchases(), getOptions()]);
  } catch (e) {
    error = e instanceof Error ? e.message : "Unknown error";
  }

  return (
    <PurchasesView
      purchases={purchases}
      options={options}
      error={error}
      initialQuery={q ?? ""}
      kind="parts"
    />
  );
}
