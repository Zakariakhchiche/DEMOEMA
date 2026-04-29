"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import {
  Database,
  ChevronRight,
  Sparkles,
  Newspaper,
  Activity,
  ShieldAlert,
  Network,
  Target,
  Search,
  Loader2,
} from "lucide-react";
import type { TableInfo } from "@/lib/api";
import { cn } from "@/lib/utils";

const CATEGORY_META: Record<string, { label: string; icon: React.ComponentType<{ className?: string }>; color: string }> = {
  core: { label: "Master tables", icon: Database, color: "text-blue-300" },
  ma: { label: "Cibles M&A", icon: Target, color: "text-emerald-300" },
  signals: { label: "Signaux marché", icon: Activity, color: "text-amber-300" },
  press: { label: "Presse", icon: Newspaper, color: "text-cyan-300" },
  risk: { label: "Compliance / Risques", icon: ShieldAlert, color: "text-rose-300" },
  network: { label: "Réseaux", icon: Network, color: "text-purple-300" },
  legal: { label: "Juridique", icon: ShieldAlert, color: "text-orange-300" },
  analytics: { label: "Analytics", icon: Sparkles, color: "text-fuchsia-300" },
  regulatory: { label: "Réglementaire", icon: ShieldAlert, color: "text-yellow-300" },
  osint: { label: "OSINT", icon: Search, color: "text-pink-300" },
  patrimoine: { label: "Patrimoine", icon: Target, color: "text-lime-300" },
};

interface Props {
  tables: TableInfo[];
  active?: string;
  onSelect: (name: string) => void;
  loading?: boolean;
  className?: string;
}

function formatCount(n: number | null): string {
  if (n === null) return "—";
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(0)}k`;
  return n.toLocaleString("fr-FR");
}

export function TableTreeSidebar({ tables, active, onSelect, loading, className }: Props) {
  const [search, setSearch] = useState("");

  const filtered = search
    ? tables.filter(
        (t) =>
          t.name.toLowerCase().includes(search.toLowerCase()) ||
          t.label.toLowerCase().includes(search.toLowerCase())
      )
    : tables;

  const grouped = filtered.reduce<Record<string, TableInfo[]>>((acc, t) => {
    (acc[t.category] ||= []).push(t);
    return acc;
  }, {});

  const orderedCategories = [
    "core",
    "ma",
    "signals",
    "press",
    "risk",
    "network",
    "legal",
    "analytics",
    "regulatory",
    "osint",
    "patrimoine",
  ].filter((k) => grouped[k]);

  return (
    <aside
      className={cn(
        "flex w-72 flex-col border-r border-white/[0.04] bg-zinc-950/50 backdrop-blur-xl",
        className
      )}
    >
      <div className="flex items-center gap-2 border-b border-white/[0.04] p-3">
        <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-emerald-500 to-cyan-500 shadow-[0_0_16px_rgba(16,185,129,0.4)]">
          <Database className="h-4 w-4 text-white" />
        </div>
        <div className="flex-1">
          <div className="text-sm font-semibold text-zinc-100">Data Explorer</div>
          <div className="text-[10px] uppercase tracking-wider text-zinc-500">
            {tables.length} tables · gold + presse
          </div>
        </div>
      </div>

      <div className="px-2 pt-2">
        <div className="flex items-center gap-2 rounded-lg bg-white/[0.02] px-3 py-1.5 ring-1 ring-white/[0.04] focus-within:ring-blue-500/30">
          <Search className="h-3.5 w-3.5 text-zinc-500" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Filtrer tables…"
            className="w-full bg-transparent text-xs text-zinc-200 placeholder-zinc-600 outline-none"
          />
        </div>
      </div>

      <div className="flex-1 overflow-y-auto px-2 pb-2 pt-3">
        {loading && (
          <div className="flex items-center gap-2 px-3 py-4 text-xs text-zinc-500">
            <Loader2 className="h-3.5 w-3.5 animate-spin" />
            Chargement des tables…
          </div>
        )}
        {!loading && tables.length === 0 && (
          <div className="rounded-lg border border-amber-500/20 bg-amber-500/5 p-3 text-[11px] text-amber-200">
            Aucune table gold n&apos;est disponible. Le datalake n&apos;est peut-être pas
            encore connecté à ce backend.
          </div>
        )}
        {orderedCategories.map((cat) => {
          const meta = CATEGORY_META[cat] ?? {
            label: cat,
            icon: Database,
            color: "text-zinc-300",
          };
          const Icon = meta.icon;
          return (
            <div key={cat} className="space-y-0.5 pb-3">
              <div className="flex items-center gap-2 px-3 pb-1 pt-1">
                <Icon className={cn("h-3 w-3", meta.color)} />
                <span className="text-[10px] uppercase tracking-wider text-zinc-500">
                  {meta.label}
                </span>
              </div>
              {grouped[cat].map((t) => (
                <motion.button
                  key={t.name}
                  whileHover={{ x: 2 }}
                  onClick={() => onSelect(t.name)}
                  className={cn(
                    "group flex w-full items-center gap-2 rounded-lg px-3 py-2 text-left text-sm transition-all",
                    "hover:bg-white/[0.04]",
                    active === t.name
                      ? "bg-blue-500/10 text-blue-100 ring-1 ring-blue-500/20"
                      : "text-zinc-400"
                  )}
                >
                  <ChevronRight
                    className={cn(
                      "h-3 w-3 shrink-0 text-zinc-600 transition-transform",
                      active === t.name && "rotate-90 text-blue-300"
                    )}
                  />
                  <div className="min-w-0 flex-1">
                    <div className="truncate text-xs font-medium">{t.label}</div>
                    <div className="truncate font-mono text-[10px] text-zinc-600">
                      {t.name}
                    </div>
                  </div>
                  <span className="shrink-0 rounded bg-white/[0.04] px-1.5 py-0.5 font-mono text-[10px] text-zinc-500">
                    {formatCount(t.row_count_approx)}
                  </span>
                </motion.button>
              ))}
            </div>
          );
        })}
      </div>

      <div className="border-t border-white/[0.04] p-2">
        <a
          href="/copilot"
          className="flex w-full items-center gap-2 rounded-lg bg-gradient-to-br from-purple-500/10 to-blue-500/10 px-3 py-2 text-xs text-zinc-300 ring-1 ring-purple-500/20 transition-all hover:from-purple-500/20 hover:to-blue-500/20"
        >
          <Sparkles className="h-3.5 w-3.5 text-purple-300" />
          Mode Chat Copilot
          <ChevronRight className="ml-auto h-3.5 w-3.5" />
        </a>
      </div>
    </aside>
  );
}
