import { describe, it, expect } from "vitest";

function classify(text: string) {
  const lower = text.toLowerCase();
  const isCompare = /compare|vs|versus/i.test(text);
  const isSiren = /^\d{8,9}$/.test(text.trim());
  const isDirigeants = /dirigeant|holding|patrimoine/i.test(text);
  const isDD = /\bdd\b|compliance|due diligence/i.test(lower);
  const SOURCING_KEYWORDS = /(cible|cibles|trouve|liste|sourcing|recherche|score m&a|score >|tech|chimie|santé|industrie|btp|naval|transport|saas|fintech|leader|pme|eti|mécanique|biotech|agroalim|finance|assurance|im[mn]o|retail|logistique|e-?commerce)/i;
  const HAS_DEPT = /\b(7[5-8]|9[1-5]|13|33|59|69|44|31|34|2[ABab]|paca|ile-?de-?france|idf|bretagne|auvergne|aquitaine|provence|hauts-?de-?france|grand est|normandie|occitanie|pdl)\b/i;
  const ACTION_WORDS = /\b(compare|vs|versus|trouve|liste|cible|cibles|recherche|sourcing|score|combien|pourquoi|quoi|qui|quand|comment|aide|help|dirigeant|patrimoine|dd|compliance|diligence)\b/i;
  const wordCount = text.trim().split(/\s+/).length;
  const hasCapName = /\b[A-ZÀ-ÖØ-Ý][A-Za-zÀ-ÖØ-öø-ÿ'’\-]{2,}/.test(text);
  const isCompanyLookup = !isSiren && !isCompare && !isDirigeants && !isDD &&
    wordCount <= 5 && hasCapName && !ACTION_WORDS.test(text) &&
    !SOURCING_KEYWORDS.test(text);
  const isSourcingIntent = isSiren || isCompare || isCompanyLookup ||
    SOURCING_KEYWORDS.test(text) || HAS_DEPT.test(text);
  return { isSiren, isCompanyLookup, isSourcingIntent, isCompare, isDirigeants, isDD };
}

describe("ChatPanel company-name detection", () => {
  it.each([
    ["Capgemini"],
    ["TotalEnergies"],
    ["Carrefour"],
    ["L'OREAL"],
    ["Société Générale"],
    ["BNP Paribas"],
    ["Renault SA"],
    ["EDF"],
  ])("isCompanyLookup is true for %s", (q) => {
    const r = classify(q);
    expect(r.isCompanyLookup, `expected isCompanyLookup for "${q}"`).toBe(true);
    expect(r.isSourcingIntent).toBe(true);
  });

  it.each([
    ["479766842"],                         // SIREN
    ["compare Capgemini vs Sopra"],        // compare
    ["trouve des cibles tech"],            // sourcing keyword
    ["cibles IDF score > 80"],             // sourcing + dept
    ["dirigeants Renault"],                // dirigeants
    ["DD compliance Total"],               // dd
    ["pourquoi mes cibles sont vides"],    // action word
    ["combien de cibles"],                 // action word + sourcing
    ["trouve moi Capgemini"],              // action word
    ["aide"],                              // action word
    ["compare"],                           // bare action
  ])("isCompanyLookup is false for %s", (q) => {
    const r = classify(q);
    expect(r.isCompanyLookup, `did not expect isCompanyLookup for "${q}"`).toBe(false);
  });

  it("SIREN goes to isSiren branch", () => {
    expect(classify("479766842").isSiren).toBe(true);
  });

  it("compare query goes to isCompare branch (not isCompanyLookup)", () => {
    const r = classify("compare Capgemini vs Sopra");
    expect(r.isCompare).toBe(true);
    expect(r.isCompanyLookup).toBe(false);
  });
});
