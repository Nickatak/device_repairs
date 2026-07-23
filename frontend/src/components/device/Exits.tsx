"use client";

import { useState } from "react";
import type { Exit } from "@/lib/api/exits";
import type { Options } from "@/lib/api/options";
import { formatDate, formatPrice } from "@/lib/format";
import ExitModal from "./ExitModal";

// The device's departure history — usually one event; a return-then-resell is
// two. Money out lives here, mirroring the purchase card's money in.
export default function Exits({
  deviceId,
  exits,
  options,
}: {
  deviceId: number;
  exits: Exit[];
  options: Options;
}) {
  const [modal, setModal] = useState<{ item: Exit | null } | null>(null);

  return (
    <section className="device-card">
      <div className="repairs-head">
        <h2>Exits</h2>
        <button className="btn-secondary" onClick={() => setModal({ item: null })}>
          + Record exit
        </button>
      </div>
      {exits.length === 0 ? (
        <p className="empty">Still on hand — no departure recorded.</p>
      ) : (
        <table>
          <thead>
            <tr>
              <th>Kind</th>
              <th>Date</th>
              <th className="num">Money</th>
              <th className="num">Fees</th>
              <th className="num">Net</th>
              <th>To who</th>
              <th>Note</th>
              <th aria-label="actions"></th>
            </tr>
          </thead>
          <tbody>
            {exits.map((exit) => (
              <tr key={exit.id}>
                <td>{exit.kind_display}</td>
                <td>{exit.happened_on ? formatDate(exit.happened_on) : "—"}</td>
                <td className="num">{formatPrice(exit.sale_price)}</td>
                <td className="num">{formatPrice(exit.fees)}</td>
                <td className="num">{formatPrice(exit.net)}</td>
                <td>{exit.to_who || "—"}</td>
                <td>
                  <span className="purchase-note" title={exit.note}>
                    {exit.note || "—"}
                  </span>
                </td>
                <td className="num">
                  <button className="btn-edit" onClick={() => setModal({ item: exit })}>
                    Edit
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      {modal && (
        <ExitModal
          deviceId={deviceId}
          item={modal.item}
          options={options}
          onClose={() => setModal(null)}
        />
      )}
    </section>
  );
}
