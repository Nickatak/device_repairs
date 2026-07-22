"use client";

import { useState } from "react";
import type { InventoryItem, Options, Purchase, ReferenceOption } from "@/lib/api";
import type { DeviceWrite } from "@/app/actions";
import { Combobox, TextCombobox } from "./Combobox";

// New devices default to shipped: a row exists once it's bought and/or inbound.
const EMPTY = {
  reference: null as number | null,
  serial: "",
  location: "",
  purchase: null as number | null,
  to_who: "",
  notes: "",
  status: "shipped",
};

// A device ENTERS the system as inbound or on-hand; later lifecycle positions
// are reached by editing, never by creation. Shared with the bulk-add modal.
export const CREATE_STATUSES = ["shipped", "acquired"];

export type DeviceFormState = typeof EMPTY;

// Single source of truth for the device form shape and its mapping to/from the
// API. Shared by the create/edit modal and the in-place editor on the device
// page, so adding a field is a one-place change here plus the fields JSX below.
export function useDeviceForm(item: InventoryItem | null) {
  const [form, setForm] = useState<DeviceFormState>(
    item
      ? {
          reference: item.reference,
          serial: item.serial,
          location: item.location ?? "",
          purchase: item.purchase?.id ?? null,
          to_who: item.to_who,
          notes: item.notes,
          status: item.status,
        }
      : EMPTY,
  );

  function set<K extends keyof DeviceFormState>(key: K, value: DeviceFormState[K]) {
    setForm((f) => ({ ...f, [key]: value }));
  }

  function buildData(): DeviceWrite {
    return {
      reference: form.reference,
      serial: form.serial,
      location: form.location,
      purchase: form.purchase,
      to_who: form.to_who,
      notes: form.notes,
      status: form.status,
    };
  }

  return { form, set, buildData };
}

function refLabel(ref: ReferenceOption): string {
  return `${ref.brand} ${ref.name}`.trim();
}

export function purchaseLabel(p: Purchase): string {
  const parts = [p.label || p.source, p.label ? null : p.order_ref].filter(Boolean);
  if (p.total_price !== null) parts.push(`$${p.total_price}`);
  return parts.join(" ") || `purchase #${p.id}`;
}

function purchaseSub(p: Purchase): string {
  return [
    p.note,
    p.expected_units !== null ? `${p.expected_units} units` : null,
    p.unit_price !== null ? `$${p.unit_price}/unit` : null,
  ]
    .filter(Boolean)
    .join(" · ");
}


// Where this device lands in the selected lot's unit count, flagged when it
// would overshoot the expected units (a 6/5th unit). `counted` = the device
// already belongs to this lot, so saving doesn't add a row.
function PurchaseCountHint({ p, counted }: { p: Purchase; counted: boolean }) {
  const of = p.expected_units !== null ? ` / ${p.expected_units}` : "";
  if (counted) {
    return (
      <p className="combo-hint">
        {p.device_count}
        {of} units entered — includes this one
      </p>
    );
  }
  const slot = p.device_count + 1;
  const over = p.expected_units !== null && slot > p.expected_units;
  return (
    <p className={`combo-hint${over ? " over" : ""}`}>
      {p.device_count}
      {of} units entered — this device would be {slot}
      {of}
      {over ? " (over expected)" : ""}
    </p>
  );
}

// The catalog picker, shared by the device form and the bulk-add modal.
export function ReferenceCombobox({
  value,
  references,
  onChange,
}: {
  value: number | null;
  references: ReferenceOption[];
  onChange: (id: number | null) => void;
}) {
  return (
    <Combobox
      value={value}
      items={references}
      onChange={onChange}
      label={refLabel}
      sublabel={(r) => [r.sku_prefix, r.model_numbers].filter(Boolean).join(" · ")}
      haystack={(r) => `${r.brand} ${r.name} ${r.sku_prefix} ${r.model_numbers}`}
      placeholder="Search catalog… (blank = off-catalog)"
    />
  );
}

export function DeviceFields({
  form,
  set,
  options,
  createMode = false,
  currentPurchase = null,
}: {
  form: DeviceFormState;
  set: <K extends keyof DeviceFormState>(key: K, value: DeviceFormState[K]) => void;
  options: Options;
  createMode?: boolean;
  // The device's SAVED purchase id — lets the count hint tell "already in this
  // lot" apart from "would add a unit to it".
  currentPurchase?: number | null;
}) {
  const statuses = createMode
    ? options.statuses.filter((s) => CREATE_STATUSES.includes(s.value))
    : options.statuses;
  const selectedPurchase =
    options.purchases.find((p) => p.id === form.purchase) ?? null;
  return (
    <>
      <label>
        Model (catalog)
        <ReferenceCombobox
          value={form.reference}
          references={options.references}
          onChange={(id) => set("reference", id)}
        />
      </label>
      <label>
        Serial
        <input value={form.serial} onChange={(e) => set("serial", e.target.value)} />
      </label>
      <label>
        Purchase (lot)
        <Combobox
          value={form.purchase}
          items={options.purchases}
          onChange={(id) => set("purchase", id)}
          label={purchaseLabel}
          sublabel={purchaseSub}
          haystack={(p) =>
            `${p.label} ${p.source ?? ""} ${p.order_ref} ${p.ledger_ref} ${p.total_price ?? ""} ${p.note}`
          }
          placeholder="Search purchases… (blank = no buy record)"
        />
        {selectedPurchase && (
          <PurchaseCountHint
            p={selectedPurchase}
            counted={selectedPurchase.id === currentPurchase}
          />
        )}
      </label>
      <div className="row">
        <label>
          Location
          <TextCombobox
            value={form.location}
            items={options.locations}
            onChange={(v) => set("location", v)}
            placeholder="Shelf 1…"
          />
        </label>
        <label>
          Status
          <select value={form.status} onChange={(e) => set("status", e.target.value)}>
            {statuses.map((s) => (
              <option key={s.value} value={s.value}>
                {s.label}
              </option>
            ))}
          </select>
        </label>
      </div>
      {form.status === "exited" && (
        <label>
          To who
          <TextCombobox
            value={form.to_who}
            items={options.people}
            onChange={(v) => set("to_who", v)}
            placeholder="buyer, friend…"
          />
        </label>
      )}
      <label>
        Notes
        <textarea
          rows={3}
          value={form.notes}
          onChange={(e) => set("notes", e.target.value)}
        />
      </label>
    </>
  );
}
