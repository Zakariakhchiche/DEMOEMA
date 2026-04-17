import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  eslint: {
    // ESLint vérifié séparément en CI — ne bloque pas le build Vercel
    ignoreDuringBuilds: true,
  },
  async rewrites() {
    // In production, Vercel routes (vercel.json) intercept /api/* before Next.js
    // This rewrite only applies in local development
    if (process.env.NODE_ENV === "production") {
      return [];
    }
    return [
      {
        source: "/api/:path*",
        destination: "http://localhost:8000/api/:path*",
      },
    ];
  },
};

export default nextConfig;
