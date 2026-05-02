"use client";

import { Icon } from "./Icon";
import { ScoreBadge } from "./ScoreBadge";
import type { Person } from "@/lib/dem/types";

interface Props {
  person: Person;
  onOpen?: (p: Person) => void;
}

export function PersonCard({ person, onOpen }: Props) {
  return (
    <div className="dem-glass card-lift" style={{ borderRadius: 14, padding: "14px 18px", display: "flex", gap: 14, alignItems: "center" }}>
      <div style={{
        width: 40, height: 40, borderRadius: 999,
        background: "linear-gradient(135deg, #3b3b44, #1a1a20)",
        border: "1px solid var(--border-soft)",
        display: "flex", alignItems: "center", justifyContent: "center",
        fontWeight: 600, fontSize: 13, color: "var(--text-secondary)", flexShrink: 0,
      }}>
        {person.nom.split(" ").map((n) => n[0]).join("").slice(0, 2)}
      </div>
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap" }}>
          <span style={{ fontWeight: 600, color: "var(--text-primary)", fontSize: 14 }}>{person.nom}</span>
          <span style={{ color: "var(--text-tertiary)", fontSize: 12 }}>
            {person.age ? `${person.age} ans` : "—"}{person.dept ? ` · dept ${person.dept}` : ""}
          </span>
          <ScoreBadge value={person.score} size="sm" />
        </div>
        <div style={{ marginTop: 6, fontSize: 12, color: "var(--text-secondary)", display: "flex", gap: 14, flexWrap: "wrap" }}>
          {/* Stats : 0 = placeholder (cas focus person extrait du query / LLM
            qui n'a pas encore les vraies valeurs). Affiche "—" plutôt que "0"
            pour ne pas afficher d'info trompeuse — la fiche drawer chargera
            les vraies stats au clic. */}
          <span><span style={{ color: "var(--text-muted)" }}>Mandats</span> <span className="dem-mono">{person.mandats > 0 ? person.mandats : "—"}</span></span>
          <span><span style={{ color: "var(--text-muted)" }}>SCI</span> <span className="dem-mono">{person.sci > 0 ? person.sci : "—"}</span></span>
          {person.entreprises.length > 0 && (
            <span>
              <span style={{ color: "var(--text-muted)" }}>Entreprises </span>
              <span style={{ color: "var(--text-secondary)" }}>{person.entreprises.join(", ")}</span>
            </span>
          )}
        </div>
        {person.event && (
          <div style={{ marginTop: 6, fontSize: 11.5, color: "var(--accent-cyan)", display: "inline-flex", alignItems: "center", gap: 5 }}>
            <Icon name="sparkles" size={10} color="var(--accent-cyan)" /> {person.event}
          </div>
        )}
      </div>
      <button
        className="dem-btn dem-btn-ghost"
        title="Voir la fiche complète du dirigeant"
        onClick={() => onOpen?.(person)}
        disabled={!onOpen}
      >
        <Icon name="network" size={12} /> Fiche
      </button>
    </div>
  );
}
