import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // `standalone` produit un bundle minimal (server.js + deps) pour l'image
  // Docker VPS. Activé seulement si BUILD_TARGET=docker pour ne pas
  // impacter les builds Vercel.
  ...(process.env.BUILD_TARGET === "docker" && { output: "standalone" as const }),
  eslint: {
    // ESLint vérifié séparément en CI — ne bloque pas le build Vercel
    ignoreDuringBuilds: true,
  },
  async rewrites() {
    const backendUrl =
      process.env.NEXT_PUBLIC_BACKEND_URL ||
      (process.env.NODE_ENV === "production"
        ? "https://demoema.onrender.com"
        : "http://localhost:8000");
    return [
      {
        source: "/api/:path*",
        destination: `${backendUrl}/api/:path*`,
      },
    ];
  },
};

export default nextConfig;
