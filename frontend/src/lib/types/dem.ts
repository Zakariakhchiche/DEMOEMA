/**
 * Types DEMOEMA — Cible M&A, Dirigeant, Signaux, Conversation chat AI.
 * Issus de gold.entreprises_master + gold.dirigeants_master + gold.signaux_ma_feed.
 */

export interface Cible {
  // Identité
  siren: string;
  denomination: string;
  sigle?: string | null;
  naf: string;
  naf_libelle: string;
  forme_juridique: string;

  // Localisation
  siege_dept: string; // CHAR(3)
  siege_region: string;
  siege_commune?: string;

  // Taille & finance
  effectif_tranche: string;
  effectif_exact?: number | null;
  ca_dernier?: number | null;
  ca_n_minus_1?: number | null;
  ebitda_dernier?: number | null;
  capitaux_propres?: number | null;
  date_derniers_comptes?: string | null;

  // IDs
  lei?: string | null;
  isin?: string | null;
  is_listed: boolean;
  date_creation?: string;

  // Statut
  statut: "actif" | "cesse" | "procedure" | "radie";
  date_statut?: string | null;

  // Scoring
  pro_ma_score: number; // 0-100
  score_defaillance?: number | null;
  score_trajectoire?: number | null;

  // Signaux M&A flags
  has_balo_recent: boolean;
  has_cession_recente: boolean;
  is_pro_ma: boolean;
  has_holding_patrimoniale: boolean;
  is_asset_rich: boolean;
  patrimoine_total_eur?: number | null;

  // Compliance
  has_compliance_red_flag: boolean;
  red_flags?: string[];
  is_sanctionne: boolean;

  // Dirigeants
  n_dirigeants: number;
  top_dirigeant_full_name?: string;
  top_dirigeant_pro_ma_score?: number;
  top_dirigeant_age?: number;

  // Innovation
  is_innovation_company?: boolean;
  has_publications?: boolean;

  // Lineage
  derniere_maj: string;
  sources_de_verite?: Record<string, string>;
}

export interface Dirigeant {
  person_uid: string;
  prenom: string;
  nom: string;
  date_naissance?: string;
  age?: number | null;

  // Mandats
  n_mandats_actifs: number;
  sirens_mandats: string[];
  denominations_mandats: string[];
  is_pro_ma: boolean; // n_mandats >= 10

  // SCI / Patrimoine
  n_sci: number;
  total_capital_sci?: number;
  has_holding_patrimoniale: boolean;
  patrimoine_immo_estimee_eur?: number | null;

  // Réseau
  co_mandataires_uids: string[];
  n_co_mandataires: number;
  has_strong_network: boolean;

  // Scoring
  pro_ma_score: number;

  // Red flags
  is_sanctionne: boolean;
  has_offshore_match: boolean;
  has_political_connection: boolean;

  // Innovation
  is_kol_pharma?: boolean;
  has_publications_recent?: boolean;

  // External IDs (Person Resolution)
  resolution_confidence: "HIGH" | "MEDIUM" | "LOW" | "UNRESOLVED";
  has_wikidata: boolean;
  has_orcid: boolean;
  has_github: boolean;

  // Contacts
  has_email: boolean;
  has_phone: boolean;
  top_email?: string;
  top_phone?: string;

  derniere_maj: string;
}

export type SignalType =
  | "balo_operation"
  | "cession"
  | "bodacc_event"
  | "amf_decision"
  | "mandat_change"
  | "press_mention"
  | "procedure_collective";

export type SignalSeverity = "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";

export interface SignalEvent {
  signal_uid: string;
  signal_type: SignalType;
  severity: SignalSeverity;
  date_event: string; // ISO timestamp
  date_published?: string;

  siren?: string;
  denomination?: string;
  person_uid?: string;
  person_full_name?: string;

  title: string;
  description: string;

  source_table: string;
  source_url?: string;
  raw_payload?: Record<string, unknown>;
}

export interface ChatMessage {
  id: string;
  role: "user" | "ai";
  content: string;
  timestamp: number;
  streaming?: boolean;

  // Cards inline (cibles, dirigeants, événements)
  cards?: {
    type: "cible" | "dirigeant" | "signal" | "comparison" | "compliance";
    payload: Cible | Dirigeant | SignalEvent | unknown;
  }[];

  // Quick replies suggestions
  quick_replies?: { label: string; prompt: string }[];

  // Sources cited
  sources?: { label: string; url?: string; siren?: string }[];
}

export interface Conversation {
  id: string;
  title: string;
  created_at: number;
  updated_at: number;
  pinned?: boolean;
  messages: ChatMessage[];
}

// Filtres Data Explorer
export interface FilterCondition {
  column: string;
  operator: "=" | "!=" | ">" | ">=" | "<" | "<=" | "BETWEEN" | "IN" | "NOT IN" | "ILIKE" | "IS NULL" | "IS NOT NULL";
  value: unknown;
}

export interface SavedView {
  id: string;
  name: string;
  table: string;
  filters: FilterCondition[];
  sort: { column: string; direction: "asc" | "desc" }[];
  columns: string[];
  density: "compact" | "comfortable" | "spacious";
  created_at: number;
  shared?: boolean;
}

// Table metadata
export interface TableMeta {
  name: string; // ex "gold.entreprises_master"
  layer: "bronze" | "silver" | "gold";
  rows: number;
  size_bytes: number;
  last_updated?: string;
  primary_key?: string;
  description?: string;
}
