"use client";

import { useState, useMemo } from "react";
import { Loader2, ArrowDown, ArrowUp, AlertTriangle, ChevronLeft, ChevronRight, ExternalLink } from "lucide-react";
import { cn } from "@/lib/utils";

interface Props {
  table: string;
  columns: string[];
  rows: Record<string, unknown>[];
  loading?: boolean;
  error?: string | null;
  hasMore?: boolean;
  offset: number;
  limit: number;
  q: string;
  orderBy?: string;
  onPage: (newOffset: number) => void;
  onSearch: (q: string) => void;
  onOrder: (col: string) => void;
  onRowClick?: (row: Record<string, unknown>) => void;
}

function formatCell(v: unknown): string {
  if (v === null || v === undefined) return "—";
  if (typeof v === "boolean") return v ? "✓" : "✗";
  if (typeof v === "number") {
    if (Math.abs(v) >= 1_000_000) return `${(v / 1_000_000).toFixed(1)}M`;
    if (Math.abs(v) >= 1_000) return v.toLocaleString("fr-FR");
    return String(v);
  }
  if (typeof v === "object") {
    try {
      return JSON.stringify(v).slice(0, 80);
    } catch {
      return "[obj]";
    }
  }
  const s = String(v);
  // ISO date detection (very loose)
  if (/^\d{4}-\d{2}-\d{2}T?/.test(s)) {
    try {
      const d = new Date(s);
      if (!isNaN(d.getTime())) return d.toLocaleDateString("fr-FR");
    } catch {}
  }
  return s.length > 80 ? s.slice(0, 80) + "…" : s;
}

export function DataTable({
  table,
  columns,
  rows,
  loading,
  error,
  hasMore,
  offset,
  limit,
  q,
  orderBy,
  onPage,
  onSearch,
  onOrder,
  onRowClick,
}: Props) {
  const [searchInput, setSearchInput] = useState(q);

  const orderCol = useMemo(() => orderBy?.replace(/^-/, "") ?? null, [orderBy]);
  const orderDesc = useMemo(() => orderBy?.startsWith("-") ?? false, [orderBy]);

  return (
    <div className="flex h-full flex-col">
      {/* Header bar */}
      <div className="flex items-center justify-between gap-3 border-b border-white/[0.04] px-5 py-3">
        <div className="flex flex-1 items-center gap-3">
          <div>
            <div className="font-mono text-[11px] uppercase tracking-wider text-zinc-500">
              Table active
            </div>
            <div className="mt-0.5 font-mono text-sm font-semibold text-zinc-100">
              {table}
            </div>
          </div>
          <div className="ml-4 flex flex-1 items-center gap-2 rounded-lg bg-white/[0.02] px-3 py-1.5 ring-1 ring-white/[0.04] focus-within:ring-blue-500/30">
            <input
              value={searchInput}
              onChange={(e) => setSearchInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") onSearch(searchInput);
              }}
              placeholder={`Recherche dans ${table}…`}
              className="flex-1 bg-transparent text-xs text-zinc-200 placeholder-zinc-600 outline-none"
            />
            <button
              onClick={() => onSearch(searchInput)}
              className="rounded bg-blue-500/20 px-2 py-0.5 text-[10px] font-semibold text-blue-200 ring-1 ring-blue-500/30 hover:bg-blue-500/30"
            >
              Rechercher
            </button>
          </div>
        </div>

        <div className="flex items-center gap-2 text-[11px] text-zinc-500">
          <button
            disabled={offset === 0 || loading}
            onClick={() => onPage(Math.max(0, offset - limit))}
            className="rounded bg-white/[0.04] p-1 text-zinc-300 ring-1 ring-white/[0.06] hover:bg-white/[0.08] disabled:opacity-30"
          >
            <ChevronLeft className="h-3.5 w-3.5" />
          </button>
          <span className="font-mono">
            {offset + 1} – {offset + rows.length}
          </span>
          <button
            disabled={!hasMore || loading}
            onClick={() => onPage(offset + limit)}
            className="rounded bg-white/[0.04] p-1 text-zinc-300 ring-1 ring-white/[0.06] hover:bg-white/[0.08] disabled:opacity-30"
          >
            <ChevronRight className="h-3.5 w-3.5" />
          </button>
        </div>
      </div>

      {/* Errors */}
      {error && (
        <div className="flex items-start gap-2 border-b border-rose-500/20 bg-rose-500/5 px-5 py-2 text-[12px] text-rose-200">
          <AlertTriangle className="mt-0.5 h-3.5 w-3.5 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Body */}
      <div className="relative flex-1 overflow-auto">
        {loading && (
          <div className="absolute inset-x-0 top-0 z-10 flex items-center justify-center gap-2 bg-blue-500/5 py-1.5 text-[11px] text-blue-200">
            <Loader2 className="h-3 w-3 animate-spin" />
            Chargement…
          </div>
        )}

        {!loading && rows.length === 0 && !error && (
          <div className="flex h-full flex-col items-center justify-center gap-2 text-zinc-500">
            <div className="text-sm">Aucune ligne pour cette recherche.</div>
            <div className="text-[11px] text-zinc-600">{table}</div>
          </div>
        )}

        {rows.length > 0 && (
          <table className="min-w-full text-xs">
            <thead className="sticky top-0 z-[5] bg-zinc-950/95 backdrop-blur-xl">
              <tr className="border-b border-white/[0.06]">
                {columns.map((col) => {
                  const isActive = orderCol === col;
                  return (
                    <th
                      key={col}
                      onClick={() => onOrder(isActive && !orderDesc ? `-${col}` : col)}
                      className={cn(
                        "cursor-pointer select-none px-4 py-2.5 text-left font-mono text-[10px] uppercase tracking-wider text-zinc-500 transition-colors hover:text-zinc-200",
                        isActive && "text-blue-300"
                      )}
                    >
                      <span className="inline-flex items-center gap-1">
                        {col}
                        {isActive && (orderDesc ? <ArrowDown className="h-3 w-3" /> : <ArrowUp className="h-3 w-3" />)}
                      </span>
                    </th>
                  );
                })}
                <th className="w-8" />
              </tr>
            </thead>
            <tbody>
              {rows.map((row, i) => (
                <tr
                  key={i}
                  onClick={() => onRowClick?.(row)}
                  className={cn(
                    "border-b border-white/[0.03] transition-colors",
                    onRowClick && "cursor-pointer hover:bg-blue-500/5"
                  )}
                >
                  {columns.map((col) => (
                    <td
                      key={col}
                      className="max-w-[280px] truncate px-4 py-2 font-mono tabular-nums text-zinc-300"
                      title={row[col] != null ? String(row[col]) : ""}
                    >
                      {formatCell(row[col])}
                    </td>
                  ))}
                  <td className="px-2 py-2">
                    {onRowClick && (
                      <ExternalLink className="h-3 w-3 text-zinc-600" />
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
