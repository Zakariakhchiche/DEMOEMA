"use client";

import { useEffect, useState } from "react";
import { Icon } from "./Icon";
import { datalakeApi } from "@/lib/api";

interface AuditEntry {
  id: number;
  agent_role: string;
  source_id: string;
  action: string;
  status: string;
  duration_ms: number;
  llm_model: string | null;
  llm_tokens: number | null;
  created_at: string;
}

const COLOR_FOR: Record<string, string> = {
  ok: "var(--accent-emerald)",
  success: "var(--accent-emerald)",
  done: "var(--accent-emerald)",
  failed: "var(--accent-rose)",
  error: "var(--accent-rose)",
  running: "var(--accent-cyan)",
  pending: "var(--accent-amber)",
  skipped: "var(--text-muted)",
};

function fmtRelativeDate(iso: string): string {
  const d = new Date(iso);
  if (isNaN(d.getTime())) return iso;
  return d.toLocaleString("fr-FR", { dateStyle: "short", timeStyle: "short" });
}

export function AuditView() {
  const [entries, setEntries] = useState<AuditEntry[]>([]);
  const [filter, setFilter] = useState<string>("all");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    datalakeApi
      .auditLog(100)
      .then((r) => {
        setEntries(r.entries);
        if (r.notice) setError(r.notice);
      })
      .catch((e) => setError(e instanceof Error ? e.message : String(e)))
      .finally(() => setLoading(false));
  }, []);

  const actionTypes = Array.from(new Set(entries.map((e) => e.action))).slice(0, 10);

  const filtered = filter === "all" ? entries : entries.filter((a) => a.action === filter);

  return (
    <div style={{ flex: 1, display: "flex", flexDirection: "column", overflow: "hidden", position: "relative", zIndex: 1 }}>
      <div style={{ padding: "16px 22px 12px", borderBottom: "1px solid var(--border-subtle)" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <h1 style={{ margin: 0, fontSize: 16, fontWeight: 700, letterSpacing: "-0.01em" }}>Audit · agents datalake</h1>
          <span className="dem-mono" style={{ fontSize: 11, color: "var(--text-tertiary)" }}>
            · {entries.length} actions live · audit.agent_actions
          </span>
          <span style={{ marginLeft: "auto", display: "flex", gap: 6 }}>
            <button className="dem-btn"><Icon name="download" size={11} /> Export CSV</button>
            <button className="dem-btn"><Icon name="shield" size={11} /> Rapport conformité</button>
          </span>
        </div>
        {actionTypes.length > 0 && (
          <div style={{ marginTop: 12, display: "flex", gap: 6, flexWrap: "wrap" }}>
            <button
              className={`dem-chip ${filter === "all" ? "dem-chip-active" : ""}`}
              onClick={() => setFilter("all")}
            >
              <Icon name="list" size={10} /> Tous
            </button>
            {actionTypes.map((a) => (
              <button
                key={a}
                className={`dem-chip ${filter === a ? "dem-chip-active" : ""}`}
                onClick={() => setFilter(a)}
              >
                {a}
              </button>
            ))}
          </div>
        )}
      </div>

      <div style={{ flex: 1, overflowY: "auto", padding: "16px 22px" }}>
        {loading && <div style={{ padding: 24, textAlign: "center", color: "var(--text-tertiary)" }}>Chargement…</div>}
        {error && (
          <div style={{
            padding: "8px 12px", margin: "0 auto 12px", maxWidth: 920,
            borderRadius: 8,
            background: "rgba(251,113,133,0.06)",
            border: "1px solid rgba(251,113,133,0.20)",
            color: "var(--accent-rose)", fontSize: 12,
          }}>
            <Icon name="warning" size={11} /> {error}
          </div>
        )}
        {!loading && filtered.length === 0 && !error && (
          <div style={{ padding: 32, textAlign: "center", color: "var(--text-tertiary)" }}>
            Aucune entrée d&apos;audit.
          </div>
        )}
        <div style={{ maxWidth: 920, margin: "0 auto", display: "flex", flexDirection: "column", gap: 4 }}>
          {filtered.map((a) => {
            const color = COLOR_FOR[a.status?.toLowerCase()] ?? "var(--text-secondary)";
            return (
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
                  textTransform: "uppercase",
                }}>
                  {a.agent_role.slice(0, 2)}
                </div>
                <div style={{ flex: 1, minWidth: 0, fontSize: 12.5 }}>
                  <span style={{ fontWeight: 600, color: "var(--text-primary)" }}>{a.agent_role}</span>
                  <span style={{ margin: "0 8px", color, fontWeight: 500 }}>{a.action}</span>
                  <span className="dem-mono" style={{ color: "var(--accent-cyan)", fontSize: 11.5 }}>{a.source_id || "—"}</span>
                  {a.llm_model && (
                    <span style={{ marginLeft: 8, color: "var(--text-tertiary)", fontSize: 10.5 }}>
                      · {a.llm_model} · {a.llm_tokens ?? 0} tok
                    </span>
                  )}
                </div>
                <span className={`dem-chip`} style={{
                  fontSize: 10, padding: "1px 7px",
                  background: `${color === "var(--accent-emerald)" ? "rgba(52,211,153,0.10)" : color === "var(--accent-rose)" ? "rgba(251,113,133,0.10)" : "rgba(255,255,255,0.04)"}`,
                  color, borderColor: `${color}33`,
                }}>{a.status}</span>
                <span className="dem-mono tab-num" style={{
                  fontSize: 11, color: "var(--text-muted)",
                  minWidth: 50, textAlign: "right",
                }}>{a.duration_ms ? `${a.duration_ms}ms` : "—"}</span>
                <span className="dem-mono tab-num" style={{
                  fontSize: 10.5, color: "var(--text-tertiary)",
                  minWidth: 110, textAlign: "right",
                }}>{fmtRelativeDate(a.created_at)}</span>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
