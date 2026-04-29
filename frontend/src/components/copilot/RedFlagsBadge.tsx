"use client";

import { ShieldAlert, Globe, Gavel, Building2 } from "lucide-react";
import { cn } from "@/lib/utils";

const flagIcons: Record<string, React.ComponentType<{ className?: string }>> = {
  amf_listes_noires: ShieldAlert,
  icij_offshore_panama: Globe,
  icij_offshore_pandora: Globe,
  procedure_collective: Gavel,
  sanction_opensanctions: ShieldAlert,
  bodacc_difficulte: Building2,
};

const flagLabels: Record<string, string> = {
  amf_listes_noires: "AMF",
  icij_offshore_panama: "Panama",
  icij_offshore_pandora: "Pandora",
  procedure_collective: "Procédure",
  sanction_opensanctions: "Sanction",
  bodacc_difficulte: "Difficulté",
};

interface Props {
  flags: string[];
  className?: string;
}

export function RedFlagsBadge({ flags, className }: Props) {
  if (!flags || flags.length === 0) return null;

  return (
    <div className={cn("flex items-center gap-1", className)}>
      {flags.slice(0, 3).map((flag) => {
        const Icon = flagIcons[flag] ?? ShieldAlert;
        return (
          <span
            key={flag}
            title={flagLabels[flag] ?? flag}
            className="inline-flex items-center gap-1 rounded-md bg-rose-500/10 px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wider text-rose-300 ring-1 ring-rose-500/30"
          >
            <Icon className="h-3 w-3" />
            <span className="hidden sm:inline">{flagLabels[flag]}</span>
          </span>
        );
      })}
      {flags.length > 3 && (
        <span className="text-[10px] text-zinc-500">+{flags.length - 3}</span>
      )}
    </div>
  );
}
