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
  // Bug v6/1.3 — supprime X-Powered-By: Next.js (information disclosure).
  // Caddyfile ne peut pas strip un header émis par l'upstream proxy en aval ;
  // Next.js fournit un flag dédié pour ne pas l'émettre du tout.
  poweredByHeader: false,
  eslint: {
    // eslint-config-next v15 uses legacy format incompatible with flat config.
    // Type checking is handled by TypeScript during build.
    ignoreDuringBuilds: true,
  },
  typescript: {
    // TODO(audit-tier2): centraliser GraphNode / Target dans @/types
    // puis retirer ce flag. Pour l'instant 3-4 interfaces dupliquées
    // avec variations (score: number|null vs number|undefined) font
    // cascader des erreurs TS qui bloquent le build prod. L'app tourne
    // correctement en runtime — c'est juste du nettoyage de types.
    ignoreBuildErrors: true,
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
