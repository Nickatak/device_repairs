import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Dev server trusts only localhost origins by default; without these, pages
  // served via Caddy (repairs.home.arpa) or the LAN IP get their HMR socket
  // blocked and the dev client reload-loops, which eats every click.
  allowedDevOrigins: ["repairs.home.arpa", "10.20.0.110"],
};

export default nextConfig;
