"use client";

import React, { useState } from "react";
import { Icon } from "./Icon";
import type { datalakeApi } from "@/lib/api";
import { PersonGraphModal } from "./PersonGraphModal";

type GraphData = Awaited<ReturnType<typeof datalakeApi.personGraph>>;

interface Props {
  graph: GraphData | null;
  loading: boolean;
  error: string | null;
  /** Pour ouvrir la modal graphe interactif. Issus de PersonSheet (split du person.nom). */
  nom?: string;
  prenom?: string;
  fullName?: string;
}

const Section = ({ title, children }: { title: string; children: React.ReactNode }) => (
  <div className="dem-glass" style={{ padding: 16, marginTop: 18 }}>
    <div style={{
      fontSize: 11, color: "var(--text-tertiary)", textTransform: "uppercase",
      letterSpacing: "0.08em", fontWeight: 600, marginBottom: 12,
    }}>
      {title}
    </div>
    {children}
  </div>
);

const Flag = ({ active, label, tone }: { active: boolean; label: string; tone: "rose" | "amber" | "violet" | "teal" }) => {
  if (!active) return null;
  const colors: Record<string, { bg: string; fg: string }> = {
    rose:   { bg: "color-mix(in srgb, var(--accent-rose) 14%, transparent)", fg: "var(--accent-rose)" },
    amber:  { bg: "color-mix(in srgb, var(--accent-amber) 14%, transparent)", fg: "var(--accent-amber)" },
    violet: { bg: "color-mix(in srgb, var(--accent-violet) 14%, transparent)", fg: "var(--accent-violet)" },
    teal:   { bg: "color-mix(in srgb, var(--accent-teal) 14%, transparent)", fg: "var(--accent-teal)" },
  };
  const c = colors[tone];
  return (
    <span style={{
      display: "inline-flex", alignItems: "center", gap: 4,
      padding: "3px 10px", borderRadius: 999, fontSize: 11, fontWeight: 600,
      background: c.bg, color: c.fg, letterSpacing: "0.02em",
    }}>
      {label}
    </span>
  );
};

const fmtCapital = (v: unknown) => {
  if (v == null || v === "") return "—";
  const n = Number(v);
  if (isNaN(n) || n === 0) return "—";
  if (Math.abs(n) >= 1e9) return `${(n / 1e9).toFixed(1)} Md€`;
  if (Math.abs(n) >= 1e6) return `${(n / 1e6).toFixed(1)} M€`;
  if (Math.abs(n) >= 1e3) return `${(n / 1e3).toFixed(0)} k€`;
  return `${n.toFixed(0)} €`;
};

export function PersonGraphSection({ graph, loading, error, nom, prenom, fullName }: Props) {
  const [graphOpen, setGraphOpen] = useState(false);
  // Permet la navigation récursive : click sur un co-mandataire dans la modal
  // re-cible la modal sur cette personne (sans fermer la PersonSheet en arrière).
  const [navTarget, setNavTarget] = useState<{ nom: string; prenom: string; fullName: string } | null>(null);
  const effectiveNom = navTarget?.nom ?? nom ?? "";
  const effectivePrenom = navTarget?.prenom ?? prenom ?? "";
  const effectiveFullName = navTarget?.fullName ?? fullName ?? `${effectivePrenom} ${effectiveNom}`;
  const canOpenGraph = !!nom && !!prenom && graph != null && (graph.top_co_mandataires?.length ?? 0) > 0;
  if (loading) {
    return (
      <Section title="Réseau · Neo4j (graphe complet)">
        <div style={{ color: "var(--text-tertiary)", fontSize: 13 }}>
          Chargement du graphe…
        </div>
      </Section>
    );
  }
  if (error) {
    return (
      <Section title="Réseau · Neo4j (graphe complet)">
        <div style={{ color: "var(--text-tertiary)", fontSize: 12.5 }}>
          <Icon name="warning" size={12} /> Pas de match dans le graphe pour ce dirigeant.
          <span style={{ marginLeft: 8, color: "var(--text-muted)", fontSize: 11.5 }}>
            ({error})
          </span>
        </div>
      </Section>
    );
  }
  if (!graph || !graph.person) return null;

  const p = graph.person;
  const hasFlags =
    p.is_sanctioned || p.is_lobbyist || p.has_offshore || (p.n_sci ?? 0) > 0;

  return (
    <>
      <Section title="Réseau · Neo4j (graphe complet 18,6 M nodes)">
      {/* CTA visualisation graphe */}
      {canOpenGraph && (
        <div style={{ display: "flex", justifyContent: "flex-end", marginBottom: 8 }}>
          <button
            type="button"
            onClick={() => { setNavTarget(null); setGraphOpen(true); }}
            style={{
              fontSize: 11.5,
              padding: "6px 12px",
              borderRadius: 8,
              border: "1px solid var(--border-subtle)",
              background: "color-mix(in srgb, var(--accent-teal) 14%, transparent)",
              color: "var(--accent-teal)",
              fontWeight: 600,
              cursor: "pointer",
              display: "inline-flex",
              alignItems: "center",
              gap: 6,
            }}
            title="Voir le réseau co-mandataires en graphe interactif"
          >
            <Icon name="network" size={11} /> Voir le graphe
          </button>
        </div>
      )}
      {/* Flags compliance */}
      {hasFlags && (
        <div style={{ display: "flex", gap: 6, flexWrap: "wrap", marginBottom: 14 }}>
          <Flag active={p.is_sanctioned} label="Sanctionné" tone="rose" />
          <Flag active={p.has_offshore} label="ICIJ Offshore" tone="amber" />
          <Flag active={p.is_lobbyist} label="HATVP Lobbying" tone="violet" />
          <Flag active={(p.n_sci ?? 0) > 0} label={`SCI ×${p.n_sci}`} tone="teal" />
        </div>
      )}

      {/* Stats compactes */}
      <div style={{
        display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(140px, 1fr))",
        gap: 10, fontSize: 12, marginBottom: 14,
      }}>
        <Stat label="Mandats actifs" value={p.n_mandats_actifs ?? 0} />
        <Stat label="SCI" value={`${p.n_sci ?? 0} (${fmtCapital(p.total_capital_sci)})`} />
        <Stat label="Co-mandataires" value={graph.top_co_mandataires.length} />
        <Stat label="Companies (graph)" value={graph.companies.length} />
      </div>

      {/* Détails sanctions / lobby / offshore si présents */}
      {p.is_sanctioned && (p.sanctions_programs?.length || p.sanctions_topics?.length) && (
        <DetailRow label="Sanctions" tone="rose">
          {[...(p.sanctions_programs ?? []), ...(p.sanctions_topics ?? [])].slice(0, 6).join(" · ")}
        </DetailRow>
      )}
      {p.is_lobbyist && p.lobby_denominations?.length && (
        <DetailRow label="Lobbying" tone="violet">
          {p.lobby_denominations.slice(0, 4).join(" · ")}
        </DetailRow>
      )}
      {p.has_offshore && p.icij_leaks?.length && (
        <DetailRow label="ICIJ Leaks" tone="amber">
          {p.icij_leaks.slice(0, 4).join(" · ")}
          {p.icij_countries?.length ? ` — ${p.icij_countries.slice(0, 3).join(", ")}` : ""}
        </DetailRow>
      )}
      {p.sci_denominations?.length && (
        <DetailRow label="SCI" tone="teal">
          {p.sci_denominations.slice(0, 5).join(" · ")}
        </DetailRow>
      )}

      {/* Top co-mandataires */}
      {graph.top_co_mandataires.length > 0 && (
        <div style={{ marginTop: 16 }}>
          <div style={{
            fontSize: 11, color: "var(--text-muted)", textTransform: "uppercase",
            letterSpacing: "0.06em", fontWeight: 600, marginBottom: 8,
          }}>
            Top co-mandataires (sociétés partagées)
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
            {graph.top_co_mandataires.map((co, i) => (
              <div key={`${co.full_name}-${i}`} style={{
                display: "flex", alignItems: "center", justifyContent: "space-between",
                padding: "8px 12px", borderRadius: 8,
                background: "color-mix(in srgb, var(--surface-base) 60%, transparent)",
                border: "1px solid var(--border-subtle)",
                fontSize: 12.5,
              }}>
                <div style={{ display: "flex", alignItems: "center", gap: 8, minWidth: 0 }}>
                  <span style={{ color: "var(--text-primary)", fontWeight: 500 }}>
                    {co.full_name}
                  </span>
                  <Flag active={co.other_sanctioned} label="S" tone="rose" />
                  <Flag active={co.other_offshore} label="O" tone="amber" />
                  <Flag active={co.other_lobbyist} label="L" tone="violet" />
                </div>
                <div style={{
                  display: "flex", alignItems: "center", gap: 10,
                  color: "var(--text-tertiary)", fontSize: 11.5,
                }}>
                  <span className="dem-mono">{co.n_shared} sociétés</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Companies */}
      {graph.companies.length > 0 && (
        <div style={{ marginTop: 16 }}>
          <div style={{
            fontSize: 11, color: "var(--text-muted)", textTransform: "uppercase",
            letterSpacing: "0.06em", fontWeight: 600, marginBottom: 8,
          }}>
            Companies (mandats trouvés dans le graphe)
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
            {graph.companies.slice(0, 20).map((c) => (
              <div key={c.siren} style={{
                display: "grid", gridTemplateColumns: "auto 1fr auto auto", gap: 12,
                alignItems: "center", padding: "6px 12px", borderRadius: 6,
                fontSize: 12, borderBottom: "1px solid var(--border-subtle)",
              }}>
                <span className="dem-mono" style={{
                  color: "var(--text-muted)", fontSize: 11,
                }}>{c.siren}</span>
                <span style={{
                  color: "var(--text-primary)",
                  overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap",
                }}>
                  {c.denomination || "—"}
                </span>
                <span style={{ color: "var(--text-tertiary)", fontSize: 11 }}>
                  {c.forme_juridique}
                </span>
                <span style={{
                  color: c.actif ? "var(--accent-teal)" : "var(--text-muted)",
                  fontSize: 11, fontWeight: 600,
                }}>
                  {c.actif ? "actif" : "fermé"}
                </span>
              </div>
            ))}
            {graph.companies.length > 20 && (
              <div style={{
                fontSize: 11, color: "var(--text-muted)", textAlign: "center",
                padding: "6px 0",
              }}>
                + {graph.companies.length - 20} autres
              </div>
            )}
          </div>
        </div>
      )}
      </Section>

      {graphOpen && effectiveNom && effectivePrenom && (
        <PersonGraphModal
          nom={effectiveNom}
          prenom={effectivePrenom}
          fullName={effectiveFullName}
          onClose={() => { setGraphOpen(false); setNavTarget(null); }}
          onNavigate={(t) => setNavTarget(t)}
        />
      )}
    </>
  );
}

function Stat({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div style={{
      padding: "8px 10px", borderRadius: 8,
      background: "color-mix(in srgb, var(--surface-base) 50%, transparent)",
      border: "1px solid var(--border-subtle)",
    }}>
      <div style={{
        fontSize: 10.5, color: "var(--text-muted)", textTransform: "uppercase",
        letterSpacing: "0.05em", fontWeight: 600,
      }}>
        {label}
      </div>
      <div style={{
        fontSize: 14, color: "var(--text-primary)", marginTop: 2, fontWeight: 600,
      }}>
        {value}
      </div>
    </div>
  );
}

function DetailRow({
  label, tone, children,
}: { label: string; tone: "rose" | "amber" | "violet" | "teal"; children: React.ReactNode }) {
  return (
    <div style={{
      display: "flex", gap: 10, fontSize: 12, marginBottom: 6, alignItems: "baseline",
    }}>
      <Flag active={true} label={label} tone={tone} />
      <span style={{ color: "var(--text-secondary)", flex: 1, minWidth: 0 }}>
        {children}
      </span>
    </div>
  );
}
