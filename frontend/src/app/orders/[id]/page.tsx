import Link from "next/link";
import { getOptions, type Options } from "@/lib/api/options";
import { getOrder, type OrderDetail } from "@/lib/api/orders";
import OrderDetailView from "@/components/orders/OrderDetailView";

export const dynamic = "force-dynamic";

export default async function OrderPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  let order: OrderDetail | null = null;
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
    const [p, o] = await Promise.all([getOrder(Number(id)), getOptions()]);
    order = p;
    options = o;
  } catch (e) {
    error = e instanceof Error ? e.message : "Unknown error";
  }

  if (!order) {
    return (
      <main>
        <p className="back">
          <Link href="/orders">← Orders</Link>
        </p>
        <p className="error">Could not load order: {error}</p>
      </main>
    );
  }

  return <OrderDetailView order={order} options={options} />;
}
