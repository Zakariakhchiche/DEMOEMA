"use client";

import { motion } from "framer-motion";
import { TrendingUp, BarChart3, Save, GitCompareArrows, ExternalLink, Building2 } from "lucide-react";
import { ScoreBadge } from "./ScoreBadge";
import { RedFlagsBadge } from "./RedFlagsBadge";
import type { Cible } from "@/lib/types/dem";
import { cn } from "@/lib/utils";

interface Props {
  target: Cible;
  variant?: "inline" | "full";
  onView?: () => void;
  onSave?: () => void;
  onCompare?: () => void;
  className?: string;
}

function formatEur(value: number | null | undefined): string {
  if (value === null || value === undefined) return "—";
  if (value >= 1_000_000_000) return `${(value / 1_000_000_000).toFixed(1)} Md€`;
  if (value >= 1_000_000) return `${(value / 1_000_000).toFixed(0)} M€`;
  if (value >= 1_000) return `${(value / 1_000).toFixed(0)} K€`;
  return `${value} €`;
}

/**
 * TargetCard — affichage cible M&A inline dans chat ou liste.
 * Glassmorphism deep + score halo signature + 3D depth on hover.
 */
export function TargetCard({
  target,
  variant = "inline",
  onView,
  onSave,
  onCompare,
  className,
}: Props) {
  const trend =
    target.ca_dernier && target.ca_n_minus_1
      ? ((target.ca_dernier - target.ca_n_minus_1) / target.ca_n_minus_1) * 100
      : null;

  return (
    <motion.div
      whileHover={{ y: -2, rotateX: 1, rotateY: -0.5 }}
      transition={{ type: "spring", stiffness: 300, damping: 20 }}
      style={{ transformStyle: "preserve-3d", perspective: 1000 }}
      className={cn(
        "group relative overflow-hidden rounded-xl",
        "bg-zinc-950/40 backdrop-blur-2xl",
        "border border-white/[0.06] hover:border-white/[0.12]",
        "shadow-[0_8px_32px_rgba(0,0,0,0.4)]",
        "transition-all duration-300 will-change-transform",
        variant === "inline" ? "p-4" : "p-6",
        className
      )}
    >
      {/* Top row: denomination + score */}
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2 flex-wrap">
            <h3 className="font-semibold text-zinc-100 tracking-tight truncate">
              {target.denomination}
            </h3>
            {target.is_listed && (
              <span className="inline-flex items-center gap-1 rounded-md bg-cyan-500/10 px-1.5 py-0.5 text-[10px] font-semibold text-cyan-300 ring-1 ring-cyan-500/30">
                <BarChart3 className="h-2.5 w-2.5" />
                COTÉE
              </span>
            )}
            {target.is_pro_ma && (
              <span className="inline-flex items-center gap-1 rounded-md bg-purple-500/10 px-1.5 py-0.5 text-[10px] font-semibold text-purple-300 ring-1 ring-purple-500/30">
                PRO M&A
              </span>
            )}
            {target.is_asset_rich && (
              <span className="inline-flex items-center gap-1 rounded-md bg-yellow-500/10 px-1.5 py-0.5 text-[10px] font-semibold text-yellow-300 ring-1 ring-yellow-500/30">
                ASSET-RICH
              </span>
            )}
          </div>

          <div className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-zinc-500">
            <span className="font-mono tabular-nums">{target.siren}</span>
            <span className="text-zinc-700">·</span>
            <span>
              {target.naf}
              <span className="ml-1 text-zinc-600">{target.naf_libelle}</span>
            </span>
            <span className="text-zinc-700">·</span>
            <span>Dpt {target.siege_dept}</span>
          </div>
        </div>

        <ScoreBadge value={target.pro_ma_score} size="lg" />
      </div>

      {/* Stats row */}
      <div className="mt-4 grid grid-cols-3 gap-3">
        <div>
          <div className="text-[10px] uppercase tracking-wider text-zinc-500">CA</div>
          <div className="mt-0.5 flex items-baseline gap-1.5">
            <span className="font-mono tabular-nums text-sm font-semibold text-zinc-200">
              {formatEur(target.ca_dernier)}
            </span>
            {trend !== null && (
              <span
                className={cn(
                  "inline-flex items-center gap-0.5 text-[10px] font-mono",
                  trend >= 0 ? "text-emerald-400" : "text-rose-400"
                )}
              >
                <TrendingUp className={cn("h-2.5 w-2.5", trend < 0 && "rotate-180")} />
                {trend >= 0 ? "+" : ""}
                {trend.toFixed(0)}%
              </span>
            )}
          </div>
        </div>
        <div>
          <div className="text-[10px] uppercase tracking-wider text-zinc-500">EBITDA</div>
          <div className="mt-0.5 font-mono tabular-nums text-sm font-semibold text-zinc-200">
            {formatEur(target.ebitda_dernier)}
          </div>
        </div>
        <div>
          <div className="text-[10px] uppercase tracking-wider text-zinc-500">Effectif</div>
          <div className="mt-0.5 font-mono tabular-nums text-sm font-semibold text-zinc-200">
            {target.effectif_exact?.toLocaleString("fr-FR") ?? target.effectif_tranche}
          </div>
        </div>
      </div>

      {/* Top dirigeant */}
      {target.top_dirigeant_full_name && (
        <div className="mt-3 flex items-center gap-2 rounded-lg bg-white/[0.02] px-3 py-2 ring-1 ring-white/[0.04]">
          <div className="flex h-7 w-7 items-center justify-center rounded-full bg-gradient-to-br from-purple-500/20 to-pink-500/20 text-xs font-semibold text-purple-200">
            {target.top_dirigeant_full_name
              .split(" ")
              .map((s) => s[0])
              .slice(0, 2)
              .join("")}
          </div>
          <div className="min-w-0 flex-1">
            <div className="truncate text-xs font-medium text-zinc-300">
              {target.top_dirigeant_full_name}
            </div>
            <div className="text-[10px] text-zinc-500">
              {target.top_dirigeant_age ? `${target.top_dirigeant_age} ans` : "—"} ·{" "}
              {target.n_dirigeants} mandats
            </div>
          </div>
          {target.top_dirigeant_pro_ma_score && (
            <ScoreBadge value={target.top_dirigeant_pro_ma_score} size="sm" />
          )}
        </div>
      )}

      {/* Red flags */}
      {target.has_compliance_red_flag && target.red_flags && (
        <div className="mt-2">
          <RedFlagsBadge flags={target.red_flags} />
        </div>
      )}

      {/* Actions */}
      <div className="mt-4 flex items-center gap-2">
        <button
          onClick={onView}
          className="inline-flex items-center gap-1.5 rounded-lg bg-blue-500/10 px-3 py-1.5 text-xs font-medium text-blue-300 ring-1 ring-blue-500/30 transition-all hover:bg-blue-500/20 hover:ring-blue-400/50"
        >
          <Building2 className="h-3.5 w-3.5" />
          Fiche
        </button>
        <button
          onClick={onSave}
          className="inline-flex items-center gap-1.5 rounded-lg bg-white/[0.04] px-3 py-1.5 text-xs font-medium text-zinc-300 ring-1 ring-white/[0.06] transition-all hover:bg-white/[0.08]"
        >
          <Save className="h-3.5 w-3.5" />
          Sauver
        </button>
        <button
          onClick={onCompare}
          className="inline-flex items-center gap-1.5 rounded-lg bg-white/[0.04] px-3 py-1.5 text-xs font-medium text-zinc-300 ring-1 ring-white/[0.06] transition-all hover:bg-white/[0.08]"
        >
          <GitCompareArrows className="h-3.5 w-3.5" />
          Compare
        </button>
        <button
          className="ml-auto inline-flex items-center justify-center rounded-lg p-1.5 text-zinc-500 transition-all hover:bg-white/[0.04] hover:text-zinc-300"
          title="Source INPI"
        >
          <ExternalLink className="h-3.5 w-3.5" />
        </button>
      </div>

      {/* Subtle aurora gradient decorative */}
      <div className="pointer-events-none absolute inset-0 -z-10 opacity-30 [mask-image:radial-gradient(ellipse_at_top_right,black,transparent_70%)]">
        <div className="absolute right-0 top-0 h-32 w-32 rounded-full bg-blue-500/10 blur-3xl" />
      </div>
    </motion.div>
  );
}
