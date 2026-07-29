"use client";

import { useState, useTransition } from "react";
import { useRouter } from "next/navigation";
import {
  createTemplate,
  deleteTemplate,
  updateTemplate,
  type TemplateWrite,
} from "@/app/actions";
import type { Options } from "@/lib/api/options";
import { REPAIR_PHASES, type NoteTemplate, type PhaseKey } from "@/lib/api/repairlog";
import { ReferenceCombobox } from "@/components/inventory/DeviceForm";
import { formEnterGuard } from "@/components/ui/formKeys";

// Authoring surface for the (model × phase) note prefills. Templates are
// config, not ledger — the one place in the UI with a real Delete.

interface MeasurementDraft {
  what: string;
  expected: string;
}

interface EntryDraft {
  title: string;
  text: string;
  placeholder: string;
  measurements: MeasurementDraft[];
}

interface Draft {
  id: number | null; // null = creating
  reference: number | null;
  phase: PhaseKey;
  name: string;
  entries: EntryDraft[];
}

const EMPTY_DRAFT: Draft = {
  id: null,
  reference: null,
  phase: "diagnostics",
  name: "",
  entries: [{ title: "", text: "", placeholder: "", measurements: [] }],
};

function draftFrom(template: NoteTemplate): Draft {
  return {
    id: template.id,
    reference: template.reference,
    phase: template.phase,
    name: template.name,
    entries: template.entries.map((e) => ({
      title: e.title,
      text: e.text,
      placeholder: e.placeholder,
      measurements: e.measurements.map((m) => ({ what: m.what, expected: m.expected })),
    })),
  };
}

function phaseLabel(key: PhaseKey): string {
  return REPAIR_PHASES.find((p) => p.key === key)?.label ?? key;
}

export default function TemplatesView({
  templates,
  options,
  error,
  initialReference,
}: {
  templates: NoteTemplate[];
  options: Options | null;
  error: string | null;
  initialReference: number | null;
}) {
  const router = useRouter();
  const [pending, startTransition] = useTransition();
  const [draft, setDraft] = useState<Draft | null>(null);
  const [saveError, setSaveError] = useState<string | null>(null);

  const references = options?.references ?? [];
  const refName = (id: number) => {
    const ref = references.find((r) => r.id === id);
    return ref ? `${ref.brand} ${ref.name}`.trim() : `#${id}`;
  };

  const visible = initialReference
    ? templates.filter((t) => t.reference === initialReference)
    : templates;

  function patchDraft(patch: Partial<Draft>) {
    setDraft((d) => (d ? { ...d, ...patch } : d));
  }

  function patchEntry(i: number, patch: Partial<EntryDraft>) {
    setDraft((d) =>
      d
        ? {
            ...d,
            entries: d.entries.map((e, j) => (j === i ? { ...e, ...patch } : e)),
          }
        : d,
    );
  }

  function patchMeasurement(i: number, mi: number, patch: Partial<MeasurementDraft>) {
    setDraft((d) =>
      d
        ? {
            ...d,
            entries: d.entries.map((e, j) =>
              j === i
                ? {
                    ...e,
                    measurements: e.measurements.map((m, k) =>
                      k === mi ? { ...m, ...patch } : m,
                    ),
                  }
                : e,
            ),
          }
        : d,
    );
  }

  function onSave(e: React.FormEvent) {
    e.preventDefault();
    if (!draft || draft.reference === null) {
      setSaveError("Pick a catalog model.");
      return;
    }
    setSaveError(null);
    const payload: TemplateWrite = {
      reference: draft.reference,
      phase: draft.phase,
      name: draft.name,
      entries: draft.entries
        .filter((entry) => entry.title.trim() || entry.text.trim() || entry.placeholder.trim() || entry.measurements.length)
        .map((entry, i) => ({
          position: i,
          title: entry.title,
          text: entry.text,
          placeholder: entry.placeholder,
          measurements: entry.measurements
            .filter((m) => m.what.trim())
            .map((m, mi) => ({ position: mi, what: m.what, expected: m.expected })),
        })),
    };
    startTransition(async () => {
      const result = draft.id
        ? await updateTemplate(draft.id, payload)
        : await createTemplate(payload);
      if (result.ok) {
        router.refresh();
        setDraft(null);
      } else {
        setSaveError(result.error);
      }
    });
  }

  function onDelete(template: NoteTemplate) {
    if (!window.confirm(`Delete "${template.name}"? Notes it already created are untouched.`)) {
      return;
    }
    startTransition(async () => {
      const result = await deleteTemplate(template.id);
      if (result.ok) {
        router.refresh();
        setDraft(null);
      } else {
        setSaveError(result.error);
      }
    });
  }

  return (
    <main>
      <header className="page-head">
        <div>
          <h1>Note templates</h1>
          <p className="subtitle">
            One prefill per model × phase, offered by the add-note modal
            {initialReference ? ` — filtered to ${refName(initialReference)}` : ""}
          </p>
        </div>
        <button
          className="btn-primary"
          onClick={() => {
            setSaveError(null);
            setDraft({ ...EMPTY_DRAFT, reference: initialReference });
          }}
        >
          + New template
        </button>
      </header>

      {error ? (
        <p className="error">Could not load templates: {error}</p>
      ) : visible.length === 0 && !draft ? (
        <p className="empty">No templates yet — create the first.</p>
      ) : (
        <table>
          <thead>
            <tr>
              <th>Model</th>
              <th>Phase</th>
              <th>Name</th>
              <th>Entries</th>
              <th aria-label="actions"></th>
            </tr>
          </thead>
          <tbody>
            {visible.map((t) => (
              <tr key={t.id}>
                <td>{refName(t.reference)}</td>
                <td>{phaseLabel(t.phase)}</td>
                <td>{t.name}</td>
                <td>
                  {t.entries
                    .map(
                      (e) =>
                        (e.title || "untitled") +
                        (e.measurements.length ? ` (${e.measurements.length} meas.)` : ""),
                    )
                    .join(", ")}
                </td>
                <td className="num">
                  <button
                    className="btn-edit"
                    onClick={() => {
                      setSaveError(null);
                      setDraft(draftFrom(t));
                    }}
                  >
                    Edit
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      {draft && (
        <section className="device-card template-editor">
          <h2>{draft.id ? "Edit template" : "New template"}</h2>
          <form onKeyDown={formEnterGuard} onSubmit={onSave} className="card-edit">
            <label>
              Model (catalog)
              <ReferenceCombobox
                value={draft.reference}
                references={references}
                onChange={(id) => patchDraft({ reference: id })}
              />
            </label>
            <div className="row">
              <label className="narrow">
                Phase
                <select
                  value={draft.phase}
                  onChange={(e) => patchDraft({ phase: e.target.value as PhaseKey })}
                >
                  {REPAIR_PHASES.map((p) => (
                    <option key={p.key} value={p.key}>
                      {p.label}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                Name
                <input
                  required
                  placeholder="Hall Mod, Voltage readings…"
                  value={draft.name}
                  onChange={(e) => patchDraft({ name: e.target.value })}
                />
              </label>
            </div>

            {draft.entries.map((entry, i) => (
              <fieldset key={i} className="template-entry">
                <div className="row">
                  <label>
                    Entry title
                    <input
                      placeholder="L hall module / Standby rails…"
                      value={entry.title}
                      onChange={(e) => patchEntry(i, { title: e.target.value })}
                    />
                  </label>
                  <button
                    type="button"
                    className="btn-edit"
                    title="Remove this entry"
                    onClick={() =>
                      patchDraft({ entries: draft.entries.filter((_, j) => j !== i) })
                    }
                  >
                    ✕
                  </button>
                </div>
                <label>
                  Prefilled text (lands in the note)
                  <textarea
                    rows={2}
                    value={entry.text}
                    onChange={(e) => patchEntry(i, { text: e.target.value })}
                  />
                </label>
                <label>
                  Placeholder (ghost hint only)
                  <input
                    placeholder="JDM-XXX"
                    value={entry.placeholder}
                    onChange={(e) => patchEntry(i, { placeholder: e.target.value })}
                  />
                </label>
                {entry.measurements.map((m, mi) => (
                  <div className="row template-measurement-row" key={mi}>
                    <label>
                      Measurement
                      <input
                        placeholder="1.1V rail"
                        value={m.what}
                        onChange={(e) => patchMeasurement(i, mi, { what: e.target.value })}
                      />
                    </label>
                    <label>
                      Expected (placeholder)
                      <input
                        placeholder="1.1"
                        value={m.expected}
                        onChange={(e) =>
                          patchMeasurement(i, mi, { expected: e.target.value })
                        }
                      />
                    </label>
                    <button
                      type="button"
                      className="btn-edit"
                      title="Remove this measurement"
                      onClick={() =>
                        patchEntry(i, {
                          measurements: entry.measurements.filter((_, k) => k !== mi),
                        })
                      }
                    >
                      ✕
                    </button>
                  </div>
                ))}
                <div className="add-note-row">
                  <button
                    type="button"
                    className="btn-edit"
                    onClick={() =>
                      patchEntry(i, {
                        measurements: [...entry.measurements, { what: "", expected: "" }],
                      })
                    }
                  >
                    + measurement slot
                  </button>
                </div>
              </fieldset>
            ))}
            <div className="add-note-row">
              <button
                type="button"
                className="btn-edit"
                onClick={() =>
                  patchDraft({
                    entries: [...draft.entries, { title: "", text: "", placeholder: "", measurements: [] }],
                  })
                }
              >
                + entry
              </button>
            </div>

            {saveError && <p className="error">{saveError}</p>}

            <div className="modal-actions">
              {draft.id !== null && (
                <button
                  type="button"
                  className="btn-secondary template-delete"
                  disabled={pending}
                  onClick={() => {
                    const original = templates.find((t) => t.id === draft.id);
                    if (original) onDelete(original);
                  }}
                >
                  Delete
                </button>
              )}
              <button
                type="button"
                className="btn-secondary"
                onClick={() => setDraft(null)}
                disabled={pending}
              >
                Cancel
              </button>
              <button type="submit" className="btn-primary" disabled={pending}>
                {pending ? "Saving…" : "Save template"}
              </button>
            </div>
          </form>
        </section>
      )}
    </main>
  );
}
