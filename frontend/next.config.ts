import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  eslint: {
    // ESLint vérifié séparément en CI — ne bloque pas le build Vercel
    ignoreDuringBuilds: true,
  },
  async rewrites() {
    if (process.env.NODE_ENV === "production") {
      // In production (Vercel experimentalServices), backend is mounted at /_/backend
      return [
        {
          source: "/api/:path*",
          destination: "/_/backend/api/:path*",
        },
      ];
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
