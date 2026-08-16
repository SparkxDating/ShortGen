import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Docker uses standalone. Vercel supplies its own output handling.
  output: process.env.VERCEL ? undefined : "standalone",
  poweredByHeader: false,
};

export default nextConfig;
