/**
 * Client API typé pour le backend FastAPI EdRCF.
 *
 * En prod (Caddy), le backend est exposé sur le même domaine via reverse proxy
 * (`/api/*` → backend:8000). En dev, NEXT_PUBLIC_API_URL peut pointer vers
 * http://localhost:8000.
 */

import type { Cible } from "@/lib/types/dem";

const BASE = process.env.NEXT_PUBLIC_API_URL || "";

async function jget<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    ...init,
    headers: { Accept: "application/json", ...(init?.headers || {}) },
  });
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`API ${path} → ${res.status}: ${text.slice(0, 200)}`);
  }
  return res.json();
}

/**
 * Mapper row brut gold.entreprises_master → forme `Cible` consommée par
 * TargetCard. Le schéma exact étant codegen'é, on tente plusieurs noms de
 * colonnes (score_ma | pro_ma_score, etc.) et on dégrade gracefulement.
 */
function rowToCible(r: Record<string, unknown>): Partial<Cible> {
  const num = (v: unknown): number | null =>
    typeof v === "number" ? v : v == null ? null : Number(v) || null;
  const bool = (v: unknown): boolean => v === true || v === "t" || v === 1;
  const str = (v: unknown): string => (typeof v === "string" ? v : v == null ? "" : String(v));
  const score =
    num(r.score_ma) ?? num(r.pro_ma_score) ?? num(r.score) ?? 0;
  return {
    siren: str(r.siren),
    denomination: str(r.denomination) || str(r.nom),
    naf: str(r.naf),
    naf_libelle: str(r.naf_libelle),
    forme_juridique: str(r.forme_juridique),
    siege_dept: str(r.siege_dept),
    siege_region: str(r.siege_region),
    effectif_tranche: str(r.effectif_tranche),
    effectif_exact: num(r.effectif_exact),
    ca_dernier: num(r.ca_dernier),
    ca_n_minus_1: num(r.ca_n_minus_1),
    ebitda_dernier: num(r.ebitda_dernier),
    capitaux_propres: num(r.capitaux_propres),
    is_listed: bool(r.is_listed) || Boolean(r.isin),
    statut: (str(r.statut) || "actif") as Cible["statut"],
    pro_ma_score: score ?? 0,
    has_balo_recent: bool(r.has_balo_recent) || bool(r.has_balo_operations_recent),
    has_cession_recente: bool(r.has_cession_recente) || (num(r.n_cession_events_24m) ?? 0) > 0,
    is_pro_ma: bool(r.is_pro_ma) || score >= 70,
    has_holding_patrimoniale: bool(r.has_holding_patrimoniale),
    is_asset_rich: bool(r.is_asset_rich),
    has_compliance_red_flag: bool(r.has_compliance_red_flag) || bool(r.has_amf_red_flag) || bool(r.has_sanction),
    red_flags: Array.isArray(r.red_flags) ? (r.red_flags as string[]) : undefined,
    is_sanctionne: bool(r.has_sanction) || bool(r.is_sanctionne),
    n_dirigeants: num(r.n_dirigeants) ?? 0,
    top_dirigeant_full_name: str(r.top_dirigeant_full_name) || undefined,
    top_dirigeant_pro_ma_score: num(r.top_dirigeant_pro_ma_score) || num(r.top_dirigeant_score) || undefined,
    top_dirigeant_age: num(r.top_dirigeant_age) || undefined,
    derniere_maj: str(r.derniere_maj) || str(r.updated_at) || "",
  };
}

// ───── Datalake — gold + silver ────────────────────────────────────────

export interface TableInfo {
  name: string;
  label: string;
  category: string;
  row_count_approx: number | null;
  preview_cols: string[];
}

export const datalakeApi = {
  listTables: () => jget<{ tables: TableInfo[] }>(`/api/datalake/tables`),

  queryTable: (
    schema: string,
    table: string,
    opts: { limit?: number; offset?: number; q?: string; orderBy?: string } = {}
  ) => {
    const p = new URLSearchParams();
    if (opts.limit) p.set("limit", String(opts.limit));
    if (opts.offset) p.set("offset", String(opts.offset));
    if (opts.q) p.set("q", opts.q);
    if (opts.orderBy) p.set("order_by", opts.orderBy);
    return jget<{
      table: string;
      columns: string[];
      rows: Record<string, unknown>[];
      limit: number;
      offset: number;
      has_more: boolean;
    }>(`/api/datalake/${schema}/${table}?${p.toString()}`);
  },

  searchCibles: async (opts: {
    q?: string;
    dept?: string;
    naf?: string;
    minScore?: number;
    isProMa?: boolean;
    isAssetRich?: boolean;
    hasRedFlags?: boolean;
    sort?: "score_ma" | "ca_dernier" | "date_creation";
    limit?: number;
  } = {}) => {
    const p = new URLSearchParams();
    if (opts.q) p.set("q", opts.q);
    if (opts.dept) p.set("dept", opts.dept);
    if (opts.naf) p.set("naf", opts.naf);
    if (opts.minScore != null) p.set("min_score", String(opts.minScore));
    if (opts.isProMa) p.set("is_pro_ma", "true");
    if (opts.isAssetRich) p.set("is_asset_rich", "true");
    if (opts.hasRedFlags === true) p.set("has_red_flags", "true");
    if (opts.hasRedFlags === false) p.set("has_red_flags", "false");
    if (opts.sort) p.set("sort", opts.sort);
    p.set("limit", String(opts.limit ?? 20));
    const raw = await jget<{ cibles: Record<string, unknown>[]; has_more: boolean }>(
      `/api/datalake/cibles?${p.toString()}`
    );
    return {
      cibles: raw.cibles.map(rowToCible),
      has_more: raw.has_more,
    };
  },

  ficheEntreprise: (siren: string) =>
    jget<{
      fiche: Record<string, unknown>;
      dirigeants: Record<string, unknown>[];
      signaux: Record<string, unknown>[];
      red_flags: Record<string, unknown>[];
      network: Record<string, unknown>[];
      presse: Record<string, unknown>[];
    }>(`/api/datalake/fiche/${siren}`),

  /** Fiche complète dirigeant : INPI identité + SCI patrimoine + OSINT + sanctions + DVF.
   * Backend route /dirigeant/{nom}/{prenom}[/{date_naissance}]. */
  dirigeantFull: (nom: string, prenom: string, dateNaissance?: string) => {
    const path = dateNaissance
      ? `/api/datalake/dirigeant/${encodeURIComponent(nom)}/${encodeURIComponent(prenom)}/${encodeURIComponent(dateNaissance)}`
      : `/api/datalake/dirigeant/${encodeURIComponent(nom)}/${encodeURIComponent(prenom)}`;
    return jget<{
      identity: Record<string, unknown> | null;
      sci_patrimoine: Record<string, unknown> | null;
      sci_value_total: Record<string, unknown> | null;
      sci_values_per_company: Record<string, unknown>[];
      osint: Record<string, unknown> | null;
      osint_raw: Record<string, unknown> | null;
      sanctions: Record<string, unknown>[];
      dvf_zones: Record<string, unknown> | null;
    }>(path);
  },

  /** Scoring v3 PRO : 4 axes business + tier + percentile + EV estimée */
  scoringDetail: (siren: string) =>
    jget<{
      siren: string;
      denomination: string;
      deal_score: number;
      deal_percentile: number | null;
      tier: string | null;
      axes: { transmission: number; attractivity: number; scale: number; structure: number };
      risk: {
        multiplier: number;
        has_sanction_ofac_eu: boolean;
        has_sanction_cnil: boolean;
        has_sanction_dgccrf: boolean;
        has_proc_collective_recent: boolean;
        has_cession_recent: boolean;
        n_contentieux_recent: number;
        has_late_filing: boolean;
      };
      financials: {
        ca_latest: number | null;
        capitaux_propres_latest: number | null;
        resultat_net_latest: number | null;
        proxy_ebitda: number | null;
        proxy_margin: number | null;
        sector_multiple: number | null;
        ev_estimated_eur: number | null;
      };
      context: Record<string, unknown>;
      score_total: number;
      feature_version: string;
      derniere_maj: string | null;
    }>(`/api/datalake/scoring/${siren}`),

  pressRecent: (opts: { limit?: number; siren?: string; signal?: string } = {}) => {
    const p = new URLSearchParams();
    if (opts.limit) p.set("limit", String(opts.limit));
    if (opts.siren) p.set("siren", opts.siren);
    if (opts.signal) p.set("signal", opts.signal);
    return jget<{ articles: Record<string, unknown>[]; notice?: string }>(
      `/api/datalake/press/recent?${p.toString()}`
    );
  },

  dashboard: () =>
    jget<{
      kpis: {
        n_cibles_pro_ma?: number;
        n_red_flags?: number;
        sigma_top50_ca?: number;
        n_signals_7d?: number;
        n_qualified_30d?: number;
      };
      heatmap: { dept: string; count: number; label: string }[];
      alerts: Record<string, unknown>[];
      top_targets: Record<string, unknown>[];
    }>(`/api/datalake/dashboard`),

  pipeline: () =>
    jget<{
      stages: { id: string; label: string; color: string }[];
      deals: {
        id: string;
        siren: string;
        name: string;
        stage: string;
        value: string;
        value_num: number;
        owner: string;
        days: number;
        score: number;
        side: "buy-side" | "sell-side";
        next: string;
        urgent: boolean;
      }[];
    }>(`/api/datalake/pipeline`),

  network: (siren: string) =>
    jget<{
      nodes: { id: string; label: string; type: "target" | "person" | "company" | "sci"; x: number; y: number }[];
      links: { source: string; target: string; kind: string }[];
    }>(`/api/datalake/co-mandats/${siren}`),

  auditLog: (limit = 50) =>
    jget<{
      entries: {
        id: number;
        agent_role: string;
        source_id: string;
        action: string;
        status: string;
        duration_ms: number;
        llm_model: string | null;
        llm_tokens: number | null;
        created_at: string;
      }[];
      notice?: string;
    }>(`/api/datalake/agent-actions?limit=${limit}`),

  auditFreshness: () =>
    jget<{
      sources: {
        source_id: string;
        last_success_at: string | null;
        last_failure_at: string | null;
        rows_last_run: number | null;
        total_rows: number;
        sla_minutes: number;
        status: string;
        completeness_pct: number | null;
        retry_count: number;
      }[];
    }>(`/api/datalake/source-health`),
};

// ───── Copilot SSE streaming ──────────────────────────────────────────

export interface CopilotStreamEvent {
  chunk?: string;
  done?: boolean;
  source?: string;
  targets_updated?: boolean;
  targets_count?: number;
}

/** Stream le copilot via fetch + ReadableStream (mieux qu'EventSource pour POST/headers). */
export async function* streamCopilot(
  q: string,
  signal?: AbortSignal
): AsyncGenerator<CopilotStreamEvent> {
  const res = await fetch(`${BASE}/api/copilot/stream?q=${encodeURIComponent(q)}`, {
    method: "GET",
    signal,
    headers: { Accept: "text/event-stream" },
  });
  if (!res.ok || !res.body) {
    throw new Error(`Copilot stream HTTP ${res.status}`);
  }
  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buf = "";
  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    buf += decoder.decode(value, { stream: true });
    const events = buf.split("\n\n");
    buf = events.pop() ?? "";
    for (const ev of events) {
      const line = ev.split("\n").find((l) => l.startsWith("data: "));
      if (!line) continue;
      const payload = line.slice(6).trim();
      if (!payload) continue;
      try {
        yield JSON.parse(payload) as CopilotStreamEvent;
      } catch {
        // ignore malformed
      }
    }
  }
}
