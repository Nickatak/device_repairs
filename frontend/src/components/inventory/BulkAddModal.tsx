"use client";

import { useState, useTransition } from "react";
import { useRouter } from "next/navigation";
import { bulkCreateDevices, type BulkLine } from "@/app/actions";
import type { Options } from "@/lib/api/options";
import type { Order } from "@/lib/api/orders";
import { orderLabel } from "@/lib/order-format";
import Modal from "@/components/ui/Modal";
import { CREATE_STATUSES, ReferenceCombobox } from "./DeviceForm";
import { TextCombobox } from "@/components/ui/Combobox";
import { formEnterGuard } from "@/components/ui/formKeys";

type LineState = { reference: number | null; quantity: string };

// "2x DS5 + 3x DS4 arrived" → spawn the lot's device rows in one shot; each
// line is one homogeneous slice (reference × quantity). Per-unit identity
// (serial, cost override) is refined on each row afterward.
export default function BulkAddModal({
  order,
  options,
  onClose,
}: {
  order: Order;
  options: Options;
  onClose: () => void;
}) {
  const router = useRouter();
  const [pending, startTransition] = useTransition();
  const [error, setError] = useState<string | null>(null);

  // Prefill with the lot's remaining units when the expectation is known.
  const remaining =
    order.expected_units !== null
      ? Math.max(order.expected_units - order.device_count, 1)
      : 1;

  const [lines, setLines] = useState<LineState[]>([
    { reference: null, quantity: String(remaining) },
  ]);
  const [location, setLocation] = useState("");
  // An arrived lot's units are on hand; an unarrived one's are inbound.
  const [status, setStatus] = useState(order.arrived_on ? "acquired" : "shipped");
  const [notes, setNotes] = useState("");

  const statuses = options.statuses.filter((s) => CREATE_STATUSES.includes(s.value));
  const total = lines.reduce((sum, l) => sum + (Number(l.quantity) || 0), 0);

  function setLine(i: number, patch: Partial<LineState>) {
    setLines((ls) => ls.map((l, j) => (j === i ? { ...l, ...patch } : l)));
  }

  function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    const payload: BulkLine[] = lines.map((l) => ({
      reference: l.reference,
      quantity: Number(l.quantity),
    }));
    startTransition(async () => {
      const result = await bulkCreateDevices({
        order: order.id,
        location,
        notes,
        status,
        lines: payload,
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
      <h2>Add devices — {orderLabel(order)}</h2>
      <form onKeyDown={formEnterGuard} onSubmit={onSubmit}>
        {lines.map((line, i) => (
          <div className="row" key={i}>
            <label>
              Model (catalog)
              <ReferenceCombobox
                value={line.reference}
                references={options.references}
                onChange={(id) => setLine(i, { reference: id })}
              />
            </label>
            <label className="narrow">
              Qty
              <input
                inputMode="numeric"
                value={line.quantity}
                onChange={(e) => setLine(i, { quantity: e.target.value })}
              />
            </label>
            {lines.length > 1 && (
              <button
                type="button"
                className="btn-edit"
                title="Remove line"
                onClick={() => setLines((ls) => ls.filter((_, j) => j !== i))}
              >
                ✕
              </button>
            )}
          </div>
        ))}
        <div className="add-note-row">
          <button
            type="button"
            className="btn-edit"
            title="Mixed lot? One line per model (2x DS5 + 3x DS4)"
            onClick={() =>
              setLines((ls) => [...ls, { reference: null, quantity: "1" }])
            }
          >
            + line
          </button>
        </div>
        <div className="row">
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
              : `Create ${total} device${total === 1 ? "" : "s"}`}
          </button>
        </div>
      </form>
    </Modal>
  );
}
