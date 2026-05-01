/**
 * Tests format helpers — gestion notation scientifique + €/M€/Md€.
 *
 * Audit QA 2026-05-01 (SCRUM-NEW-14) : Explorer affichait des CA en notation
 * scientifique illisibles (`2.66540E+9`, `9.9000E+8`) car formatCell ne gérait
 * pas les strings numériques. Ce helper centralise + corrige.
 */
import { describe, it, expect } from "vitest";
import {
  parseNumericLoose,
  formatEurCompact,
  formatCompactNumber,
  formatPct,
  formatSiren,
  formatSiret,
} from "@/lib/dem/format";

describe("parseNumericLoose", () => {
  it("number stays number", () => {
    expect(parseNumericLoose(42)).toBe(42);
    expect(parseNumericLoose(3.14)).toBe(3.14);
  });

  it("scientific notation strings parsed", () => {
    expect(parseNumericLoose("2.66540E+9")).toBeCloseTo(2_665_400_000);
    expect(parseNumericLoose("9.9000E+8")).toBeCloseTo(990_000_000);
    expect(parseNumericLoose("1.5e-3")).toBeCloseTo(0.0015);
  });

  it("plain numeric strings parsed", () => {
    expect(parseNumericLoose("1234")).toBe(1234);
    expect(parseNumericLoose("3.14")).toBe(3.14);
    expect(parseNumericLoose("-50")).toBe(-50);
  });

  it("non-numeric returns null", () => {
    expect(parseNumericLoose("abc")).toBe(null);
    expect(parseNumericLoose("123abc")).toBe(null);
    expect(parseNumericLoose("")).toBe(null);
    expect(parseNumericLoose(null)).toBe(null);
    expect(parseNumericLoose(undefined)).toBe(null);
    expect(parseNumericLoose(NaN)).toBe(null);
    expect(parseNumericLoose(Infinity)).toBe(null);
  });

  it("objects returns null", () => {
    expect(parseNumericLoose({})).toBe(null);
    expect(parseNumericLoose([])).toBe(null);
  });
});

describe("formatEurCompact", () => {
  it("milliards", () => {
    expect(formatEurCompact(2_665_400_000)).toBe("2,7 Md€");
    expect(formatEurCompact("2.66540E+9")).toBe("2,7 Md€");
  });

  it("millions", () => {
    expect(formatEurCompact(285_700_000)).toBe("285,7 M€");
    expect(formatEurCompact(28_600_000)).toBe("28,6 M€");
    expect(formatEurCompact("9.9000E+8")).toBe("990,0 M€");
  });

  it("milliers", () => {
    expect(formatEurCompact(850_000)).toBe("850 K€");
    expect(formatEurCompact(1_500)).toBe("2 K€");
  });

  it("petits montants", () => {
    expect(formatEurCompact(500)).toBe("500 €");
  });

  it("négatif", () => {
    expect(formatEurCompact(-1_000_000)).toMatch(/^-1,0 M€/);
  });

  it("non-numeric retourne brut", () => {
    expect(formatEurCompact("abc")).toBe("abc");
    expect(formatEurCompact(null)).toBe("—");
    expect(formatEurCompact("")).toBe("—");
  });
});

describe("formatCompactNumber", () => {
  it("millions sans symbole", () => {
    expect(formatCompactNumber(2_500_000)).toBe("2,5M");
  });

  it("milliers en french separator", () => {
    const out = formatCompactNumber(12_345);
    // Intl français peut utiliser narrow space ; on accepte espace ou narrow no-break
    expect(out).toMatch(/12[   ]345/);
  });

  it("scientific notation parsed", () => {
    expect(formatCompactNumber("1.5E+6")).toBe("1,5M");
  });
});

describe("formatPct", () => {
  it("ratio (<=1) interprété en %", () => {
    expect(formatPct(0.17)).toBe("17,0 %");
  });

  it("déjà en %", () => {
    expect(formatPct(17)).toBe("17,0 %");
  });
});

describe("formatSiren / formatSiret (existants — non régression)", () => {
  it("formatSiren OK 9 digits", () => {
    expect(formatSiren("333275774")).toBe("333 275 774");
  });

  it("formatSiret OK 14 digits", () => {
    expect(formatSiret("33327577400012")).toBe("333 275 774 00012");
  });
});
