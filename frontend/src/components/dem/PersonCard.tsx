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
    // Backend accepte 1974 (LIKE '1974%') ou 1974-04 (LIKE '1974-04%') ou
    // 1974-04-12 (exact). On passe ce qu'on a — au minimum l'année suffit
    // pour disambiguer 6 homonymes Vincent LAMOUR. Cf. SKILL demoema-fiche-dirigeant
    // : la clé d'unicité silver.inpi_dirigeants = (nom, prenom, date_naissance).
    const dn = person.date_naissance && person.date_naissance.length >= 4
      ? (person.date_naissance.length >= 7 ? person.date_naissance.slice(0, 7) : person.date_naissance.slice(0, 4))
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
          {person.is_transmission && (
            <span title="Âge ≥ 65 + multi-mandats : cession probable" style={{
              display: "inline-flex", alignItems: "center", gap: 4, padding: "2px 7px", borderRadius: 999,
              background: "rgba(52,211,153,0.12)", border: "1px solid var(--accent-emerald,#34d399)",
              color: "var(--accent-emerald,#34d399)", fontSize: 10.5, fontWeight: 600,
            }}>🎯 Transmission</span>
          )}
          {person.is_lobbyist && (
            <span title="Dirige une société inscrite au registre HATVP (lobbying)" style={{
              display: "inline-flex", alignItems: "center", gap: 4, padding: "2px 7px", borderRadius: 999,
              background: "rgba(251,191,36,0.10)", border: "1px solid rgba(251,191,36,0.35)",
              color: "var(--accent-amber,#fbbf24)", fontSize: 10.5, fontWeight: 600,
            }}>⚠️ Lobbyiste</span>
          )}
          {person.has_sanctioned_company && (
            <span title="Une de ses sociétés a un red flag compliance (sanction / offshore)" style={{
              display: "inline-flex", alignItems: "center", gap: 4, padding: "2px 7px", borderRadius: 999,
              background: "rgba(251,113,133,0.10)", border: "1px solid rgba(251,113,133,0.35)",
              color: "var(--accent-rose,#fb7185)", fontSize: 10.5, fontWeight: 600,
            }}>🔴 Société sanctionnée</span>
          )}
        </div>
        <div style={{ marginTop: 6, fontSize: 12, color: "var(--text-secondary)", display: "flex", gap: 14, flexWrap: "wrap" }}>
          {/* Stats : 0 = placeholder (cas focus person extrait du query / LLM
            qui n'a pas encore les vraies valeurs). Affiche "—" plutôt que "0"
            pour ne pas afficher d'info trompeuse — la fiche drawer chargera
            les vraies stats au clic. */}
          <span><span style={{ color: "var(--text-muted)" }}>Mandats</span> <span className="dem-mono">{mandatsDisplay > 0 ? mandatsDisplay : "—"}</span></span>
          <span><span style={{ color: "var(--text-muted)" }}>SCI</span> <span className="dem-mono">{sciDisplay > 0 ? sciDisplay : "—"}</span></span>
          {person.role && (
            <span><span style={{ color: "var(--text-muted)" }}>Rôle</span> <span style={{ color: "var(--text-secondary)" }}>{person.role}</span></span>
          )}
          {(person.ceded ?? 0) > 0 && (
            <span title="Mandats clôturés = sorties/cessions passées" style={{ color: "var(--accent-cyan)" }}>
              {person.ceded} cédé{(person.ceded ?? 0) > 1 ? "s" : ""}
            </span>
          )}
        </div>
        {person.companies && person.companies.length > 0 && (
          <div style={{ marginTop: 5, fontSize: 11.5, color: "var(--text-secondary)", display: "flex", gap: 6, alignItems: "baseline", flexWrap: "wrap" }}>
            <span style={{ color: "var(--text-muted)" }}>
              Dirige {person.n_companies ?? person.companies.length} société{(person.n_companies ?? person.companies.length) > 1 ? "s" : ""} ·
            </span>
            <span style={{ color: "var(--text-secondary)" }}>
              {person.companies.slice(0, 3).join(", ")}
              {(person.n_companies ?? 0) > 3 ? `, +${(person.n_companies ?? 0) - 3}` : ""}
            </span>
          </div>
        )}
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
