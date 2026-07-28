"use client";

import { useState, useTransition } from "react";
import { useRouter } from "next/navigation";
import { createDevice, updateDevice } from "@/app/actions";
import type { InventoryItem } from "@/lib/api/inventory";
import type { Options } from "@/lib/api/options";
import Modal from "@/components/ui/Modal";
import { DeviceFields, useDeviceForm } from "./DeviceForm";
import { formEnterGuard } from "@/components/ui/formKeys";

// item === null => create mode; item set => edit mode.
export default function DeviceModal({
  item,
  options,
  onClose,
}: {
  item: InventoryItem | null;
  options: Options;
  onClose: () => void;
}) {
  const router = useRouter();
  const [pending, startTransition] = useTransition();
  const [error, setError] = useState<string | null>(null);
  const { form, set, buildData } = useDeviceForm(item);

  function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    const data = buildData();
    startTransition(async () => {
      const result = item
        ? await updateDevice(item.id, data)
        : await createDevice(data);
      if (result.ok) {
        router.refresh();
        onClose();
      } else {
        setError(result.error);
      }
    });
  }

  const title = item ? "Edit device" : "Add device";
  const submitLabel = pending ? "Saving…" : item ? "Save" : "Create";

  return (
    <Modal onClose={onClose}>
      <h2>{title}</h2>
      <form onKeyDown={formEnterGuard} onSubmit={onSubmit}>
        <DeviceFields
          form={form}
          set={set}
          options={options}
          createMode={!item}
          currentPurchase={item?.purchase?.id ?? null}
        />

        {error && <p className="error">{error}</p>}

        <div className="modal-actions">
          <button
            type="button"
            className="btn-secondary"
            onClick={onClose}
            disabled={pending}
          >
            Cancel
          </button>
          <button type="submit" className="btn-primary" disabled={pending}>
            {submitLabel}
          </button>
        </div>
      </form>
    </Modal>
  );
}
