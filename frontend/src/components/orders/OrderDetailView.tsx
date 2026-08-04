"use client";

import { useState, useTransition } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { markArrived } from "@/app/actions";
import type { Options } from "@/lib/api/options";
import type { OrderDetail } from "@/lib/api/orders";
import { bandClass, formatDate, formatPrice } from "@/lib/format";
import { orderLabel } from "@/lib/order-format";
import BulkAddModal from "@/components/inventory/BulkAddModal";
import OrderModal from "./OrderModal";

function Field({ label, value }: { label: string; value: string | null }) {
  return (
    <div className="card-field">
      <dt>{label}</dt>
      <dd>{value || "—"}</dd>
    </div>
  );
}

// Today's date in the form the date input wants, in LOCAL time (toISOString
// would be UTC and can sit on tomorrow from an evening PST bench).
function todayISO(): string {
  const now = new Date();
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}-${String(now.getDate()).padStart(2, "0")}`;
}

// The arrival stroke: stamp the date and flip the lot's shipped units to
// acquired — the ledger's on-arrival rule, one button instead of N edits.
function ArrivalRow({ order }: { order: OrderDetail }) {
  const router = useRouter();
  const [pending, startTransition] = useTransition();
  const [error, setError] = useState<string | null>(null);
  const [date, setDate] = useState(todayISO());

  const inbound = order.devices.filter((d) => d.status === "shipped").length;

  function onArrive() {
    setError(null);
    startTransition(async () => {
      const result = await markArrived(order.id, date);
      if (result.ok) {
        router.refresh();
      } else {
        setError(result.error);
      }
    });
  }

  return (
    <div className="add-note-row">
      <input type="date" value={date} onChange={(e) => setDate(e.target.value)} />
      <button className="btn-primary" disabled={pending} onClick={onArrive}>
        {pending
          ? "Marking…"
          : `Mark arrived${inbound ? ` — ${inbound} unit${inbound === 1 ? "" : "s"} → acquired` : ""}`}
      </button>
      {error && <p className="error">{error}</p>}
    </div>
  );
}

export default function OrderDetailView({
  order,
  options,
}: {
  order: OrderDetail;
  options: Options;
}) {
  const [modal, setModal] = useState<"edit" | "bulk" | null>(null);

  const parts = order.kind === "parts";
  const mismatch =
    !parts &&
    order.expected_units !== null &&
    order.device_count !== order.expected_units;

  return (
    <main>
      <p className="back">
        <Link href={parts ? "/parts" : "/orders"}>
          ← {parts ? "Parts" : "Orders"}
        </Link>
      </p>

      <header className="page-head">
        <h1>{orderLabel(order)}</h1>
      </header>

      <section className="device-card">
        <button className="btn-edit device-card-edit" onClick={() => setModal("edit")}>
          Edit order
        </button>
        <dl className="card-grid">
          <Field label="ID" value={order.ledger_ref || `#${order.id}`} />
          <Field label="Kind" value={parts ? "Parts order" : "Device lot"} />
          <Field label="Source" value={order.source} />
          <div className="card-field">
            <dt>Order #</dt>
            <dd>
              {order.url ? (
                <a href={order.url} target="_blank" rel="noreferrer" title={order.url}>
                  {order.order_ref || "order page"}
                </a>
              ) : (
                order.order_ref || "—"
              )}
            </dd>
          </div>
          <Field label="From who" value={order.from_who} />
          <Field label="Total" value={formatPrice(order.total_price)} />
          <Field
            label={parts ? "Pieces" : "Units"}
            value={
              parts
                ? order.expected_units !== null
                  ? String(order.expected_units)
                  : null
                : order.expected_units !== null
                  ? `${order.device_count} entered of ${order.expected_units} expected`
                  : `${order.device_count} entered`
            }
          />
          {!parts && (
            <Field
              label="Default unit share"
              value={
                order.unit_price !== null
                  ? `${formatPrice(order.unit_price)} (overrides carved out first)`
                  : null
              }
            />
          )}
          <Field
            label="Ordered"
            value={order.ordered_on ? formatDate(order.ordered_on) : null}
          />
          <div className="card-field">
            <dt>Arrived</dt>
            <dd>
              {order.arrived_on ? (
                formatDate(order.arrived_on)
              ) : (
                <span className="badge band-holding">inbound</span>
              )}
            </dd>
          </div>
        </dl>
        {mismatch && (
          <p className="error">
            Unit mismatch: {order.device_count} device row
            {order.device_count === 1 ? "" : "s"} entered, {order.expected_units}{" "}
            expected — reconcile below.
          </p>
        )}
        {order.note && (
          <div className="card-notes">
            <dt>Note</dt>
            <dd>{order.note}</dd>
          </div>
        )}
        {!order.arrived_on && <ArrivalRow order={order} />}
      </section>

      {!parts && (
        <>
          <div className="repairs-head">
            <h2>Units</h2>
            <button className="btn-secondary" onClick={() => setModal("bulk")}>
              + Add devices
            </button>
          </div>
          {order.devices.length === 0 ? (
            <p className="empty">
              No device rows yet — add them when identity firms up on arrival.
            </p>
          ) : (
            <table>
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Device</th>
                  <th>Serial</th>
                  <th>Location</th>
                  <th className="num">Unit cost</th>
                  <th className="num">Repairs</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {order.devices.map((unit) => (
                  <tr key={unit.id} className="row-link">
                    <td>{unit.ledger_ref || `#${unit.id}`}</td>
                    <td className="device">
                      <Link href={`/devices/${unit.id}`} className="row-link-anchor">
                        {unit.label}
                      </Link>
                    </td>
                    <td>{unit.serial || "—"}</td>
                    <td>{unit.location ?? "—"}</td>
                    <td
                      className="num"
                      title={
                        unit.cost_override !== null
                          ? "explicit unit cost (override)"
                          : "even share of the lot remainder"
                      }
                    >
                      {formatPrice(unit.unit_cost)}
                      {unit.cost_override !== null ? "*" : ""}
                    </td>
                    <td className="num">{unit.repair_count}</td>
                    <td>
                      <span className={`badge ${bandClass(unit.status)}`}>
                        {unit.status_display}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </>
      )}

      {modal === "edit" && (
        <OrderModal
          item={order}
          options={options}
          defaultKind={order.kind}
          onClose={() => setModal(null)}
        />
      )}
      {modal === "bulk" && (
        <BulkAddModal
          order={order}
          options={options}
          onClose={() => setModal(null)}
        />
      )}
    </main>
  );
}
