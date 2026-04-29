/**
 * Configuration UI uniquement — zéro mock data.
 *
 * Tout ce qui était mock (CONVERSATIONS, PIPELINE_DEALS, WATCHLIST_ALERTS,
 * AUDIT_LOG, KPIS, HEATMAP, NETWORK_NODES, TARGETS, PERSONS) est désormais
 * récupéré via /api/datalake/* — voir lib/api.ts et lib/dem/adapter.ts.
 *
 * Ce fichier ne contient plus que des constantes d'UI (suggestions de prompts,
 * commandes slash) qui ne sont pas des données mais de la configuration de
 * l'interface.
 */

import type { SlashCommand } from "./types";

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
