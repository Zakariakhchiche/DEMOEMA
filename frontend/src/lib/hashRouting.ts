/**
 * Hash routing helpers — extrait de app/page.tsx pour testabilité.
 *
 * Audit QA 2026-05-01 (SCRUM-119) : la nav UI affiche les labels FR (Graphe,
 * Comparer) qui produisaient les hashes #graphe / #comparer absents de
 * VALID_MODES → fallback silencieux vers "dashboard" (25 % de la nav non
 * fonctionnelle). On accepte FR et EN.
 */

import type { Mode } from "@/lib/dem/types";

export const VALID_MODES: Mode[] = [
  "dashboard",
  "chat",
  "pipeline",
  "watchlist",
  "explorer",
  "graph",
  "compare",
  "audit",
];

export const HASH_ALIASES: Record<string, Mode> = {
  // FR -> EN canonique
  graphe: "graph",
  comparer: "compare",
  // Alias defensifs
  tableau: "dashboard",
  home: "dashboard",
  bookmark: "watchlist",
};

/**
 * Convertit un raw hash (sans le `#`) en Mode valide. Fallback dashboard.
 * SSR-safe : si window indéfini, retourne "dashboard".
 */
export function resolveHashToMode(rawHash: string): Mode {
  const norm = rawHash.toLowerCase();
  const alias = HASH_ALIASES[norm];
  if (alias) return alias;
  return VALID_MODES.includes(rawHash as Mode) ? (rawHash as Mode) : "dashboard";
}

export function readHashMode(): Mode {
  if (typeof window === "undefined") return "dashboard";
  const raw = window.location.hash.replace("#", "");
  return resolveHashToMode(raw);
}
