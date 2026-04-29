"use client";

import { useState, useEffect } from "react";
import { Icon } from "./Icon";
import { ScoreBadge } from "./ScoreBadge";
import { PersonCard } from "./PersonCard";
import type { Target } from "@/lib/dem/types";

interface Props {
  target: Target;
  onClose: () => void;
  onPitch: () => void;
}

const TABS = [
  { k: "overview", label: "Overview", icon: "eye" },
  { k: "dirigeants", label: "Dirigeants", icon: "user" },
  { k: "signaux", label: "Signaux M&A", icon: "sparkles" },
  { k: "compliance", label: "Compliance", icon: "shield" },
  { k: "contentieux", label: "Contentieux", icon: "warning" },
  { k: "reseau", label: "Réseau", icon: "network" },
] as const;

function BarChart({ data, labels }: { data: number[]; labels: string[] }) {
  if (data.length === 0) return null;
  const max = Math.max(...data);
  return (
    <div style={{ display: "flex", alignItems: "flex-end", gap: 12, height: 120, marginTop: 14 }}>
      {data.map((v, i) => (
        <div key={i} style={{ flex: 1, display: "flex", flexDirection: "column", alignItems: "center", gap: 6 }}>
          <div className="dem-mono tab-num" style={{ fontSize: 11, color: "var(--text-secondary)" }}>{v}M€</div>
          <div style={{
            width: "100%", height: `${(v / max) * 80}%`,
            background: i === data.length - 1
              ? "linear-gradient(180deg, var(--accent-blue), rgba(96,165,250,0.30))"
              : "rgba(255,255,255,0.10)",
            borderRadius: 4,
            boxShadow: i === data.length - 1 ? "0 0 16px -2px rgba(96,165,250,0.40)" : "none",
          }} />
          <div className="dem-mono" style={{ fontSize: 10.5, color: "var(--text-tertiary)" }}>{labels[i]}</div>
        </div>
      ))}
    </div>
  );
}

export function TargetSheet({ target, onClose, onPitch }: Props) {
  const [tab, setTab] = useState<typeof TABS[number]["k"]>("overview");

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") onClose(); };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  const ebitdaMargin = target.ebitda && target.ca ? (target.ebitda / target.ca) * 100 : null;

  return (
    <>
      <div className="sheet-backdrop" onClick={onClose} />
      <div className="sheet-panel">
        <div style={{
          padding: "20px 28px 18px", borderBottom: "1px solid var(--border-subtle)",
          display: "flex", alignItems: "flex-start", gap: 18,
        }}>
          <ScoreBadge value={target.score} size="lg" breakdown={target.score_breakdown} />
          <div style={{ flex: 1, minWidth: 0 }}>
            <div style={{
              fontSize: 11, color: "var(--text-tertiary)",
              textTransform: "uppercase", letterSpacing: "0.08em", fontWeight: 600,
            }}>
              Cible M&A · {target.naf_label}
            </div>
            <div style={{
              fontSize: 26, fontWeight: 700, letterSpacing: "-0.02em",
              color: "var(--text-primary)", marginTop: 4,
            }}>
              {target.denomination}
            </div>
            <div style={{
              display: "flex", gap: 14, marginTop: 6, fontSize: 12,
              color: "var(--text-secondary)", flexWrap: "wrap",
            }}>
              <span className="dem-mono">siren {target.siren}</span>
              {target.forme && <span>{target.forme}</span>}
              {target.creation && target.creation !== "—" && <span>Créé en {target.creation}</span>}
              {target.ville && <span>{target.ville}{target.dept ? `, dept ${target.dept}` : ""}</span>}
            </div>
          </div>
          <div style={{ display: "flex", gap: 6 }}>
            <button className="dem-btn dem-btn-primary" onClick={onPitch}>
              <Icon name="sparkles" size={12} /> Pitch Ready
            </button>
            <button className="dem-btn">
              <Icon name="bookmark" size={12} /> Sauver
            </button>
            <button className="dem-btn dem-btn-ghost dem-btn-icon" onClick={onClose} title="Fermer (Esc)">
              <span style={{ fontSize: 16, lineHeight: 1 }}>×</span>
            </button>
          </div>
        </div>

        <div style={{ flex: 1, display: "flex", overflow: "hidden" }}>
          <div style={{
            width: 200, borderRight: "1px solid var(--border-subtle)",
            padding: "12px 8px", display: "flex", flexDirection: "column", gap: 2,
          }}>
            {TABS.map((t) => (
              <button
                key={t.k}
                onClick={() => setTab(t.k)}
                style={{
                  display: "flex", alignItems: "center", gap: 9,
                  padding: "8px 12px", borderRadius: 7, border: "none",
                  background: tab === t.k ? "rgba(96,165,250,0.10)" : "transparent",
                  color: tab === t.k ? "#cfe1fb" : "var(--text-secondary)",
                  cursor: "pointer", fontSize: 12.5, textAlign: "left",
                  fontWeight: tab === t.k ? 600 : 500,
                }}
              >
                <Icon name={t.icon} size={12} />
                {t.label}
              </button>
            ))}
          </div>

          <div style={{ flex: 1, overflowY: "auto", padding: "20px 28px 32px" }}>
            {tab === "overview" && (
              <div>
                <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 10 }}>
                  {[
                    { l: "CA dernier", v: target.ca_str, sub: target.ca_history.length >= 2 ? `+${(((target.ca_history[target.ca_history.length-1] - target.ca_history[target.ca_history.length-2]) / target.ca_history[target.ca_history.length-2]) * 100).toFixed(1)}% YoY` : "", color: "var(--accent-emerald)" },
                    { l: "EBITDA", v: target.ebitda_str, sub: ebitdaMargin != null ? `marge ${ebitdaMargin.toFixed(1)}%` : "", color: "var(--accent-blue)" },
                    { l: "Effectif", v: target.effectif ?? "—", sub: target.forme || "", color: "var(--text-secondary)" },
                    { l: "Valorisation est.", v: target.ca ? `${(target.ca * 1.4 / 1e6).toFixed(0)} M€` : "—", sub: "1.4× CA (sect.)", color: "var(--accent-purple)" },
                  ].map((k, i) => (
                    <div key={i} className="dem-glass" style={{ borderRadius: 12, padding: "14px 16px" }}>
                      <div style={{
                        fontSize: 10.5, color: "var(--text-tertiary)",
                        textTransform: "uppercase", letterSpacing: "0.06em", fontWeight: 600,
                      }}>{k.l}</div>
                      <div className="dem-mono tab-num" style={{
                        fontSize: 22, fontWeight: 700, color: "var(--text-primary)", marginTop: 4,
                      }}>{k.v}</div>
                      {k.sub && <div style={{ fontSize: 11, color: k.color, marginTop: 2 }}>{k.sub}</div>}
                    </div>
                  ))}
                </div>

                {target.ca_history.length >= 2 && (
                  <div className="dem-glass" style={{ borderRadius: 12, padding: 18, marginTop: 14 }}>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline" }}>
                      <div style={{ fontSize: 13, fontWeight: 600 }}>Évolution CA — 5 ans</div>
                      <div style={{ fontSize: 11, color: "var(--text-tertiary)" }}>Source : INPI comptes annuels</div>
                    </div>
                    <BarChart data={target.ca_history} labels={["2021", "2022", "2023", "2024", "2025"].slice(0, target.ca_history.length)} />
                  </div>
                )}

                <div style={{
                  marginTop: 14, padding: "14px 18px", borderRadius: 12,
                  background: "linear-gradient(135deg, rgba(96,165,250,0.06), rgba(167,139,250,0.06))",
                  border: "1px solid rgba(96,165,250,0.20)",
                  display: "flex", gap: 12,
                }}>
                  <Icon name="sparkles" size={16} color="var(--accent-purple)" />
                  <div>
                    <div style={{ fontSize: 12, fontWeight: 600, color: "var(--accent-purple)", marginBottom: 4 }}>Verdict DEMOEMA</div>
                    <div style={{ fontSize: 13, color: "var(--text-primary)", lineHeight: 1.55 }}>
                      Cible <strong>{target.score >= 80 ? "HIGH" : target.score >= 70 ? "MID-HIGH" : "MID"} potentiel</strong> pour mandat sell-side {target.naf_label.toLowerCase()}.
                      Score {target.score}/100 — {target.score >= 80 ? "tier-1, prioritaire" : target.score >= 70 ? "tier-1, à qualifier" : "tier-2, surveillance"}.
                      {target.red_flags.length > 0 && " Attention : red flag à expliquer en DD."}
                    </div>
                  </div>
                </div>

                <div style={{ marginTop: 14, fontSize: 11.5, color: "var(--text-tertiary)" }}>
                  <strong style={{ color: "var(--text-secondary)" }}>Sources auditables :</strong>
                  {" "}
                  {target.sources.map((s, i) => (
                    <span key={i}>
                      {i > 0 ? " · " : " "}
                      <span style={{
                        color: "var(--accent-cyan)", textDecoration: "underline",
                        textDecorationColor: "rgba(103,232,249,0.30)", textUnderlineOffset: 2, cursor: "pointer",
                      }}>{s}</span>
                    </span>
                  ))}
                </div>
              </div>
            )}

            {tab === "dirigeants" && target.top_dirigeant.nom !== "—" && (
              <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                <PersonCard person={{
                  id: "_t",
                  nom: target.top_dirigeant.nom,
                  age: target.top_dirigeant.age,
                  score: target.top_dirigeant.score,
                  mandats: target.top_dirigeant.mandats,
                  sci: 0,
                  entreprises: [target.denomination],
                  event: null,
                  dept: target.dept,
                }} />
              </div>
            )}

            {tab === "compliance" && (
              <div>
                {target.red_flags.length === 0 ? (
                  <div className="dem-glass" style={{
                    padding: 24, borderRadius: 12, textAlign: "center",
                    borderColor: "rgba(52,211,153,0.20)",
                  }}>
                    <Icon name="check" size={32} color="var(--accent-emerald)" />
                    <div style={{ fontSize: 16, fontWeight: 600, marginTop: 8 }}>Aucun red flag identifié</div>
                    <div style={{ fontSize: 12, color: "var(--text-tertiary)", marginTop: 4 }}>
                      Sanctions UE/US, ICIJ, procédures collectives, contentieux récents
                    </div>
                  </div>
                ) : (
                  target.red_flags.map((f, i) => (
                    <div key={i} className="dem-glass" style={{
                      padding: 16, borderRadius: 12,
                      borderColor: "rgba(251,113,133,0.30)",
                      background: "rgba(251,113,133,0.04)",
                      display: "flex", gap: 12,
                    }}>
                      <Icon name="warning" size={20} color="var(--accent-rose)" />
                      <div>
                        <div style={{ fontSize: 13, fontWeight: 600, color: "var(--accent-rose)" }}>{f.label}</div>
                        <div style={{ fontSize: 11.5, color: "var(--text-tertiary)", marginTop: 4 }}>
                          Source : {f.source} · sévérité {f.severity}
                        </div>
                      </div>
                    </div>
                  ))
                )}
              </div>
            )}

            {(tab === "signaux" || tab === "contentieux" || tab === "reseau") && (
              <div className="dem-glass" style={{
                padding: 24, borderRadius: 12,
                color: "var(--text-tertiary)", fontSize: 13, textAlign: "center",
              }}>
                Section <strong>{TABS.find((t) => t.k === tab)?.label}</strong> — données détaillées disponibles dans Data Explorer.
              </div>
            )}
          </div>
        </div>
      </div>
    </>
  );
}
