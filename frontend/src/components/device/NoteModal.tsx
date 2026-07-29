"use client";

import { useState, useTransition } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { createNote, updateNote } from "@/app/actions";
import {
  REPAIR_PHASES,
  type Note,
  type NoteTemplate,
  type PhaseKey,
} from "@/lib/api/repairlog";
import Modal from "@/components/ui/Modal";
import { formEnterGuard } from "@/components/ui/formKeys";

export type NoteModalState =
  | {
      mode: "create";
      repairId: number;
      phase: PhaseKey;
      nextPosition: number;
      templates: NoteTemplate[];
      // Device's catalog row — targets the "create a template" link when
      // this model × phase has none yet. Null = off-catalog unit.
      reference: number | null;
    }
  | { mode: "edit"; note: Note };

function phaseLabel(key: PhaseKey): string {
  return REPAIR_PHASES.find((p) => p.key === key)?.label ?? key;
}

// One editable copy of a template entry: title/text plus measurement rows
// (name fixed from the template; value typed in, expected as placeholder).
interface EntryDraft {
  title: string;
  text: string;
  placeholder: string;
  measurements: { what: string; expected: string; value: string }[];
}

function draftsFromTemplate(template: NoteTemplate): EntryDraft[] {
  return template.entries.map((entry) => ({
    title: entry.title,
    text: entry.text,
    placeholder: entry.placeholder,
    measurements: entry.measurements.map((m) => ({
      what: m.what,
      expected: m.expected,
      value: "",
    })),
  }));
}

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
  // Max one template per (model × phase); "text" = today's plain note.
  const template =
    state.mode === "create" && state.templates.length > 0 ? state.templates[0] : null;
  const [kind, setKind] = useState<"text" | "template">("text");
  const [drafts, setDrafts] = useState<EntryDraft[]>([]);
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

  function pickKind(next: "text" | "template") {
    setKind(next);
    if (next === "template" && template && drafts.length === 0) {
      setDrafts(draftsFromTemplate(template));
    }
  }

  function setDraft(i: number, patch: Partial<Omit<EntryDraft, "measurements">>) {
    setDrafts((d) => d.map((entry, j) => (j === i ? { ...entry, ...patch } : entry)));
  }

  function setDraftValue(i: number, mi: number, value: string) {
    setDrafts((d) =>
      d.map((entry, j) =>
        j === i
          ? {
              ...entry,
              measurements: entry.measurements.map((m, k) =>
                k === mi ? { ...m, value } : m,
              ),
            }
          : entry,
      ),
    );
  }

  function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);

    startTransition(async () => {
      if (state.mode === "edit") {
        const result = await updateNote(deviceId, state.note.id, {
          phase: state.note.phase,
          position: parseInt(form.position, 10) || 0,
          title: form.title,
          text: form.text,
          comment: form.comment,
        });
        if (!result.ok) return setError(result.error);
        router.refresh();
        return onClose();
      }

      if (kind === "template" && template) {
        // One note per entry; a measurement row left blank creates nothing.
        let position = state.nextPosition;
        for (const draft of drafts) {
          const result = await createNote(deviceId, {
            repair: state.repairId,
            phase: state.phase,
            position: position++,
            title: draft.title,
            text: draft.text,
            comment: "",
            measurements: draft.measurements
              .filter((m) => m.value.trim() !== "")
              .map((m) => ({ what: m.what, value: m.value })),
          });
          if (!result.ok) return setError(result.error);
        }
        router.refresh();
        return onClose();
      }

      const result = await createNote(deviceId, {
        repair: state.repairId,
        phase: state.phase,
        position: parseInt(form.position, 10) || 0,
        title: form.title,
        text: form.text,
        comment: form.comment,
      });
      if (!result.ok) return setError(result.error);
      router.refresh();
      onClose();
    });
  }

  const heading = isEdit
    ? `Edit note · ${phaseLabel(state.note.phase)}`
    : `Add note · ${phaseLabel(state.phase)}`;

  return (
    <Modal onClose={onClose}>
      <h2>{heading}</h2>
      <form onKeyDown={formEnterGuard} onSubmit={onSubmit}>
        {!isEdit && (
          <label className="narrow">
            Type
            <select
              value={kind}
              onChange={(e) => pickKind(e.target.value as "text" | "template")}
            >
              <option value="text">Text</option>
              {template && <option value="template">{template.name}</option>}
            </select>
          </label>
        )}
        {!isEdit && !template && (
          <p className="combo-hint">
            No template for this model × {phaseLabel(state.phase)} yet —{" "}
            <Link
              href={
                state.reference !== null
                  ? `/templates?reference=${state.reference}`
                  : "/templates"
              }
            >
              create one
            </Link>
            .
          </p>
        )}

        {kind === "template" && template ? (
          <>
            {drafts.map((draft, i) => (
              <fieldset key={i} className="template-entry">
                <label>
                  Title
                  <input
                    value={draft.title}
                    onChange={(e) => setDraft(i, { title: e.target.value })}
                  />
                </label>
                <label>
                  Text
                  <textarea
                    rows={2}
                    value={draft.text}
                    placeholder={draft.placeholder || undefined}
                    onChange={(e) => setDraft(i, { text: e.target.value })}
                  />
                </label>
                {draft.measurements.length > 0 && (
                  <div className="template-measurements">
                    {draft.measurements.map((m, mi) => (
                      <label key={mi} className="template-measurement">
                        {m.what}
                        <input
                          value={m.value}
                          placeholder={m.expected || "reading"}
                          onChange={(e) => setDraftValue(i, mi, e.target.value)}
                          title="Leave blank to skip this row"
                        />
                      </label>
                    ))}
                  </div>
                )}
              </fieldset>
            ))}
            <p className="combo-hint">
              Blank measurement values are skipped.{" "}
              <Link href={`/templates?reference=${template.reference}`}>
                Edit this template
              </Link>
            </p>
          </>
        ) : (
          <>
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
          </>
        )}

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
