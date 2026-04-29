"use client";

import { Icon } from "./Icon";

export interface ChatConvSummary {
  id: string;
  title: string;
  updated_at: number;
  type?: "sourcing" | "dd" | "compare" | "graph";
}

interface Props {
  active?: string;
  conversations: ChatConvSummary[];
  onSelect: (id: string) => void;
  onNew: () => void;
  collapsed?: boolean;
}

function relativeTime(ts: number): string {
  const diff = Date.now() - ts;
  if (diff < 60_000) return "à l'instant";
  if (diff < 3600_000) return `il y a ${Math.floor(diff / 60_000)} min`;
  if (diff < 86_400_000) return `il y a ${Math.floor(diff / 3600_000)} h`;
  const d = new Date(ts);
  return d.toLocaleDateString("fr-FR", { day: "numeric", month: "short" });
}

function bucket(ts: number): "today" | "7d" | "30d" | "older" {
  const age = Date.now() - ts;
  if (age < 86_400_000) return "today";
  if (age < 7 * 86_400_000) return "7d";
  if (age < 30 * 86_400_000) return "30d";
  return "older";
}

export function ChatSidebar({ active, conversations, onSelect, onNew, collapsed }: Props) {
  if (collapsed) return null;

  const groups: { key: "today" | "7d" | "30d" | "older"; label: string }[] = [
    { key: "today", label: "Aujourd'hui" },
    { key: "7d", label: "7 derniers jours" },
    { key: "30d", label: "30 derniers jours" },
    { key: "older", label: "Plus ancien" },
  ];

  return (
    <div style={{
      width: 264, borderRight: "1px solid var(--border-subtle)",
      display: "flex", flexDirection: "column",
      background: "rgba(10,10,13,0.40)", flexShrink: 0,
    }}>
      <div style={{ padding: "12px 12px 8px" }}>
        <button
          onClick={onNew}
          className="dem-btn dem-btn-primary"
          style={{ width: "100%", justifyContent: "center", padding: "9px 12px", fontSize: 13 }}
        >
          <Icon name="plus" size={13} /> Nouvelle conversation
          <span style={{ marginLeft: "auto", display: "flex", gap: 3 }}>
            <span className="kbd">⌘</span>
            <span className="kbd">N</span>
          </span>
        </button>
      </div>

      <div style={{ flex: 1, overflowY: "auto", padding: "4px 6px 12px" }}>
        {conversations.length === 0 && (
          <div style={{ padding: "20px 14px", fontSize: 12, color: "var(--text-tertiary)", textAlign: "center" }}>
            Aucune conversation.<br />
            Démarre la première en posant une question.
          </div>
        )}
        {groups.map((g) => {
          const items = conversations.filter((c) => bucket(c.updated_at) === g.key);
          if (!items.length) return null;
          return (
            <div key={g.key} style={{ marginTop: 10 }}>
              <div className="section-label" style={{ padding: "6px 10px" }}>{g.label}</div>
              {items.map((c) => (
                <button
                  key={c.id}
                  onClick={() => onSelect(c.id)}
                  style={{
                    display: "flex", alignItems: "center", gap: 8, width: "100%",
                    padding: "8px 10px", borderRadius: 7, border: "none",
                    background: active === c.id ? "rgba(255,255,255,0.05)" : "transparent",
                    color: active === c.id ? "var(--text-primary)" : "var(--text-secondary)",
                    cursor: "pointer", fontSize: 12.5, textAlign: "left",
                    transition: "background .1s ease",
                  }}
                  onMouseEnter={(e) => {
                    if (active !== c.id) e.currentTarget.style.background = "rgba(255,255,255,0.025)";
                  }}
                  onMouseLeave={(e) => {
                    if (active !== c.id) e.currentTarget.style.background = "transparent";
                  }}
                >
                  <Icon
                    name={c.type === "dd" ? "shield" : c.type === "compare" ? "layers" : c.type === "graph" ? "network" : "search"}
                    size={11}
                    color="var(--text-tertiary)"
                  />
                  <span style={{ flex: 1, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{c.title}</span>
                  <span style={{ fontSize: 10.5, color: "var(--text-muted)", flexShrink: 0 }}>{relativeTime(c.updated_at)}</span>
                </button>
              ))}
            </div>
          );
        })}
      </div>

      <div style={{ borderTop: "1px solid var(--border-subtle)", padding: "8px 10px", display: "flex", gap: 4 }}>
        <button className="dem-btn dem-btn-ghost" style={{ flex: 1, justifyContent: "flex-start" }}>
          <Icon name="settings" size={12} /> Settings
        </button>
        <button className="dem-btn dem-btn-ghost dem-btn-icon" title="Aide">
          <span style={{ fontWeight: 700, fontSize: 11 }}>?</span>
        </button>
      </div>
    </div>
  );
}
