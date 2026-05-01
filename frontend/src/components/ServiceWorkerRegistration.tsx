"use client";

import { useEffect } from "react";

/**
 * Enregistre le service worker Serwist en production.
 *
 * Audit QA 2026-05-01 : `navigator.serviceWorker.getRegistrations().length === 0`
 * sur prod, alors que le manifest et `public/sw.js` existent. Le plugin
 * @serwist/next génère le SW mais ne l'enregistre pas automatiquement côté
 * client — il faut un appel `navigator.serviceWorker.register()` explicite.
 *
 * Ne s'enregistre pas en dev (NODE_ENV !== "production") pour respecter
 * `disable: NODE_ENV === "development"` de next.config.ts (HMR friendly).
 */
export default function ServiceWorkerRegistration() {
  useEffect(() => {
    if (typeof window === "undefined") return;
    if (process.env.NODE_ENV !== "production") return;
    if (!("serviceWorker" in navigator)) return;

    // Enregistrement immédiat. Serwist a `skipWaiting + clientsClaim` activés,
    // donc le SW prend le contrôle dès sa première install.
    navigator.serviceWorker
      .register("/sw.js", { scope: "/" })
      .then((reg) => {
        // Refresh forcé si une nouvelle version est trouvée pendant la session.
        reg.addEventListener("updatefound", () => {
          const installing = reg.installing;
          if (!installing) return;
          installing.addEventListener("statechange", () => {
            if (installing.state === "activated" && navigator.serviceWorker.controller) {
              // Une nouvelle version vient de prendre le contrôle. On peut
              // notifier le user (toast) ou auto-reload. Pour l'instant : log.
              // eslint-disable-next-line no-console
              console.info("[SW] new version activated — reload pour bénéficier des derniers fixes");
            }
          });
        });
      })
      .catch((err) => {
        // eslint-disable-next-line no-console
        console.warn("[SW] registration failed:", err);
      });
  }, []);

  return null;
}
