import Link from "next/link";
import { getDevice, type DeviceDetail as DeviceDetailT } from "@/lib/api/inventory";
import { getOptions, type Options } from "@/lib/api/options";
import DeviceDetail from "@/components/device/DeviceDetail";

export const dynamic = "force-dynamic";

export default async function DevicePage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  let device: DeviceDetailT | null = null;
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
    const [d, o] = await Promise.all([getDevice(Number(id)), getOptions()]);
    device = d;
    options = o;
  } catch (e) {
    error = e instanceof Error ? e.message : "Unknown error";
  }

  if (!device) {
    return (
      <main>
        <p className="back">
          <Link href="/">← Inventory</Link>
        </p>
        <p className="error">Could not load device: {error}</p>
      </main>
    );
  }

  return (
    <DeviceDetail device={device} options={options} />
  );
}
