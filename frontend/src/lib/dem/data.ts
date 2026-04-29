/**
 * Mocks pour les vues qui n'ont pas encore d'endpoint dédié — Pipeline,
 * Watchlist, Audit, Heatmap, KPIs, Conversations, Schema-tree, Slash-commands,
 * Tour, ToolCalls. Les `Target`s et `Person`s viennent eux du datalake live.
 *
 * À mesure que les endpoints arrivent côté backend, on remplace ici un par
 * un — l'app reste stable car tout passe par ce module.
 */

import type {
  Conversation,
  SavedSearch,
  Schema,
  PipelineStage,
  PipelineDeal,
  WatchlistAlert,
  WatchlistRule,
  AuditEntry,
  KPI,
  SlashCommand,
  NetworkNode,
  NetworkLink,
  ToolCall,
  HeatmapCell,
} from "./types";

export const CONVERSATIONS: Conversation[] = [
  { id: "c1", title: "Cibles chimie IDF", time: "il y a 14 min", group: "today", type: "sourcing", proactive: true },
  { id: "c2", title: "DD Acme Industries", time: "il y a 1 h", group: "today", type: "dd" },
  { id: "c3", title: "Compare Beta vs Gamma", time: "il y a 3 h", group: "today", type: "compare" },
  { id: "c4", title: "Carbon Capture network", time: "hier", group: "7d", type: "graph" },
  { id: "c5", title: "Top dirigeants 60+ Var", time: "lun. 27 avril", group: "7d", type: "sourcing" },
  { id: "c6", title: "Sourcing biotech Q2", time: "ven. 24 avril", group: "7d", type: "sourcing" },
  { id: "c7", title: "DD Lazard benchmark", time: "mer. 22 avril", group: "7d", type: "dd" },
  { id: "c8", title: "Pharma cotées CAC Mid", time: "11 avril", group: "30d", type: "sourcing" },
  { id: "c9", title: "Compliance audit Q1", time: "8 avril", group: "30d", type: "dd" },
];

export const SAVED_SEARCHES: SavedSearch[] = [
  { id: "s1", name: "Top tech IDF", count: 47 },
  { id: "s2", name: "Pharma >50M€", count: 23 },
  { id: "s3", name: "DD ready cibles", count: 12 },
  { id: "s4", name: "Dirigeants 60+ Var", count: 31 },
];

export const SCHEMA: Schema = {
  bronze: [
    { group: "INPI", tables: [
      { name: "inpi_dirigeants_*", rows: "8.1M", size: "13 GB" },
      { name: "inpi_comptes_*", rows: "6.3M", size: "14 GB" },
      { name: "inpi_rne_*", rows: "5.4M", size: "8.2 GB" },
    ]},
    { group: "DILA", tables: [
      { name: "bodacc_*", rows: "4.2M", size: "11 GB" },
      { name: "balo_*", rows: "180K", size: "2.1 GB" },
    ]},
    { group: "OSINT", tables: [
      { name: "icij_offshore_*", rows: "2.1M", size: "1.8 GB" },
      { name: "press_mentions_*", rows: "12M", size: "44 GB" },
    ]},
  ],
  silver: [
    { name: "entreprises_consolidated", rows: "5.4M" },
    { name: "press_mentions_matched", rows: "8.7M" },
    { name: "signaux_ma_unified", rows: "1.2M" },
  ],
  gold: [
    { name: "entreprises_master", rows: "5.1M", star: true },
    { name: "dirigeants_master", rows: "8.1M", star: true },
    { name: "cibles_ma_top", rows: "123K", star: true },
    { name: "signaux_ma_feed", rows: "847K" },
    { name: "compliance_red_flags", rows: "12K" },
    { name: "network_mandats", rows: "23M" },
    { name: "parcelles_cibles", rows: "94K" },
    { name: "marches_publics_unifies", rows: "1.8M" },
    { name: "veille_reglementaire", rows: "4.2K" },
    { name: "persons_master_universal", rows: "11.4M" },
    { name: "persons_contacts_master", rows: "3.2M" },
    { name: "benchmarks_sectoriels", rows: "732" },
    { name: "score_breakdown_full", rows: "5.1M" },
  ],
};

export const SUGGESTIONS_INITIAL = [
  "Top cibles tech IDF >20M€",
  "DD compliance Acme Industries",
  "Compare Beta Pharma et Gamma Chimie",
  "Dirigeants 60+ avec holding patrimoniale Var",
];

export const QUICK_REPLIES = [
  "Affiner score ≥ 70",
  "Sans red flags",
  "Avec dirigeant 60+",
  "Holding patrimoniale",
  "Compare top 3",
  "Export en watchlist",
];

export const SLASH_COMMANDS: SlashCommand[] = [
  { cmd: "/siren", desc: "Recherche directe par SIREN", example: "/siren 838291045" },
  { cmd: "/compare", desc: "Comparer 2-5 cibles", example: "/compare 838291045 432198765" },
  { cmd: "/dd", desc: "Due diligence rapide", example: "/dd 838291045" },
  { cmd: "/graph", desc: "Ouvre le graphe réseau", example: "/graph 838291045" },
  { cmd: "/save", desc: "Sauver la dernière liste", example: "/save Top tech IDF" },
  { cmd: "/export", desc: "Export CSV / Parquet", example: "/export csv" },
  { cmd: "/clear", desc: "Clear la conversation", example: "/clear" },
];

export const NETWORK_NODES: NetworkNode[] = [
  { id: "acme", label: "Acme Industries", type: "target", x: 0, y: 0 },
  { id: "marc", label: "Marc Dubois", type: "person", x: -180, y: -140 },
  { id: "acme-h", label: "Acme Holding", type: "company", x: 200, y: -120 },
  { id: "md-pat", label: "MD Patrimoine", type: "company", x: -240, y: 80 },
  { id: "sci-md", label: "SCI Marc Dubois", type: "sci", x: 60, y: 180 },
  { id: "sci-md2", label: "SCI Famille D.", type: "sci", x: 240, y: 110 },
  { id: "beta", label: "Beta Pharma", type: "target", x: -120, y: 220 },
  { id: "sophie", label: "Sophie Laurent", type: "person", x: -340, y: 220 },
  { id: "carbon", label: "Carbon Capture", type: "target", x: 320, y: 220 },
  { id: "jean", label: "Jean Dupont", type: "person", x: 380, y: 60 },
  { id: "engie", label: "Engie (ex-)", type: "company", x: 440, y: -80 },
];

export const NETWORK_LINKS: NetworkLink[] = [
  { source: "acme", target: "marc", kind: "dirigeant" },
  { source: "acme", target: "acme-h", kind: "subsidiary" },
  { source: "marc", target: "md-pat", kind: "mandat" },
  { source: "marc", target: "sci-md", kind: "sci" },
  { source: "acme-h", target: "sci-md2", kind: "patrimoine" },
  { source: "marc", target: "beta", kind: "mandat" },
  { source: "beta", target: "sophie", kind: "dirigeant" },
  { source: "carbon", target: "jean", kind: "dirigeant" },
  { source: "jean", target: "engie", kind: "ex-mandat" },
  { source: "marc", target: "carbon", kind: "co-mandat" },
];

export const PIPELINE_STAGES: PipelineStage[] = [
  { id: "sourcing", label: "Sourcing", color: "var(--accent-blue)" },
  { id: "approche", label: "Approche", color: "var(--accent-cyan)" },
  { id: "dd", label: "Due Diligence", color: "var(--accent-purple)" },
  { id: "loi", label: "LOI / Term Sheet", color: "var(--accent-amber)" },
  { id: "closing", label: "Closing", color: "var(--accent-emerald)" },
];

export const PIPELINE_DEALS: PipelineDeal[] = [
  { id: "d1", siren: "432198765", name: "Beta Pharma SA", stage: "dd", value: "120 M€", owner: "AM", days: 12, score: 91, side: "sell-side", next: "Présenter VDD jeudi", urgent: true },
  { id: "d2", siren: "838291045", name: "Acme Industries", stage: "sourcing", value: "47 M€", owner: "AM", days: 3, score: 82, side: "buy-side", next: "Premier contact dirigeant" },
  { id: "d3", siren: "612345678", name: "Carbon Solutions", stage: "approche", value: "32 M€", owner: "TS", days: 7, score: 76, side: "buy-side", next: "Relance dirigeant" },
  { id: "d4", siren: "445678123", name: "Helios Energy", stage: "dd", value: "85 M€", owner: "TS", days: 21, score: 88, side: "sell-side", next: "Q&A management" },
  { id: "d5", siren: "789012345", name: "Verde Logistics", stage: "loi", value: "65 M€", owner: "AM", days: 34, score: 84, side: "sell-side", next: "Négo prix" },
  { id: "d6", siren: "234567890", name: "Atlas Industries", stage: "closing", value: "180 M€", owner: "AM", days: 62, score: 92, side: "sell-side", next: "Signature 02/05" },
  { id: "d7", siren: "901234567", name: "Nordic Tech", stage: "sourcing", value: "28 M€", owner: "TS", days: 1, score: 74, side: "buy-side", next: "Qualifier" },
  { id: "d8", siren: "345678901", name: "Pacific Foods", stage: "approche", value: "55 M€", owner: "AM", days: 9, score: 79, side: "buy-side", next: "RDV planifié" },
];

export const WATCHLIST_ALERTS: WatchlistAlert[] = [
  { id: "a1", target: "Beta Pharma SA", siren: "432198765", type: "finance", severity: "high", title: "CA Δ +18.3 % YoY publié", time: "il y a 2 h", source: "Pappers" },
  { id: "a2", target: "Acme Industries SAS", siren: "838291045", type: "redflag", severity: "high", title: "Ouverture procédure collective", time: "il y a 5 h", source: "BODACC 12/03/26" },
  { id: "a3", target: "Carbon Solutions", siren: "612345678", type: "person", severity: "med", title: "Nouveau dirigeant nommé : Pierre Klein", time: "hier", source: "INPI" },
  { id: "a4", target: "Helios Energy", siren: "445678123", type: "press", severity: "low", title: "3 mentions presse positives (Les Echos, AGEFI)", time: "hier", source: "Press monitor" },
  { id: "a5", target: "Verde Logistics", siren: "789012345", type: "finance", severity: "med", title: "Comptes annuels 2025 déposés", time: "il y a 2 j", source: "INPI" },
];

export const WATCHLIST_RULES: WatchlistRule[] = [
  { id: "r1", name: "Cibles tech IDF", trigger: "CA Δ > 15 % OU nouveau dirigeant", active: true, count: 47, last: "il y a 3 h" },
  { id: "r2", name: "Pharma >50M€", trigger: "Toute publication BODACC", active: true, count: 23, last: "hier" },
  { id: "r3", name: "Distressed signals", trigger: "Procédure collective OU contentieux", active: true, count: 14, last: "il y a 5 h" },
  { id: "r4", name: "Dirigeants 60+", trigger: "Cession récente OU age > 60", active: false, count: 89, last: "il y a 4 j" },
];

export const AUDIT_LOG: AuditEntry[] = [
  { id: "1", who: "Anne Martin", role: "Director M&A", action: "viewed", target: "Acme Industries SAS (838291045)", surface: "Fiche détaillée", time: "10:42", date: "aujourd'hui" },
  { id: "2", who: "Anne Martin", role: "Director M&A", action: "exported", target: "Pitch Ready PDF · Beta Pharma", surface: "Pitch generator", time: "10:28", date: "aujourd'hui" },
  { id: "3", who: "Thomas Sevin", role: "Senior Associate", action: "queried", target: "gold.cibles_ma_top WHERE naf LIKE '24.%'", surface: "Data Explorer", time: "09:51", date: "aujourd'hui" },
  { id: "4", who: "Anne Martin", role: "Director M&A", action: "saved", target: "Watchlist Cibles tech IDF", surface: "Watchlist", time: "09:14", date: "aujourd'hui" },
  { id: "5", who: "Salomé Cadet", role: "Partner", action: "viewed", target: "DD compliance · Acme Industries", surface: "Fiche détaillée", time: "16:42", date: "hier" },
  { id: "6", who: "Thomas Sevin", role: "Senior Associate", action: "compared", target: "Acme vs Beta Pharma", surface: "Chat", time: "15:30", date: "hier" },
  { id: "7", who: "Anne Martin", role: "Director M&A", action: "exported", target: "47 cibles → CSV", surface: "Data Explorer", time: "14:12", date: "hier" },
  { id: "8", who: "Salomé Cadet", role: "Partner", action: "viewed", target: "Beta Pharma SA (432198765)", surface: "Fiche détaillée", time: "11:08", date: "hier" },
];

export const HEATMAP: HeatmapCell[] = [
  { dept: "75", count: 47, label: "Paris" },
  { dept: "92", count: 38, label: "Hauts-de-Seine" },
  { dept: "78", count: 21, label: "Yvelines" },
  { dept: "69", count: 19, label: "Rhône" },
  { dept: "13", count: 16, label: "Bouches-du-Rhône" },
  { dept: "44", count: 14, label: "Loire-Atlantique" },
  { dept: "33", count: 12, label: "Gironde" },
  { dept: "59", count: 11, label: "Nord" },
  { dept: "31", count: 9, label: "Haute-Garonne" },
  { dept: "67", count: 8, label: "Bas-Rhin" },
  { dept: "06", count: 7, label: "Alpes-Maritimes" },
  { dept: "94", count: 6, label: "Val-de-Marne" },
];

export const TOOL_CALLS_SOURCING: ToolCall[] = [
  { tool: "query", desc: "gold.cibles_ma_top", detail: "filter naf LIKE '24.%' AND ca >= 20M", duration: 240, rows: 1247 },
  { tool: "enrich", desc: "INPI mandats", detail: "join on siren · 8.2M dirigeants", duration: 180, rows: 47 },
  { tool: "cross_ref", desc: "BODACC 90j", detail: "filter procédures + nominations", duration: 120, rows: 47 },
  { tool: "score", desc: "pro_ma_score()", detail: "9 features · gradient boost", duration: 90, rows: 47 },
  { tool: "rank", desc: "ORDER BY score DESC", detail: "limit 5 for chat preview", duration: 30, rows: 5 },
];

export const REASONING_TRACE = [
  "L'utilisateur demande des cibles tech / chimie spé en IDF avec CA >20M€.",
  "→ Je filtre gold.cibles_ma_top sur NAF 24.x (chimie) + 26.x (tech) + dept ∈ {75, 92, 78, 91, 93, 94, 95, 77}.",
  "→ 1 247 cibles correspondent au filtre brut.",
  "→ Je croise avec score_ma ≥ 70 (calibré sur 5 ans de deals EdRCF) → 47 cibles.",
  "→ Je trie par EBITDA/CA décroissant pour prioriser les targets profitables.",
  "→ Je remonte les 5 premières dans le chat, les 42 autres restent accessibles dans Data Explorer.",
];

export const KPIS: KPI[] = [
  { label: "Deals actifs", value: 8, delta: "+2 cette semaine", color: "var(--accent-blue)" },
  { label: "Watchlist alertes 24h", value: 5, delta: "2 critiques", color: "var(--accent-rose)" },
  { label: "Σ pipeline", value: "612 M€", delta: "+85 M€", color: "var(--accent-emerald)" },
  { label: "Cibles qualifiées (mois)", value: 142, delta: "+23 vs M-1", color: "var(--accent-purple)" },
];
