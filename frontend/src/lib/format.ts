// Shared presentation helpers used by the inventory table and the device page.

// Device lifecycle bands (mirrors Device.Status on the backend):
// pipeline = not in your possession; active = on the bench; good = fixed onward;
// dead = value-terminal exits.
const STATUS_BAND: Record<string, string> = {
  shipped: "band-holding",
  acquired: "band-inflight",
  in_repair: "band-inflight",
  fixed: "band-good",
  exited: "band-dead",
};

export function bandClass(status: string | null): string {
  if (!status) return "band-none";
  return STATUS_BAND[status] ?? "band-none";
}

export function formatPrice(value: string | null): string {
  if (value === null) return "—";
  return `$${Number(value).toFixed(2)}`;
}

// Date-only values (e.g. purchased_on "2026-07-21") — split by hand so the
// UTC-midnight parse can't shift the day in local time.
export function formatDate(iso: string): string {
  const [y, m, d] = iso.split("-");
  return `${Number(m)}/${Number(d)}/${y}`;
}

// All timestamps render date + H:MM AM/PM (Nick, 2026-07-21).
export function formatDateTime(iso: string): string {
  return new Date(iso).toLocaleString([], {
    month: "numeric",
    day: "numeric",
    year: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}
