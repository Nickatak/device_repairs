// Global keyboard rule (Nick, 2026-07-28): plain Enter never submits a form —
// in a textarea it stays a newline, in a single-line input it does nothing
// (no implicit submission). Ctrl+Enter (Cmd+Enter on Mac) is the universal
// "save" from anywhere inside the form. Attach to every <form> as onKeyDown;
// inline (non-form) editors implement the same contract by hand.
export function formEnterGuard(e: React.KeyboardEvent<HTMLFormElement>) {
  if (e.key !== "Enter") return;
  if (e.ctrlKey || e.metaKey) {
    e.preventDefault();
    e.currentTarget.requestSubmit();
    return;
  }
  if ((e.target as HTMLElement).tagName === "INPUT") {
    e.preventDefault();
  }
}
