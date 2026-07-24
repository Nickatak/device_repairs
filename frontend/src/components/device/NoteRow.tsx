"use client";

import { useRef, useState } from "react";
import type { MediaItem, Note } from "@/lib/api/repairlog";
import { uploadNoteMedia } from "@/app/actions";
import { formatDateTime } from "@/lib/format";
import Measurements from "./Measurements";

// Thumbnail strip + attach control. Chronology tooltip prefers the EXIF shutter
// moment; upload time is the fallback for files that arrived without one.
function NoteMedia({
  deviceId,
  note,
  frozen,
}: {
  deviceId: number;
  note: Note;
  frozen: boolean;
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
    const res = await uploadNoteMedia(deviceId, note.id, formData);
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

  if (note.media.length === 0 && frozen) return null;

  return (
    <div className="note-media">
      {note.media.map((m) => (
        <a key={m.id} href={m.image} target="_blank" rel="noreferrer" title={mediaTitle(m)}>
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img className="note-thumb" src={m.image} alt={m.caption || "repair photo"} />
        </a>
      ))}
      {!frozen && (
        <>
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
        </>
      )}
      {error && <span className="error">{error}</span>}
    </div>
  );
}

export default function NoteRow({
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
          <NoteMedia deviceId={deviceId} note={note} frozen={frozen} />
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
