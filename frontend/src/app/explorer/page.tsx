"use client";

import { useEffect, useState, useCallback, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import { X, Sparkles, AlertTriangle, Database } from "lucide-react";
import { TableTreeSidebar } from "@/components/explorer/TableTreeSidebar";
import { DataTable } from "@/components/explorer/DataTable";
import { datalakeApi, type TableInfo } from "@/lib/api";

interface RowsState {
  table: string;
  columns: string[];
  rows: Record<string, unknown>[];
  hasMore: boolean;
  offset: number;
  limit: number;
  q: string;
  orderBy?: string;
}

function ExplorerInner() {
  const params = useSearchParams();
  const [tables, setTables] = useState<TableInfo[]>([]);
  const [tablesLoading, setTablesLoading] = useState(true);
  const [active, setActive] = useState<string>("");
  const [data, setData] = useState<RowsState | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [globalErr, setGlobalErr] = useState<string | null>(null);

  // Drill-down sheet (fiche entreprise)
  const [ficheSiren, setFicheSiren] = useState<string | null>(
    params.get("siren")
  );
  const [fiche, setFiche] = useState<Awaited<
    ReturnType<typeof datalakeApi.ficheEntreprise>
  > | null>(null);
  const [ficheLoading, setFicheLoading] = useState(false);

  // Initial: load tables list
  useEffect(() => {
    setTablesLoading(true);
    datalakeApi
      .listTables()
      .then((r) => {
        setTables(r.tables);
        if (r.tables.length > 0 && !active) {
          setActive(r.tables[0].name);
        }
      })
      .catch((e) => setGlobalErr(e instanceof Error ? e.message : String(e)))
      .finally(() => setTablesLoading(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const loadTable = useCallback(
    async (name: string, opts: { offset?: number; q?: string; orderBy?: string } = {}) => {
      const [schema, table] = name.split(".");
      if (!schema || !table) return;
      setLoading(true);
      setError(null);
      try {
        const r = await datalakeApi.queryTable(schema, table, {
          limit: 50,
          offset: opts.offset ?? 0,
          q: opts.q,
          orderBy: opts.orderBy,
        });
        setData({
          table: r.table,
          columns: r.columns,
          rows: r.rows,
          hasMore: r.has_more,
          offset: r.offset,
          limit: r.limit,
          q: opts.q ?? "",
          orderBy: opts.orderBy,
        });
      } catch (e) {
        setError(e instanceof Error ? e.message : String(e));
        setData(null);
      } finally {
        setLoading(false);
      }
    },
    []
  );

  useEffect(() => {
    if (active) {
      void loadTable(active, {});
    }
  }, [active, loadTable]);

  // Fiche fetch
  useEffect(() => {
    if (!ficheSiren) {
      setFiche(null);
      return;
    }
    setFicheLoading(true);
    datalakeApi
      .ficheEntreprise(ficheSiren)
      .then(setFiche)
      .catch(() => setFiche(null))
      .finally(() => setFicheLoading(false));
  }, [ficheSiren]);

  return (
    <div className="flex h-screen overflow-hidden bg-zinc-950 text-zinc-100">
      <div
        className="pointer-events-none fixed inset-0 -z-10"
        style={{
          background:
            "radial-gradient(ellipse at top right, rgba(16,185,129,0.06), transparent 50%), radial-gradient(ellipse at bottom left, rgba(59,130,246,0.05), transparent 50%)",
        }}
      />

      <TableTreeSidebar
        tables={tables}
        active={active}
        onSelect={setActive}
        loading={tablesLoading}
      />

      <main className="flex flex-1 flex-col">
        <header className="flex items-center justify-between border-b border-white/[0.04] bg-zinc-950/40 px-6 py-3 backdrop-blur-xl">
          <div className="flex items-center gap-2">
            <Database className="h-4 w-4 text-emerald-300" />
            <span className="text-sm font-semibold tracking-tight">
              {data?.table ?? "Data Explorer"}
            </span>
            {data && (
              <span className="ml-2 rounded bg-emerald-500/10 px-2 py-0.5 font-mono text-[10px] text-emerald-300 ring-1 ring-emerald-500/20">
                live · gold/silver
              </span>
            )}
          </div>
          <div className="flex items-center gap-3">
            <a
              href="/copilot"
              className="flex items-center gap-1.5 rounded-lg border border-white/[0.06] bg-white/[0.02] px-3 py-1 text-[11px] font-medium text-zinc-400 transition-all hover:border-purple-400/40 hover:bg-purple-500/10 hover:text-purple-200"
            >
              <Sparkles className="h-3 w-3" />
              Copilot Chat
            </a>
            <span className="text-[11px] text-zinc-500">Anne Dupont · EdRCF</span>
          </div>
        </header>

        {globalErr && (
          <div className="flex items-start gap-2 border-b border-amber-500/20 bg-amber-500/5 px-6 py-2 text-[12px] text-amber-200">
            <AlertTriangle className="mt-0.5 h-3.5 w-3.5 shrink-0" />
            <span>
              Datalake non joignable : <code className="font-mono">{globalErr}</code>
            </span>
          </div>
        )}

        {!active && !globalErr && (
          <div className="flex flex-1 items-center justify-center text-zinc-500">
            <div className="text-center">
              <Database className="mx-auto mb-3 h-10 w-10 text-zinc-700" />
              <div className="text-sm">Sélectionne une table dans la sidebar.</div>
            </div>
          </div>
        )}

        {active && data && (
          <DataTable
            table={data.table}
            columns={data.columns}
            rows={data.rows}
            loading={loading}
            error={error}
            hasMore={data.hasMore}
            offset={data.offset}
            limit={data.limit}
            q={data.q}
            orderBy={data.orderBy}
            onPage={(off) => loadTable(active, { offset: off, q: data.q, orderBy: data.orderBy })}
            onSearch={(q) => loadTable(active, { q, orderBy: data.orderBy })}
            onOrder={(col) => loadTable(active, { q: data.q, orderBy: col })}
            onRowClick={(row) => {
              const s = row.siren;
              if (typeof s === "string" && s.length === 9) setFicheSiren(s);
            }}
          />
        )}

        {active && !data && loading && (
          <div className="flex flex-1 items-center justify-center text-zinc-500">
            <div className="text-center">
              <div className="text-sm">Chargement…</div>
            </div>
          </div>
        )}
      </main>

      {/* Fiche drawer */}
      <AnimatePresence>
        {ficheSiren && (
          <motion.aside
            initial={{ x: 480 }}
            animate={{ x: 0 }}
            exit={{ x: 480 }}
            transition={{ type: "spring", stiffness: 300, damping: 30 }}
            className="absolute right-0 top-0 z-30 flex h-screen w-[480px] flex-col border-l border-white/[0.06] bg-zinc-950/95 backdrop-blur-2xl shadow-[-12px_0_40px_rgba(0,0,0,0.5)]"
          >
            <div className="flex items-center justify-between border-b border-white/[0.06] px-5 py-3">
              <div>
                <div className="text-[10px] uppercase tracking-wider text-zinc-500">
                  Fiche entreprise
                </div>
                <div className="font-mono text-sm font-semibold text-zinc-100">
                  SIREN {ficheSiren}
                </div>
              </div>
              <button
                onClick={() => setFicheSiren(null)}
                className="rounded-lg p-1.5 text-zinc-400 hover:bg-white/[0.04] hover:text-zinc-200"
              >
                <X className="h-4 w-4" />
              </button>
            </div>

            <div className="flex-1 overflow-y-auto p-5">
              {ficheLoading && <div className="text-xs text-zinc-500">Chargement…</div>}
              {!ficheLoading && fiche && (
                <div className="space-y-5">
                  <FicheBlock title="Identité" rows={pickFields(fiche.fiche, [
                    "denomination", "siren", "naf_libelle", "forme_juridique",
                    "siege_dept", "siege_region", "date_creation", "statut",
                  ])} />
                  <FicheBlock title="Finance" rows={pickFields(fiche.fiche, [
                    "ca_dernier", "ca_n_minus_1", "ebitda_dernier",
                    "capitaux_propres", "effectif_exact", "effectif_tranche",
                  ])} />
                  <FicheBlock title="Scoring M&A" rows={pickFields(fiche.fiche, [
                    "score_ma", "pro_ma_score", "is_pro_ma",
                    "is_asset_rich", "has_compliance_red_flag",
                  ])} />
                  {fiche.dirigeants.length > 0 && (
                    <FicheList title={`Dirigeants (${fiche.dirigeants.length})`} items={fiche.dirigeants} cols={["nom", "prenom", "qualite", "score_decideur"]} />
                  )}
                  {fiche.signaux.length > 0 && (
                    <FicheList title={`Signaux M&A (${fiche.signaux.length})`} items={fiche.signaux} cols={["event_date", "signal_type", "severity", "source"]} />
                  )}
                  {fiche.presse.length > 0 && (
                    <FicheList title={`Presse (${fiche.presse.length})`} items={fiche.presse} cols={["published_at", "source", "title"]} />
                  )}
                </div>
              )}
              {!ficheLoading && !fiche && (
                <div className="rounded-lg border border-amber-500/20 bg-amber-500/5 p-3 text-[11px] text-amber-200">
                  Pas de fiche disponible pour ce SIREN.
                </div>
              )}
            </div>
          </motion.aside>
        )}
      </AnimatePresence>
    </div>
  );
}

function pickFields(obj: Record<string, unknown>, keys: string[]) {
  return keys
    .filter((k) => obj[k] !== undefined && obj[k] !== null)
    .map((k) => ({ k, v: obj[k] }));
}

function fmt(v: unknown): string {
  if (v === null || v === undefined) return "—";
  if (typeof v === "boolean") return v ? "✓" : "✗";
  if (typeof v === "number") {
    if (Math.abs(v) >= 1_000_000) return `${(v / 1_000_000).toFixed(1)} M`;
    return v.toLocaleString("fr-FR");
  }
  return String(v);
}

function FicheBlock({ title, rows }: { title: string; rows: { k: string; v: unknown }[] }) {
  if (rows.length === 0) return null;
  return (
    <section>
      <h3 className="mb-2 text-[10px] font-semibold uppercase tracking-wider text-zinc-500">
        {title}
      </h3>
      <div className="space-y-1 rounded-lg border border-white/[0.04] bg-white/[0.02] p-3">
        {rows.map(({ k, v }) => (
          <div key={k} className="flex items-baseline justify-between gap-3">
            <span className="text-[11px] text-zinc-500">{k}</span>
            <span className="truncate font-mono text-xs text-zinc-200">{fmt(v)}</span>
          </div>
        ))}
      </div>
    </section>
  );
}

function FicheList({
  title,
  items,
  cols,
}: {
  title: string;
  items: Record<string, unknown>[];
  cols: string[];
}) {
  return (
    <section>
      <h3 className="mb-2 text-[10px] font-semibold uppercase tracking-wider text-zinc-500">
        {title}
      </h3>
      <div className="overflow-hidden rounded-lg border border-white/[0.04] bg-white/[0.02]">
        {items.map((it, i) => (
          <div
            key={i}
            className="flex items-center justify-between gap-3 border-b border-white/[0.03] px-3 py-2 last:border-0"
          >
            {cols.map((c) => (
              <span
                key={c}
                className="truncate font-mono text-[11px] text-zinc-300"
              >
                {fmt(it[c])}
              </span>
            ))}
          </div>
        ))}
      </div>
    </section>
  );
}

export default function ExplorerPage() {
  return (
    <Suspense fallback={<div className="flex h-screen items-center justify-center bg-zinc-950 text-zinc-500">Chargement…</div>}>
      <ExplorerInner />
    </Suspense>
  );
}
