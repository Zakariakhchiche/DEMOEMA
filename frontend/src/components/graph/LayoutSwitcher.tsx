"use client";

import { Network, GitBranch, Circle, Sun } from "lucide-react";

type LayoutType = "force" | "dagre" | "radial" | "circular";

const LAYOUTS: { key: LayoutType; label: string; icon: typeof Network }[] = [
  { key: "force", label: "Force", icon: Network },
  { key: "dagre", label: "Hiérarchie", icon: GitBranch },
  { key: "radial", label: "Radial", icon: Sun },
  { key: "circular", label: "Circulaire", icon: Circle },
];

interface LayoutSwitcherProps {
  current: LayoutType;
  onChange: (layout: LayoutType) => void;
}

export default function LayoutSwitcher({ current, onChange }: LayoutSwitcherProps) {
  return (
    <div className="flex items-center gap-1 p-1 rounded-2xl bg-black/60 border border-white/10">
      {LAYOUTS.map(({ key, label, icon: Icon }) => (
        <button
          key={key}
          onClick={() => onChange(key)}
          className={`flex items-center gap-2 px-3 py-2 rounded-xl text-[10px] font-black uppercase tracking-widest transition-all ${
            current === key
              ? "bg-white/10 text-white border border-white/20"
              : "text-gray-500 hover:text-gray-300 hover:bg-white/5"
          }`}
          title={label}
        >
          <Icon size={14} />
          <span className="hidden sm:inline">{label}</span>
        </button>
      ))}
    </div>
  );
}
