"use client";

import { useState, useTransition } from "react";
import { useRouter } from "next/navigation";
import { bulkCreateDevices } from "@/app/actions";
import type { Options } from "@/lib/api/options";
import type { Purchase } from "@/lib/api/purchases";
import Modal from "@/components/ui/Modal";
import { CREATE_STATUSES, ReferenceCombobox, purchaseLabel } from "./DeviceForm";
import { TextCombobox } from "@/components/ui/Combobox";

// "3x controllers arrived" → spawn N identical device rows from this purchase.
// Per-unit identity (model #, serial) is refined on each row afterward.
export default function BulkAddModal({
  purchase,
  options,
  onClose,
}: {
  purchase: Purchase;
  options: Options;
  onClose: () => void;
}) {
  const router = useRouter();
  const [pending, startTransition] = useTransition();
  const [error, setError] = useState<string | null>(null);

  // Prefill with the lot's remaining units when the expectation is known.
  const remaining =
    purchase.expected_units !== null
      ? Math.max(purchase.expected_units - purchase.device_count, 1)
      : 1;

  const [reference, setReference] = useState<number | null>(null);
  const [quantity, setQuantity] = useState(String(remaining));
  const [location, setLocation] = useState("");
  // An arrived lot's units are on hand; an unarrived one's are inbound.
  const [status, setStatus] = useState(purchase.arrived_on ? "acquired" : "shipped");
  const [notes, setNotes] = useState("");

  const statuses = options.statuses.filter((s) => CREATE_STATUSES.includes(s.value));

  function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    startTransition(async () => {
      const result = await bulkCreateDevices({
        purchase: purchase.id,
        reference,
        location,
        notes,
        status,
        quantity: Number(quantity),
      });
      if (result.ok) {
        router.refresh();
        onClose();
      } else {
        setError(result.error);
      }
    });
  }

  return (
    <Modal onClose={onClose}>
      <h2>Add devices — {purchaseLabel(purchase)}</h2>
      <form onSubmit={onSubmit}>
        <label>
          Model (catalog)
          <ReferenceCombobox
            value={reference}
            references={options.references}
            onChange={setReference}
          />
        </label>
        <div className="row">
          <label className="narrow">
            Quantity
            <input
              inputMode="numeric"
              value={quantity}
              onChange={(e) => setQuantity(e.target.value)}
            />
          </label>
          <label>
            Status
            <select value={status} onChange={(e) => setStatus(e.target.value)}>
              {statuses.map((s) => (
                <option key={s.value} value={s.value}>
                  {s.label}
                </option>
              ))}
            </select>
          </label>
        </div>
        <label>
          Location
          <TextCombobox
            value={location}
            items={options.locations}
            onChange={setLocation}
            placeholder="Shelf 1…"
          />
        </label>
        <label>
          Note (duplicated on each unit)
          <textarea
            rows={2}
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
          />
        </label>

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
            {pending
              ? "Creating…"
              : `Create ${Number(quantity) || 0} device${Number(quantity) === 1 ? "" : "s"}`}
          </button>
        </div>
      </form>
    </Modal>
  );
}
