"use client";

import { useEffect, useState } from "react";
import { Icon } from "./Icon";
import { ScoreBadge } from "./ScoreBadge";
import { Sparkline } from "./Sparkline";
import { datalakeApi } from "@/lib/api";
import { rowToTarget } from "@/lib/dem/adapter";
import type { Mode, Target } from "@/lib/dem/types";

interface Props {
  onMode: (m: Mode) => void;
  onOpenTarget: (t: Target) => void;
}

type KpiNum = number | string | null | undefined;

interface DashboardData {
  kpis: {
    n_comptes_total?: KpiNum;
    n_red_flags?: KpiNum;
    n_signals_7d?: KpiNum;
    n_signals_30d?: KpiNum;
    n_dirigeants_total?: KpiNum;
    n_osint?: KpiNum;
  };
  heatmap: { dept: string; count: number; label: string }[];
  alerts: Record<string, unknown>[];
  top_targets: Record<string, unknown>[];
}

function fmtNum(v: number | string | null | undefined): string {
  if (v == null || v === "") return "—";
  const n = Number(v);
  if (isNaN(n)) return "—";
  if (n >= 1e6) return `${(n / 1e6).toFixed(1)}M`;
  if (n >= 1e3) return `${(n / 1e3).toFixed(0)}k`;
  return n.toLocaleString("fr-FR");
}

function severityFor(family: unknown): "high" | "med" | "low" {
  const s = String(family || "").toLowerCase();
  if (s.includes("liquidation") || s.includes("redressement")) return "high";
  if (s.includes("procédure") || s.includes("procedure")) return "high";
  if (s.includes("cession")) return "med";
  return "low";
}

export function DashboardView({ onMode, onOpenTarget }: Props) {
  const [data, setData] = useState<DashboardData | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    datalakeApi
      .dashboard()
      .then(setData)
      .catch((e) => setError(e instanceof Error ? e.message : String(e)));
  }, []);

  const maxCount = Math.max(1, ...(data?.heatmap.map((h) => h.count) ?? [1]));
  const colorScale = (c: number) => {
    const t = c / maxCount;
    return `rgba(96, 165, 250, ${0.10 + t * 0.55})`;
  };

  return (
    <div style={{ flex: 1, overflowY: "auto", position: "relative", zIndex: 1 }}>
      <div style={{ maxWidth: 1280, margin: "0 auto", padding: "28px 32px" }}>
        <div style={{ marginBottom: 6, fontSize: 22, fontWeight: 700, letterSpacing: "-0.02em" }}>
          Bonjour Anne ☕
        </div>
        <div style={{ fontSize: 13, color: "var(--text-tertiary)" }}>
          {data?.kpis.n_signals_7d != null
            ? `${fmtNum(data.kpis.n_signals_7d)} signaux BODACC sur 7 jours · datalake live`
            : error
            ? `Datalake indisponible : ${error}`
            : "Chargement live…"}
        </div>

        <div style={{ marginTop: 22, display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 12 }}>
          {[
            {
              label: "Comptes annuels INPI",
              value: fmtNum(data?.kpis.n_comptes_total),
              delta: "silver.inpi_comptes",
              color: "var(--accent-blue)",
            },
            {
              label: "Dirigeants INPI",
              value: fmtNum(data?.kpis.n_dirigeants_total),
              delta: "silver.inpi_dirigeants",
              color: "var(--accent-purple)",
            },
            {
              label: "Red flags compliance",
              value: fmtNum(data?.kpis.n_red_flags),
              delta: "silver.opensanctions",
              color: "var(--accent-rose)",
            },
            {
              label: "Annonces BODACC 30j",
              value: fmtNum(data?.kpis.n_signals_30d),
              delta: `dont ${fmtNum(data?.kpis.n_signals_7d)} sur 7j`,
              color: "var(--accent-emerald)",
            },
          ].map((k, i) => (
            <div
              key={i}
              className="dem-glass card-lift fade-up"
              style={{ borderRadius: 12, padding: 18, animationDelay: `${i * 60}ms` }}
            >
              <div style={{
                fontSize: 11, color: "var(--text-tertiary)",
                textTransform: "uppercase", letterSpacing: "0.06em", fontWeight: 600,
              }}>{k.label}</div>
              <div className="dem-mono tab-num" style={{
                marginTop: 8, fontSize: 28, fontWeight: 700, color: k.color, letterSpacing: "-0.02em",
              }}>{k.value}</div>
              <div style={{ marginTop: 4, fontSize: 11.5, color: "var(--text-secondary)" }}>{k.delta}</div>
            </div>
          ))}
        </div>

        <div style={{ marginTop: 18, display: "grid", gridTemplateColumns: "1.4fr 1fr", gap: 14 }}>
          <div className="dem-glass" style={{ borderRadius: 12, padding: 18 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 14 }}>
              <div style={{ fontSize: 14, fontWeight: 700 }}>Top cibles · score décroissant</div>
              <span className="dem-mono" style={{ fontSize: 11, color: "var(--text-tertiary)" }}>
                · {data?.top_targets.length ?? 0} live
              </span>
              <button className="dem-btn dem-btn-ghost" style={{ marginLeft: "auto" }} onClick={() => onMode("explorer")}>
                Tout voir →
              </button>
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
              {!data && !error && <div style={{ padding: 12, fontSize: 12, color: "var(--text-tertiary)" }}>Chargement…</div>}
              {data?.top_targets.length === 0 && (
                <div style={{ padding: 12, fontSize: 12, color: "var(--text-tertiary)" }}>
                  Aucune cible disponible dans le datalake actuel.
                </div>
              )}
              {data?.top_targets.map((row, i) => {
                const t = rowToTarget(row);
                return (
                  <div
                    key={t.siren}
                    style={{
                      display: "flex", alignItems: "center", gap: 12,
                      padding: "10px 12px", borderRadius: 8,
                      background: "rgba(255,255,255,0.02)", cursor: "pointer",
                    }}
                    onClick={() => onOpenTarget(t)}
                  >
                    <span className="dem-mono tab-num" style={{ fontSize: 11, color: "var(--text-muted)", width: 18 }}>#{i + 1}</span>
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div style={{ fontSize: 13, fontWeight: 600 }}>{t.denomination}</div>
                      <div style={{ fontSize: 11, color: "var(--text-tertiary)" }}>
                        {t.naf || "—"}{t.dept && ` · ${t.dept}`} · {t.ca_str}
                      </div>
                    </div>
                    {t.ca_history.length >= 2 && (
                      <Sparkline data={t.ca_history} color="var(--accent-blue)" width={64} height={20} />
                    )}
                    <ScoreBadge value={t.score} size="sm" />
                  </div>
                );
              })}
            </div>
          </div>

          <div className="dem-glass" style={{ borderRadius: 12, padding: 18 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 14 }}>
              <div style={{ fontSize: 14, fontWeight: 700 }}>Alertes BODACC 14j</div>
              <span className="dem-mono" style={{ fontSize: 11, color: "var(--accent-rose)" }}>· {data?.alerts.length ?? 0}</span>
              <button className="dem-btn dem-btn-ghost" style={{ marginLeft: "auto" }} onClick={() => onMode("watchlist")}>
                Tout voir →
              </button>
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: 6, maxHeight: 420, overflowY: "auto" }}>
              {data?.alerts.slice(0, 6).map((a, i) => {
                const sev = severityFor(a.family);
                const date = String(a.date_parution || "").slice(0, 10);
                return (
                  <div
                    key={i}
                    style={{
                      display: "flex", alignItems: "flex-start", gap: 10,
                      padding: "10px 12px", borderRadius: 8,
                      background: "rgba(255,255,255,0.02)",
                    }}
                  >
                    <span className={`sev-dot ${sev}`} style={{ marginTop: 5 }} />
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div style={{ fontSize: 12.5, fontWeight: 600 }}>
                        {String(a.denomination ?? a.siren ?? "—")}
                      </div>
                      <div style={{
                        fontSize: 11.5,
                        color: sev === "high" ? "var(--accent-rose)" : "var(--text-secondary)",
                        marginTop: 2,
                      }}>{String(a.title ?? "")}</div>
                      <div style={{ fontSize: 10.5, color: "var(--text-tertiary)", marginTop: 2 }}>
                        {date} · {String(a.ville ?? "")}{a.code_dept ? ` (${a.code_dept})` : ""}
                      </div>
                    </div>
                  </div>
                );
              })}
              {data?.alerts.length === 0 && (
                <div style={{ padding: 12, fontSize: 12, color: "var(--text-tertiary)" }}>
                  Aucune alerte sur 14j.
                </div>
              )}
            </div>
          </div>
        </div>

        <div className="dem-glass" style={{ borderRadius: 12, padding: 18, marginTop: 14 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 14 }}>
            <div style={{ fontSize: 14, fontWeight: 700 }}>Sourcing par département</div>
            <span className="dem-mono" style={{ fontSize: 11, color: "var(--text-tertiary)" }}>
              · top {data?.heatmap.length ?? 0} · live OSINT companies
            </span>
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(6, 1fr)", gap: 8 }}>
            {data?.heatmap.map((h) => (
              <div key={h.dept} className="heat-cell" style={{ background: colorScale(h.count) }}>
                <div className="dem-mono tab-num" style={{ fontSize: 18, fontWeight: 700, color: "var(--text-primary)" }}>
                  {h.count.toLocaleString("fr-FR")}
                </div>
                <div style={{ marginTop: 2, fontSize: 11, color: "var(--text-secondary)" }}>{h.label}</div>
                <div className="dem-mono" style={{ fontSize: 10, color: "var(--text-tertiary)" }}>{h.dept}</div>
              </div>
            ))}
          </div>
        </div>

        <div style={{ marginTop: 14, display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 10 }}>
          {[
            { icon: "chat", label: "Démarrer une recherche", action: () => onMode("chat"), color: "var(--accent-blue)" },
            { icon: "kanban", label: "Voir le pipeline", action: () => onMode("pipeline"), color: "var(--accent-purple)" },
            { icon: "table", label: "Data Explorer", action: () => onMode("explorer"), color: "var(--accent-cyan)" },
            { icon: "shield", label: "Audit conformité", action: () => onMode("audit"), color: "var(--accent-amber)" },
          ].map((q, i) => (
            <button
              key={i}
              className="dem-glass card-lift"
              onClick={q.action}
              style={{
                borderRadius: 10, padding: "14px 16px",
                display: "flex", alignItems: "center", gap: 12,
                cursor: "pointer", border: "1px solid var(--border-subtle)",
                background: "rgba(17,17,20,0.40)",
                color: "var(--text-primary)", fontFamily: "inherit", textAlign: "left",
              }}
            >
              <div style={{
                width: 32, height: 32, borderRadius: 8,
                background: "rgba(96,165,250,0.10)",
                display: "flex", alignItems: "center", justifyContent: "center",
              }}>
                <Icon name={q.icon} size={14} color={q.color} />
              </div>
              <span style={{ fontSize: 13, fontWeight: 500 }}>{q.label}</span>
              <Icon name="chevron-right" size={12} color="var(--text-tertiary)" style={{ marginLeft: "auto" }} />
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
