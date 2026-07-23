"use client";

import { useState, useTransition } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { markArrived } from "@/app/actions";
import type { Options } from "@/lib/api/options";
import type { PurchaseDetail } from "@/lib/api/purchases";
import { bandClass, formatDate, formatPrice } from "@/lib/format";
import { purchaseLabel } from "@/lib/purchase-format";
import BulkAddModal from "@/components/inventory/BulkAddModal";
import PurchaseModal from "./PurchaseModal";

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
function ArrivalRow({ purchase }: { purchase: PurchaseDetail }) {
  const router = useRouter();
  const [pending, startTransition] = useTransition();
  const [error, setError] = useState<string | null>(null);
  const [date, setDate] = useState(todayISO());

  const inbound = purchase.devices.filter((d) => d.status === "shipped").length;

  function onArrive() {
    setError(null);
    startTransition(async () => {
      const result = await markArrived(purchase.id, date);
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

export default function PurchaseDetailView({
  purchase,
  options,
}: {
  purchase: PurchaseDetail;
  options: Options;
}) {
  const [modal, setModal] = useState<"edit" | "bulk" | null>(null);

  const parts = purchase.kind === "parts";
  const mismatch =
    !parts &&
    purchase.expected_units !== null &&
    purchase.device_count !== purchase.expected_units;

  return (
    <main>
      <p className="back">
        <Link href={parts ? "/parts" : "/purchases"}>
          ← {parts ? "Parts" : "Purchases"}
        </Link>
      </p>

      <header className="page-head">
        <h1>{purchaseLabel(purchase)}</h1>
      </header>

      <section className="device-card">
        <button className="btn-edit device-card-edit" onClick={() => setModal("edit")}>
          Edit purchase
        </button>
        <dl className="card-grid">
          <Field label="ID" value={purchase.ledger_ref || `#${purchase.id}`} />
          <Field label="Kind" value={parts ? "Parts order" : "Device lot"} />
          <Field label="Source" value={purchase.source} />
          <div className="card-field">
            <dt>Order #</dt>
            <dd>
              {purchase.url ? (
                <a href={purchase.url} target="_blank" rel="noreferrer" title={purchase.url}>
                  {purchase.order_ref || "order page"}
                </a>
              ) : (
                purchase.order_ref || "—"
              )}
            </dd>
          </div>
          <Field label="From who" value={purchase.from_who} />
          <Field label="Total" value={formatPrice(purchase.total_price)} />
          <Field
            label={parts ? "Pieces" : "Units"}
            value={
              parts
                ? purchase.expected_units !== null
                  ? String(purchase.expected_units)
                  : null
                : purchase.expected_units !== null
                  ? `${purchase.device_count} entered of ${purchase.expected_units} expected`
                  : `${purchase.device_count} entered`
            }
          />
          {!parts && (
            <Field
              label="Default unit share"
              value={
                purchase.unit_price !== null
                  ? `${formatPrice(purchase.unit_price)} (overrides carved out first)`
                  : null
              }
            />
          )}
          <Field
            label="Purchased"
            value={purchase.purchased_on ? formatDate(purchase.purchased_on) : null}
          />
          <div className="card-field">
            <dt>Arrived</dt>
            <dd>
              {purchase.arrived_on ? (
                formatDate(purchase.arrived_on)
              ) : (
                <span className="badge band-holding">inbound</span>
              )}
            </dd>
          </div>
        </dl>
        {mismatch && (
          <p className="error">
            Unit mismatch: {purchase.device_count} device row
            {purchase.device_count === 1 ? "" : "s"} entered, {purchase.expected_units}{" "}
            expected — reconcile below.
          </p>
        )}
        {purchase.note && (
          <div className="card-notes">
            <dt>Note</dt>
            <dd>{purchase.note}</dd>
          </div>
        )}
        {!purchase.arrived_on && <ArrivalRow purchase={purchase} />}
      </section>

      {!parts && (
        <>
          <div className="repairs-head">
            <h2>Units</h2>
            <button className="btn-secondary" onClick={() => setModal("bulk")}>
              + Add devices
            </button>
          </div>
          {purchase.devices.length === 0 ? (
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
                {purchase.devices.map((unit) => (
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
        <PurchaseModal
          item={purchase}
          options={options}
          defaultKind={purchase.kind}
          onClose={() => setModal(null)}
        />
      )}
      {modal === "bulk" && (
        <BulkAddModal
          purchase={purchase}
          options={options}
          onClose={() => setModal(null)}
        />
      )}
    </main>
  );
}
