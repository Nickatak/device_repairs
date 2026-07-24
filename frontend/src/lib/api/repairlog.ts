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
  taken_at: string | null;
  created_at: string;
}

export interface Note {
  id: number;
  position: number;
  title: string;
  text: string;
  comment: string;
  parent: number | null;
  measurements: Measurement[];
  media: MediaItem[];
  subnotes: Note[];
}

// Mirrors Repair.PHASES on the backend — the fixed bench pipeline.
export const REPAIR_PHASES = [
  { key: "teardown", label: "Teardown" },
  { key: "wash", label: "Wash" },
  { key: "repair", label: "Repair" },
  { key: "reassemble", label: "Re-assemble" },
  { key: "verify", label: "Verify" },
] as const;

export type PhaseKey = (typeof REPAIR_PHASES)[number]["key"];

export type PhaseFields = {
  [K in PhaseKey as `${K}_done_at`]: string | null;
} & {
  [K in PhaseKey as `${K}_note`]: string;
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
