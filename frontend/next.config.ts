import withSerwistInit from "@serwist/next";
import type { NextConfig } from "next";

const withSerwist = withSerwistInit({
  swSrc: "src/sw.ts",
  swDest: "public/sw.js",
  disable: process.env.NODE_ENV === "development",
});

const nextConfig: NextConfig = {
  // "standalone" produit un bundle minimal pour Docker (VPS).
  // Sur Cloudflare Workers (OpenNext), on laisse la sortie Next par défaut.
  ...(process.env.BUILD_TARGET === "docker" && { output: "standalone" as const }),
  eslint: {
    // eslint-config-next v15 uses legacy format incompatible with flat config.
    // Type checking is handled by TypeScript during build.
    ignoreDuringBuilds: true,
  },
  async rewrites() {
    // En dev : proxy vers FastAPI local (ou BACKEND_URL override).
    // En prod :
    //   - Vercel : vercel.json gère le routing (pas de rewrite ici).
    //   - Cloudflare Workers / autre : utiliser BACKEND_URL pour cibler
    //     le backend FastAPI hébergé séparément (VPS, Vercel, etc.).
    if (process.env.NODE_ENV === "production") {
      if (process.env.BACKEND_URL) {
        return [
          {
            source: "/api/:path*",
            destination: `${process.env.BACKEND_URL}/api/:path*`,
          },
        ];
      }
      return [];
    }
    const backendUrl = process.env.BACKEND_URL || "http://localhost:8000";
    return [
      {
        source: "/api/:path*",
        destination: `${backendUrl}/api/:path*`,
      },
    ];
  },
};

export default withSerwist(nextConfig);
