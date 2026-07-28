"use client";

import { useState, useTransition } from "react";
import { useRouter } from "next/navigation";
import { createPurchase, updatePurchase } from "@/app/actions";
import type { Options } from "@/lib/api/options";
import type { Purchase } from "@/lib/api/purchases";
import Modal from "@/components/ui/Modal";
import { TextCombobox } from "@/components/ui/Combobox";
import { formEnterGuard } from "@/components/ui/formKeys";

// Record a buy event as it happens: "ebay order 111-1231312, $55.42, 2x DS4".
// Device rows link to it afterward via the device form's purchase combobox.
// item === null => create mode; item set => edit mode.
export default function PurchaseModal({
  item = null,
  options,
  onClose,
  defaultKind = "device",
}: {
  item?: Purchase | null;
  options: Options;
  onClose: () => void;
  // Create mode starts on the launching tab's kind; the select stays as the
  // recategorize escape hatch.
  defaultKind?: Purchase["kind"];
}) {
  const router = useRouter();
  const [pending, startTransition] = useTransition();
  const [error, setError] = useState<string | null>(null);
  const [form, setForm] = useState(
    item
      ? {
          kind: item.kind,
          label: item.label,
          source: item.source ?? "",
          order_ref: item.order_ref,
          url: item.url,
          total_price: item.total_price ?? "",
          purchased_on: item.purchased_on ?? "",
          arrived_on: item.arrived_on ?? "",
          from_who: item.from_who,
          expected_units: item.expected_units?.toString() ?? "",
          note: item.note,
        }
      : {
          kind: defaultKind,
          label: "",
          source: "",
          order_ref: "",
          url: "",
          total_price: "",
          purchased_on: "",
          arrived_on: "",
          from_who: "",
          expected_units: "",
          note: "",
        },
  );

  function set(key: keyof typeof form, value: string) {
    setForm((f) => ({ ...f, [key]: value }));
  }

  function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    const data = {
      kind: form.kind,
      label: form.label,
      source: form.source,
      order_ref: form.order_ref,
      url: form.url,
      total_price: form.total_price.trim() === "" ? null : form.total_price.trim(),
      purchased_on: form.purchased_on === "" ? null : form.purchased_on,
      arrived_on: form.arrived_on === "" ? null : form.arrived_on,
      from_who: form.from_who,
      expected_units:
        form.expected_units.trim() === "" ? null : Number(form.expected_units),
      note: form.note,
    };
    startTransition(async () => {
      const result = item
        ? await updatePurchase(item.id, data)
        : await createPurchase(data);
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
      <h2>{item ? "Edit purchase" : "Add purchase"}</h2>
      <form onKeyDown={formEnterGuard} onSubmit={onSubmit}>
        <div className="row">
          <label>
            Kind
            <select
              value={form.kind}
              onChange={(e) => set("kind", e.target.value)}
            >
              <option value="device">Devices</option>
              <option value="parts">Parts</option>
            </select>
          </label>
          <label>
            Label
            <input
              placeholder="DS4 hall module 20-pack"
              value={form.label}
              onChange={(e) => set("label", e.target.value)}
            />
          </label>
        </div>
        <div className="row">
          <label>
            Source
            <TextCombobox
              value={form.source}
              items={options.sources}
              onChange={(v) => set("source", v)}
              placeholder="eBay…"
            />
          </label>
          <label>
            Order #
            <input
              placeholder="27-14860-22553"
              value={form.order_ref}
              onChange={(e) => set("order_ref", e.target.value)}
            />
          </label>
        </div>
        <label>
          URL
          <input
            type="url"
            placeholder="https://order.ebay.com/ord/show?orderId=…"
            value={form.url}
            onChange={(e) => set("url", e.target.value)}
          />
        </label>
        <div className="row">
          <label>
            Total price
            <input
              inputMode="decimal"
              placeholder="55.42"
              value={form.total_price}
              onChange={(e) => set("total_price", e.target.value)}
            />
          </label>
          <label>
            Expected units
            <input
              inputMode="numeric"
              placeholder="2"
              value={form.expected_units}
              onChange={(e) => set("expected_units", e.target.value)}
            />
          </label>
        </div>
        <div className="row">
          <label>
            Purchased on
            <input
              type="date"
              value={form.purchased_on}
              onChange={(e) => set("purchased_on", e.target.value)}
            />
          </label>
          <label>
            Arrived on
            <input
              type="date"
              value={form.arrived_on}
              onChange={(e) => set("arrived_on", e.target.value)}
            />
          </label>
        </div>
        <label>
          From who
          <TextCombobox
            value={form.from_who}
            items={options.people}
            onChange={(v) => set("from_who", v)}
            placeholder="friend's name, seller handle…"
          />
        </label>
        <label>
          Note
          <textarea
            rows={2}
            placeholder="2x DS4 controllers, untested"
            value={form.note}
            onChange={(e) => set("note", e.target.value)}
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
            {pending ? "Saving…" : item ? "Save" : "Create"}
          </button>
        </div>
      </form>
    </Modal>
  );
}
