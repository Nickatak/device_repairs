"use client";

import { useEffect } from "react";

/**
 * Shared modal shell: overlay + panel, Escape-to-close, and "sticky" close.
 *
 * Sticky: the modal closes only when a mousedown lands directly on the overlay
 * (a deliberate press outside). It will NOT close when a drag that began inside
 * the modal — e.g. selecting text in a field — releases over the overlay.
 */
export default function Modal({
  onClose,
  children,
}: {
  onClose: () => void;
  children: React.ReactNode;
}) {
  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") onClose();
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  return (
    <div
      className="modal-overlay"
      onMouseDown={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div className="modal" role="dialog" aria-modal="true">
        {children}
      </div>
    </div>
  );
}
