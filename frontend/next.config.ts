import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  /* config options here */
  output: "standalone",
  cacheComponents: true,
  partialPrefetching: true,
  // Development only: production routes /api to Django in the reverse proxy.
  async rewrites() {
    if (process.env.NODE_ENV === "production") return [];
    const target = process.env.API_INTERNAL_URL ?? "http://127.0.0.1:8000";
    return [{ source: "/api/:path*", destination: `${target}/api/:path*` }];
  },
  turbopack: {
    rules: {
      "*.css": {
        loaders: ["@tailwindcss/turbopack"],
        as: "*.css",
      },
    },
  },
};

export default nextConfig;
