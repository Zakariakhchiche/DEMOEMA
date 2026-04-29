"use client";

import { useState } from "react";
import { Icon } from "./Icon";
import { AUDIT_LOG } from "@/lib/dem/data";
import type { AuditEntry } from "@/lib/dem/types";

const ACTIONS = [
  { id: "all" as const, label: "Tous", icon: "list" },
  { id: "viewed" as const, label: "Consultations", icon: "eye" },
  { id: "exported" as const, label: "Exports", icon: "download" },
  { id: "queried" as const, label: "Requêtes", icon: "search" },
  { id: "saved" as const, label: "Sauvegardes", icon: "bookmark" },
  { id: "compared" as const, label: "Comparaisons", icon: "layers" },
];

const COLOR_FOR: Record<AuditEntry["action"], string> = {
  viewed: "var(--accent-blue)",
  exported: "var(--accent-amber)",
  queried: "var(--accent-cyan)",
  saved: "var(--accent-emerald)",
  compared: "var(--accent-purple)",
};

export function AuditView() {
  const [filter, setFilter] = useState<typeof ACTIONS[number]["id"]>("all");
  const filtered = filter === "all" ? AUDIT_LOG : AUDIT_LOG.filter((a) => a.action === filter);

  return (
    <div style={{ flex: 1, display: "flex", flexDirection: "column", overflow: "hidden", position: "relative", zIndex: 1 }}>
      <div style={{ padding: "16px 22px 12px", borderBottom: "1px solid var(--border-subtle)" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <div style={{ fontSize: 16, fontWeight: 700, letterSpacing: "-0.01em" }}>Audit · qui a vu quoi</div>
          <span className="dem-mono" style={{ fontSize: 11, color: "var(--text-tertiary)" }}>
            · {AUDIT_LOG.length} actions sur 14 jours · 6 utilisateurs
          </span>
          <span style={{ marginLeft: "auto", display: "flex", gap: 6 }}>
            <button className="dem-btn"><Icon name="download" size={11} /> Export CSV</button>
            <button className="dem-btn"><Icon name="shield" size={11} /> Rapport conformité</button>
          </span>
        </div>
        <div style={{ marginTop: 12, display: "flex", gap: 6, flexWrap: "wrap" }}>
          {ACTIONS.map((a) => (
            <button
              key={a.id}
              className={`dem-chip ${filter === a.id ? "dem-chip-active" : ""}`}
              onClick={() => setFilter(a.id)}
            >
              <Icon name={a.icon} size={10} /> {a.label}
            </button>
          ))}
        </div>
      </div>

      <div style={{ flex: 1, overflowY: "auto", padding: "16px 22px" }}>
        <div style={{ maxWidth: 920, margin: "0 auto" }}>
          {(["aujourd'hui", "hier"] as const).map((date) => {
            const items = filtered.filter((a) => a.date === date);
            if (!items.length) return null;
            return (
              <div key={date} style={{ marginBottom: 24 }}>
                <div className="section-label" style={{ marginBottom: 10 }}>{date}</div>
                <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
                  {items.map((a) => (
                    <div key={a.id} style={{
                      display: "flex", alignItems: "center", gap: 12,
                      padding: "10px 14px", borderRadius: 8,
                      background: "rgba(255,255,255,0.02)",
                    }}>
                      <div style={{
                        width: 30, height: 30, borderRadius: 999,
                        background: "rgba(255,255,255,0.04)",
                        display: "flex", alignItems: "center", justifyContent: "center",
                        flexShrink: 0, fontSize: 11, fontWeight: 600, color: "var(--text-secondary)",
                      }}>
                        {a.who.split(" ").map((p) => p[0]).join("")}
                      </div>
                      <div style={{ flex: 1, minWidth: 0, fontSize: 12.5 }}>
                        <span style={{ fontWeight: 600, color: "var(--text-primary)" }}>{a.who}</span>
                        <span style={{ color: "var(--text-tertiary)" }}> · {a.role}</span>
                        <span style={{ margin: "0 8px", color: COLOR_FOR[a.action], fontWeight: 500 }}>{a.action}</span>
                        <span style={{ color: "var(--text-secondary)" }}>{a.target}</span>
                      </div>
                      <span style={{ fontSize: 11, color: "var(--text-tertiary)" }}>{a.surface}</span>
                      <span className="dem-mono tab-num" style={{
                        fontSize: 11, color: "var(--text-muted)",
                        minWidth: 40, textAlign: "right",
                      }}>{a.time}</span>
                    </div>
                  ))}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
