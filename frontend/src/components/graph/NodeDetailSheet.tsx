"use client";

import { X, AlertTriangle, Zap, ArrowUpRight, Building2 } from "lucide-react";
import Link from "next/link";

interface GraphNode {
  id: string;
  name: string;
  type: string;
  role: string;
  color: string;
  company?: string;
  score?: number;
  signals_count?: number;
  signals?: string[];
  is_holding?: boolean;
}

interface NodeDetailSheetProps {
  node: GraphNode | null;
  onClose: () => void;
}

const typeLabel = (type: string) => {
  if (type === "internal") return "Équipe EDR";
  if (type === "target") return "Cible";
  if (type === "advisor") return "Conseil";
  if (type === "subsidiary") return "Filiale";
  return type;
};

export default function NodeDetailSheet({ node, onClose }: NodeDetailSheetProps) {
  if (!node) return null;

  return (
    <div className="fixed lg:relative bottom-0 left-0 right-0 lg:bottom-auto lg:left-auto lg:right-auto lg:col-span-1 rounded-t-[2rem] lg:rounded-[2rem] bg-black/90 lg:bg-black/40 border border-white/10 lg:backdrop-blur-3xl p-6 sm:p-8 flex flex-col max-h-[65vh] lg:max-h-full overflow-y-auto shadow-2xl space-y-6 z-[60]"
      style={{ paddingBottom: "max(env(safe-area-inset-bottom, 0px), 1.5rem)" }}
    >
      {/* Mobile handle + close */}
      <div className="flex items-center justify-between lg:hidden mb-1">
        <div className="absolute top-2 left-1/2 -translate-x-1/2 w-10 h-1 rounded-full bg-white/20" />
        <span className="text-[10px] font-black text-gray-600 uppercase tracking-widest">
          Fiche Contact
        </span>
        <button
          onClick={onClose}
          className="p-2 rounded-lg bg-white/5 text-gray-500 active:scale-95"
          aria-label="Fermer"
        >
          <X size={16} />
        </button>
      </div>

      {/* Avatar + Name */}
      <div className="space-y-4">
        <div
          className="w-14 h-14 lg:w-16 lg:h-16 rounded-[1.2rem] lg:rounded-[1.5rem] flex items-center justify-center text-white font-black text-xl lg:text-2xl shadow-[0_0_20px_rgba(99,102,241,0.2)]"
          style={{
            backgroundColor: node.color + "20",
            border: `1px solid ${node.color}40`,
          }}
        >
          {node.name
            .split(" ")
            .map((n) => n[0])
            .join("")
            .substring(0, 2)}
        </div>
        <div>
          <div className="flex items-center gap-2 flex-wrap">
            <h2 className="text-xl lg:text-2xl font-black text-white leading-tight tracking-tighter">
              {node.name}
            </h2>
            {node.is_holding && (
              <span className="px-2 py-0.5 rounded-lg bg-purple-500/10 border border-purple-500/20 text-[9px] font-black text-purple-400 uppercase tracking-widest flex items-center gap-1">
                <Building2 size={10} /> Groupe
              </span>
            )}
          </div>
          <p className="text-indigo-400 text-[10px] font-black uppercase tracking-widest mt-1 opacity-80">
            {node.role}
          </p>
        </div>
      </div>

      {/* Meta grid */}
      <div className="grid grid-cols-2 gap-3">
        <div className="p-3 lg:p-4 rounded-2xl lg:rounded-3xl bg-white/[0.03] border border-white/5 space-y-1">
          <div className="text-[9px] font-black text-gray-600 uppercase tracking-widest">
            Type
          </div>
          <div className="text-sm font-black text-white capitalize">
            {typeLabel(node.type)}
          </div>
        </div>
        <div className="p-3 lg:p-4 rounded-2xl lg:rounded-3xl bg-white/[0.03] border border-white/5 space-y-1">
          <div className="text-[9px] font-black text-gray-600 uppercase tracking-widest">
            Score
          </div>
          <div className="text-sm font-black text-white">
            {node.score ? `${node.score}/100` : "N/A"}
          </div>
        </div>
      </div>

      {/* Company */}
      {node.company && (
        <div className="space-y-2">
          <h3 className="text-[10px] font-black text-gray-600 uppercase tracking-[0.2em]">
            Entreprise
          </h3>
          <div className="p-3 rounded-xl bg-white/[0.02] border border-white/5">
            <div className="text-sm font-bold text-gray-300">{node.company}</div>
          </div>
        </div>
      )}

      {/* Signals */}
      {(node.signals_count ?? 0) > 0 && node.signals && (
        <div className="space-y-3">
          <h3 className="text-[10px] font-black text-gray-600 uppercase tracking-[0.2em] flex items-center gap-2">
            <AlertTriangle size={12} className="text-red-400" />
            Signaux actifs ({node.signals_count})
          </h3>
          <div className="space-y-2">
            {node.signals.map((sig, i) => (
              <div
                key={i}
                className="flex items-start gap-2 p-2.5 rounded-xl bg-red-500/5 border border-red-500/10"
              >
                <div className="w-1.5 h-1.5 rounded-full bg-red-400 mt-1.5 shrink-0" />
                <span className="text-xs text-gray-300 font-medium leading-snug">
                  {sig}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Intelligence path */}
      <div className="space-y-4">
        <h3 className="text-[10px] font-black text-gray-600 uppercase tracking-[0.2em]">
          Intelligence Chemin
        </h3>
        <div className="p-4 rounded-2xl lg:rounded-3xl bg-indigo-500/5 border border-indigo-500/10 flex gap-3">
          <Zap size={18} className="text-indigo-400 shrink-0" />
          <p className="text-xs text-gray-400 leading-relaxed font-medium">
            Connexion identifiée via le{" "}
            <span className="text-white font-bold">réseau EdRCF 6.0</span>.
            Analyse de proximité basée sur les données Pappers et le mapping
            relationnel.
          </p>
        </div>
      </div>

      {/* CTA */}
      {node.type === "target" && (
        <div className="pt-4 mt-auto">
          <Link
            href={`/targets/${node.id}`}
            className="w-full py-3.5 lg:py-4 rounded-[1.2rem] lg:rounded-[1.5rem] bg-white text-black font-black text-xs uppercase tracking-widest hover:bg-indigo-50 transition-all shadow-[0_10px_30px_rgba(0,0,0,0.2)] flex items-center justify-center gap-3 active:scale-95"
          >
            Ouvrir la Fiche <ArrowUpRight size={18} />
          </Link>
        </div>
      )}
    </div>
  );
}
