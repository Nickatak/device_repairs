"use client";

import { useState, useTransition } from "react";
import { useRouter } from "next/navigation";
import { createMeasurement, updateMeasurement } from "@/app/actions";
import type { Measurement, Note } from "@/lib/api/repairlog";

// Quick bench annotations on a step: "5V rail: 4.98 V". Click one to edit;
// "+ measurement" opens the same tiny inline form for a new one.
export default function Measurements({
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
