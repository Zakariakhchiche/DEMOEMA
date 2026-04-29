"use client";

import { useEffect, useState } from "react";
import { Icon } from "./Icon";
import { ScoreBadge } from "./ScoreBadge";
import { Sparkline } from "./Sparkline";
import { KPIS, HEATMAP, WATCHLIST_ALERTS } from "@/lib/dem/data";
import { fetchTargets } from "@/lib/dem/adapter";
import type { Mode, Target } from "@/lib/dem/types";

interface Props {
  onMode: (m: Mode) => void;
  onOpenTarget: (t: Target) => void;
}

export function DashboardView({ onMode, onOpenTarget }: Props) {
  const [topTargets, setTopTargets] = useState<Target[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    fetchTargets({ limit: 5 })
      .then(setTopTargets)
      .finally(() => setLoading(false));
  }, []);

  const maxCount = Math.max(...HEATMAP.map((h) => h.count));
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
          Mardi 29 avril · 8h14 · 47 nouveaux signaux cette nuit
        </div>

        <div style={{ marginTop: 22, display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 12 }}>
          {KPIS.map((k, i) => (
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
                · {topTargets.length} actives (live)
              </span>
              <button className="dem-btn dem-btn-ghost" style={{ marginLeft: "auto" }} onClick={() => onMode("explorer")}>
                Tout voir →
              </button>
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
              {loading && <div style={{ padding: 12, fontSize: 12, color: "var(--text-tertiary)" }}>Chargement…</div>}
              {!loading && topTargets.length === 0 && (
                <div style={{ padding: 12, fontSize: 12, color: "var(--text-tertiary)" }}>
                  Datalake non joignable. Vérifie /api/datalake/cibles.
                </div>
              )}
              {topTargets.map((t, i) => (
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
                      {t.naf_label}{t.dept && ` · ${t.dept}`} · {t.ca_str}
                    </div>
                  </div>
                  {t.ca_history.length >= 2 && (
                    <Sparkline data={t.ca_history} color="var(--accent-blue)" width={64} height={20} />
                  )}
                  <ScoreBadge value={t.score} size="sm" />
                </div>
              ))}
            </div>
          </div>

          <div className="dem-glass" style={{ borderRadius: 12, padding: 18 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 14 }}>
              <div style={{ fontSize: 14, fontWeight: 700 }}>Alertes 24h</div>
              <span className="dem-mono" style={{ fontSize: 11, color: "var(--accent-rose)" }}>· 2 critiques</span>
              <button className="dem-btn dem-btn-ghost" style={{ marginLeft: "auto" }} onClick={() => onMode("watchlist")}>
                Tout voir →
              </button>
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
              {WATCHLIST_ALERTS.slice(0, 4).map((a) => (
                <div
                  key={a.id}
                  style={{
                    display: "flex", alignItems: "flex-start", gap: 10,
                    padding: "10px 12px", borderRadius: 8,
                    background: "rgba(255,255,255,0.02)",
                  }}
                >
                  <span className={`sev-dot ${a.severity}`} style={{ marginTop: 5 }} />
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ fontSize: 12.5, fontWeight: 600 }}>{a.target}</div>
                    <div style={{
                      fontSize: 11.5,
                      color: a.severity === "high" ? "var(--accent-rose)" : "var(--text-secondary)",
                      marginTop: 2,
                    }}>{a.title}</div>
                    <div style={{ fontSize: 10.5, color: "var(--text-tertiary)", marginTop: 2 }}>{a.time}</div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        <div className="dem-glass" style={{ borderRadius: 12, padding: 18, marginTop: 14 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 14 }}>
            <div style={{ fontSize: 14, fontWeight: 700 }}>Sourcing par département</div>
            <span className="dem-mono" style={{ fontSize: 11, color: "var(--text-tertiary)" }}>· top 12 · 208 cibles total</span>
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(6, 1fr)", gap: 8 }}>
            {HEATMAP.map((h) => (
              <div key={h.dept} className="heat-cell" style={{ background: colorScale(h.count) }}>
                <div className="dem-mono tab-num" style={{ fontSize: 18, fontWeight: 700, color: "var(--text-primary)" }}>{h.count}</div>
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
