"use client";

import { motion } from "framer-motion";
import { cn } from "@/lib/utils";

interface ScoreBadgeProps {
  value: number; // 0-100
  size?: "sm" | "md" | "lg" | "xl";
  showLabel?: boolean;
  pulse?: boolean;
  className?: string;
}

/**
 * Score halo badge — signature DEMOEMA.
 * - score >= 70 : emerald glow (Tier 1, hot M&A)
 * - score 50-69 : amber glow (Tier 2)
 * - score 30-49 : rose subtle (Tier 3)
 * - score < 30  : muted (skip)
 */
export function ScoreBadge({
  value,
  size = "md",
  showLabel = false,
  pulse = false,
  className,
}: ScoreBadgeProps) {
  const tier =
    value >= 70 ? "high" : value >= 50 ? "medium" : value >= 30 ? "low" : "muted";

  const sizes = {
    sm: "w-8 h-8 text-xs",
    md: "w-12 h-12 text-sm",
    lg: "w-16 h-16 text-base",
    xl: "w-24 h-24 text-2xl",
  };

  const colors = {
    high: {
      bg: "bg-emerald-500/10",
      ring: "ring-emerald-400/40",
      text: "text-emerald-300",
      glow: "shadow-[0_0_24px_rgba(52,211,153,0.4)]",
      dot: "bg-emerald-400",
    },
    medium: {
      bg: "bg-amber-500/10",
      ring: "ring-amber-400/40",
      text: "text-amber-300",
      glow: "shadow-[0_0_16px_rgba(251,191,36,0.3)]",
      dot: "bg-amber-400",
    },
    low: {
      bg: "bg-rose-500/10",
      ring: "ring-rose-400/40",
      text: "text-rose-300",
      glow: "shadow-[0_0_12px_rgba(251,113,133,0.3)]",
      dot: "bg-rose-400",
    },
    muted: {
      bg: "bg-zinc-800/50",
      ring: "ring-zinc-700",
      text: "text-zinc-500",
      glow: "",
      dot: "bg-zinc-500",
    },
  } as const;

  const c = colors[tier];

  return (
    <motion.div
      initial={pulse ? { scale: 0.95 } : false}
      animate={pulse ? { scale: [0.95, 1.02, 0.95] } : {}}
      transition={pulse ? { duration: 2, repeat: Infinity } : {}}
      className={cn(
        "relative inline-flex items-center justify-center rounded-full font-mono tabular-nums font-semibold",
        "ring-2 transition-all duration-300",
        sizes[size],
        c.bg,
        c.ring,
        c.text,
        c.glow,
        className
      )}
    >
      <span>{value}</span>
      {showLabel && (
        <span className="absolute -bottom-5 text-[10px] uppercase tracking-wider opacity-70">
          {tier === "high"
            ? "Tier 1"
            : tier === "medium"
            ? "Tier 2"
            : tier === "low"
            ? "Tier 3"
            : "—"}
        </span>
      )}
    </motion.div>
  );
}
