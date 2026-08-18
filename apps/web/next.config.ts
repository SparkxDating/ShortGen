import type { NextConfig } from "next";

const apiInternal = process.env.API_INTERNAL_URL || "http://127.0.0.1:8000";

const nextConfig: NextConfig = {
  // Docker uses standalone. Vercel supplies its own output handling.
  output: process.env.VERCEL ? undefined : "standalone",
  poweredByHeader: false,
  async rewrites() {
    return [
      { source: "/api/:path*", destination: `${apiInternal}/api/:path*` },
      { source: "/storage/:path*", destination: `${apiInternal}/storage/:path*` },
    ];
  },
};

export default nextConfig;
