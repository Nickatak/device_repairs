"use client";

import { useState, useTransition } from "react";
import { useRouter } from "next/navigation";
import { createExit, updateExit } from "@/app/actions";
import { EXIT_KINDS, type Exit } from "@/lib/api/exits";
import type { Options } from "@/lib/api/options";
import Modal from "@/components/ui/Modal";
import { TextCombobox } from "@/components/ui/Combobox";
import { formEnterGuard } from "@/components/ui/formKeys";

// Record or correct a departure event. Creating one flips the device to
// exited on the backend (ledger rule: a unit exit = status flip + exit row).
export default function ExitModal({
  deviceId,
  item,
  options,
  onClose,
}: {
  deviceId: number;
  item: Exit | null; // null = record a new exit
  options: Options;
  onClose: () => void;
}) {
  const router = useRouter();
  const [pending, startTransition] = useTransition();
  const [error, setError] = useState<string | null>(null);

  const [kind, setKind] = useState<string>(item?.kind ?? "sold");
  const [happenedOn, setHappenedOn] = useState(item?.happened_on ?? "");
  const [salePrice, setSalePrice] = useState(item?.sale_price ?? "");
  const [fees, setFees] = useState(item?.fees ?? "");
  const [toWho, setToWho] = useState(item?.to_who ?? "");
  const [note, setNote] = useState(item?.note ?? "");

  // Money fields only make sense on money kinds; a gift has a recipient but no price.
  const moneyKind = kind === "sold" || kind === "returned";

  function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    const data = {
      kind,
      happened_on: happenedOn || null,
      sale_price: moneyKind && salePrice.trim() ? salePrice.trim() : null,
      fees: moneyKind && fees.trim() ? fees.trim() : null,
      to_who: toWho,
      note,
    };
    startTransition(async () => {
      const result = item
        ? await updateExit(deviceId, item.id, data)
        : await createExit(deviceId, data);
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
      <h2>{item ? "Edit exit" : "Record exit"}</h2>
      <form onKeyDown={formEnterGuard} onSubmit={onSubmit}>
        <div className="row">
          <label>
            Kind
            <select value={kind} onChange={(e) => setKind(e.target.value)}>
              {EXIT_KINDS.map((k) => (
                <option key={k.value} value={k.value}>
                  {k.label}
                </option>
              ))}
            </select>
          </label>
          <label>
            Date
            <input
              type="date"
              value={happenedOn}
              onChange={(e) => setHappenedOn(e.target.value)}
            />
          </label>
        </div>
        {moneyKind && (
          <div className="row">
            <label className="narrow">
              {kind === "returned" ? "Refund received" : "Sale price"}
              <input
                inputMode="decimal"
                value={salePrice}
                onChange={(e) => setSalePrice(e.target.value)}
                placeholder="34.99"
              />
            </label>
            <label className="narrow">
              Fees + shipping
              <input
                inputMode="decimal"
                value={fees}
                onChange={(e) => setFees(e.target.value)}
                placeholder="8.12"
              />
            </label>
          </div>
        )}
        <label>
          To who
          <TextCombobox
            value={toWho}
            items={options.people}
            onChange={setToWho}
            placeholder="buyer, friend…"
          />
        </label>
        <label>
          Note
          <textarea rows={2} value={note} onChange={(e) => setNote(e.target.value)} />
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
            {pending ? "Saving…" : item ? "Save" : "Record exit"}
          </button>
        </div>
      </form>
    </Modal>
  );
}
