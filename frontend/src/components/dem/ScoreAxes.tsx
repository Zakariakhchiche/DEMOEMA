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
  // Les 4 axes v3 ne sont pas calculés dans le scoring_ma courant → tous à 0.
  // Afficher "0/100" sur les 4 est trompeur (laisse croire à un score nul réel).
  // On masque la section tant qu'aucun axe n'est renseigné.
  if (values.every((a) => !a.value)) return null;

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
              // Couleur pleine via token (un gradient `${var()}88` est invalide → le
              // navigateur l'ignore et la barre restait vide ; cf. variante compact).
              background: tone(axis.value),
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

/* ── Ratios financiers (grille "Financial ratio assessment") ─────────────── */

type Ratios = {
  ebitda_margin: number | null;
  ebit_margin: number | null;
  net_margin: number | null;
  debt_to_ebitda: number | null;
  debt_to_equity: number | null;
  debt_ratio: number | null;
  equity_ratio: number | null;
  dso_days: number | null;
  revenue_growth_yoy: number | null;
  roa?: number | null;
  bfr_jours?: number | null;
  intensite_capitalistique?: number | null;
  financial_health_tier: string | null;
  has_negative_equity: boolean;
  has_negative_ebitda: boolean;
  has_high_leverage: boolean;
  has_revenue_decline: boolean;
} | null | undefined;

// rating : +1 above / 0 average / -1 below (seuils grille Orascom). higherBetter
// = un ratio élevé est bon (marges) ; sinon élevé = mauvais (dette, DSO).
function rate(v: number | null, below: number, above: number, higherBetter: boolean): number | null {
  if (v == null) return null;
  if (higherBetter) return v >= above ? 1 : v < below ? -1 : 0;
  return v <= above ? 1 : v > below ? -1 : 0;
}
const RATING_COLOR = ["var(--accent-emerald,#34d399)", "var(--accent-amber,#fbbf24)", "var(--text-muted,#9b2c2c)"];
function ratingColor(r: number | null): string {
  if (r == null) return "var(--text-tertiary,#8a8a92)";
  return r > 0 ? RATING_COLOR[0] : r === 0 ? RATING_COLOR[1] : "#f87171";
}
const pct = (v: number | null) => (v == null ? "—" : `${(v * 100).toFixed(1)}%`);
const xfmt = (v: number | null) => (v == null ? "—" : `${v.toFixed(2)}×`);
const dfmt = (v: number | null) => (v == null ? "—" : `${Math.round(v)} j`);
const xc = (v: number | null) => (v == null ? "—" : `${v.toFixed(1)}×`);

export function FinancialRatios({ ratios }: { ratios: Ratios }) {
  if (!ratios) return null;
  const rows: { label: string; val: string; rating: number | null }[] = [
    { label: "Marge EBITDA", val: pct(ratios.ebitda_margin), rating: rate(ratios.ebitda_margin, 0.08, 0.15, true) },
    { label: "Marge nette", val: pct(ratios.net_margin), rating: rate(ratios.net_margin, 0.05, 0.15, true) },
    { label: "ROA (rentabilité actifs)", val: pct(ratios.roa ?? null), rating: rate(ratios.roa ?? null, 0.02, 0.08, true) },
    { label: "Dette / EBITDA", val: xfmt(ratios.debt_to_ebitda), rating: rate(ratios.debt_to_ebitda, 4, 1.5, false) },
    { label: "Dette / Fonds propres", val: xfmt(ratios.debt_to_equity), rating: rate(ratios.debt_to_equity, 2, 0.6, false) },
    { label: "Ratio d'endettement", val: pct(ratios.debt_ratio), rating: rate(ratios.debt_ratio, 0.9, 0.4, false) },
    { label: "DSO (créances)", val: dfmt(ratios.dso_days), rating: rate(ratios.dso_days, 75, 40, false) },
    { label: "BFR (stocks + créances)", val: dfmt(ratios.bfr_jours ?? null), rating: rate(ratios.bfr_jours ?? null, 120, 45, false) },
    { label: "Intensité capitalistique", val: xc(ratios.intensite_capitalistique ?? null), rating: null },
    { label: "Croissance CA", val: pct(ratios.revenue_growth_yoy), rating: rate(ratios.revenue_growth_yoy, 0, 0.05, true) },
  ].filter((r) => r.val !== "—");
  if (rows.length === 0) return null;

  const tierMeta: Record<string, { label: string; color: string }> = {
    above_average: { label: "Au-dessus", color: RATING_COLOR[0] },
    average: { label: "Acceptable", color: RATING_COLOR[1] },
    below_average: { label: "En-dessous", color: "#f87171" },
  };
  const tier = ratios.financial_health_tier ? tierMeta[ratios.financial_health_tier] : null;
  const flags = [
    ratios.has_negative_equity && "Capitaux propres négatifs",
    ratios.has_negative_ebitda && "EBITDA négatif",
    ratios.has_high_leverage && "Surendettement",
    ratios.has_revenue_decline && "Chute d'activité",
  ].filter(Boolean) as string[];

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 8, marginTop: 8 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <span style={{ fontSize: 12.5, fontWeight: 700, color: "var(--text-primary)" }}>Ratios financiers</span>
        {tier && (
          <span style={{ fontSize: 10.5, fontWeight: 700, color: tier.color, padding: "1px 8px", borderRadius: 999, background: "rgba(255,255,255,0.05)" }}>
            {tier.label}
          </span>
        )}
      </div>
      <div style={{ display: "grid", gridTemplateColumns: "1fr auto", gap: "4px 12px" }}>
        {rows.map((r) => (
          <div key={r.label} style={{ display: "contents" }}>
            <span style={{ fontSize: 11.5, color: "var(--text-secondary,#c0c0c8)" }}>{r.label}</span>
            <span className="dem-mono tab-num" style={{ fontSize: 11.5, fontWeight: 700, color: ratingColor(r.rating), textAlign: "right" }}>{r.val}</span>
          </div>
        ))}
      </div>
      {flags.length > 0 && (
        <div style={{ display: "flex", gap: 5, flexWrap: "wrap", marginTop: 2 }}>
          {flags.map((f) => (
            <span key={f} style={{ fontSize: 9.5, fontWeight: 600, color: "#f87171", padding: "1px 7px", borderRadius: 999, background: "rgba(248,113,113,0.12)" }}>⚠ {f}</span>
          ))}
        </div>
      )}
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
