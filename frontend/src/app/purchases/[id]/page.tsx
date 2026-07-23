import Link from "next/link";
import { getOptions, type Options } from "@/lib/api/options";
import { getPurchase, type PurchaseDetail } from "@/lib/api/purchases";
import PurchaseDetailView from "@/components/purchases/PurchaseDetailView";

export const dynamic = "force-dynamic";

export default async function PurchasePage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  let purchase: PurchaseDetail | null = null;
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
    const [p, o] = await Promise.all([getPurchase(Number(id)), getOptions()]);
    purchase = p;
    options = o;
  } catch (e) {
    error = e instanceof Error ? e.message : "Unknown error";
  }

  if (!purchase) {
    return (
      <main>
        <p className="back">
          <Link href="/purchases">← Purchases</Link>
        </p>
        <p className="error">Could not load purchase: {error}</p>
      </main>
    );
  }

  return <PurchaseDetailView purchase={purchase} options={options} />;
}
