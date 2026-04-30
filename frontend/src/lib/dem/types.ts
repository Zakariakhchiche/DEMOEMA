/**
 * DEMOEMA shell types — port du Claude Design vers TypeScript.
 * Les types `Target` et `Person` sont alimentés par /api/datalake/*. Les autres
 * (Conversation, Pipeline, Watchlist, Audit) restent mock pour le moment et
 * peuvent évoluer vers des endpoints dédiés.
 */

export type Mode =
  | "dashboard"
  | "chat"
  | "pipeline"
  | "watchlist"
  | "explorer"
  | "graph"
  | "compare"
  | "audit";

export type Density = "compact" | "comfortable" | "spacious";

export interface Target {
  siren: string;
  denomination: string;
  score: number;
  naf: string;
  naf_label: string;
  ca: number;
  ca_str: string;
  ebitda: number | null;
  ebitda_str: string;
  effectif: number | null;
  dept: string;
  ville: string;
  forme: string;
  creation: string;
  top_dirigeant: { nom: string; age: number | null; score: number; mandats: number };
  red_flags: { type: string; label: string; source: string; severity: "high" | "medium" | "low" }[];
  sources: string[];
  score_breakdown: { label: string; value: number }[];
  ca_history: number[];
  spark?: number[];
  statut?: string; // 'actif' | 'cesse' | 'cessée' | 'C' | 'RADIE' — exposé par /api/datalake/cibles
  // Scoring v3 PRO — 4 axes business + risk + EV
  axes?: {
    transmission: number;  // 0-100, prob cession dirigeant
    attractivity: number;  // 0-100, valeur réelle (marge × multiple sectoriel)
    scale: number;         // 0-100, taille pour barrière transactionnelle
    structure: number;     // 0-100, suitability transaction (forme juridique, holding)
  };
  tier?: "A_HOT" | "B_WARM" | "C_PIPELINE" | "D_WATCH" | "E_REJECT" | "Z_ELIM";
  deal_percentile?: number;  // 1-100, ntile DESC sur deal_score
  risk_multiplier?: number;  // 0-1, multiplicateur appliqué au composite
  ev_estimated_eur?: number; // Valorisation indicative
}

export interface Person {
  id: string;
  nom: string;
  age: number | null;
  score: number;
  mandats: number;
  sci: number;
  entreprises: string[];
  event: string | null;
  dept: string;
}

export interface Conversation {
  id: string;
  title: string;
  time: string;
  group: "today" | "7d" | "30d";
  unread?: boolean;
  type: "sourcing" | "dd" | "compare" | "graph";
  proactive?: boolean;
}

export interface SavedSearch {
  id: string;
  name: string;
  count: number;
}

export interface SchemaTable {
  name: string;
  rows: string;
  size?: string;
  star?: boolean;
}

export interface Schema {
  bronze: { group: string; tables: SchemaTable[] }[];
  silver: SchemaTable[];
  gold: SchemaTable[];
}

export interface PipelineStage {
  id: string;
  label: string;
  color: string;
}

export interface PipelineDeal {
  id: string;
  siren: string;
  name: string;
  stage: string;
  value: string;
  owner: string;
  days: number;
  score: number;
  side: "buy-side" | "sell-side";
  next: string;
  urgent?: boolean;
}

export interface WatchlistAlert {
  id: string;
  target: string;
  siren: string;
  type: "finance" | "redflag" | "person" | "press";
  severity: "high" | "med" | "low";
  title: string;
  time: string;
  source: string;
}

export interface WatchlistRule {
  id: string;
  name: string;
  trigger: string;
  active: boolean;
  count: number;
  last: string;
}

export interface AuditEntry {
  id: string;
  who: string;
  role: string;
  action: "viewed" | "exported" | "queried" | "saved" | "compared";
  target: string;
  surface: string;
  time: string;
  date: "aujourd'hui" | "hier";
}

export interface KPI {
  label: string;
  value: string | number;
  delta: string;
  color: string;
}

export interface SlashCommand {
  cmd: string;
  desc: string;
  example: string;
}

export interface NetworkNode {
  id: string;
  label: string;
  type: "target" | "person" | "company" | "sci";
  x: number;
  y: number;
}

export interface NetworkLink {
  source: string;
  target: string;
  kind: string;
}

export interface ToolCall {
  tool: string;
  desc: string;
  detail: string;
  duration: number;
  rows: number;
}

export interface Citation {
  id: number;
  label: string;
  detail: string;
}

export interface AiMessageData {
  role: "ai";
  kind: "proactive" | "sourcing" | "compare" | "siren" | "persons" | "dd" | "plain";
  header?: string;
  content: string;
  cards?: Target[];
  persons?: Person[];
  compare?: { a: Target; b: Target };
  dd?: Target;
  stats?: { l: string; v: string; color?: string }[];
  suggestion?: string;
  followups?: string[];
  quickReplies?: string[];
  seeMore?: number;
  citations?: Citation[];
  reasoning?: string[];
  toolCalls?: ToolCall[];
  verdict?: string;
}

export interface UserMessageData {
  role: "user";
  content: string;
}

export type ChatMsg = AiMessageData | UserMessageData;

export interface HeatmapCell {
  dept: string;
  count: number;
  label: string;
}
