"use client";

import { Icon } from "./Icon";
import { CONVERSATIONS, SAVED_SEARCHES } from "@/lib/dem/data";

interface Props {
  active?: string;
  onSelect: (id: string) => void;
  onNew: () => void;
  collapsed?: boolean;
}

const GROUPS = [
  { key: "today" as const, label: "Aujourd'hui" },
  { key: "7d" as const, label: "7 derniers jours" },
  { key: "30d" as const, label: "30 derniers jours" },
];

export function ChatSidebar({ active, onSelect, onNew, collapsed }: Props) {
  if (collapsed) return null;
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
        {GROUPS.map((g) => {
          const items = CONVERSATIONS.filter((c) => c.group === g.key);
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
                  {c.proactive ? (
                    <span style={{
                      width: 6, height: 6, borderRadius: 999,
                      background: "var(--accent-cyan)",
                      boxShadow: "0 0 8px var(--accent-cyan)",
                      flexShrink: 0,
                    }} />
                  ) : (
                    <Icon
                      name={c.type === "dd" ? "shield" : c.type === "compare" ? "layers" : c.type === "graph" ? "network" : "search"}
                      size={11}
                      color="var(--text-tertiary)"
                    />
                  )}
                  <span style={{ flex: 1, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{c.title}</span>
                  <span style={{ fontSize: 10.5, color: "var(--text-muted)", flexShrink: 0 }}>{c.time}</span>
                </button>
              ))}
            </div>
          );
        })}

        <div style={{ marginTop: 18 }}>
          <div className="section-label" style={{ padding: "6px 10px" }}>Recherches sauvées</div>
          {SAVED_SEARCHES.map((s) => (
            <button
              key={s.id}
              style={{
                display: "flex", alignItems: "center", gap: 8, width: "100%",
                padding: "8px 10px", borderRadius: 7, border: "none",
                background: "transparent", color: "var(--text-secondary)",
                cursor: "pointer", fontSize: 12.5, textAlign: "left",
              }}
              onMouseEnter={(e) => (e.currentTarget.style.background = "rgba(255,255,255,0.025)")}
              onMouseLeave={(e) => (e.currentTarget.style.background = "transparent")}
            >
              <Icon name="bookmark" size={11} color="var(--text-tertiary)" />
              <span style={{ flex: 1 }}>{s.name}</span>
              <span className="dem-mono" style={{ fontSize: 10.5, color: "var(--text-muted)" }}>{s.count}</span>
            </button>
          ))}
        </div>
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
