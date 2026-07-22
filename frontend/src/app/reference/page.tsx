import { getLanes, getReference, type Lane, type ReferenceItem } from "@/lib/api";
import ReferenceView from "@/components/ReferenceView";

// The sheet changes with every comp pull — always fetch fresh.
export const dynamic = "force-dynamic";

export default async function ReferencePage() {
  let items: ReferenceItem[] = [];
  let lanes: Lane[] = [];
  let error: string | null = null;
  try {
    [items, lanes] = await Promise.all([getReference(), getLanes()]);
  } catch (e) {
    error = e instanceof Error ? e.message : "Unknown error";
  }

  return <ReferenceView items={items} lanes={lanes} error={error} />;
}
