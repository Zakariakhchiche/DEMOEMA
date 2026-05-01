import { defaultCache } from "@serwist/next/worker";
import type { PrecacheEntry, SerwistGlobalConfig } from "serwist";
import {
  Serwist,
  NetworkFirst,
  CacheFirst,
  ExpirationPlugin,
} from "serwist";

declare global {
  interface WorkerGlobalScope extends SerwistGlobalConfig {
    __SW_MANIFEST: (PrecacheEntry | string)[] | undefined;
  }
}

declare const self: ServiceWorkerGlobalScope & WorkerGlobalScope;

// Audit QA 2026-05-01 (G3 fix part 2) : avant, runtimeCaching utilisait
// `handler: "NetworkFirst" as any` et `"CacheFirst" as any` (cast string forcé),
// ce qui faisait throw Serwist v9+ à l'init du SW :
//   `ServiceWorker script evaluation failed`
// Correction : instancier les Strategy directement (pattern Serwist v9
// recommandé), avec ExpirationPlugin pour la rotation.
const serwist = new Serwist({
  precacheEntries: self.__SW_MANIFEST,
  skipWaiting: true,
  clientsClaim: true,
  navigationPreload: true,
  runtimeCaching: [
    // API calls — network first avec timeout 10s, cache fallback pour offline
    {
      matcher: /\/api\/.*/i,
      handler: new NetworkFirst({
        cacheName: "api-cache",
        networkTimeoutSeconds: 10,
        plugins: [
          new ExpirationPlugin({
            maxEntries: 100,
            maxAgeSeconds: 60 * 60, // 1h
          }),
        ],
      }),
    },
    // Static assets — cache first, 30 jours
    {
      matcher: /\.(?:png|jpg|jpeg|svg|gif|ico|webp|avif|woff2?)$/i,
      handler: new CacheFirst({
        cacheName: "static-assets",
        plugins: [
          new ExpirationPlugin({
            maxEntries: 100,
            maxAgeSeconds: 30 * 24 * 60 * 60, // 30j
          }),
        ],
      }),
    },
    // Defaults Next.js (HTML, JS chunks, fonts) fournis par @serwist/next
    ...defaultCache,
  ],
  fallbacks: {
    entries: [
      {
        url: "/~offline",
        matcher({ request }: { request: Request }) {
          return request.destination === "document";
        },
      },
    ],
  },
});

serwist.addEventListeners();
