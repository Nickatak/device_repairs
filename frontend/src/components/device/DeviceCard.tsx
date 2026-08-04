"use client";

import Link from "next/link";
import type { DeviceDetail as DeviceDetailT } from "@/lib/api/inventory";
import { bandClass, formatDateTime, formatPrice } from "@/lib/format";
import { orderHref, orderLabel, orderShort } from "@/lib/order-format";

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
          <dt>Order</dt>
          <dd>
            {device.order ? (
              <Link
                href={orderHref(device.order)}
                title={orderLabel(device.order)}
              >
                {orderShort(device.order)}
              </Link>
            ) : (
              "—"
            )}
          </dd>
        </div>
        <Field
          label="Acquired"
          value={
            device.order
              ? formatPrice(device.unit_cost) +
                (device.cost_override !== null ? " (override)" : "") +
                (device.order.expected_units || device.order.order_ref
                  ? ` (lot: ${formatPrice(device.order.total_price)}${device.order.order_ref ? ` · ${device.order.order_ref}` : ""})`
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
        <Field label="Edited" value={formatDateTime(device.touched_at)} />
      </dl>
    </section>
  );
}
