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
/** Extrait la personne FOCUS d'une question utilisateur (pas d'une réponse LLM).
 *
 * Couvre 4 conventions de casse que les utilisateurs tapent :
 *   - LLM-style :        "Bernard ARNAULT", "Profil d'Éric BACONNIER"
 *   - Title case :       "Vincent Lamour", "fiche de Bernard Arnault"
 *   - all lowercase :    "qui est vincent lamour" ← utilisateur pressé
 *   - all UPPER :        "VINCENT LAMOUR"
 *
 * Stratégie :
 *   1. Pattern strict "Prénom NOMCAPS" (LLM-style) — capté en premier sans
 *      ambiguïté.
 *   2. Sinon, on cherche un marqueur d'intention ("qui est", "fiche de",
 *      "profil de", "infos sur", etc.) et on extrait les 2-3 mots qui suivent
 *      comme candidat nom — peu importe la casse.
 *   3. Sinon, fallback sur 2 mots Title/Title ("Vincent Lamour" sans intent).
 *
 * Returns la 1re personne détectée. Backend route `/api/datalake/dirigeant/`
 * normalise déjà côté Python (UPPER + strip accents), donc on renvoie la
 * casse originale ; PersonSheet drawer fera le reste.
 */
/** Mots qui trahissent un nom d'entreprise quand ils apparaissent dans
 * candidate.nom ou candidate.prenom — utilisé pour rejeter "ATRIUM PATRIMOINE",
 * "MESANGE CAPITAL", "MAISON LAMOUR", etc. dans extractFocusPersonFromQuery
 * (ils tomberont alors dans extractFocusEntrepriseFromQuery). */
const CORPORATE_SUFFIX_TOKENS = new Set([
  "patrimoine", "capital", "holding", "holdings", "groupe", "group",
  "société", "societe", "compagnie", "company", "industries", "industrie",
  "finance", "finances", "investissement", "investissements", "invest",
  "consulting", "conseil", "conseils", "services", "service",
  "immobilier", "immobiliere", "immobiliers",
  "sci", "sas", "sasu", "sarl", "eurl", "snc", "sa",
  "association", "fondation", "fonds",
  "banque", "assurance", "assurances",
  "energie", "energies", "telecom", "telecoms",
  "international", "france", "europe", "monde",
  "gestion", "management", "partners", "partenaires",
  "technologie", "technologies", "tech", "labs", "lab",
  "solutions", "solution", "systems", "system", "studio", "studios",
  "media", "medias", "edition", "editions",
  "immobiliere", "patrimoines",
]);

export function extractFocusPersonFromQuery(text: string): { nom: string; prenom: string; dateNaissance?: string } | null {
  if (!text || text.length < 5 || text.length > 500) return null;

  // Capture optionnelle de l'année de naissance pour disambiguer homonymes.
  // Ex: "vincent lamour né en 1974" -> 1974. Backend silver fait LIKE '1974%'
  // donc match les formats 1974, 1974-04-12, etc. CRITIQUE: silver.inpi_dirigeants
  // a 6 Vincent LAMOUR distincts (clé d'unicité = nom+prenom+date_naissance).
  // Sans date, le tie-breaker prend un autre Vincent et la fiche affiche
  // 1 mandat + Pascale NICOL au lieu de 23 mandats + Estelle DUBERNARD.
  const reYear = /\b(?:né\(?e?\)?|nee?|ne|born)\s+(?:en|le|in|à)?\s*(?:\d{1,2}[\/\-\s])*(\d{4})\b/i;
  const mYear = reYear.exec(text);
  const dateNaissance = mYear?.[1];

  const blacklist = new Set([
    "donne", "liste", "fiche", "profil", "recherche", "cherche", "trouve",
    "demoema", "compare", "bonjour", "merci", "salut", "explique", "voici",
    "qui", "est", "sont", "le", "la", "les", "un", "une", "des", "de", "du",
    "pour", "avec", "sans", "sur", "sous", "dans", "par", "mon", "ma", "mes",
    "tu", "tes", "ton", "ta", "il", "elle", "on", "nous", "vous", "ils",
    "ce", "cet", "cette", "ces", "moi", "toi", "et", "ou", "mais", "donc",
    "au", "aux", "que", "qui", "comment", "pourquoi", "quand", "où",
  ]);

  const hasCorporateToken = (s: string): boolean => {
    return s.toLowerCase().split(/[\s\-']+/).some(t => CORPORATE_SUFFIX_TOKENS.has(t));
  };

  const isPersonName = (prenom: string, nom: string): boolean => {
    if (prenom.length < 2 || prenom.length > 30) return false;
    if (nom.length < 2 || nom.length > 60) return false;
    if (blacklist.has(prenom.toLowerCase())) return false;
    if (blacklist.has(nom.toLowerCase().split(" ")[0])) return false;
    // Reject si l'un des tokens trahit une entreprise (PATRIMOINE, CAPITAL, SCI…).
    // L'extraction entreprise prendra alors le relai.
    if (hasCorporateToken(prenom) || hasCorporateToken(nom)) return false;
    // Nom doit contenir uniquement lettres/-/'/espace
    if (!/^[A-Za-zÀ-ÿ\-' ]+$/.test(prenom)) return false;
    if (!/^[A-Za-zÀ-ÿ\-' ]+$/.test(nom)) return false;
    return true;
  };

  // Strippe les suffixes "né en 1974" / "née le 12 mars" / "born in 1974"
  // qui polluent le nom quand le user tape "qui est vincent lamour né en 1974".
  // Sans ce strip, mIntent[2] = "lamour né en" et /dirigeant/lamour%20né%20en
  // remonte 404 + PersonCard reste à "—".
  const stripDateSuffix = (s: string): string => {
    return s
      .replace(/\s+(?:né\(e\)|née?|ne|nee|born)\s+.*$/i, "")
      .trim();
  };

  // 1. LLM-style strict : "Prénom NOMCAPS" — peut apparaître au milieu d'une
  //    phrase ("Profil compliance et reseau de Bernard ARNAULT").
  const reLLM = /(?<![A-Za-zÀ-ÿ])([A-ZÀ-ÖØ-Ý][a-zà-öø-ÿ\-']{1,30})\s+([A-ZÀ-ÖØ-Ý][A-ZÀ-ÖØ-Ý\-']{1,40}(?:\s+[A-ZÀ-ÖØ-Ý][A-ZÀ-ÖØ-Ý\-']{1,40}){0,3})(?![A-Za-zÀ-ÿ])/;
  const mLLM = reLLM.exec(text);
  if (mLLM) {
    const prenom = mLLM[1].trim();
    const nom = stripDateSuffix(mLLM[2].trim().replace(/\s+/g, " "));
    if (isPersonName(prenom, nom)) return { nom, prenom, ...(dateNaissance && { dateNaissance }) };
  }

  // 2. Intent-based : extraction après marqueur d'intention (case-insensitive).
  //    Couvre "qui est vincent lamour", "fiche de Bernard Arnault", "profil
  //    d'Éric Baconnier", "le dirigeant Roland Favier", etc.
  const reIntent = /(?:qui\s+(?:est|sont)|fiche\s+(?:de|du|d'|détaillée\s+de)|profil\s+(?:de|du|d'|complet\s+de|compliance\s+(?:de|d'))|(?:le\s+)?dirigeant|infos?\s+sur|recherche|cherche|trouve|donne[ -]moi(?:\s+(?:la\s+fiche|le\s+profil|les?\s+infos))?\s+(?:de|sur|pour|du|d')|montre[ -]moi(?:\s+la\s+fiche)?\s+(?:de|d')|parle[ -]moi\s+de|connais|associes?\s+(?:de|d')|reseau\s+(?:de|d')|r[éeèê]seau\s+(?:de|d')|entourage\s+(?:de|d'))\s+(?:l['ea]\s+)?([A-Za-zÀ-ÿ][A-Za-zÀ-ÿ\-']{1,30})\s+([A-Za-zÀ-ÿ][A-Za-zÀ-ÿ\-']{1,40}(?:\s+[A-Za-zÀ-ÿ][A-Za-zÀ-ÿ\-']{1,40}){0,2})(?![A-Za-zÀ-ÿ])/i;
  const mIntent = reIntent.exec(text);
  if (mIntent) {
    const prenom = mIntent[1].trim();
    const nom = stripDateSuffix(mIntent[2].trim().replace(/\s+/g, " "));
    if (isPersonName(prenom, nom)) return { nom, prenom, ...(dateNaissance && { dateNaissance }) };
  }

  // 3. Fallback : 2 mots Title-case consécutifs (Vincent Lamour) sans intent.
  //    Plus risqué de faux-positif → on n'autorise QUE Title+Title (pas
  //    lowercase pure car ambigu : "il pense que" matcherait).
  const reTitle = /(?<![A-Za-zÀ-ÿ])([A-ZÀ-ÖØ-Ý][a-zà-öø-ÿ\-']{2,30})\s+([A-ZÀ-ÖØ-Ý][a-zà-öø-ÿ\-']{2,40})(?![A-Za-zÀ-ÿ])/;
  const mTitle = reTitle.exec(text);
  if (mTitle) {
    const prenom = mTitle[1].trim();
    const nom = stripDateSuffix(mTitle[2].trim());
    if (isPersonName(prenom, nom)) return { nom, prenom, ...(dateNaissance && { dateNaissance }) };
  }

  return null;
}

/** Extrait le nom d'entreprise FOCUS d'une question utilisateur.
 *
 * Couvre les patterns :
 *   - "qui est ATRIUM PATRIMOINE" / "qui est atrium patrimoine"
 *   - "fiche de MESANGE CAPITAL"
 *   - "infos sur Maison Lamour"
 *   - "PUMA CAPITAL" tout court (token entreprise dominant, query courte)
 *   - "TotalEnergies", "Carrefour" (single capitalized word, query <= 4 mots)
 *
 * Stratégie :
 *   1. Marqueur d'intention (qui est, fiche de, infos sur…) suivi de N mots.
 *   2. Si la query est courte (≤ 5 mots) sans marqueur d'intention, cherche un
 *      groupe de mots dont au moins un est un token "corporate" (PATRIMOINE,
 *      CAPITAL, HOLDING, SCI, etc.) ou tout en majuscules.
 *
 * Returns la dénomination (telle que tapée, capitalisation préservée — le
 * backend silver fait ILIKE % donc casse-insensible).
 */
export function extractFocusEntrepriseFromQuery(text: string): { q: string } | null {
  if (!text || text.length < 3 || text.length > 500) return null;
  const trimmed = text.trim();

  const hasCorporateToken = (s: string): boolean => {
    return s.toLowerCase().split(/[\s\-']+/).some(t => CORPORATE_SUFFIX_TOKENS.has(t));
  };

  // 0. SIREN brut (9 chiffres) — déclenche TargetCard via /entreprise/search?q=siren.
  // Ex: "qui est le siren 897992525", "897992525", "fiche siren 892318312".
  // Sans ce path, le siren brut tombait dans le siren direct lookup côté backend
  // qui retournait juste markdown texte (R2 audit 2026-05-05) — pas de TargetCard
  // cliquable avec drawer accessible.
  const sirenMatch = trimmed.match(/\b(\d{9})\b/);
  if (sirenMatch) {
    return { q: sirenMatch[1] };
  }

  // 1. Intent-based : "qui est <X>", "fiche de <X>", "infos sur <X>",
  //    "analyse <X>", "audit <X>", "compliance <X>", "risque <X>", "DD <X>".
  // Couvre les patterns M&A type "analyse compliance LVMH", "audit risque
  // TotalEnergies", "due diligence Carrefour". Le mot-cible peut être suivi
  // de mots qualifiants (ex: "analyse compliance LVMH risk score sanctions")
  // — on capture le 1er token capitalisé non-keyword qui suit l'intent.
  const reIntent = /(?:qui\s+(?:est|sont)|fiche\s+(?:de|du|d'|détaillée\s+de)|infos?\s+sur|recherche|donne[ -]moi(?:\s+(?:la\s+fiche|le\s+profil|les?\s+infos))?\s+(?:de|sur|pour|du|d')|montre[ -]moi(?:\s+la\s+fiche)?\s+(?:de|d')|parle[ -]moi\s+de)\s+(?:l['ea]\s+)?([A-Za-zÀ-ÿ0-9][A-Za-zÀ-ÿ0-9\-' ]{1,80})\??\s*$/i;
  const mIntent = reIntent.exec(trimmed);
  if (mIntent) {
    const candidate = mIntent[1].trim().replace(/\s+/g, " ");
    if (candidate.length >= 3 && /[A-Za-zÀ-ÿ]/.test(candidate)) {
      return { q: candidate };
    }
  }

  // 1bis. Verbes M&A (analyse, audit, compliance, risque, DD…) — pattern
  // libre : on extrait le 1er nom propre (token avec maj initiale ou
  // ALL-CAPS ≥ 3 chars) qui suit le verbe, ignorant les mots qualifiants
  // (risk, score, compliance, etc.).
  const M_AND_A_KEYWORDS = new Set([
    "risk", "risque", "score", "compliance", "sanctions", "procedure", "procédure",
    "collective", "red", "flags", "due", "diligence", "audit", "analyse", "verifie",
    "vérifie", "check", "evalue", "évalue", "trends", "trend", "dettes", "urssaf",
    "fiscales", "sociales", "bodacc", "offshore", "lobbying", "sci", "patrimoine",
    "filiale", "filiales", "dirigeants", "dirigeant", "ca", "ebitda", "marge",
    "et", "ou", "des", "le", "la", "les", "un", "une", "de", "du", "pour", "sur",
  ]);
  if (/^(analyse|audit|verifi|vérifi|évalue|evalue|check|compliance|risque|risk|due\s+diligence|dd|donne(\s+moi)?\s+(le|la|les|l)?(risk|score|risque))/i.test(trimmed)) {
    // Scan tous les tokens à la recherche d'un nom propre distinctif
    const tokens = trimmed.split(/\s+/);
    for (const tok of tokens) {
      const clean = tok.replace(/[^\wÀ-ÿ\-']/g, "");
      if (clean.length < 3) continue;
      const lower = clean.toLowerCase();
      if (M_AND_A_KEYWORDS.has(lower)) continue;
      // Match si Capitalized ou ALL-CAPS ≥ 3 lettres
      if (/^[A-ZÀ-ÖØ-Ý][A-Za-zÀ-ÿ]{2,}$/.test(clean) || /^[A-ZÀ-ÖØ-Ý]{3,}$/.test(clean)) {
        return { q: clean };
      }
    }
  }

  // 2. Query courte (≤ 10 mots, bumpé 6→10) + au moins un token corporate
  //    ou un mot all-caps. Élargi pour capturer "analyse compliance LVMH
  //    risk score sanctions" (7 mots, contient TotalEnergies).
  const words = trimmed.split(/\s+/);
  if (words.length <= 10) {
    const hasUpperWord = words.some(w => /^[A-ZÀ-ÖØ-Ý]{3,}/.test(w) && w.length >= 3);
    if (hasCorporateToken(trimmed) || hasUpperWord) {
      // Strip filler words at start ("la", "le", "les", "société", "groupe")
      const cleaned = trimmed
        .replace(/^(la|le|les|société|societe|groupe|group)\s+/i, "")
        .trim();
      if (cleaned.length >= 3) {
        return { q: cleaned };
      }
    }
  }

  // 3. Query 1-2 mots capitalisés type "Bouygues", "Renault", "Total Energies".
  // Aucune des paths 1/1bis/2 ne couvre ce cas si le mot n'est ni ALL-CAPS
  // ni suivi d'une forme juridique (SE/SA/SAS). Match si: 1-2 tokens, chacun
  // capitalisé (1ère lettre majuscule) avec ≥4 lettres, pas de mot stop.
  const STOP_WORDS = new Set([
    "qui", "quoi", "comment", "pourquoi", "quand", "fiche", "infos", "info",
    "donne", "montre", "parle", "trouve", "liste", "compare", "audit",
    "analyse", "check", "vérifie", "verifie", "the", "this", "that",
  ]);
  if (words.length <= 2) {
    const allValid = words.every(w => {
      const clean = w.replace(/[^\wÀ-ÿ\-']/g, "");
      if (clean.length < 4) return false;
      if (STOP_WORDS.has(clean.toLowerCase())) return false;
      return /^[A-ZÀ-ÖØ-Ý][A-Za-zÀ-ÿ\-']*$/.test(clean);
    });
    if (allValid) {
      return { q: trimmed };
    }
  }

  return null;
}

/** Cherche une entreprise par nom en backend silver (sans floor CA). */
export async function searchEntrepriseByName(q: string, limit = 5): Promise<Target[]> {
  if (!q || q.length < 2) return [];
  try {
    const res = await fetch(
      `/api/datalake/entreprise/search?q=${encodeURIComponent(q)}&limit=${limit}`,
      { credentials: "same-origin" }
    );
    if (!res.ok) return [];
    const data = (await res.json()) as { results?: Record<string, unknown>[] };
    const results = data.results ?? [];
    return results.map((r) => rowToTarget(r));
  } catch {
    return [];
  }
}

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
  // proxy_ebitda (gold.scoring_ma) : EBITDA estimé exposé par /cibles — évite le
  // "—" sur les cartes quand ebitda_dernier comptable n'est pas dispo.
  const ebitda = num(r.ebitda_dernier) ?? num(r.proxy_ebitda) ?? num(r.resultat_net);
  // Véracité EBITDA : réel si comptable (ebitda_dernier) ou flag gold ebitda_is_real=true ;
  // estimé (proxy résultat_net + 5% capital) si false ; inconnu sinon.
  const ebitdaIsReal: boolean | undefined =
    r.ebitda_dernier != null ? true
    : typeof r.ebitda_is_real === "boolean" ? (r.ebitda_is_real as boolean)
    : undefined;
  const score = num(r.score_ma) ?? num(r.pro_ma_score) ?? num(r.score) ?? 0;
  const naf = str(r.naf) || str(r.code_ape) || "";
  const ville = str(r.ville) || str(r.libelle_commune) || str(r.adresse_commune) || "";
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
    ebitda_is_real: ebitdaIsReal,
    procedure_nature: str(r.last_procedure_nature) || undefined,
    procedure_active: r.has_procedure_collective_active === true,
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
    // VRAI historique CA (exercices INPI réels, fournis par /cibles). En millions
    // d'euros, ordre ancien→récent. Aucune donnée inventée : si absent, courbe vide.
    ca_history: Array.isArray(r.ca_history)
      ? (r.ca_history as unknown[]).map((x) => Math.round((num(x) ?? 0) / 1e6))
      : [],
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
  // Patrimoine SCI : on l'expose en `event` (ligne mise en avant sur la card)
  // car le compte n_sci seul ("SCI 1") sous-estime un patrimoine d'1 SCI à 1,5 Md€.
  const capitalSci = num(r.total_capital_sci);
  const sciEvent = capitalSci && capitalSci > 0 ? `Patrimoine SCI ${fmtEur(capitalSci)}` : null;
  return {
    id: `p_${idx}_${nom}`,
    nom: `${prenom} ${nom}`.trim(),
    age: num(r.age_2026) ?? num(r.age),
    score: num(r.pro_ma_score) ?? num(r.score) ?? 50,
    mandats: num(r.n_mandats_actifs) ?? num(r.n_mandats_total) ?? sirens.length,
    sci: num(r.n_sci) ?? 0,
    entreprises: denos.slice(0, 4),
    event: sciEvent,
    dept: str(r.dept) || "",
    nom_raw: nom || undefined,
    prenom_raw: prenom || undefined,
    date_naissance: dn || null,
  };
}

export async function fetchTargets(opts: {
  limit?: number; minScore?: number; q?: string; dept?: string; naf?: string;
  minCa?: number; maxCa?: number; minEbitdaMargin?: number; maxDebtEbitda?: number;
  minAgeDirigeant?: number; isAssetRich?: boolean; isDistressed?: boolean;
  distress?: "plan_cession" | "reprise" | "active" | "liquidation";
  sort?: NonNullable<Parameters<typeof datalakeApi.searchCibles>[0]>["sort"];
} = {}): Promise<Target[]> {
  try {
    const r = await datalakeApi.searchCibles({
      limit: opts.limit ?? 8,
      minScore: opts.minScore,
      q: opts.q,
      dept: opts.dept,
      naf: opts.naf,
      minCa: opts.minCa,
      maxCa: opts.maxCa,
      minEbitdaMargin: opts.minEbitdaMargin,
      maxDebtEbitda: opts.maxDebtEbitda,
      minAgeDirigeant: opts.minAgeDirigeant,
      isAssetRich: opts.isAssetRich,
      isDistressed: opts.isDistressed,
      distress: opts.distress,
      sort: opts.sort ?? "score_ma",
    });
    return r.cibles.map((c) => rowToTarget(c as Record<string, unknown>));
  } catch (e) {
    console.error("[dem] fetchTargets failed:", e);
    return [];
  }
}

export async function fetchPersons(
  limit = 4,
  opts: { minAge?: number; maxMandats?: number; minSci?: number; sort?: string } = {}
): Promise<Person[]> {
  // PIVOT v3 PRO : gold.dirigeants_master au lieu de silver.inpi_dirigeants raw.
  // L'ancien orderBy retournait toujours THIBAUD/ERIC/BASTIEN (avocats / CAC
  // concentrateurs avec 6000+ mandats), pas des cibles M&A. Maintenant on filtre
  // (filter= structuré côté backend) : âge mini, plafond mandats pour exclure les
  // concentrateurs (maxMandats), nb SCI mini — dérivés de la question.
  // Plafond mandats par défaut = 80 (au-dessus = concentrateur, pas un dirigeant cible).
  const maxMandats = opts.maxMandats ?? 50;
  const buildFilter = (ageCol: string) => {
    // mandats 2..50 (exclut concentrateurs/nominees) + âge ≤ 100 (exclut age_2026=125
    // = data corrompue) ; bornes basses d'âge dérivées de la question.
    const clauses = [`n_mandats_actifs.gte.2`, `n_mandats_actifs.lte.${maxMandats}`, `${ageCol}.lte.100`];
    if (opts.minAge) clauses.push(`${ageCol}.gte.${opts.minAge}`);
    if (opts.minSci) clauses.push(`n_sci.gte.${opts.minSci}`);
    return clauses.join(",");
  };
  try {
    // Tentative 1 : gold.dirigeants_master (best signal)
    const r = await datalakeApi.queryTable("gold", "dirigeants_master", {
      limit,
      orderBy: opts.sort ?? "-pro_ma_score",
      filter: buildFilter("age_2026"),
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

/**
 * Top dirigeants par patrimoine SCI réel — silver.dirigeant_sci_patrimoine
 * (3.5M), trié par capital SCI cumulé décroissant. Source déterministe pour les
 * questions "plus gros patrimoine SCI / asset-rich" : remplit le compte SCI
 * (n_sci) là où gold.dirigeants_master ne l'a pas. Évite les noms génériques
 * extraits du texte LLM (GINA CALLOUET, SCI=1) qui ne reflètent pas la question.
 */
export async function fetchSciDirigeants(limit = 8): Promise<Person[]> {
  try {
    const r = await datalakeApi.queryTable("silver", "dirigeant_sci_patrimoine", {
      limit,
      orderBy: "-total_capital_sci",
      filter: "n_sci.gte.2",
    });
    return r.rows.map((row, i) => rowToPerson(row, i));
  } catch (e) {
    console.error("[dem] fetchSciDirigeants failed:", e);
    return [];
  }
}
