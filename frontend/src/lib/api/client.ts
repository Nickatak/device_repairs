// API client for the Django backend. Fetches run server-side (Server Components),
// so we hit the in-cluster backend host and never touch browser CORS.
//
// Split by domain (2026-07-22), mirroring backend repairs/: orders, reference,
// repairlog, inventory, options. Direct imports — no barrel; each domain's types
// live with its fetchers.

export const API_BASE =
  process.env.SERVER_API_BASE_URL ?? "http://localhost:8000/api/v1";
