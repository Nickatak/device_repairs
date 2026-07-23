"use client";

import { useState, useTransition } from "react";
import { useRouter } from "next/navigation";
import {
  createStockIntake,
  createStockItem,
  recountStockItem,
  updateStockItem,
  type StockItemWrite,
} from "@/app/actions";
import type { Options } from "@/lib/api/options";
import type { Purchase } from "@/lib/api/purchases";
import { STOCK_STATES, type FitsLink, type StockItem } from "@/lib/api/stock";
import { purchaseLabel } from "@/lib/purchase-format";
import { Combobox, TextCombobox } from "@/components/ui/Combobox";
import Modal from "@/components/ui/Modal";

// Flattened revision option across the whole catalog — the fits picker needs
// "JDM-055 (Sony DualShock 4 (v2))" because rev names repeat across refs.
function revisionOptions(options: Options) {
  return options.references.flatMap((ref) =>
    ref.revisions.map((rev) => ({
      id: rev.id,
      name: `${rev.name} (${`${ref.brand} ${ref.name}`.trim()})`,
    })),
  );
}

function FitsPicker({
  label,
  chosen,
  pool,
  onChange,
}: {
  label: string;
  chosen: FitsLink[];
  pool: { id: number; name: string }[];
  onChange: (next: FitsLink[]) => void;
}) {
  const available = pool.filter((p) => !chosen.some((c) => c.id === p.id));
  return (
    <label>
      {label}
      {chosen.length > 0 && (
        <p className="ref-configs">
          {chosen.map((c) => (
            <button
              key={c.id}
              type="button"
              className="ref-chip active"
              title="Remove"
              onClick={() => onChange(chosen.filter((x) => x.id !== c.id))}
            >
              {c.name} ×
            </button>
          ))}
        </p>
      )}
      <Combobox
        value={null}
        items={available}
        onChange={(id) => {
          const pick = available.find((p) => p.id === id);
          if (pick) onChange([...chosen, pick]);
        }}
        label={(p) => p.name}
        sublabel={() => ""}
        haystack={(p) => p.name}
        placeholder={`Add ${label.toLowerCase()}…`}
      />
    </label>
  );
}

// item === null => mint a new bucket; item set => edit its identity fields.
export function StockModal({
  item,
  options,
  categories,
  onClose,
}: {
  item: StockItem | null;
  options: Options;
  categories: string[];
  onClose: () => void;
}) {
  const router = useRouter();
  const [pending, startTransition] = useTransition();
  const [error, setError] = useState<string | null>(null);
  const [form, setForm] = useState({
    name: item?.name ?? "",
    category: item?.category ?? "",
    note: item?.note ?? "",
    mode: item?.mode ?? ("presence" as StockItem["mode"]),
    state: item?.state ?? ("in_stock" as StockItem["state"]),
    fits_references: item?.fits_references ?? [],
    fits_revisions: item?.fits_revisions ?? [],
  });

  function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    const data: StockItemWrite = {
      name: form.name.trim(),
      category: form.category.trim(),
      note: form.note,
      mode: form.mode,
      state: form.state,
      fits_references: form.fits_references.map((f) => f.id),
      fits_revisions: form.fits_revisions.map((f) => f.id),
    };
    startTransition(async () => {
      const result = item
        ? await updateStockItem(item.id, data)
        : await createStockItem(data);
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
      <h2>{item ? "Edit bucket" : "New stock bucket"}</h2>
      <form onSubmit={onSubmit}>
        <label>
          Name (the minted SKU — at consumption grain)
          <input
            required
            value={form.name}
            onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
            placeholder="DS4 rubber set, 030/040 family"
          />
        </label>
        <div className="row">
          <label>
            Category
            <TextCombobox
              value={form.category}
              items={categories}
              onChange={(v) => setForm((f) => ({ ...f, category: v }))}
              placeholder="controller-parts…"
            />
          </label>
          <label>
            Tracking
            <select
              value={form.mode}
              onChange={(e) =>
                setForm((f) => ({ ...f, mode: e.target.value as StockItem["mode"] }))
              }
              title="Counted = the number gates decisions (transactional: intakes add, draws subtract, recounts override). Presence = jellybeans, have/low/out by eyeball."
            >
              <option value="presence">Presence (have/low/out)</option>
              <option value="counted">Counted</option>
            </select>
          </label>
          {form.mode === "presence" && (
            <label>
              State
              <select
                value={form.state}
                onChange={(e) =>
                  setForm((f) => ({
                    ...f,
                    state: e.target.value as StockItem["state"],
                  }))
                }
              >
                {STOCK_STATES.map((s) => (
                  <option key={s.value} value={s.value}>
                    {s.label}
                  </option>
                ))}
              </select>
            </label>
          )}
        </div>
        <FitsPicker
          label="Fits models (rev-agnostic)"
          chosen={form.fits_references}
          pool={options.references.map((r) => ({
            id: r.id,
            name: `${r.brand} ${r.name}`.trim(),
          }))}
          onChange={(next) => setForm((f) => ({ ...f, fits_references: next }))}
        />
        <FitsPicker
          label="Fits revisions (rev-specific)"
          chosen={form.fits_revisions}
          pool={revisionOptions(options)}
          onChange={(next) => setForm((f) => ({ ...f, fits_revisions: next }))}
        />
        <label>
          Note (compatibility knowledge)
          <textarea
            rows={3}
            value={form.note}
            onChange={(e) => setForm((f) => ({ ...f, note: e.target.value }))}
            placeholder="XSTC + D-pad pieces interchange across families; home button is family-specific."
          />
        </label>

        {error && <p className="error">{error}</p>}

        <div className="modal-actions">
          <button type="button" className="btn-secondary" onClick={onClose} disabled={pending}>
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

export function IntakeModal({
  item,
  partsPurchases,
  onClose,
}: {
  item: StockItem;
  partsPurchases: Purchase[];
  onClose: () => void;
}) {
  const router = useRouter();
  const [pending, startTransition] = useTransition();
  const [error, setError] = useState<string | null>(null);
  const [purchase, setPurchase] = useState<number | null>(null);
  const [quantity, setQuantity] = useState("");
  const [note, setNote] = useState("");

  function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (purchase === null) {
      setError("Pick the parts purchase this came from.");
      return;
    }
    setError(null);
    startTransition(async () => {
      const result = await createStockIntake({
        purchase,
        stock_item: item.id,
        quantity: Number(quantity),
        note,
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
      <h2>Intake — {item.name}</h2>
      <form onSubmit={onSubmit}>
        <label>
          From parts purchase
          <Combobox
            value={purchase}
            items={partsPurchases}
            onChange={setPurchase}
            label={purchaseLabel}
            sublabel={(p) => p.note}
            haystack={(p) => `${p.label} ${p.source ?? ""} ${p.order_ref} ${p.note}`}
            placeholder="Search parts orders…"
          />
        </label>
        <label className="narrow">
          Quantity
          <input
            required
            inputMode="numeric"
            value={quantity}
            onChange={(e) => setQuantity(e.target.value)}
          />
        </label>
        <label>
          Note
          <input value={note} onChange={(e) => setNote(e.target.value)} />
        </label>

        {error && <p className="error">{error}</p>}

        <div className="modal-actions">
          <button type="button" className="btn-secondary" onClick={onClose} disabled={pending}>
            Cancel
          </button>
          <button type="submit" className="btn-primary" disabled={pending}>
            {pending ? "Saving…" : "+ Intake"}
          </button>
        </div>
      </form>
    </Modal>
  );
}

export function RecountModal({
  item,
  onClose,
}: {
  item: StockItem;
  onClose: () => void;
}) {
  const router = useRouter();
  const [pending, startTransition] = useTransition();
  const [error, setError] = useState<string | null>(null);
  const [count, setCount] = useState("");

  function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    startTransition(async () => {
      const result = await recountStockItem(item.id, Number(count));
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
      <h2>Recount — {item.name}</h2>
      <p className="subtitle">
        The physical count on the shelf right now. Overrides the running number;
        intakes and draws move from this new base.
      </p>
      <form onSubmit={onSubmit}>
        <label className="narrow">
          Counted
          <input
            required
            autoFocus
            inputMode="numeric"
            value={count}
            onChange={(e) => setCount(e.target.value)}
            placeholder={item.count !== null ? `running: ${item.count}` : "first count"}
          />
        </label>

        {error && <p className="error">{error}</p>}

        <div className="modal-actions">
          <button type="button" className="btn-secondary" onClick={onClose} disabled={pending}>
            Cancel
          </button>
          <button type="submit" className="btn-primary" disabled={pending}>
            {pending ? "Saving…" : "Record count"}
          </button>
        </div>
      </form>
    </Modal>
  );
}
