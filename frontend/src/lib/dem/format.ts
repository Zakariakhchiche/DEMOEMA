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
