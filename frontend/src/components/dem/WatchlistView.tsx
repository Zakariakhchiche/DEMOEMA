"use client";

import { useEffect, useState } from "react";
import { Icon } from "./Icon";
import { datalakeApi } from "@/lib/api";
import { fetchTargets } from "@/lib/dem/adapter";
import type { Target } from "@/lib/dem/types";

interface Props {
  onOpenTarget: (t: Target) => void;
}

interface Alert {
  id: string;
  siren: string;
  denomination: string;
  title: string;
  family: string;
  source: string;
  ville: string;
  departement: string;
  code_dept: string;
  date_parution: string;
  severity: "high" | "med" | "low";
}

function severityFor(family: unknown): "high" | "med" | "low" {
  const s = String(family || "").toLowerCase();
  if (s.includes("liquidation") || s.includes("redressement") || s.includes("procédure") || s.includes("procedure")) return "high";
  if (s.includes("cession") || s.includes("vente")) return "med";
  return "low";
}

export function WatchlistView({ onOpenTarget }: Props) {
  const [tab, setTab] = useState<"alerts" | "rules">("alerts");
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    datalakeApi
      .dashboard()
      .then((d) => {
        const mapped: Alert[] = d.alerts.map((a, i) => ({
          id: `a_${i}_${a.siren}`,
          siren: String(a.siren ?? ""),
          denomination: String(a.denomination ?? a.siren ?? "—"),
          title: String(a.title ?? ""),
          family: String(a.family ?? ""),
          source: String(a.source ?? "BODACC"),
          ville: String(a.ville ?? ""),
          departement: String(a.departement ?? ""),
          code_dept: String(a.code_dept ?? ""),
          date_parution: String(a.date_parution ?? "").slice(0, 10),
          severity: severityFor(a.family),
        }));
        setAlerts(mapped);
      })
      .finally(() => setLoading(false));
  }, []);

  const openAlert = async (siren: string) => {
    if (!siren) return;
    const targets = await fetchTargets({ q: siren, limit: 1 });
    if (targets[0]) onOpenTarget(targets[0]);
  };

  return (
    <div style={{ flex: 1, display: "flex", flexDirection: "column", overflow: "hidden", position: "relative", zIndex: 1 }}>
      <div style={{ padding: "16px 22px 0", borderBottom: "1px solid var(--border-subtle)" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <div style={{ fontSize: 16, fontWeight: 700, letterSpacing: "-0.01em" }}>Watchlist &amp; Alertes</div>
          <span className="dem-mono" style={{ fontSize: 11, color: "var(--text-tertiary)" }}>
            · {alerts.length} alertes BODACC 14j · datalake live
          </span>
          <span style={{ marginLeft: "auto" }}>
            <button className="dem-btn dem-btn-primary"><Icon name="plus" size={11} /> Nouvelle règle</button>
          </span>
        </div>
        <div style={{ display: "flex", gap: 4, marginTop: 14 }}>
          {[
            { id: "alerts" as const, label: "Alertes BODACC", count: alerts.length },
            { id: "rules" as const, label: "Règles", count: 0 },
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
            {loading && <div style={{ padding: 12, fontSize: 12, color: "var(--text-tertiary)" }}>Chargement…</div>}
            {!loading && alerts.length === 0 && (
              <div style={{ padding: 24, textAlign: "center", color: "var(--text-tertiary)" }}>
                Aucune alerte BODACC sur 14 jours.
              </div>
            )}
            {alerts.map((a) => (
              <div
                key={a.id}
                className="dem-glass card-lift fade-up"
                style={{ borderRadius: 10, padding: 14, display: "flex", gap: 14, alignItems: "center", cursor: "pointer" }}
                onClick={() => openAlert(a.siren)}
              >
                <span className={`sev-dot ${a.severity}`} />
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                    <span style={{ fontSize: 13.5, fontWeight: 600 }}>{a.denomination}</span>
                    <span className="dem-mono" style={{ fontSize: 10.5, color: "var(--text-muted)" }}>siren {a.siren}</span>
                  </div>
                  <div style={{ marginTop: 4, fontSize: 12.5, color: a.severity === "high" ? "var(--accent-rose)" : "var(--text-secondary)" }}>
                    {a.title}
                  </div>
                  <div style={{ marginTop: 6, fontSize: 11, color: "var(--text-tertiary)" }}>
                    {a.date_parution} · {a.ville}{a.code_dept ? ` (${a.code_dept})` : ""} · <span className="dem-mono" style={{ color: "var(--accent-cyan)" }}>{a.source}</span>
                  </div>
                </div>
                <button className="dem-btn"><Icon name="eye" size={11} /> Voir fiche</button>
              </div>
            ))}
          </div>
        )}
        {tab === "rules" && (
          <div style={{ maxWidth: 920, margin: "0 auto", padding: 24 }}>
            <div className="dem-glass" style={{ padding: 32, borderRadius: 12, textAlign: "center", color: "var(--text-tertiary)", fontSize: 13 }}>
              <Icon name="bookmark" size={24} color="var(--text-muted)" />
              <div style={{ marginTop: 8, fontSize: 14, color: "var(--text-secondary)", fontWeight: 600 }}>
                Aucune règle sauvegardée
              </div>
              <div style={{ marginTop: 4, fontSize: 12 }}>
                Crée ta première règle de watchlist pour être alerté automatiquement.
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
