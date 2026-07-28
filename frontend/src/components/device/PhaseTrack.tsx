"use client";

import { useState, useTransition } from "react";
import { useRouter } from "next/navigation";
import { updateRepair } from "@/app/actions";
import {
  REPAIR_PHASES,
  type Note,
  type PhaseKey,
  type RepairWithNotes,
} from "@/lib/api/repairlog";
import { formatDateTime } from "@/lib/format";
import NoteRow from "./NoteRow";

// The bench pipeline. Each phase row is an ACCORDION (2026-07-28): notes live
// per-phase now — the body holds that substep's notes and its add button; the
// row keeps the done-check, date, and the one-liner deviation chip.
export default function PhaseTrack({
  deviceId,
  repair,
  onAddNote,
  onEditNote,
}: {
  deviceId: number;
  repair: RepairWithNotes;
  onAddNote: (phase: PhaseKey) => void;
  onEditNote: (note: Note) => void;
}) {
  const router = useRouter();
  const [pending, startTransition] = useTransition();
  const [error, setError] = useState<string | null>(null);
  const [noteEditor, setNoteEditor] = useState<{ key: PhaseKey; text: string } | null>(
    null,
  );
  // Volume grows fast (imagine every Xbox rail measurement) — phases start
  // collapsed except wherever the bench currently stands.
  const [expanded, setExpanded] = useState<Set<PhaseKey>>(() => {
    const phase = repair.current_phase;
    return new Set(REPAIR_PHASES.some((p) => p.key === phase) ? [phase as PhaseKey] : []);
  });

  function toggleExpanded(key: PhaseKey) {
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(key)) {
        next.delete(key);
      } else {
        next.add(key);
      }
      return next;
    });
  }

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
        const phaseNotes = repair.notes.filter((n) => n.phase === key);
        const open = expanded.has(key);
        return (
          <div key={key} className={`phase-section${open ? " open" : ""}`}>
            <div
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
                    // Not a <form>, so the global chord is wired by hand:
                    // Ctrl/Cmd+Enter saves, Escape cancels, plain Enter = newline.
                    onKeyDown={(e) => {
                      if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) {
                        e.preventDefault();
                        save({ [`${key}_note`]: noteEditor.text }, () => setNoteEditor(null));
                      } else if (e.key === "Escape") {
                        setNoteEditor(null);
                      }
                    }}
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
              <button
                className={`phase-expand${phaseNotes.length > 0 ? " has-notes" : ""}`}
                onClick={() => toggleExpanded(key)}
                title={open ? "Collapse notes" : "Expand notes"}
              >
                {open ? "▾" : "▸"} {phaseNotes.length}
              </button>
            </div>
            {open && (
              <div className="phase-body">
                {phaseNotes.length === 0 ? (
                  <p className="empty-steps">No notes on this step.</p>
                ) : (
                  <ol className="notes-list">
                    {phaseNotes.map((n) => (
                      <NoteRow
                        key={n.id}
                        deviceId={deviceId}
                        note={n}
                        frozen={completed}
                        onEdit={onEditNote}
                      />
                    ))}
                  </ol>
                )}
                {!completed && (
                  <div className="add-note-row">
                    <button className="btn-edit" onClick={() => onAddNote(key)}>
                      + Add note
                    </button>
                  </div>
                )}
              </div>
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
