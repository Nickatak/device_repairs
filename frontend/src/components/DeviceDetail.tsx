"use client";

import { useState, useTransition } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  createMeasurement,
  createRepair,
  updateDevice,
  updateMeasurement,
  updateRepair,
} from "@/app/actions";
import {
  REPAIR_PHASES,
  type DeviceDetail as DeviceDetailT,
  type InventoryItem,
  type Measurement,
  type Note,
  type Options,
  type PhaseKey,
  type RepairWithNotes,
} from "@/lib/api";
import { bandClass, formatDateTime, formatPrice } from "@/lib/format";
import { DeviceFields, purchaseLabel, useDeviceForm } from "./DeviceForm";
import { purchaseHref, purchaseShort } from "./InventoryView";
import NoteModal, { type NoteModalState } from "./NoteModal";

// The form speaks InventoryItem; the detail payload carries the same device fields.
function asInventoryItem(device: DeviceDetailT): InventoryItem {
  return {
    id: device.id,
    label: device.label,
    ledger_ref: device.ledger_ref,
    reference: device.reference?.id ?? null,
    serial: device.serial,
    location: device.location,
    purchase: device.purchase,
    to_who: device.to_who,
    notes: device.notes,
    status: device.status,
    status_display: device.status_display,
    repair_count: device.repairs.length,
  };
}

// Quick bench annotations on a step: "5V rail: 4.98 V". Click one to edit;
// "+ measurement" opens the same tiny inline form for a new one.
function Measurements({
  deviceId,
  note,
  frozen,
}: {
  deviceId: number;
  note: Note;
  frozen: boolean;
}) {
  const router = useRouter();
  const [pending, startTransition] = useTransition();
  const [error, setError] = useState<string | null>(null);
  const [editor, setEditor] = useState<
    | { id: number | null; what: string; value: string; comment: string }
    | null
  >(null);

  function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!editor || !editor.what.trim()) return;
    setError(null);
    const data = { what: editor.what, value: editor.value, comment: editor.comment };
    startTransition(async () => {
      const result = editor.id
        ? await updateMeasurement(deviceId, editor.id, data)
        : await createMeasurement(deviceId, note.id, data);
      if (result.ok) {
        router.refresh();
        setEditor(null);
      } else {
        setError(result.error);
      }
    });
  }

  return (
    <div className="measurements">
      {note.measurements.map((m: Measurement) =>
        editor?.id === m.id ? null : frozen ? (
          <span key={m.id} className="measurement frozen" title={m.comment || undefined}>
            <span className="m-what">{m.what}</span>
            {m.value && <span className="m-value">{m.value}</span>}
          </span>
        ) : (
          <button
            key={m.id}
            className="measurement"
            title={m.comment || "Edit measurement"}
            onClick={() =>
              setEditor({ id: m.id, what: m.what, value: m.value, comment: m.comment })
            }
          >
            <span className="m-what">{m.what}</span>
            {m.value && <span className="m-value">{m.value}</span>}
          </button>
        ),
      )}
      {editor ? (
        <form className="measurement-edit" onSubmit={onSubmit}>
          <input
            placeholder="what — 5V rail"
            value={editor.what}
            autoFocus
            onChange={(e) => setEditor({ ...editor, what: e.target.value })}
          />
          <input
            placeholder="value — 4.98 V"
            value={editor.value}
            onChange={(e) => setEditor({ ...editor, value: e.target.value })}
          />
          <input
            placeholder="comment (optional)"
            value={editor.comment}
            onChange={(e) => setEditor({ ...editor, comment: e.target.value })}
          />
          <button type="submit" className="btn-edit" disabled={pending}>
            {pending ? "…" : "Save"}
          </button>
          <button type="button" className="btn-edit" onClick={() => setEditor(null)}>
            Cancel
          </button>
        </form>
      ) : frozen ? null : (
        <button
          className="measurement add"
          onClick={() => setEditor({ id: null, what: "", value: "", comment: "" })}
        >
          + measurement
        </button>
      )}
      {error && <p className="error">{error}</p>}
    </div>
  );
}

function NoteRow({
  deviceId,
  note,
  frozen,
  onEdit,
}: {
  deviceId: number;
  note: Note;
  frozen: boolean;
  onEdit: (n: Note) => void;
}) {
  return (
    <li className="note-item">
      <div className="note-main">
        <span className="note-pos">{note.position}</span>
        <div className="note-body">
          <div className="note-head">
            {note.title && <span className="note-title">{note.title}</span>}
          </div>
          {note.text && <div className="note-text">{note.text}</div>}
          {note.comment && <div className="note-comment">{note.comment}</div>}
          <Measurements deviceId={deviceId} note={note} frozen={frozen} />
        </div>
        {!frozen && (
          <button className="btn-edit" onClick={() => onEdit(note)}>
            Edit
          </button>
        )}
      </div>
      {note.subnotes.length > 0 && (
        <ol className="notes-list subnotes">
          {note.subnotes.map((sub) => (
            <NoteRow
              key={sub.id}
              deviceId={deviceId}
              note={sub}
              frozen={frozen}
              onEdit={onEdit}
            />
          ))}
        </ol>
      )}
    </li>
  );
}

function nextPosition(notes: Note[]): number {
  return notes.reduce((max, n) => Math.max(max, n.position), 0) + 1;
}

// The bench pipeline: toggle a phase done/undone, keep a deviation note per phase.
// Detail work stays in Steps — this is the checklist layer above them.
function PhaseTrack({
  deviceId,
  repair,
}: {
  deviceId: number;
  repair: RepairWithNotes;
}) {
  const router = useRouter();
  const [pending, startTransition] = useTransition();
  const [error, setError] = useState<string | null>(null);
  const [noteEditor, setNoteEditor] = useState<{ key: PhaseKey; text: string } | null>(
    null,
  );

  function save(data: Record<string, string | null>, onDone?: () => void) {
    setError(null);
    startTransition(async () => {
      const result = await updateRepair(deviceId, repair.id, data);
      if (result.ok) {
        router.refresh();
        onDone?.();
      } else {
        setError(result.error);
      }
    });
  }

  const completed = !!repair.completed_at;
  // A completed repair's phase track is frozen — un-mark completion to edit it.

  return (
    <div className="phase-track">
      {REPAIR_PHASES.map(({ key, label }) => {
        const doneAt = repair[`${key}_done_at`];
        const note = repair[`${key}_note`];
        const isCurrent = repair.current_phase === key;
        const editing = noteEditor?.key === key;
        // On a completed repair, an unchecked phase demonstrably did NOT happen.
        const skipped = completed && !doneAt;
        return (
          <div
            key={key}
            className={`phase-row${doneAt ? " done" : ""}${skipped ? " skipped" : ""}`}
          >
            <button
              className={`phase-check${isCurrent ? " current" : ""}`}
              disabled={pending || completed}
              title={
                skipped
                  ? "Did not happen — repair was completed without this phase"
                  : completed
                    ? "Repair completed — un-mark completion to edit phases"
                    : doneAt
                      ? "Click to un-mark"
                      : "Mark phase done"
              }
              onClick={() =>
                save({ [`${key}_done_at`]: doneAt ? null : new Date().toISOString() })
              }
            >
              {doneAt ? "✓" : skipped ? "✕" : ""}
            </button>
            <span className="phase-label">{label}</span>
            <span className="phase-date">
              {doneAt ? formatDateTime(doneAt) : skipped ? "not performed" : ""}
            </span>
            {editing ? (
              <span className="phase-note-edit">
                <textarea
                  value={noteEditor.text}
                  rows={2}
                  autoFocus
                  onChange={(e) => setNoteEditor({ key, text: e.target.value })}
                />
                <button
                  className="btn-edit"
                  disabled={pending}
                  onClick={() =>
                    save({ [`${key}_note`]: noteEditor.text }, () => setNoteEditor(null))
                  }
                >
                  Save
                </button>
                <button className="btn-edit" onClick={() => setNoteEditor(null)}>
                  Cancel
                </button>
              </span>
            ) : completed ? (
              <span className="phase-note frozen">{note}</span>
            ) : (
              <button
                className={note ? "phase-note" : "phase-note add"}
                onClick={() => setNoteEditor({ key, text: note })}
                title="Edit phase note"
              >
                {note || "+ note"}
              </button>
            )}
          </div>
        );
      })}
      <div className={`phase-row completion-row${completed ? " done" : ""}`}>
        <button
          className={`phase-check${repair.current_phase === "completion" ? " current" : ""}`}
          disabled={pending}
          title={
            completed
              ? "Click to un-mark completion"
              : "Mark repair completed — unchecked phases will read as 'not performed'"
          }
          onClick={() =>
            save({ completed_at: completed ? null : new Date().toISOString() })
          }
        >
          {completed ? "✓" : ""}
        </button>
        <span className="phase-label">Completed</span>
        <span className="phase-date">
          {completed ? formatDateTime(repair.completed_at!) : ""}
        </span>
      </div>
      {error && <p className="error">{error}</p>}
    </div>
  );
}

function Field({ label, value }: { label: string; value: string | null }) {
  return (
    <div className="card-field">
      <dt>{label}</dt>
      <dd>{value || "—"}</dd>
    </div>
  );
}

function DeviceCard({
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
              ? `${device.reference.brand} ${device.reference.name}`.trim()
              : null
          }
        />
        <Field label="Location" value={device.location} />
        {device.status === "exited" && (
          <Field label="To who" value={device.to_who} />
        )}
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
              ? formatPrice(device.purchase.unit_price) +
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

// In-place editor that replaces the read-only card while editing.
function DeviceCardEdit({
  device,
  options,
  onDone,
}: {
  device: DeviceDetailT;
  options: Options;
  onDone: () => void;
}) {
  const router = useRouter();
  const [pending, startTransition] = useTransition();
  const [error, setError] = useState<string | null>(null);
  const item = asInventoryItem(device);
  const { form, set, buildData } = useDeviceForm(item);

  function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    startTransition(async () => {
      const result = await updateDevice(device.id, buildData());
      if (result.ok) {
        router.refresh();
        onDone();
      } else {
        setError(result.error);
      }
    });
  }

  return (
    <section className="device-card">
      <form onSubmit={onSubmit} className="card-edit">
        <DeviceFields
          form={form}
          set={set}
          options={options}
          currentPurchase={device.purchase?.id ?? null}
        />

        {error && <p className="error">{error}</p>}

        <div className="modal-actions">
          <button
            type="button"
            className="btn-secondary"
            onClick={onDone}
            disabled={pending}
          >
            Cancel
          </button>
          <button type="submit" className="btn-primary" disabled={pending}>
            {pending ? "Saving…" : "Save"}
          </button>
        </div>
      </form>
    </section>
  );
}

export default function DeviceDetail({
  device,
  options,
}: {
  device: DeviceDetailT;
  options: Options;
}) {
  const router = useRouter();
  const [modal, setModal] = useState<NoteModalState | null>(null);
  const [editing, setEditing] = useState(false);
  const [startingRepair, startTransition] = useTransition();
  // Completed repairs start minimized — the page opens focused on live work.
  const [minimized, setMinimized] = useState<Set<number>>(
    () => new Set(device.repairs.filter((r) => r.completed_at).map((r) => r.id)),
  );

  function toggleMinimized(id: number) {
    setMinimized((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  }

  return (
    <main>
      <p className="back">
        <Link href="/">← Inventory</Link>
      </p>

      <header className="page-head">
        <h1>{device.label}</h1>
      </header>

      {editing ? (
        <DeviceCardEdit
          device={device}
          options={options}
          onDone={() => setEditing(false)}
        />
      ) : (
        <DeviceCard device={device} onEdit={() => setEditing(true)} />
      )}

      <div className="repairs-head">
        <h2>Bench log</h2>
        <button
          className="btn-secondary"
          disabled={startingRepair}
          onClick={() => {
            const open = device.repairs.filter((r) => !r.completed_at);
            if (
              open.length > 0 &&
              !window.confirm(
                `${open.length === 1 ? `Repair #${open[0].id} is` : `${open.length} repairs are`} still open (not completed). Start another repair on this device?`,
              )
            ) {
              return;
            }
            startTransition(async () => {
              await createRepair(device.id);
              router.refresh();
            });
          }}
        >
          {startingRepair ? "Starting…" : "+ Start repair"}
        </button>
      </div>

      {device.repairs.length === 0 ? (
        <p className="empty">
          No bench work yet — start a repair when the unit hits the bench.
        </p>
      ) : (
        device.repairs.map((repair) => (
          <section key={repair.id} className="repair-block">
            <div className="repair-head">
              {/* Status lives on the device card; here the phase track is the state. */}
              <span className="repair-title">
                Repair #{repair.id} · {formatDateTime(repair.created_at)}
              </span>
              <button
                className="btn-edit repair-minimize"
                title={minimized.has(repair.id) ? "Expand repair" : "Minimize repair"}
                onClick={() => toggleMinimized(repair.id)}
              >
                {minimized.has(repair.id) ? "▸" : "▾"}
              </button>
            </div>
            {!minimized.has(repair.id) && (
              <>
                <PhaseTrack deviceId={device.id} repair={repair} />
                {!repair.completed_at && (
                  <div className="add-note-row">
                    <button
                      className="btn-edit"
                      onClick={() =>
                        setModal({
                          mode: "create",
                          repairId: repair.id,
                          nextPosition: nextPosition(repair.notes),
                        })
                      }
                    >
                      + Add note
                    </button>
                  </div>
                )}
                {repair.notes.length === 0 ? (
                  <p className="empty-steps">No notes yet.</p>
                ) : (
                  <ol className="notes-list">
                    {repair.notes.map((note) => (
                      <NoteRow
                        key={note.id}
                        deviceId={device.id}
                        note={note}
                        frozen={!!repair.completed_at}
                        onEdit={(n) => setModal({ mode: "edit", note: n })}
                      />
                    ))}
                  </ol>
                )}
              </>
            )}
          </section>
        ))
      )}

      {modal && (
        <NoteModal
          deviceId={device.id}
          state={modal}
          onClose={() => setModal(null)}
        />
      )}

    </main>
  );
}
