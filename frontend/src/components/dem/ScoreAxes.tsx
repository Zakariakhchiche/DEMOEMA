"use client";

/**
 * ScoreAxes — affichage des 4 axes business du scoring v3 PRO.
 *
 * 4 axes 0-100 :
 * - TRANSMISSION : probabilité de cession (âge dirigeant + patrimoine optimisé)
 * - ATTRACTIVITY : valeur réelle (marge × multiple sectoriel)
 * - SCALE : barrière transactionnelle (CA absolu)
 * - STRUCTURE : suitability (forme juridique + multi-mandats)
 *
 * Score composite = (T × A × S)^(1/3) × risk_multiplier
 * Voir docs/SIGNAUX_MA.md pour le barème détaillé.
 */

interface Axes {
  transmission?: number | null;
  attractivity?: number | null;
  scale?: number | null;
  structure?: number | null;
}

interface Props {
  axes?: Axes;
  variant?: "compact" | "detailed";
}

const AXIS_META: { key: keyof Axes; label: string; short: string; color: string; description: string }[] = [
  { key: "transmission", label: "Transmission", short: "TRA", color: "var(--accent-purple, #a78bfa)", description: "Probabilité de cession (âge dirigeant + patrimoine fiscalement optimisé)" },
  { key: "attractivity", label: "Attractivity", short: "ATT", color: "var(--accent-blue, #60a5fa)", description: "Valeur réelle de la cible (marge × multiple sectoriel)" },
  { key: "scale", label: "Scale", short: "SCA", color: "var(--accent-emerald, #34d399)", description: "Barrière transactionnelle (CA absolu)" },
  { key: "structure", label: "Structure", short: "STR", color: "var(--accent-amber, #fbbf24)", description: "Suitability transaction (forme juridique + multi-mandats)" },
];

function tone(value: number): string {
  // Couleur selon le score (vert si fort, ambre si moyen, gris si faible)
  if (value >= 70) return "var(--accent-emerald, #34d399)";
  if (value >= 50) return "var(--accent-blue, #60a5fa)";
  if (value >= 30) return "var(--accent-amber, #fbbf24)";
  return "var(--text-muted, #6b6b75)";
}

export function ScoreAxes({ axes, variant = "compact" }: Props) {
  if (!axes) return null;
  const values = AXIS_META.map((m) => ({ ...m, value: axes[m.key] ?? 0 }));

  if (variant === "compact") {
    // Mini-bars sur une ligne (intégré dans TargetCard)
    return (
      <div style={{ display: "flex", gap: 10, marginTop: 6, flexWrap: "wrap" }}>
        {values.map((axis) => (
          <div key={axis.key} title={`${axis.label} : ${axis.value}/100 — ${axis.description}`} style={{ display: "flex", alignItems: "center", gap: 5 }}>
            <span style={{ fontSize: 9.5, color: "var(--text-tertiary, #8a8a92)", fontWeight: 600, letterSpacing: "0.04em" }}>{axis.short}</span>
            <div style={{ position: "relative", width: 32, height: 4, borderRadius: 2, background: "rgba(255,255,255,0.06)", overflow: "hidden" }}>
              <div style={{
                position: "absolute", left: 0, top: 0, bottom: 0,
                width: `${Math.max(0, Math.min(100, axis.value))}%`,
                background: tone(axis.value), borderRadius: 2,
              }} />
            </div>
            <span className="dem-mono tab-num" style={{ fontSize: 10.5, color: "var(--text-secondary, #c0c0c8)", fontWeight: 600, minWidth: 18 }}>
              {axis.value}
            </span>
          </div>
        ))}
      </div>
    );
  }

  // Detailed : section complète pour la fiche entreprise
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 10, marginTop: 8 }}>
      {values.map((axis) => (
        <div key={axis.key} style={{ display: "flex", flexDirection: "column", gap: 4 }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline" }}>
            <span style={{ fontSize: 12.5, fontWeight: 600, color: "var(--text-primary)" }}>
              {axis.label}
            </span>
            <span className="dem-mono tab-num" style={{ fontSize: 13, fontWeight: 700, color: tone(axis.value) }}>
              {axis.value}<span style={{ fontSize: 10, color: "var(--text-tertiary)", fontWeight: 400 }}>/100</span>
            </span>
          </div>
          <div style={{ position: "relative", width: "100%", height: 6, borderRadius: 3, background: "rgba(255,255,255,0.06)", overflow: "hidden" }}>
            <div style={{
              position: "absolute", left: 0, top: 0, bottom: 0,
              width: `${Math.max(0, Math.min(100, axis.value))}%`,
              background: `linear-gradient(90deg, ${tone(axis.value)}88, ${tone(axis.value)})`,
              borderRadius: 3,
              transition: "width 0.4s cubic-bezier(.16,1,.3,1)",
            }} />
          </div>
          <span style={{ fontSize: 10.5, color: "var(--text-tertiary)", fontStyle: "italic" }}>
            {axis.description}
          </span>
        </div>
      ))}
    </div>
  );
}

interface TierBadgeProps {
  tier?: "A_HOT" | "B_WARM" | "C_PIPELINE" | "D_WATCH" | "E_REJECT" | "Z_ELIM" | string;
  percentile?: number;
}

const TIER_LABELS: Record<string, { label: string; color: string; bg: string }> = {
  A_HOT: { label: "A · Hot", color: "#fff", bg: "#ef4444" },
  B_WARM: { label: "B · Warm", color: "#fff", bg: "#f97316" },
  C_PIPELINE: { label: "C · Pipeline", color: "#fff", bg: "#3b82f6" },
  D_WATCH: { label: "D · Watch", color: "#1f2937", bg: "#cbd5e1" },
  E_REJECT: { label: "E · Reject", color: "#9ca3af", bg: "rgba(255,255,255,0.04)" },
  Z_ELIM: { label: "Z · Éliminé", color: "#fff", bg: "#71717a" },
};

export function TierBadge({ tier, percentile }: TierBadgeProps) {
  if (!tier) return null;
  const meta = TIER_LABELS[tier] || { label: tier, color: "#fff", bg: "#71717a" };
  return (
    <span
      title={percentile ? `Percentile ${percentile} sur la pop. M&A` : meta.label}
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: 4,
        padding: "2px 8px",
        borderRadius: 999,
        background: meta.bg,
        color: meta.color,
        fontSize: 10.5,
        fontWeight: 700,
        letterSpacing: "0.04em",
        textTransform: "uppercase",
      }}
    >
      {meta.label}
      {percentile != null && (
        <span style={{ fontSize: 9.5, opacity: 0.85, fontWeight: 500 }}>
          P{percentile}
        </span>
      )}
    </span>
  );
}
