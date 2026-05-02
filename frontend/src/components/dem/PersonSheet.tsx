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
  const dn = person.date_naissance && person.date_naissance.length >= 10
    ? person.date_naissance.slice(0, 10)
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
            <div style={{
              display: "flex", gap: 14, marginTop: 6, fontSize: 12,
              color: "var(--text-secondary)", flexWrap: "wrap", alignItems: "center",
            }}>
              {person.age != null && <span>{person.age} ans</span>}
              <span><span style={{ color: "var(--text-muted)" }}>Mandats</span> <span className="dem-mono">{person.mandats}</span></span>
              <span><span style={{ color: "var(--text-muted)" }}>SCI</span> <span className="dem-mono">{person.sci}</span></span>
              {person.dept && <span>dept {person.dept}</span>}
            </div>
            {person.entreprises.length > 0 && (
              <div style={{ marginTop: 4, fontSize: 11.5, color: "var(--text-tertiary)" }}>
                {person.entreprises.slice(0, 4).join(" · ")}
              </div>
            )}
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
          />
        </div>
      </div>
    </>
  );
}
