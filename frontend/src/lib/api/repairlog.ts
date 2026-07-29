// Bench work — repairs (phase track), notes, measurements. Types only: these
// payloads arrive nested inside the device detail; writes go through actions.

export interface Measurement {
  id: number;
  what: string;
  value: string;
  comment: string;
}

// A photo on a note (or the repair itself). `image` is a relative /media/ URL,
// served same-origin through the Next rewrite. taken_at = EXIF shutter moment
// (UTC, null when the file had none); created_at = upload stamp.
export interface MediaItem {
  id: number;
  image: string;
  caption: string;
  note: number | null;
  repair: number | null;
  device_note: number | null;
  taken_at: string | null;
  created_at: string;
}

export interface Note {
  id: number;
  phase: PhaseKey;
  position: number;
  title: string;
  text: string;
  comment: string;
  parent: number | null;
  created_at: string;
  updated_at: string;
  measurements: Measurement[];
  media: MediaItem[];
  subnotes: Note[];
}

// Note-template layer: one prefill per (catalog model × phase), consumed by
// the add-note modal. `expected` renders as the value placeholder only.
export interface NoteTemplateMeasurement {
  id: number;
  position: number;
  what: string;
  expected: string;
}

export interface NoteTemplateEntry {
  id: number;
  position: number;
  title: string;
  // text = real prefill (lands in the note); placeholder = ghost hint only.
  text: string;
  placeholder: string;
  measurements: NoteTemplateMeasurement[];
}

export interface NoteTemplate {
  id: number;
  reference: number;
  phase: PhaseKey;
  name: string;
  entries: NoteTemplateEntry[];
}

// Mirrors Repair.PHASES on the backend — the fixed bench pipeline.
export const REPAIR_PHASES = [
  { key: "intake", label: "Intake" },
  { key: "teardown", label: "Teardown" },
  { key: "diagnostics", label: "Diagnostics" },
  { key: "repair", label: "Repair" },
  { key: "wash", label: "Wash" },
  { key: "reassemble", label: "Re-assemble" },
  { key: "verify", label: "Verify" },
] as const;

export type PhaseKey = (typeof REPAIR_PHASES)[number]["key"];

// Done-stamps only — phase prose lives in per-phase step Notes (2026-07-28).
export type PhaseFields = {
  [K in PhaseKey as `${K}_done_at`]: string | null;
};

export interface RepairWithNotes extends PhaseFields {
  id: number;
  current_phase: PhaseKey | "completion" | "complete";
  created_at: string;
  completed_at: string | null;
  comment: string;
  notes: Note[];
  media: MediaItem[];
}
