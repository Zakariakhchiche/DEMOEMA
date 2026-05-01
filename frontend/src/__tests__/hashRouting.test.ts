/**
 * Tests hash routing — alias FR/EN.
 *
 * Audit QA 2026-05-01 (SCRUM-119) : 6 cas où la nav cliquait sur un label FR
 * (#graphe, #comparer) mais le state ne s'update pas car VALID_MODES contenait
 * uniquement les versions EN.
 */
import { describe, it, expect } from "vitest";
import { resolveHashToMode, VALID_MODES, HASH_ALIASES } from "@/lib/hashRouting";

describe("resolveHashToMode — canonique EN", () => {
  it.each([
    "dashboard",
    "chat",
    "pipeline",
    "watchlist",
    "explorer",
    "graph",
    "compare",
    "audit",
  ])("'%s' reste sur lui-même", (raw) => {
    expect(resolveHashToMode(raw)).toBe(raw);
  });
});

describe("resolveHashToMode — alias FR", () => {
  it("'graphe' -> 'graph'", () => {
    expect(resolveHashToMode("graphe")).toBe("graph");
  });

  it("'comparer' -> 'compare'", () => {
    expect(resolveHashToMode("comparer")).toBe("compare");
  });

  it("'tableau' -> 'dashboard'", () => {
    expect(resolveHashToMode("tableau")).toBe("dashboard");
  });

  it("'home' -> 'dashboard'", () => {
    expect(resolveHashToMode("home")).toBe("dashboard");
  });

  it("'bookmark' -> 'watchlist'", () => {
    expect(resolveHashToMode("bookmark")).toBe("watchlist");
  });
});

describe("resolveHashToMode — case insensitive sur les alias", () => {
  it("'GRAPHE' -> 'graph'", () => {
    expect(resolveHashToMode("GRAPHE")).toBe("graph");
  });

  it("'Comparer' -> 'compare'", () => {
    expect(resolveHashToMode("Comparer")).toBe("compare");
  });
});

describe("resolveHashToMode — fallback dashboard", () => {
  it("hash vide → dashboard", () => {
    expect(resolveHashToMode("")).toBe("dashboard");
  });

  it("hash inconnu → dashboard", () => {
    expect(resolveHashToMode("randomstuff")).toBe("dashboard");
  });

  it("hash en majuscules d'un mode valide n'est pas accepté (canonique sensible à la casse)", () => {
    // VALID_MODES check est case-sensitive. Mais comme HASH_ALIASES.toLowerCase()
    // gère "GRAPH" via alias, il faut tester que "DASHBOARD" majuscules tombe en
    // fallback (pas d'alias DASHBOARD) → dashboard via fallback.
    expect(resolveHashToMode("DASHBOARD")).toBe("dashboard");
  });
});

describe("VALID_MODES integrity", () => {
  it("contient exactement 8 modes (8 sections nav)", () => {
    expect(VALID_MODES).toHaveLength(8);
  });

  it("ne contient AUCUN alias FR (sinon double mapping)", () => {
    expect(VALID_MODES).not.toContain("graphe");
    expect(VALID_MODES).not.toContain("comparer");
  });
});

describe("HASH_ALIASES integrity", () => {
  it("toutes les valeurs cibles sont dans VALID_MODES", () => {
    for (const target of Object.values(HASH_ALIASES)) {
      expect(VALID_MODES).toContain(target);
    }
  });

  it("inclut au moins 'graphe' et 'comparer' (cas audit)", () => {
    expect(HASH_ALIASES).toHaveProperty("graphe");
    expect(HASH_ALIASES).toHaveProperty("comparer");
  });
});
