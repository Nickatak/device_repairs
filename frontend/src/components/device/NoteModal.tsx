"use client";

import { useState, useTransition } from "react";
import { useRouter } from "next/navigation";
import { createNote, updateNote } from "@/app/actions";
import type { Note } from "@/lib/api/repairlog";
import Modal from "@/components/ui/Modal";

export type NoteModalState =
  | { mode: "create"; repairId: number; nextPosition: number }
  | { mode: "edit"; note: Note };

export default function NoteModal({
  deviceId,
  state,
  onClose,
}: {
  deviceId: number;
  state: NoteModalState;
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
          comment: state.note.comment,
        }
      : {
          position: String(state.nextPosition),
          title: "",
          text: "",
          comment: "",
        },
  );

  function set(key: keyof typeof form, value: string) {
    setForm((f) => ({ ...f, [key]: value }));
  }

  function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    const position = parseInt(form.position, 10) || 0;
    const fields = {
      position,
      title: form.title,
      text: form.text,
      comment: form.comment,
    };
    startTransition(async () => {
      const result =
        state.mode === "edit"
          ? await updateNote(deviceId, state.note.id, fields)
          : await createNote(deviceId, { repair: state.repairId, ...fields });
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
      <h2>{isEdit ? "Edit note" : "Add note"}</h2>
      <form onSubmit={onSubmit}>
          <div className="row">
            <label>
              Title
              <input
                required
                autoFocus
                placeholder="short heading"
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
              placeholder="the notation — what was tested / observed / done"
              value={form.text}
              onChange={(e) => set("text", e.target.value)}
            />
          </label>
          <label>
            Comment
            <textarea
              rows={2}
              value={form.comment}
              onChange={(e) => set("comment", e.target.value)}
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
