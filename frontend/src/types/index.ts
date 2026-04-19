// ── Dirigeant ──────────────────────────────────────────────────────
export interface Dirigeant {
  name: string;
  role: string;
  age: number;
  since: string;
  ex_pe?: boolean;
}

// ── Signal (enriched) ──────────────────────────────────────────────
export interface Signal {
  id: string;
  label: string;
  source: string;
  source_url: string;
  dimension: string;
  points: number;
  severity: string;
  family: string;
}

// ── Scoring Dimension ──────────────────────────────────────────────
export interface ScoringDimension {
  score: number;
  raw: number;
  max: number;
  label: string;
}

// ── Group Info ─────────────────────────────────────────────────────
export interface GroupInfo {
  is_group: boolean;
  is_holding?: boolean;
  parent: string | null;
  subsidiaries: string[];
  nb_etablissements?: number;
  procedure_collective_en_cours?: boolean;
  consolidated_revenue: string | null;
}

// ── Financials (enriched) ──────────────────────────────────────────
export interface Financials {
  revenue: string;
  revenue_growth: string;
  ebitda: string;
  ebitda_margin: string;
  ebitda_range: string;
  effectif: number;
  last_published_year: number;
}

// ── Relationship (enriched) ────────────────────────────────────────
export interface Relationship {
  strength: number;
  path: string;
  common_connections: number;
  edr_banker: string | null;
}

// ── Analysis ───────────────────────────────────────────────────────
export interface TargetAnalysis {
  type: string;
  window: string;
  narrative: string;
}

// ── Activation ─────────────────────────────────────────────────────
export interface Activation {
  deciders: string[];
  approach: string;
  reason: string;
}

// ── Risks ──────────────────────────────────────────────────────────
export interface Risks {
  falsePositive: string;
  uncertainties: string;
}

// ── Target ─────────────────────────────────────────────────────────
export interface Target {
  id: string;
  siren: string;
  name: string;
  sector: string;
  sub_sector: string;
  region: string;
  city: string;
  code_naf: string;
  creation_date: string;
  structure: string; // "Familiale" | "PE-backed" | "Groupe côté"
  statut_activite?: string;
  date_cessation?: string | null;
  publication_status: string; // "Publie" | "Ne publie pas"
  globalScore: number;
  priorityLevel: string; // "Action Prioritaire" | "Qualification" | "Monitoring" | "Veille Passive"
  dirigeants: Dirigeant[];
  financials: Financials;
  scoring_details?: Record<string, ScoringDimension>;
  topSignals: Signal[];
  group?: GroupInfo;
  relationship?: Relationship;
  analysis?: TargetAnalysis;
  activation?: Activation;
  risks?: Risks;
  bodacc_recent?: boolean;
  dept?: string;
  ma_score?: number;
}

// ── Filter Options (returned by API) ───────────────────────────────
export interface FilterOptions {
  sectors: string[];
  regions: string[];
  structures: string[];
  ebitda_ranges: string[];
}

// ── Targets API Response ───────────────────────────────────────────
export interface TargetsApiResponse {
  data: Target[];
  total: number;
  filters: FilterOptions;
}

// ── Scoring Config ─────────────────────────────────────────────────
export interface ScoringConfigEntry {
  weight: number;
  max: number;
  label: string;
}

export interface ScoringConfig {
  data: Record<string, ScoringConfigEntry>;
}

// ── Sectors Heat ───────────────────────────────────────────────────
export interface SectorsHeat {
  name: string;
  count: number;
  avgScore: number;
}

// ── Search Result ──────────────────────────────────────────────────
export interface SearchResult {
  id: string;
  name: string;
  sector: string;
  type: "page" | "target";
  path: string;
}

// ── Copilot Message ────────────────────────────────────────────────
export interface Message {
  role: "user" | "assistant";
  content: string;
  id: string;
  timestamp: string;
}
