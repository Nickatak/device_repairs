"use client";

import { useState, useTransition } from "react";
import { useRouter } from "next/navigation";
import { updateDevice } from "@/app/actions";
import type { DeviceDetail as DeviceDetailT, InventoryItem } from "@/lib/api/inventory";
import type { Options } from "@/lib/api/options";
import { DeviceFields, useDeviceForm } from "@/components/inventory/DeviceForm";

// The form speaks InventoryItem; the detail payload carries the same device fields.
function asInventoryItem(device: DeviceDetailT): InventoryItem {
  return {
    id: device.id,
    label: device.label,
    ledger_ref: device.ledger_ref,
    reference: device.reference?.id ?? null,
    revision: device.revision,
    serial: device.serial,
    location: device.location,
    purchase: device.purchase,
    notes: device.notes,
    status: device.status,
    status_display: device.status_display,
    repair_count: device.repairs.length,
    cost_override: device.cost_override,
    unit_cost: device.unit_cost,
  };
}

// In-place editor that replaces the read-only card while editing.
export default function DeviceCardEdit({
  device,
  options,
  onDone,
}: {
  device: DeviceDetailT;
  options: Options;
  onDone: () => void;
}) {
  const router = useRouter();
  const [pending, startTransition] = useTransition();
  const [error, setError] = useState<string | null>(null);
  const item = asInventoryItem(device);
  const { form, set, buildData } = useDeviceForm(item);

  function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    startTransition(async () => {
      const result = await updateDevice(device.id, buildData());
      if (result.ok) {
        router.refresh();
        onDone();
      } else {
        setError(result.error);
      }
    });
  }

  return (
    <section className="device-card">
      <form onSubmit={onSubmit} className="card-edit">
        <DeviceFields
          form={form}
          set={set}
          options={options}
          currentPurchase={device.purchase?.id ?? null}
        />

        {error && <p className="error">{error}</p>}

        <div className="modal-actions">
          <button
            type="button"
            className="btn-secondary"
            onClick={onDone}
            disabled={pending}
          >
            Cancel
          </button>
          <button type="submit" className="btn-primary" disabled={pending}>
            {pending ? "Saving…" : "Save"}
          </button>
        </div>
      </form>
    </section>
  );
}
