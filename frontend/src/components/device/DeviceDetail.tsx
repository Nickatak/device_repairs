"use client";

import { useState, useTransition } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { createRepair } from "@/app/actions";
import type { DeviceDetail as DeviceDetailT } from "@/lib/api/inventory";
import type { Options } from "@/lib/api/options";
import type { Note, PhaseKey } from "@/lib/api/repairlog";
import { formatDateTime } from "@/lib/format";
import DeviceCard from "./DeviceCard";
import DeviceCardEdit from "./DeviceCardEdit";
import DeviceNotes from "./DeviceNotes";
import Exits from "./Exits";
import NoteModal, { type NoteModalState } from "./NoteModal";
import PhaseTrack from "./PhaseTrack";

function nextPosition(notes: Note[]): number {
  return notes.reduce((max, n) => Math.max(max, n.position), 0) + 1;
}

export default function DeviceDetail({
  device,
  options,
}: {
  device: DeviceDetailT;
  options: Options;
}) {
  const router = useRouter();
  const [modal, setModal] = useState<NoteModalState | null>(null);
  const [editing, setEditing] = useState(false);
  const [startingRepair, startTransition] = useTransition();
  // Completed repairs start minimized — the page opens focused on live work.
  const [minimized, setMinimized] = useState<Set<number>>(
    () => new Set(device.repairs.filter((r) => r.completed_at).map((r) => r.id)),
  );

  function toggleMinimized(id: number) {
    setMinimized((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  }

  return (
    <main>
      <p className="back">
        <Link href="/">← Inventory</Link>
      </p>

      <header className="page-head">
        <h1>{device.label}</h1>
      </header>

      {editing ? (
        <DeviceCardEdit
          device={device}
          options={options}
          onDone={() => setEditing(false)}
        />
      ) : (
        <DeviceCard device={device} onEdit={() => setEditing(true)} />
      )}

      <DeviceNotes deviceId={device.id} notes={device.device_notes} />

      <div className="repairs-head">
        <h2>Bench log</h2>
        <button
          className="btn-secondary"
          disabled={startingRepair}
          onClick={() => {
            const open = device.repairs.filter((r) => !r.completed_at);
            if (
              open.length > 0 &&
              !window.confirm(
                `${open.length === 1 ? `Repair #${open[0].id} is` : `${open.length} repairs are`} still open (not completed). Start another repair on this device?`,
              )
            ) {
              return;
            }
            startTransition(async () => {
              await createRepair(device.id);
              router.refresh();
            });
          }}
        >
          {startingRepair ? "Starting…" : "+ Start repair"}
        </button>
      </div>

      {device.repairs.length === 0 ? (
        <p className="empty">
          No bench work yet — start a repair when the unit hits the bench.
        </p>
      ) : (
        device.repairs.map((repair) => (
          <section key={repair.id} className="repair-block">
            <div className="repair-head">
              {/* Status lives on the device card; here the phase track is the state. */}
              <span className="repair-title">
                Repair #{repair.id} · {formatDateTime(repair.created_at)}
              </span>
              <button
                className="btn-edit repair-minimize"
                title={minimized.has(repair.id) ? "Expand repair" : "Minimize repair"}
                onClick={() => toggleMinimized(repair.id)}
              >
                {minimized.has(repair.id) ? "▸" : "▾"}
              </button>
            </div>
            {!minimized.has(repair.id) && (
              // Notes are per-phase (2026-07-28): they live inside each phase
              // row's accordion body — there is no repair-global notes list.
              <PhaseTrack
                deviceId={device.id}
                repair={repair}
                onAddNote={(phase: PhaseKey) =>
                  setModal({
                    mode: "create",
                    repairId: repair.id,
                    phase,
                    nextPosition: nextPosition(repair.notes),
                    templates: device.note_templates.filter((t) => t.phase === phase),
                    reference: device.reference?.id ?? null,
                  })
                }
                onEditNote={(n: Note) => setModal({ mode: "edit", note: n })}
              />
            )}
          </section>
        ))
      )}

      {/* Departure history below the bench log — the timeline's natural end.
          Any state can exit (scrap a dud mid-repair, sell as-is). */}
      <Exits deviceId={device.id} exits={device.exits} options={options} />

      {modal && (
        <NoteModal
          deviceId={device.id}
          state={modal}
          onClose={() => setModal(null)}
        />
      )}

    </main>
  );
}
