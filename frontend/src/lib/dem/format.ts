// Format helpers DEMOEMA — affichages standards INSEE / M&A.

/**
 * Formatte un SIREN au format INSEE officiel "XXX XXX XXX".
 * Tolérant : retourne la chaîne brute si pas 9 chiffres.
 */
export function formatSiren(siren: string | null | undefined): string {
  if (!siren) return "—";
  const digits = String(siren).replace(/\D/g, "");
  if (digits.length !== 9) return String(siren);
  return `${digits.slice(0, 3)} ${digits.slice(3, 6)} ${digits.slice(6, 9)}`;
}

/**
 * Formatte un SIRET au format INSEE "XXX XXX XXX XXXXX".
 */
export function formatSiret(siret: string | null | undefined): string {
  if (!siret) return "—";
  const digits = String(siret).replace(/\D/g, "");
  if (digits.length !== 14) return String(siret);
  return `${digits.slice(0, 3)} ${digits.slice(3, 6)} ${digits.slice(6, 9)} ${digits.slice(9, 14)}`;
}

const SCI_NUM_RE = /^-?\d+(\.\d+)?[eE][+-]?\d+$/;

/**
 * Convertit en number si l'input est une string numérique (incl. notation
 * scientifique 2.66E+9). Retourne null si non numérique.
 *
 * Audit QA 2026-05-01 : l'Explorer recevait des CA en notation scientifique
 * depuis Postgres numeric (`2.66540E+9`) — illisible. Ce helper normalise.
 */
export function parseNumericLoose(v: unknown): number | null {
  if (typeof v === "number") return Number.isFinite(v) ? v : null;
  if (typeof v !== "string") return null;
  const s = v.trim();
  if (!s) return null;
  if (SCI_NUM_RE.test(s) || /^-?\d+(\.\d+)?$/.test(s)) {
    const n = Number(s);
    return Number.isFinite(n) ? n : null;
  }
  return null;
}

/**
 * Format compact € — humanisé pour les UI de scan rapide.
 *   2_665_400_000 -> "2,7 Md€"
 *   285_700_000   -> "285,7 M€"
 *   28_600_000    -> "28,6 M€"
 *   850_000       -> "850 K€"
 *   1_500         -> "1 500 €"
 *
 * Si l'input n'est pas numérique, retourne la chaîne brute.
 */
export function formatEurCompact(v: unknown): string {
  const n = parseNumericLoose(v);
  if (n === null) return v == null || v === "" ? "—" : String(v);
  const abs = Math.abs(n);
  const sign = n < 0 ? "-" : "";
  if (abs >= 1_000_000_000) {
    return `${sign}${(abs / 1_000_000_000).toFixed(1).replace(".", ",")} Md€`;
  }
  if (abs >= 1_000_000) {
    return `${sign}${(abs / 1_000_000).toFixed(1).replace(".", ",")} M€`;
  }
  if (abs >= 1_000) {
    return `${sign}${Math.round(abs / 1_000)} K€`;
  }
  return `${sign}${Math.round(abs).toLocaleString("fr-FR")} €`;
}

/**
 * Format compact d'un nombre (sans suffixe €). Utile pour effectifs, mandats…
 */
export function formatCompactNumber(v: unknown): string {
  const n = parseNumericLoose(v);
  if (n === null) return v == null || v === "" ? "—" : String(v);
  if (Math.abs(n) >= 1_000_000) return `${(n / 1_000_000).toFixed(1).replace(".", ",")}M`;
  if (Math.abs(n) >= 1_000) return n.toLocaleString("fr-FR");
  return String(Math.round(n));
}

/**
 * Format pourcentage. Accepte ratio (0.17) ou déjà-pourcent (17).
 * Heuristique : si abs(v) <= 1, on suppose un ratio.
 */
export function formatPct(v: unknown): string {
  const n = parseNumericLoose(v);
  if (n === null) return v == null ? "—" : String(v);
  const pct = Math.abs(n) <= 1 ? n * 100 : n;
  return `${pct.toFixed(1).replace(".", ",")} %`;
}
