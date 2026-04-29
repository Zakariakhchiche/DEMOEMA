"use client";

import { useState } from "react";
import { Icon } from "./Icon";
import { WATCHLIST_ALERTS, WATCHLIST_RULES } from "@/lib/dem/data";
import { fetchTargets } from "@/lib/dem/adapter";
import type { Target } from "@/lib/dem/types";

interface Props {
  onOpenTarget: (t: Target) => void;
}

export function WatchlistView({ onOpenTarget }: Props) {
  const [tab, setTab] = useState<"alerts" | "rules">("alerts");

  const openAlert = async (siren: string) => {
    const targets = await fetchTargets({ q: siren, limit: 1 });
    if (targets[0]) onOpenTarget(targets[0]);
  };

  return (
    <div style={{ flex: 1, display: "flex", flexDirection: "column", overflow: "hidden", position: "relative", zIndex: 1 }}>
      <div style={{ padding: "16px 22px 0", borderBottom: "1px solid var(--border-subtle)" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <div style={{ fontSize: 16, fontWeight: 700, letterSpacing: "-0.01em" }}>Watchlist &amp; Alertes</div>
          <span className="dem-mono" style={{ fontSize: 11, color: "var(--text-tertiary)" }}>
            · {WATCHLIST_ALERTS.length} alertes 24h · {WATCHLIST_RULES.filter((r) => r.active).length} règles actives
          </span>
          <span style={{ marginLeft: "auto" }}>
            <button className="dem-btn dem-btn-primary"><Icon name="plus" size={11} /> Nouvelle règle</button>
          </span>
        </div>
        <div style={{ display: "flex", gap: 4, marginTop: 14 }}>
          {[
            { id: "alerts" as const, label: "Alertes", count: WATCHLIST_ALERTS.length },
            { id: "rules" as const, label: "Règles", count: WATCHLIST_RULES.length },
          ].map((t) => (
            <button
              key={t.id}
              onClick={() => setTab(t.id)}
              style={{
                padding: "8px 14px", border: "none", background: "transparent",
                color: tab === t.id ? "var(--text-primary)" : "var(--text-tertiary)",
                borderBottom: `2px solid ${tab === t.id ? "var(--accent-blue)" : "transparent"}`,
                cursor: "pointer", fontSize: 13, fontWeight: tab === t.id ? 600 : 500,
              }}
            >
              {t.label}{" "}
              <span className="dem-mono" style={{ fontSize: 10.5, color: "var(--text-muted)", marginLeft: 4 }}>{t.count}</span>
            </button>
          ))}
        </div>
      </div>

      <div style={{ flex: 1, overflowY: "auto", padding: 22 }}>
        {tab === "alerts" && (
          <div style={{ display: "flex", flexDirection: "column", gap: 8, maxWidth: 920, margin: "0 auto" }}>
            {WATCHLIST_ALERTS.map((a) => (
              <div
                key={a.id}
                className="dem-glass card-lift fade-up"
                style={{ borderRadius: 10, padding: 14, display: "flex", gap: 14, alignItems: "center", cursor: "pointer" }}
                onClick={() => openAlert(a.siren)}
              >
                <span className={`sev-dot ${a.severity}`} />
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                    <span style={{ fontSize: 13.5, fontWeight: 600 }}>{a.target}</span>
                    <span className="dem-mono" style={{ fontSize: 10.5, color: "var(--text-muted)" }}>siren {a.siren}</span>
                  </div>
                  <div style={{ marginTop: 4, fontSize: 12.5, color: a.severity === "high" ? "var(--accent-rose)" : "var(--text-secondary)" }}>
                    {a.title}
                  </div>
                  <div style={{ marginTop: 6, fontSize: 11, color: "var(--text-tertiary)" }}>
                    {a.time} · <span className="dem-mono" style={{ color: "var(--accent-cyan)" }}>{a.source}</span>
                  </div>
                </div>
                <button className="dem-btn"><Icon name="eye" size={11} /> Voir fiche</button>
              </div>
            ))}
          </div>
        )}
        {tab === "rules" && (
          <div style={{ display: "flex", flexDirection: "column", gap: 8, maxWidth: 920, margin: "0 auto" }}>
            {WATCHLIST_RULES.map((r) => (
              <div key={r.id} className="dem-glass" style={{ borderRadius: 10, padding: 16, display: "flex", gap: 14, alignItems: "center" }}>
                <div style={{
                  width: 38, height: 38, borderRadius: 999,
                  background: r.active ? "rgba(52,211,153,0.10)" : "rgba(255,255,255,0.04)",
                  display: "flex", alignItems: "center", justifyContent: "center",
                }}>
                  <Icon name="bookmark" size={15} color={r.active ? "var(--accent-emerald)" : "var(--text-muted)"} />
                </div>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ fontSize: 13.5, fontWeight: 600 }}>{r.name}</div>
                  <div className="dem-mono" style={{ marginTop: 4, fontSize: 11, color: "var(--text-tertiary)" }}>WHEN {r.trigger}</div>
                  <div style={{ marginTop: 4, fontSize: 11, color: "var(--text-muted)" }}>
                    {r.count} cibles surveillées · dernière alerte {r.last}
                  </div>
                </div>
                <span
                  className="dem-chip"
                  style={{
                    background: r.active ? "rgba(52,211,153,0.10)" : "transparent",
                    borderColor: r.active ? "rgba(52,211,153,0.30)" : "var(--border-soft)",
                    color: r.active ? "var(--accent-emerald)" : "var(--text-muted)",
                  }}
                >
                  {r.active ? "● Active" : "○ Inactive"}
                </span>
                <button className="dem-btn dem-btn-ghost dem-btn-icon"><Icon name="more" size={13} /></button>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
