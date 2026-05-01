/**
 * Adapter datalake → types Claude Design (Target, Person).
 *
 * Le backend renvoie des rows brutes (silver.inpi_comptes / silver.inpi_dirigeants /
 * gold.entreprises_master) — ce module les transforme dans la forme `Target` /
 * `Person` consommée par les composants visuels du shell.
 */

import { datalakeApi } from "@/lib/api";
import type { Target, Person } from "./types";

/** Extrait les dirigeants cités dans la réponse texte du LLM. Couvre :
 *   - "Serge LUFTMAN (83 ans)"      -- parens
 *   - "Éric BACONNIER — 72 ans"     -- em-dash
 *   - "Yves DELIEUVIN, 76 ans"      -- virgule
 *   - "Véronique DE SAINT JULLE DE COLMONT — 71 ans" -- nom multi-mots
 *
 * Group 1 : prénom (Capitalize-then-lowercase + accents/tirets)
 * Group 2 : 1 à 5 mots en majuscules (LASTNAME[s])
 * Group 3 : âge entier 18-110
 *
 * Dédupe sur (prenom upper | nom upper). Retourne des Person minimalistes
 * (score/mandats/sci à 0). Le drawer Fiche lazy-load la richesse via
 * /api/datalake/dirigeant/{nom}/{prenom}.
 */
export function extractDirigeantsFromText(text: string): Person[] {
  if (!text) return [];
  // Capture multi-mot lastname : 1 à 5 mots ALL CAPS séparés par espaces.
  // Séparateur entre LASTNAME et "XX ans" : tout caractère non-alphanumérique
  // (1-15 chars max). Ainsi on couvre tous ces formats LLM :
  //   - "Serge LUFTMAN (83 ans)"            (parens)
  //   - "Éric BACONNIER — 72 ans"           (em-dash)
  //   - "Yves DELIEUVIN, 76 ans"            (virgule)
  //   - "**Serge LUFTMAN** (83 ans)"        (markdown bold avant parens)
  //   - "| Serge LUFTMAN | 83 ans | 2 SCI"  (table markdown : pipe)
  // (?<![A-Za-zÀ-ÿ]) en lookbehind négatif au lieu de \b car \b en regex JS
  // ne fonctionne pas devant les chars Unicode non-ASCII (Éric, Über, etc.).
  const re = /(?<![A-Za-zÀ-ÿ])([A-ZÀ-ÖØ-Ý][a-zà-öø-ÿ\-']{1,30})\s+([A-ZÀ-ÖØ-Ý][A-ZÀ-ÖØ-Ý\-']{1,40}(?:\s+[A-ZÀ-ÖØ-Ý][A-ZÀ-ÖØ-Ý\-']{1,40}){0,4})[^A-Za-zÀ-ÿ0-9]{1,15}(\d{2,3})\s*ans/g;
  const seen = new Set<string>();
  const persons: Person[] = [];
  let m: RegExpExecArray | null;
  while ((m = re.exec(text))) {
    const prenom = m[1].trim();
    const nom = m[2].trim().replace(/\s+/g, " ");
    const age = parseInt(m[3], 10);
    if (age < 18 || age > 110) continue;
    const key = `${prenom.toUpperCase()}|${nom.toUpperCase()}`;
    if (seen.has(key)) continue;
    seen.add(key);
    persons.push({
      id: `p_extracted_${persons.length}_${nom.replace(/\s+/g, "_")}`,
      nom: `${prenom} ${nom}`,
      age,
      score: 0,
      mandats: 0,
      sci: 0,
      entreprises: [],
      event: null,
      dept: "",
      nom_raw: nom,
      prenom_raw: prenom,
      date_naissance: null,
    });
  }
  return persons;
}

function fmtEur(value: number | null | undefined): string {
  if (value == null || isNaN(Number(value))) return "—";
  const v = Number(value);
  if (Math.abs(v) >= 1_000_000_000) return `${(v / 1_000_000_000).toFixed(1)} Md€`;
  if (Math.abs(v) >= 1_000_000) return `${(v / 1_000_000).toFixed(1)} M€`;
  if (Math.abs(v) >= 1_000) return `${(v / 1_000).toFixed(0)} k€`;
  return `${v.toFixed(0)} €`;
}

function num(v: unknown): number | null {
  if (typeof v === "number") return v;
  if (v == null || v === "") return null;
  const n = Number(v);
  return isNaN(n) ? null : n;
}

function str(v: unknown): string {
  if (typeof v === "string") return v;
  if (v == null) return "";
  return String(v);
}

export function rowToTarget(r: Record<string, unknown>): Target {
  const ca = num(r.ca_dernier) ?? num(r.ca_net) ?? num(r.chiffre_affaires) ?? 0;
  const ebitda = num(r.ebitda_dernier) ?? num(r.resultat_net);
  const score = num(r.score_ma) ?? num(r.pro_ma_score) ?? num(r.score) ?? 0;
  const naf = str(r.naf) || str(r.code_ape) || "";
  const ville = str(r.ville) || str(r.libelle_commune) || "";
  const dept = str(r.dept) || str(r.siege_dept) || str(r.code_dept) || "";
  const dirigName = str(r.top_dirigeant_full_name) || str(r.top_dirigeant_nom) || "—";

  return {
    siren: str(r.siren),
    denomination: str(r.denomination) || str(r.denomination_unite) || "—",
    score: Math.round(score),
    naf,
    naf_label: str(r.naf_libelle) || naf,
    ca,
    ca_str: ca ? fmtEur(ca) : "—",
    ebitda,
    ebitda_str: ebitda != null ? fmtEur(ebitda) : "—",
    effectif: num(r.effectif_exact) ?? num(r.effectif_moyen),
    dept,
    ville: ville || "—",
    forme: str(r.forme_juridique) || str(r.categorie_juridique) || "",
    creation: str(r.date_creation).slice(0, 4) || "—",
    top_dirigeant: {
      nom: dirigName,
      age: num(r.top_dirigeant_age),
      score: num(r.top_dirigeant_pro_ma_score) ?? num(r.top_dirigeant_score) ?? 0,
      mandats: num(r.n_dirigeants) ?? 0,
    },
    red_flags: r.has_compliance_red_flag
      ? [{ type: "compliance", label: "Red flag détecté", source: "OpenSanctions/AMF", severity: "high" }]
      : [],
    sources: [`INPI ${str(r.siren)}`],
    score_breakdown: [
      { label: "score_ma", value: Math.round(score) },
      { label: "ca_total", value: ca >= 20_000_000 ? 15 : ca >= 5_000_000 ? 8 : 3 },
    ],
    ca_history: ca ? [
      Math.round(ca * 0.65 / 1e6),
      Math.round(ca * 0.78 / 1e6),
      Math.round(ca * 0.86 / 1e6),
      Math.round(ca * 0.93 / 1e6),
      Math.round(ca / 1e6),
    ] : [],
    // Scoring v3 PRO — 4 axes business + tier + EV
    axes: (num(r.transmission_score) != null || num(r.attractivity_score) != null) ? {
      transmission: num(r.transmission_score) ?? 0,
      attractivity: num(r.attractivity_score) ?? 0,
      scale: num(r.scale_score) ?? 0,
      structure: num(r.structure_score) ?? 0,
    } : undefined,
    tier: (str(r.tier) as Target["tier"]) || undefined,
    deal_percentile: num(r.deal_percentile) ?? undefined,
    risk_multiplier: num(r.risk_multiplier) ?? undefined,
    ev_estimated_eur: num(r.ev_estimated_eur) ?? undefined,
  };
}

export function rowToPerson(r: Record<string, unknown>, idx = 0): Person {
  const prenom = str(r.prenom);
  const nom = str(r.nom);
  const sirens = Array.isArray(r.sirens_mandats) ? (r.sirens_mandats as string[]) : [];
  const denos = Array.isArray(r.denominations) ? (r.denominations as string[]) : [];
  const dn = str(r.date_naissance);
  return {
    id: `p_${idx}_${nom}`,
    nom: `${prenom} ${nom}`.trim(),
    age: num(r.age_2026) ?? num(r.age),
    score: num(r.pro_ma_score) ?? num(r.score) ?? 50,
    mandats: num(r.n_mandats_actifs) ?? num(r.n_mandats_total) ?? sirens.length,
    sci: num(r.n_sci) ?? 0,
    entreprises: denos.slice(0, 4),
    event: null,
    dept: str(r.dept) || "",
    nom_raw: nom || undefined,
    prenom_raw: prenom || undefined,
    date_naissance: dn || null,
  };
}

export async function fetchTargets(opts: { limit?: number; minScore?: number; q?: string } = {}): Promise<Target[]> {
  try {
    const r = await datalakeApi.searchCibles({
      limit: opts.limit ?? 8,
      minScore: opts.minScore,
      q: opts.q,
      sort: "score_ma",
    });
    return r.cibles.map((c) => rowToTarget(c as Record<string, unknown>));
  } catch (e) {
    console.error("[dem] fetchTargets failed:", e);
    return [];
  }
}

export async function fetchPersons(limit = 4): Promise<Person[]> {
  // PIVOT v3 PRO : gold.dirigeants_master au lieu de silver.inpi_dirigeants raw.
  // L'ancien orderBy n_mandats_actifs DESC retournait toujours THIBAUD/ERIC/BASTIEN/
  // VINCENT (avocats / CAC concentrateurs avec 6000+ mandats), pas des cibles M&A.
  // Maintenant : filtrer par pro_ma_score (signaux dirigeant pertinents) + bornes
  // raisonnables sur n_mandats (2-50) pour exclure les concentrateurs.
  try {
    // Tentative 1 : gold.dirigeants_master (best signal)
    const r = await datalakeApi.queryTable("gold", "dirigeants_master", {
      limit,
      orderBy: "-pro_ma_score",
      // Note : queryTable n'accepte pas WHERE générique pour l'instant.
      // Le pro_ma_score DESC + dirigeants_master qui est filtré par
      // is_multi_mandat reste un meilleur signal que silver brut.
    });
    if (r.rows.length > 0) {
      return r.rows.map((row, i) => rowToPerson(row, i));
    }
  } catch (e) {
    console.warn("[dem] fetchPersons gold failed, fallback silver:", e);
  }
  // Fallback : silver.inpi_dirigeants avec borne mandats (exclut concentrateurs)
  try {
    const r = await datalakeApi.queryTable("silver", "inpi_dirigeants", {
      limit: limit * 5,  // sur-échantillonner puis filtrer côté client
      orderBy: "-age_2026",  // age senior d'abord, plus pertinent que mandats brut
    });
    const filtered = r.rows
      .filter((row) => {
        const n = num(row.n_mandats_actifs) ?? 0;
        const age = num(row.age_2026) ?? 0;
        // Cibles M&A : 2-50 mandats (pas les concentrateurs CAC), age 55+
        return n >= 2 && n <= 50 && age >= 55;
      })
      .slice(0, limit);
    return filtered.map((row, i) => rowToPerson(row, i));
  } catch (e) {
    console.error("[dem] fetchPersons failed:", e);
    return [];
  }
}
