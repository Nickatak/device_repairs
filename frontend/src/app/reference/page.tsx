import type { Metadata } from "next";
import { getReference, type ReferenceItem } from "@/lib/api/reference";
import { getInventory, type InventoryItem } from "@/lib/api/inventory";
import ReferenceView from "@/components/reference/ReferenceView";

// The sheet changes with every comp pull — always fetch fresh.
export const dynamic = "force-dynamic";

export const metadata: Metadata = { title: "Price Sheet" };

export default async function ReferencePage() {
  let items: ReferenceItem[] = [];
  let devices: InventoryItem[] = [];
  let error: string | null = null;
  try {
    [items, devices] = await Promise.all([getReference(), getInventory()]);
  } catch (e) {
    error = e instanceof Error ? e.message : "Unknown error";
  }

  return <ReferenceView items={items} devices={devices} error={error} />;
}
