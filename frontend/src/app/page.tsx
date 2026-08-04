import { getInventory, type InventoryItem } from "@/lib/api/inventory";
import { getOptions, type Options } from "@/lib/api/options";
import InventoryView from "@/components/inventory/InventoryView";

// Always render fresh from the DB — inventory changes as repairs progress.
export const dynamic = "force-dynamic";

export default async function InventoryPage({
  searchParams,
}: {
  searchParams: Promise<{ q?: string }>;
}) {
  const { q } = await searchParams;
  let items: InventoryItem[] = [];
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
    [items, options] = await Promise.all([getInventory(), getOptions()]);
  } catch (e) {
    error = e instanceof Error ? e.message : "Unknown error";
  }

  return (
    <InventoryView
      items={items}
      options={options}
      error={error}
      initialQuery={q ?? ""}
    />
  );
}
