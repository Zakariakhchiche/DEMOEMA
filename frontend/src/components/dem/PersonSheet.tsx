"use client";

import { useEffect, useState } from "react";
import { Icon } from "./Icon";
import { ScoreBadge } from "./ScoreBadge";
import { DirigeantDrillContent } from "./DirigeantDrillContent";
import { PersonGraphSection } from "./PersonGraphSection";
import { datalakeApi } from "@/lib/api";
import type { Person } from "@/lib/dem/types";

type GraphData = Awaited<ReturnType<typeof datalakeApi.personGraph>>;

interface Props {
  person: Person;
  onClose: () => void;
}

function splitNomPrenom(p: Person): { nom: string; prenom: string } {
  if (p.nom_raw && p.prenom_raw) return { nom: p.nom_raw, prenom: p.prenom_raw };
  const parts = p.nom.trim().split(/\s+/);
  if (parts.length === 1) return { nom: parts[0], prenom: "" };
  return { prenom: parts[0], nom: parts.slice(1).join(" ") };
}

export function PersonSheet({ person, onClose }: Props) {
  const [data, setData] = useState<Awaited<ReturnType<typeof datalakeApi.dirigeantFull>> | null>(null);
  const [graph, setGraph] = useState<GraphData | null>(null);
  const [graphLoading, setGraphLoading] = useState(true);
  const [graphError, setGraphError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const { nom, prenom } = splitNomPrenom(person);
  // Backend accepte 1974 (LIKE) | 1974-04 | 1974-04-12 — silver fait LIKE $1||'%'
  // donc tout préfixe valable. CRITIQUE pour disambiguer 6 homonymes Vincent
  // LAMOUR : sans dn, tie-breaker prend un autre Vincent.
  const dn = person.date_naissance && person.date_naissance.length >= 4
    ? (person.date_naissance.length >= 10 ? person.date_naissance.slice(0, 10)
       : person.date_naissance.length >= 7 ? person.date_naissance.slice(0, 7)
       : person.date_naissance.slice(0, 4))
    : undefined;

  useEffect(() => {
    if (!nom || !prenom) {
      setLoading(false);
      setGraphLoading(false);
      setError("Nom ou prénom manquant pour identifier le dirigeant.");
      return;
    }
    setLoading(true);
    setGraphLoading(true);
    setError(null);
    setGraphError(null);

    datalakeApi
      .dirigeantFull(nom, prenom, dn)
      .then(setData)
      .catch((e) => setError(e instanceof Error ? e.message : String(e)))
      .finally(() => setLoading(false));

    datalakeApi
      .personGraph(nom, prenom, 10)
      .then(setGraph)
      .catch((e) => setGraphError(e instanceof Error ? e.message : String(e)))
      .finally(() => setGraphLoading(false));
  }, [nom, prenom, dn]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") onClose(); };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  return (
    <>
      <div className="sheet-backdrop" onClick={onClose} />
      <div className="sheet-panel" role="dialog" aria-modal="true" aria-labelledby="person-sheet-title">
        <div style={{
          padding: "20px 28px 18px", borderBottom: "1px solid var(--border-subtle)",
          display: "flex", alignItems: "flex-start", gap: 18,
        }}>
          <ScoreBadge value={person.score} size="lg" />
          <div style={{ flex: 1, minWidth: 0 }}>
            <div id="person-sheet-title" style={{
              fontSize: 11, color: "var(--text-tertiary)",
              textTransform: "uppercase", letterSpacing: "0.08em", fontWeight: 600,
            }}>
              Dirigeant · profil M&amp;A complet
            </div>
            <div style={{
              fontSize: 26, fontWeight: 700, letterSpacing: "-0.02em",
              color: "var(--text-primary)", marginTop: 4,
              display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap",
            }}>
              {person.nom || `${prenom} ${nom}`.trim() || "—"}
            </div>
            {/* Header stats — préfère les valeurs API (data.identity / data.graph)
              quand chargées plutôt que les placeholders du PersonCard. Cas
              focus person : la card est créée avec age=0, mandats=0, sci=0
              car on n'a pas encore l'info — on utilise les vraies dès que dispo. */}
            {(() => {
              const ident = data?.identity as Record<string, unknown> | null;
              const g = data?.graph as Record<string, unknown> | null;
              const age = (ident?.age as number | null) ?? person.age;
              const mandats = (ident?.n_mandats_actifs as number | null)
                ?? (g?.n_mandats_actifs as number | null) ?? person.mandats;
              // Préférer silver.dirigeant_sci_patrimoine (4 SCI Vincent Lamour)
              // au n_sci Neo4j (qui retourne 1 à cause des md5 mismatches).
              const nSci = (data?.sci_patrimoine as { n_sci?: number } | null)?.n_sci
                ?? (g?.n_sci as number | null)
                ?? person.sci;
              return (
                <div style={{
                  display: "flex", gap: 14, marginTop: 6, fontSize: 12,
                  color: "var(--text-secondary)", flexWrap: "wrap", alignItems: "center",
                }}>
                  {age != null && age > 0 && <span>{age} ans</span>}
                  <span><span style={{ color: "var(--text-muted)" }}>Mandats</span> <span className="dem-mono">{mandats ?? 0}</span></span>
                  <span><span style={{ color: "var(--text-muted)" }}>SCI</span> <span className="dem-mono">{nSci ?? 0}</span></span>
                  {person.dept && <span>dept {person.dept}</span>}
                </div>
              );
            })()}
            {person.entreprises.length > 0 && (
              <div style={{ marginTop: 4, fontSize: 11.5, color: "var(--text-tertiary)" }}>
                {person.entreprises.slice(0, 4).join(" · ")}
              </div>
            )}
            {/* Bandeau signaux DD en un coup d'œil (réseau + compliance) — la fiche
              est longue, ce résumé donne le verdict immédiat sans scroller. */}
            {data && (() => {
              const dd = data as Record<string, unknown>;
              const c = (dd.compliance as Record<string, Record<string, unknown>> | null) || null;
              const nCo = Array.isArray(dd.co_mandataires_detail) ? (dd.co_mandataires_detail as unknown[]).length : 0;
              const cnt = (k: string) => Number((c?.[k]?.count as number) ?? 0);
              const chips: { txt: string; c: string; bg: string }[] = [];
              const lvl = c?.risk_level as string | undefined;
              if (lvl) {
                const m: Record<string, [string, string]> = {
                  low: ["var(--accent-emerald,#34d399)", "rgba(52,211,153,0.12)"],
                  medium: ["var(--accent-amber,#fbbf24)", "rgba(251,191,36,0.12)"],
                  high: ["var(--accent-rose,#fb7185)", "rgba(251,113,133,0.12)"],
                  critical: ["var(--accent-rose,#fb7185)", "rgba(251,113,133,0.20)"],
                };
                const [col, bg] = m[lvl] || m.medium;
                chips.push({ txt: `Risque ${lvl}`, c: col, bg });
              }
              if (cnt("interdiction_gerer") > 0) chips.push({ txt: "🚫 Interdiction de gérer", c: "var(--accent-rose,#fb7185)", bg: "rgba(251,113,133,0.16)" });
              if (cnt("faillite_personnelle") > 0) chips.push({ txt: "🔴 Faillite personnelle", c: "var(--accent-rose,#fb7185)", bg: "rgba(251,113,133,0.12)" });
              if (cnt("opensanctions") > 0) chips.push({ txt: `⚠️ ${cnt("opensanctions")} sanction/PEP`, c: "var(--accent-amber,#fbbf24)", bg: "rgba(251,191,36,0.10)" });
              if (c?.hatvp_lobbying?.active) chips.push({ txt: "📋 Lobbyiste HATVP", c: "var(--accent-amber,#fbbf24)", bg: "rgba(251,191,36,0.10)" });
              if (cnt("co_mandataires_toxiques") > 0) chips.push({ txt: `☠️ ${cnt("co_mandataires_toxiques")} co-mandataire(s) à risque`, c: "var(--accent-rose,#fb7185)", bg: "rgba(251,113,133,0.10)" });
              if (cnt("mandats_en_procedure") > 0) chips.push({ txt: `⚖️ ${cnt("mandats_en_procedure")} mandat(s) en procédure`, c: "var(--accent-amber,#fbbf24)", bg: "rgba(251,191,36,0.10)" });
              if (nCo > 0) chips.push({ txt: `🕸️ ${nCo} co-mandataire${nCo > 1 ? "s" : ""}`, c: "var(--accent-blue,#60a5fa)", bg: "rgba(96,165,250,0.10)" });
              if (chips.length === 0) chips.push({ txt: "✓ Aucun signal de risque", c: "var(--accent-emerald,#34d399)", bg: "rgba(52,211,153,0.10)" });
              return (
                <div style={{ marginTop: 10, display: "flex", gap: 6, flexWrap: "wrap" }}>
                  {chips.map((ch, i) => (
                    <span key={i} style={{
                      fontSize: 11, fontWeight: 600, padding: "3px 9px", borderRadius: 999,
                      color: ch.c, background: ch.bg, border: `1px solid ${ch.c}`,
                    }}>{ch.txt}</span>
                  ))}
                </div>
              );
            })()}
          </div>
          <div style={{ display: "flex", gap: 6 }}>
            <button className="dem-btn dem-btn-ghost dem-btn-icon" onClick={onClose} title="Fermer (Esc)">
              <span style={{ fontSize: 16, lineHeight: 1 }}>×</span>
            </button>
          </div>
        </div>

        {error && (
          <div style={{ padding: "14px 28px", color: "var(--accent-rose)", fontSize: 13 }}>
            <Icon name="warning" size={12} /> {error}
          </div>
        )}

        <div style={{ flex: 1, overflowY: "auto", padding: "18px 28px 28px" }}>
          {loading && <div style={{ color: "var(--text-tertiary)", fontSize: 13 }}>Chargement de la fiche…</div>}
          {!loading && !error && !data && (
            <div style={{ color: "var(--text-tertiary)", fontSize: 13 }}>Aucune donnée pour ce dirigeant.</div>
          )}
          {!loading && data && <DirigeantDrillContent data={data} />}

          <PersonGraphSection
            graph={graph}
            loading={graphLoading}
            error={graphError}
            nom={nom}
            prenom={prenom}
            fullName={person.nom || `${prenom} ${nom}`.trim()}
            mandatsDetail={data?.mandats_detail as Parameters<typeof PersonGraphSection>[0]["mandatsDetail"]}
            coMandatairesDetail={data?.co_mandataires_detail as Parameters<typeof PersonGraphSection>[0]["coMandatairesDetail"]}
            nMandatsActifsPg={(data?.identity as { n_mandats_actifs?: number | null } | null)?.n_mandats_actifs ?? null}
            nSciPg={(data?.sci_patrimoine as { n_sci?: number | null } | null)?.n_sci ?? null}
            totalCapitalSciPg={(data?.sci_patrimoine as { total_capital_sci?: number | null } | null)?.total_capital_sci ?? null}
          />
        </div>
      </div>
    </>
  );
}
