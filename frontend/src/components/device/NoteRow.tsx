"use client";

import type { Note } from "@/lib/api/repairlog";
import Measurements from "./Measurements";

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
