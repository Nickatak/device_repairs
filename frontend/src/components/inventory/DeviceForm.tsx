"use client";

import { useState } from "react";
import type { InventoryItem } from "@/lib/api/inventory";
import type { Options, ReferenceOption } from "@/lib/api/options";
import type { Purchase } from "@/lib/api/purchases";
import type { DeviceWrite } from "@/app/actions";
import { purchaseLabel } from "@/lib/purchase-format";
import { Combobox, TextCombobox } from "@/components/ui/Combobox";

// New devices default to shipped: a row exists once it's bought and/or inbound.
const EMPTY = {
  reference: null as number | null,
  revision: null as number | null,
  serial: "",
  location: "",
  purchase: null as number | null,
  notes: "",
  status: "shipped",
  cost_override: "",
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
          revision: item.revision?.id ?? null,
          serial: item.serial,
          location: item.location ?? "",
          purchase: item.purchase?.id ?? null,
          notes: item.notes,
          status: item.status,
          cost_override: item.cost_override ?? "",
        }
      : EMPTY,
  );

  function set<K extends keyof DeviceFormState>(key: K, value: DeviceFormState[K]) {
    setForm((f) => ({ ...f, [key]: value }));
  }

  function buildData(): DeviceWrite {
    return {
      reference: form.reference,
      revision: form.revision,
      serial: form.serial,
      location: form.location,
      purchase: form.purchase,
      notes: form.notes,
      status: form.status,
      cost_override: form.cost_override.trim() ? form.cost_override.trim() : null,
    };
  }

  return { form, set, buildData };
}

function refLabel(ref: ReferenceOption): string {
  return `${ref.brand} ${ref.name}`.trim();
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
  const revisions =
    options.references.find((r) => r.id === form.reference)?.revisions ?? [];
  return (
    <>
      <label>
        Model (catalog)
        <ReferenceCombobox
          value={form.reference}
          references={options.references}
          onChange={(id) => {
            set("reference", id);
            // A revision belongs to one reference — changing model clears it.
            set("revision", null);
          }}
        />
      </label>
      {revisions.length > 0 && (
        <label className="narrow">
          Board revision
          <select
            value={form.revision ?? ""}
            onChange={(e) =>
              set("revision", e.target.value ? Number(e.target.value) : null)
            }
            title="Read off the silkscreen once the shell is open (JDM-040). Blank = not yet identified."
          >
            <option value="">not identified</option>
            {revisions.map((r) => (
              <option key={r.id} value={r.id}>
                {r.name}
              </option>
            ))}
          </select>
        </label>
      )}
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
      {form.purchase !== null && (
        <label className="narrow">
          Unit cost override
          <input
            inputMode="decimal"
            value={form.cost_override}
            onChange={(e) => set("cost_override", e.target.value)}
            placeholder="blank = even lot split"
            title="Explicit cost for this unit in a mixed lot (2 DS5 + 3 DS4 shouldn't split evenly); the rest split the remainder"
          />
        </label>
      )}
      {createMode && (
        <label>
          Initial note
          <textarea
            rows={3}
            placeholder="intake fault line — becomes the unit's first note chunk"
            value={form.notes}
            onChange={(e) => set("notes", e.target.value)}
          />
        </label>
      )}
    </>
  );
}
