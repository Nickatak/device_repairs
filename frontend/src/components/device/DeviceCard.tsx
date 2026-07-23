"use client";

import Link from "next/link";
import type { DeviceDetail as DeviceDetailT } from "@/lib/api/inventory";
import { bandClass, formatPrice } from "@/lib/format";
import { purchaseHref, purchaseLabel, purchaseShort } from "@/lib/purchase-format";

function Field({ label, value }: { label: string; value: string | null }) {
  return (
    <div className="card-field">
      <dt>{label}</dt>
      <dd>{value || "—"}</dd>
    </div>
  );
}

export default function DeviceCard({
  device,
  onEdit,
}: {
  device: DeviceDetailT;
  onEdit: () => void;
}) {
  return (
    <section className="device-card">
      <button className="btn-edit device-card-edit" onClick={onEdit}>
        Edit device
      </button>
      <dl className="card-grid">
        <Field label="ID" value={device.ledger_ref || `#${device.id}`} />
        <Field
          label="Model"
          value={
            device.reference
              ? `${device.reference.brand} ${device.reference.name}`.trim() +
                (device.revision ? ` · ${device.revision.name}` : "")
              : null
          }
        />
        <Field label="Location" value={device.location} />
        <Field label="Serial" value={device.serial} />
        <div className="card-field">
          <dt>Purchase</dt>
          <dd>
            {device.purchase ? (
              <Link
                href={purchaseHref(device.purchase)}
                title={purchaseLabel(device.purchase)}
              >
                {purchaseShort(device.purchase)}
              </Link>
            ) : (
              "—"
            )}
          </dd>
        </div>
        <Field
          label="Acquired"
          value={
            device.purchase
              ? formatPrice(device.unit_cost) +
                (device.cost_override !== null ? " (override)" : "") +
                (device.purchase.expected_units || device.purchase.order_ref
                  ? ` (lot: ${formatPrice(device.purchase.total_price)}${device.purchase.order_ref ? ` · ${device.purchase.order_ref}` : ""})`
                  : "")
              : null
          }
        />
        <div className="card-field">
          <dt>Status</dt>
          <dd>
            <span className={`badge ${bandClass(device.status)}`}>
              {device.status_display}
            </span>
          </dd>
        </div>
        <Field label="Repairs" value={String(device.repairs.length)} />
      </dl>
      {device.notes && (
        <div className="card-notes">
          <dt>Notes</dt>
          <dd>{device.notes}</dd>
        </div>
      )}
    </section>
  );
}
