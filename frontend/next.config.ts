import type { NextConfig } from "next";

// Django origin for the /media/ proxy — SERVER_API_BASE_URL minus its /api/v1 path.
const backendOrigin = new URL(
  process.env.SERVER_API_BASE_URL ?? "http://localhost:8000/api/v1",
).origin;

const nextConfig: NextConfig = {
  // Dev server trusts only localhost origins by default; without these, pages
  // served via Caddy (repairs.home.arpa) or the LAN IP get their HMR socket
  // blocked and the dev client reload-loops, which eats every click.
  allowedDevOrigins: ["repairs.home.arpa", "10.20.0.110"],
  // Uploaded repair photos live on the backend; proxying keeps image URLs
  // same-origin in the browser (no per-instance backend host in the payload).
  async rewrites() {
    return [{ source: "/media/:path*", destination: `${backendOrigin}/media/:path*` }];
  },
};

export default nextConfig;
