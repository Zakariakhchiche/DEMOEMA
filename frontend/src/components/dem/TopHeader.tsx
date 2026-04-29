"use client";

import { Icon } from "./Icon";
import type { Mode } from "@/lib/dem/types";

const TABS: { k: Mode; icon: string; label: string }[] = [
  { k: "dashboard", icon: "grid", label: "Home" },
  { k: "chat", icon: "chat", label: "Chat" },
  { k: "pipeline", icon: "kanban", label: "Pipeline" },
  { k: "watchlist", icon: "bookmark", label: "Watchlist" },
  { k: "explorer", icon: "table", label: "Explorer" },
  { k: "graph", icon: "network", label: "Graphe" },
  { k: "compare", icon: "grid", label: "Comparer" },
  { k: "audit", icon: "shield", label: "Audit" },
];

interface Props {
  mode: Mode;
  setMode: (m: Mode) => void;
  onCmdK: () => void;
}

export function TopHeader({ mode, setMode, onCmdK }: Props) {
  return (
    <div style={{
      height: 52,
      borderBottom: "1px solid var(--border-subtle)",
      display: "flex", alignItems: "center",
      padding: "0 16px", gap: 16,
      background: "rgba(10,10,13,0.60)",
      backdropFilter: "blur(20px)",
      position: "relative", zIndex: 10,
    }}>
      <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
        <div style={{
          width: 24, height: 24, borderRadius: 7,
          background: "conic-gradient(from 90deg, #60a5fa, #a78bfa, #67e8f9, #60a5fa)",
          boxShadow: "0 0 16px -2px rgba(167,139,250,0.5)",
        }} />
        <div style={{ fontWeight: 700, letterSpacing: "-0.02em", fontSize: 15, color: "var(--text-primary)" }}>DEMOEMA</div>
        <span style={{
          fontSize: 10, padding: "2px 6px", borderRadius: 4,
          background: "rgba(167,139,250,0.10)",
          border: "1px solid rgba(167,139,250,0.25)",
          color: "var(--accent-purple)",
          fontWeight: 600, letterSpacing: "0.05em",
        }}>BETA</span>
      </div>

      <div style={{
        display: "flex", gap: 2, marginLeft: 16, padding: 3,
        background: "rgba(255,255,255,0.025)", borderRadius: 8,
        border: "1px solid var(--border-subtle)",
      }}>
        {TABS.map((t) => (
          <button
            key={t.k}
            onClick={() => setMode(t.k)}
            style={{
              display: "inline-flex", alignItems: "center", gap: 6,
              padding: "5px 11px", borderRadius: 6, border: "none",
              background: mode === t.k ? "rgba(96,165,250,0.14)" : "transparent",
              color: mode === t.k ? "#cfe1fb" : "var(--text-secondary)",
              cursor: "pointer", fontSize: 12.5, fontWeight: 500,
              boxShadow: mode === t.k ? "inset 0 0 0 1px rgba(96,165,250,0.30)" : "none",
              transition: "all .12s ease",
            }}
          >
            <Icon name={t.icon} size={13} />
            {t.label}
          </button>
        ))}
      </div>

      <button
        onClick={onCmdK}
        style={{
          flex: 1, maxWidth: 360, marginLeft: 12,
          display: "flex", alignItems: "center", gap: 8,
          padding: "6px 12px", borderRadius: 8,
          border: "1px solid var(--border-subtle)",
          background: "rgba(255,255,255,0.02)",
          color: "var(--text-tertiary)",
          cursor: "pointer", fontSize: 12.5,
          transition: "all .12s ease",
        }}
      >
        <Icon name="search" size={13} />
        <span>Rechercher conversations, cibles, dirigeants…</span>
        <span style={{ marginLeft: "auto", display: "flex", gap: 3 }}>
          <span className="kbd">⌘</span>
          <span className="kbd">K</span>
        </span>
      </button>

      <div style={{ marginLeft: "auto", display: "flex", gap: 6, alignItems: "center" }}>
        <button className="dem-btn dem-btn-ghost dem-btn-icon" title="Notifications" style={{ position: "relative" }}>
          <Icon name="bell" size={14} />
          <span style={{
            position: "absolute", top: 4, right: 4,
            width: 6, height: 6, borderRadius: 999,
            background: "var(--accent-rose)",
            boxShadow: "0 0 8px var(--accent-rose)",
          }} />
        </button>
        <div style={{
          display: "flex", alignItems: "center", gap: 8,
          padding: "3px 10px 3px 4px", borderRadius: 999,
          border: "1px solid var(--border-subtle)",
          background: "rgba(255,255,255,0.02)",
        }}>
          <div style={{
            width: 22, height: 22, borderRadius: 999,
            background: "linear-gradient(135deg, #60a5fa, #a78bfa)",
            display: "flex", alignItems: "center", justifyContent: "center",
            fontSize: 10, fontWeight: 700, color: "#0a0a0d",
          }}>AD</div>
          <span style={{ fontSize: 12, color: "var(--text-secondary)" }}>Anne Dupont</span>
        </div>
      </div>
    </div>
  );
}
