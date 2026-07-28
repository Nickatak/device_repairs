"use client";

import { useRef, useState, useTransition } from "react";
import { useRouter } from "next/navigation";
import {
  createDeviceNote,
  updateDeviceNote,
  uploadDeviceNoteMedia,
} from "@/app/actions";
import type { DeviceNote } from "@/lib/api/inventory";
import type { MediaItem } from "@/lib/api/repairlog";
import { formatDateTime } from "@/lib/format";
import Modal from "@/components/ui/Modal";

type ModalState =
  | { mode: "create"; nextPosition: number }
  | { mode: "edit"; note: DeviceNote };

// Same shape as the repair NoteModal, minus repair-only fields (comment,
// sub-notes). Title optional: many unit facts are a bare dated line.
function DeviceNoteModal({
  deviceId,
  state,
  onClose,
}: {
  deviceId: number;
  state: ModalState;
  onClose: () => void;
}) {
  const router = useRouter();
  const [pending, startTransition] = useTransition();
  const [error, setError] = useState<string | null>(null);
  const isEdit = state.mode === "edit";
  const [form, setForm] = useState(
    state.mode === "edit"
      ? {
          position: String(state.note.position),
          title: state.note.title,
          text: state.note.text,
        }
      : { position: String(state.nextPosition), title: "", text: "" },
  );

  function set(key: keyof typeof form, value: string) {
    setForm((f) => ({ ...f, [key]: value }));
  }

  function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    const fields = {
      position: parseInt(form.position, 10) || 0,
      title: form.title,
      text: form.text,
    };
    startTransition(async () => {
      const result =
        state.mode === "edit"
          ? await updateDeviceNote(deviceId, state.note.id, fields)
          : await createDeviceNote(deviceId, fields);
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
      <h2>{isEdit ? "Edit unit note" : "Add unit note"}</h2>
      <form onSubmit={onSubmit}>
        <div className="row">
          <label>
            Title
            <input
              autoFocus
              placeholder="optional heading"
              value={form.title}
              onChange={(e) => set("title", e.target.value)}
            />
          </label>
          <label className="narrow">
            Position
            <input
              inputMode="numeric"
              value={form.position}
              onChange={(e) => set("position", e.target.value)}
            />
          </label>
        </div>
        <label>
          Text
          <textarea
            rows={3}
            placeholder="the fact — unit-grain, not bench-step-grain"
            value={form.text}
            onChange={(e) => set("text", e.target.value)}
          />
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
            {pending ? "Saving…" : isEdit ? "Save" : "Add"}
          </button>
        </div>
      </form>
    </Modal>
  );
}

// Thumbnail strip + attach control, same chronology tooltip as repair notes.
function DeviceNoteMedia({
  deviceId,
  note,
}: {
  deviceId: number;
  note: DeviceNote;
}) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function onPick(files: FileList | null) {
    if (!files || files.length === 0) return;
    const formData = new FormData();
    for (const f of files) formData.append("files", f);
    setBusy(true);
    setError(null);
    const res = await uploadDeviceNoteMedia(deviceId, note.id, formData);
    setBusy(false);
    if (!res.ok) setError(res.error);
    if (inputRef.current) inputRef.current.value = "";
  }

  function mediaTitle(m: MediaItem): string {
    const stamp = m.taken_at
      ? `taken ${formatDateTime(m.taken_at)}`
      : `uploaded ${formatDateTime(m.created_at)} (no EXIF)`;
    return m.caption ? `${m.caption} — ${stamp}` : stamp;
  }

  return (
    <div className="note-media">
      {note.media.map((m) => (
        <a key={m.id} href={m.image} target="_blank" rel="noreferrer" title={mediaTitle(m)}>
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img className="note-thumb" src={m.image} alt={m.caption || "unit photo"} />
        </a>
      ))}
      <button
        className="btn-edit note-media-add"
        disabled={busy}
        onClick={() => inputRef.current?.click()}
      >
        {busy ? "Uploading…" : "+ photo"}
      </button>
      <input
        ref={inputRef}
        type="file"
        accept="image/*"
        multiple
        hidden
        onChange={(e) => onPick(e.target.files)}
      />
      {error && <span className="error">{error}</span>}
    </div>
  );
}

// Unit-grain facts, chunked like the repair log (2026-07-27). Never frozen —
// a device keeps accreting facts for as long as it exists.
export default function DeviceNotes({
  deviceId,
  notes,
}: {
  deviceId: number;
  notes: DeviceNote[];
}) {
  const [modal, setModal] = useState<ModalState | null>(null);
  const nextPosition = notes.reduce((max, n) => Math.max(max, n.position), 0) + 1;

  return (
    <section className="repair-block">
      <div className="repairs-head">
        <h2>Unit notes</h2>
        <button
          className="btn-edit"
          onClick={() =>
            setModal({ mode: "create", nextPosition: notes.length === 0 ? 0 : nextPosition })
          }
        >
          + Add note
        </button>
      </div>
      {notes.length === 0 ? (
        <p className="empty-steps">No unit notes yet.</p>
      ) : (
        <ol className="notes-list">
          {notes.map((note) => (
            <li key={note.id} className="note-item">
              <div className="note-main">
                <span className="note-pos">{note.position}</span>
                <div className="note-body">
                  <div className="note-head">
                    {note.title && <span className="note-title">{note.title}</span>}
                    <span className="note-date" title="entry created">
                      {formatDateTime(note.created_at)}
                    </span>
                  </div>
                  {note.text && <div className="note-text">{note.text}</div>}
                  <DeviceNoteMedia deviceId={deviceId} note={note} />
                </div>
                <button
                  className="btn-edit"
                  onClick={() => setModal({ mode: "edit", note })}
                >
                  Edit
                </button>
              </div>
            </li>
          ))}
        </ol>
      )}

      {modal && (
        <DeviceNoteModal
          deviceId={deviceId}
          state={modal}
          onClose={() => setModal(null)}
        />
      )}
    </section>
  );
}
