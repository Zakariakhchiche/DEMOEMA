"use client";

import { useState, useMemo, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Download, Search, ChevronLeft, ChevronRight, ChevronUp, ChevronDown, ChevronsUpDown, Inbox } from "lucide-react";

interface Column<T> {
  key: keyof T | string;
  header: string;
  width?: string;
  render?: (value: unknown, row: T) => React.ReactNode;
  sortable?: boolean;
}

interface Props<T> {
  data: T[];
  columns: Column<T>[];
  onRowClick?: (row: T) => void;
  loading?: boolean;
  pageSize?: number;
  searchable?: boolean;
  exportable?: boolean;
  onExport?: () => void;
}

type SortDir = "asc" | "desc" | null;

function getValue<T>(row: T, key: keyof T | string): unknown {
  return (row as Record<string, unknown>)[key as string];
}

function SkeletonRows({ cols, count }: { cols: number; count: number }) {
  return (
    <>
      {Array.from({ length: count }).map((_, ri) => (
        <tr key={ri}>
          {Array.from({ length: cols }).map((_, ci) => (
            <td key={ci} className="px-4 py-3.5">
              <div
                className="h-4 rounded-md animate-pulse"
                style={{
                  background: "rgba(255,255,255,0.05)",
                  width: ci === 0 ? "60%" : ci % 2 === 0 ? "80%" : "50%",
                }}
              />
            </td>
          ))}
        </tr>
      ))}
    </>
  );
}

export default function PremiumTable<T extends object>({
  data,
  columns,
  onRowClick,
  loading = false,
  pageSize = 15,
  searchable = true,
  exportable = false,
  onExport,
}: Props<T>) {
  const [query, setQuery] = useState("");
  const [sortKey, setSortKey] = useState<keyof T | string | null>(null);
  const [sortDir, setSortDir] = useState<SortDir>(null);
  const [page, setPage] = useState(1);

  const filtered = useMemo(() => {
    if (!query.trim()) return data;
    const q = query.toLowerCase();
    return data.filter((row) =>
      columns.some((col) => {
        const val = getValue(row, col.key);
        return typeof val === "string" && val.toLowerCase().includes(q);
      })
    );
  }, [data, query, columns]);

  const sorted = useMemo(() => {
    if (!sortKey || !sortDir) return filtered;
    return [...filtered].sort((a, b) => {
      const va = getValue(a, sortKey);
      const vb = getValue(b, sortKey);
      if (va == null && vb == null) return 0;
      if (va == null) return 1;
      if (vb == null) return -1;
      const cmp =
        typeof va === "number" && typeof vb === "number"
          ? va - vb
          : String(va).localeCompare(String(vb), "fr", { numeric: true });
      return sortDir === "asc" ? cmp : -cmp;
    });
  }, [filtered, sortKey, sortDir]);

  const totalPages = Math.max(1, Math.ceil(sorted.length / pageSize));
  const safePage = Math.min(page, totalPages);
  const paginated = sorted.slice((safePage - 1) * pageSize, safePage * pageSize);

  const handleSort = useCallback(
    (key: keyof T | string) => {
      if (sortKey !== key) {
        setSortKey(key);
        setSortDir("asc");
      } else if (sortDir === "asc") {
        setSortDir("desc");
      } else if (sortDir === "desc") {
        setSortKey(null);
        setSortDir(null);
      } else {
        setSortDir("asc");
      }
      setPage(1);
    },
    [sortKey, sortDir]
  );

  const handleSearch = useCallback((v: string) => {
    setQuery(v);
    setPage(1);
  }, []);

  return (
    <div
      className="flex flex-col w-full rounded-xl border border-white/5 overflow-hidden"
      style={{
        background: "#020202",
        fontFamily: "'Inter', 'Outfit', sans-serif",
      }}
    >
      {(searchable || exportable) && (
        <div
          className="flex items-center gap-3 px-4 py-3 border-b border-white/5"
          style={{ background: "rgba(99,102,241,0.03)", backdropFilter: "blur(12px)" }}
        >
          {searchable && (
            <div className="relative flex-1 max-w-xs">
              <Search
                className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5"
                style={{ color: "#6366f1" }}
              />
              <input
                type="text"
                value={query}
                onChange={(e) => handleSearch(e.target.value)}
                placeholder="Rechercher…"
                className="w-full rounded-lg pl-8 pr-3 py-1.5 text-sm outline-none border border-white/8 focus:border-indigo-500/50 transition-colors"
                style={{
                  background: "rgba(255,255,255,0.04)",
                  color: "#ededed",
                }}
              />
            </div>
          )}
          <div className="ml-auto flex items-center gap-2">
            <span className="text-xs" style={{ color: "#6b7280" }}>
              {sorted.length.toLocaleString("fr-FR")} résultat{sorted.length !== 1 ? "s" : ""}
            </span>
            {exportable && (
              <button
                onClick={onExport}
                className="flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-medium border border-white/10 transition-all hover:border-indigo-500/50 hover:bg-indigo-500/5"
                style={{ color: "#ededed" }}
              >
                <Download className="w-3.5 h-3.5" style={{ color: "#6366f1" }} />
                Exporter
              </button>
            )}
          </div>
        </div>
      )}

      <div className="overflow-x-auto">
        <table className="w-full text-sm border-collapse" style={{ minWidth: 480 }}>
          <thead>
            <tr
              className="sticky top-0 z-10"
              style={{
                background: "rgba(2,2,2,0.9)",
                backdropFilter: "blur(16px)",
                borderBottom: "1px solid rgba(255,255,255,0.06)",
              }}
            >
              {columns.map((col) => (
                <th
                  key={String(col.key)}
                  className="px-4 py-3 text-left font-semibold select-none"
                  style={{
                    color: "#6366f1",
                    width: col.width,
                    fontSize: "0.7rem",
                    textTransform: "uppercase",
                    letterSpacing: "0.08em",
                    cursor: col.sortable ? "pointer" : "default",
                    whiteSpace: "nowrap",
                  }}
                  onClick={() => col.sortable && handleSort(col.key)}
                >
                  <span className="inline-flex items-center gap-1.5">
                    {col.header}
                    {col.sortable && (
                      <span className="inline-flex flex-col" style={{ color: "#4f46e5" }}>
                        {sortKey === col.key && sortDir === "asc" ? (
                          <ChevronUp className="w-3 h-3" style={{ color: "#818cf8" }} />
                        ) : sortKey === col.key && sortDir === "desc" ? (
                          <ChevronDown className="w-3 h-3" style={{ color: "#818cf8" }} />
                        ) : (
                          <ChevronsUpDown className="w-3 h-3 opacity-40" />
                        )}
                      </span>
                    )}
                  </span>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <SkeletonRows cols={columns.length} count={pageSize} />
            ) : paginated.length === 0 ? (
              <tr>
                <td colSpan={columns.length}>
                  <div className="flex flex-col items-center justify-center gap-3 py-16" style={{ color: "#374151" }}>
                    <Inbox className="w-10 h-10" style={{ color: "#1e1b4b" }} />
                    <p className="text-sm" style={{ color: "#4b5563" }}>
                      Aucun résultat{query ? ` pour "${query}"` : ""}
                    </p>
                  </div>
                </td>
              </tr>
            ) : (
              <AnimatePresence mode="popLayout" initial={false}>
                {paginated.map((row, ri) => (
                  <motion.tr
                    key={ri}
                    initial={{ opacity: 0, y: 4 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0 }}
                    transition={{ duration: 0.15, delay: ri * 0.015 }}
                    className="group relative transition-colors cursor-pointer"
                    style={{
                      borderBottom: "1px solid rgba(255,255,255,0.03)",
                    }}
                    onClick={() => onRowClick?.(row)}
                  >
                    {columns.map((col, ci) => (
                      <td
                        key={String(col.key)}
                        className="px-4 py-3.5 transition-colors group-hover:bg-indigo-500/5"
                        style={{
                          color: "#ededed",
                          position: ci === 0 ? "relative" : undefined,
                        }}
                      >
                        {ci === 0 && (
                          <span
                            className="absolute left-0 top-0 h-full w-0.5 opacity-0 group-hover:opacity-100 transition-opacity rounded-r-full"
                            style={{ background: "#6366f1" }}
                          />
                        )}
                        {col.render
                          ? col.render(getValue(row, col.key), row)
                          : String(getValue(row, col.key) ?? "")}
                      </td>
                    ))}
                  </motion.tr>
                ))}
              </AnimatePresence>
            )}
          </tbody>
        </table>
      </div>

      {!loading && sorted.length > 0 && (
        <div
          className="flex items-center justify-between px-4 py-3 border-t border-white/5"
          style={{ background: "rgba(99,102,241,0.02)" }}
        >
          <span className="text-xs" style={{ color: "#6b7280" }}>
            Page {safePage} sur {totalPages} — {((safePage - 1) * pageSize) + 1}–
            {Math.min(safePage * pageSize, sorted.length)} / {sorted.length}
          </span>
          <div className="flex items-center gap-1.5">
            <button
              disabled={safePage <= 1}
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              className="flex items-center gap-1 rounded-lg px-3 py-1.5 text-xs border border-white/8 transition-all hover:border-indigo-500/40 hover:bg-indigo-500/5 disabled:opacity-30 disabled:cursor-not-allowed"
              style={{ color: "#ededed" }}
            >
              <ChevronLeft className="w-3.5 h-3.5" />
              Précédent
            </button>

            {totalPages <= 7
              ? Array.from({ length: totalPages }, (_, i) => i + 1).map((p) => (
                  <button
                    key={p}
                    onClick={() => setPage(p)}
                    className="w-7 h-7 rounded-md text-xs font-medium transition-all border"
                    style={{
                      background: p === safePage ? "rgba(99,102,241,0.2)" : "transparent",
                      borderColor: p === safePage ? "rgba(99,102,241,0.5)" : "rgba(255,255,255,0.06)",
                      color: p === safePage ? "#818cf8" : "#6b7280",
                    }}
                  >
                    {p}
                  </button>
                ))
              : (
                <>
                  {[1, 2].map((p) => (
                    <button
                      key={p}
                      onClick={() => setPage(p)}
                      className="w-7 h-7 rounded-md text-xs font-medium transition-all border"
                      style={{
                        background: p === safePage ? "rgba(99,102,241,0.2)" : "transparent",
                        borderColor: p === safePage ? "rgba(99,102,241,0.5)" : "rgba(255,255,255,0.06)",
                        color: p === safePage ? "#818cf8" : "#6b7280",
                      }}
                    >
                      {p}
                    </button>
                  ))}
                  {safePage > 3 && <span className="text-xs px-1" style={{ color: "#4b5563" }}>…</span>}
                  {safePage > 2 && safePage < totalPages - 1 && (
                    <button
                      className="w-7 h-7 rounded-md text-xs font-medium border"
                      style={{
                        background: "rgba(99,102,241,0.2)",
                        borderColor: "rgba(99,102,241,0.5)",
                        color: "#818cf8",
                      }}
                    >
                      {safePage}
                    </button>
                  )}
                  {safePage < totalPages - 2 && <span className="text-xs px-1" style={{ color: "#4b5563" }}>…</span>}
                  {[totalPages - 1, totalPages].map((p) => (
                    <button
                      key={p}
                      onClick={() => setPage(p)}
                      className="w-7 h-7 rounded-md text-xs font-medium transition-all border"
                      style={{
                        background: p === safePage ? "rgba(99,102,241,0.2)" : "transparent",
                        borderColor: p === safePage ? "rgba(99,102,241,0.5)" : "rgba(255,255,255,0.06)",
                        color: p === safePage ? "#818cf8" : "#6b7280",
                      }}
                    >
                      {p}
                    </button>
                  ))}
                </>
              )}

            <button
              disabled={safePage >= totalPages}
              onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
              className="flex items-center gap-1 rounded-lg px-3 py-1.5 text-xs border border-white/8 transition-all hover:border-indigo-500/40 hover:bg-indigo-500/5 disabled:opacity-30 disabled:cursor-not-allowed"
              style={{ color: "#ededed" }}
            >
              Suivant
              <ChevronRight className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
