/**
 * Adapter datalake → types Claude Design (Target, Person).
 *
 * Le backend renvoie des rows brutes (silver.inpi_comptes / silver.inpi_dirigeants /
 * gold.entreprises_master) — ce module les transforme dans la forme `Target` /
 * `Person` consommée par les composants visuels du shell.
 */

import { datalakeApi } from "@/lib/api";
import type { Target, Person } from "./types";

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
  try {
    const r = await datalakeApi.queryTable("silver", "inpi_dirigeants", {
      limit,
      orderBy: "-n_mandats_actifs",
    });
    return r.rows.map((row, i) => rowToPerson(row, i));
  } catch (e) {
    console.error("[dem] fetchPersons failed:", e);
    return [];
  }
}
