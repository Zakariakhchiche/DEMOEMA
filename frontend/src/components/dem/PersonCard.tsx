"use client";

import { useEffect, useState } from "react";
import { Icon } from "./Icon";
import { ScoreBadge } from "./ScoreBadge";
import { datalakeApi } from "@/lib/api";
import type { Person } from "@/lib/dem/types";

interface Props {
  person: Person;
  onOpen?: (p: Person) => void;
}

function splitNomPrenom(p: Person): { nom: string; prenom: string } {
  if (p.nom_raw && p.prenom_raw) return { nom: p.nom_raw, prenom: p.prenom_raw };
  const parts = p.nom.trim().split(/\s+/);
  if (parts.length === 1) return { nom: parts[0], prenom: "" };
  return { prenom: parts[0], nom: parts.slice(1).join(" ") };
}

export function PersonCard({ person, onOpen }: Props) {
  // Hydrate les chiffres mandats / SCI / age si la card a été créée depuis
  // un focus person extrait du query (placeholders à 0). Évite l'affichage
  // "Mandats —" alors qu'on a déjà l'info côté backend (silver INPI).
  const [hydrated, setHydrated] = useState<{ age: number; mandats: number; sci: number } | null>(null);
  const needsHydration = person.mandats === 0 && person.sci === 0;

  useEffect(() => {
    if (!needsHydration) return;
    const { nom, prenom } = splitNomPrenom(person);
    if (!nom || !prenom) return;
    let cancelled = false;
    const dn = person.date_naissance && person.date_naissance.length >= 7
      ? person.date_naissance.slice(0, 7)
      : undefined;
    datalakeApi
      .dirigeantFull(nom, prenom, dn)
      .then((d) => {
        if (cancelled) return;
        const ident = d.identity as { age?: number | null; n_mandats_actifs?: number | null } | null;
        const sciP = d.sci_patrimoine as { n_sci?: number | null } | null;
        setHydrated({
          age: ident?.age ?? 0,
          mandats: ident?.n_mandats_actifs ?? 0,
          sci: sciP?.n_sci ?? 0,
        });
      })
      .catch(() => { /* silencieux : la card reste avec "—" */ });
    return () => { cancelled = true; };
  }, [person, needsHydration]);

  const ageDisplay = hydrated?.age ?? person.age;
  const mandatsDisplay = hydrated?.mandats ?? person.mandats;
  const sciDisplay = hydrated?.sci ?? person.sci;

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
            {ageDisplay ? `${ageDisplay} ans` : "—"}{person.dept ? ` · dept ${person.dept}` : ""}
          </span>
          <ScoreBadge value={person.score} size="sm" />
        </div>
        <div style={{ marginTop: 6, fontSize: 12, color: "var(--text-secondary)", display: "flex", gap: 14, flexWrap: "wrap" }}>
          {/* Stats : 0 = placeholder (cas focus person extrait du query / LLM
            qui n'a pas encore les vraies valeurs). Affiche "—" plutôt que "0"
            pour ne pas afficher d'info trompeuse — la fiche drawer chargera
            les vraies stats au clic. */}
          <span><span style={{ color: "var(--text-muted)" }}>Mandats</span> <span className="dem-mono">{mandatsDisplay > 0 ? mandatsDisplay : "—"}</span></span>
          <span><span style={{ color: "var(--text-muted)" }}>SCI</span> <span className="dem-mono">{sciDisplay > 0 ? sciDisplay : "—"}</span></span>
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
