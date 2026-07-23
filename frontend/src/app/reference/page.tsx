import { getReference, type ReferenceItem } from "@/lib/api/reference";
import ReferenceView from "@/components/reference/ReferenceView";

// The sheet changes with every comp pull — always fetch fresh.
export const dynamic = "force-dynamic";

export default async function ReferencePage() {
  let items: ReferenceItem[] = [];
  let error: string | null = null;
  try {
    items = await getReference();
  } catch (e) {
    error = e instanceof Error ? e.message : "Unknown error";
  }

  return <ReferenceView items={items} error={error} />;
}
