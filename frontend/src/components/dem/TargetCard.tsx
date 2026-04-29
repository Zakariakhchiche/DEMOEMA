"use client";

import { Icon } from "./Icon";
import { ScoreBadge } from "./ScoreBadge";
import { Sparkline } from "./Sparkline";
import type { Target, Density } from "@/lib/dem/types";

interface Props {
  target: Target;
  density?: Density;
  selected?: boolean;
  onSelect?: () => void;
  onView?: () => void;
  onSave?: () => void;
  onPitch?: () => void;
  onCompare?: () => void;
  isSaved?: boolean;
}

export function TargetCard({ target, density = "comfortable", selected, onSelect, onView, onSave, onPitch, isSaved }: Props) {
  const compact = density === "compact";
  const spacious = density === "spacious";
  const hasFlag = target.red_flags && target.red_flags.length > 0;
  return (
    <div
      className={`dem-glass card-lift ${selected ? "selected" : ""}`}
      style={{
        borderRadius: 14,
        padding: compact ? "10px 14px" : spacious ? "20px 22px" : "14px 18px",
        display: "flex",
        gap: compact ? 12 : 16,
        alignItems: compact ? "center" : "stretch",
        position: "relative",
        cursor: "pointer",
        borderColor: selected ? "rgba(96,165,250,0.45)" : undefined,
        background: selected ? "rgba(96,165,250,0.06)" : undefined,
      }}
      onClick={(e) => {
        if (e.shiftKey) onSelect?.();
        else onView?.();
      }}
    >
      <div style={{ display: "flex", alignItems: compact ? "center" : "flex-start", paddingTop: compact ? 0 : 2 }}>
        <button
          type="button"
          onClick={(e) => { e.stopPropagation(); onSelect?.(); }}
          style={{
            width: 16, height: 16, borderRadius: 4,
            border: `1.5px solid ${selected ? "var(--accent-blue)" : "var(--border-mid)"}`,
            background: selected ? "var(--accent-blue)" : "transparent",
            display: "flex", alignItems: "center", justifyContent: "center",
            cursor: "pointer", flexShrink: 0,
          }}
        >
          {selected && <Icon name="check" size={11} color="#0a0a0d" strokeWidth={3} />}
        </button>
      </div>

      <ScoreBadge value={target.score} size={compact ? "sm" : spacious ? "lg" : "md"} breakdown={target.score_breakdown} />

      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap" }}>
          <div style={{ fontWeight: 600, fontSize: compact ? 13.5 : 15, color: "var(--text-primary)", letterSpacing: "-0.01em" }}>
            {target.denomination}
          </div>
          <span className="dem-mono" style={{ fontSize: 11, color: "var(--text-tertiary)" }}>siren {target.siren}</span>
          {hasFlag && (
            <span style={{
              display: "inline-flex", alignItems: "center", gap: 4,
              padding: "2px 7px", borderRadius: 999,
              background: "rgba(251,113,133,0.10)", border: "1px solid rgba(251,113,133,0.30)",
              color: "var(--accent-rose)", fontSize: 10.5, fontWeight: 600,
            }}>
              <Icon name="warning" size={10} /> {target.red_flags[0].type === "icij" ? "ICIJ" : "Risque"}
            </span>
          )}
        </div>

        {!compact && (
          <div style={{ display: "flex", gap: 18, marginTop: 8, fontSize: 12, color: "var(--text-secondary)", flexWrap: "wrap", alignItems: "center" }}>
            <span><span style={{ color: "var(--text-muted)" }}>CA</span> <span className="dem-mono tab-num" style={{ color: "var(--text-primary)", fontWeight: 600 }}>{target.ca_str}</span></span>
            <span><span style={{ color: "var(--text-muted)" }}>EBITDA</span> <span className="dem-mono tab-num" style={{ color: "var(--text-primary)", fontWeight: 500 }}>{target.ebitda_str}</span></span>
            <span><span style={{ color: "var(--text-muted)" }}>Effectif</span> <span className="dem-mono tab-num">{target.effectif ?? "—"}</span></span>
            <span><span style={{ color: "var(--text-muted)" }}>NAF</span> <span className="dem-mono">{target.naf || "—"}</span></span>
            <span><span style={{ color: "var(--text-muted)" }}>Dept</span> <span className="dem-mono">{target.dept || "—"}</span> {target.ville && <span style={{ color: "var(--text-tertiary)" }}>· {target.ville}</span>}</span>
            {target.ca_history.length >= 2 && (
              <Sparkline data={target.ca_history} width={60} height={16} color={target.score >= 70 ? "var(--accent-emerald)" : "var(--accent-amber)"} />
            )}
          </div>
        )}

        {!compact && target.top_dirigeant.nom !== "—" && (
          <div style={{ display: "flex", alignItems: "center", gap: 8, marginTop: 10, fontSize: 11.5, color: "var(--text-secondary)" }}>
            <div style={{
              width: 22, height: 22, borderRadius: 999,
              background: "linear-gradient(135deg, #3b3b44, #1a1a20)",
              border: "1px solid var(--border-soft)", display: "flex", alignItems: "center", justifyContent: "center",
              fontWeight: 600, fontSize: 9.5, color: "var(--text-secondary)",
            }}>
              {target.top_dirigeant.nom.split(" ").map((n) => n[0]).join("").slice(0, 2)}
            </div>
            <span>{target.top_dirigeant.nom}</span>
            <span style={{ color: "var(--text-muted)" }}>
              · {target.top_dirigeant.age ?? "?"} ans · {target.top_dirigeant.mandats} mandats
            </span>
          </div>
        )}

        {hasFlag && !compact && (
          <div style={{
            marginTop: 8, padding: "6px 10px", borderRadius: 8,
            background: "rgba(251,113,133,0.06)", border: "1px solid rgba(251,113,133,0.18)",
            color: "var(--accent-rose)", fontSize: 11.5,
            display: "flex", alignItems: "center", gap: 6,
          }}>
            <Icon name="warning" size={11} />
            <span>{target.red_flags[0].label}</span>
            <span style={{ color: "var(--text-tertiary)", marginLeft: "auto" }}>via {target.red_flags[0].source}</span>
          </div>
        )}
      </div>

      {!compact && (
        <div style={{
          display: "flex",
          flexDirection: spacious ? "row" : "column",
          gap: 6, alignItems: "flex-end", justifyContent: "center",
        }}>
          <button className="dem-btn dem-btn-primary" onClick={(e) => { e.stopPropagation(); onView?.(); }}>
            <Icon name="eye" size={12} /> Fiche
          </button>
          <button className="dem-btn" onClick={(e) => { e.stopPropagation(); onSave?.(); }}>
            {isSaved ? <Icon name="check" size={12} /> : <Icon name="bookmark" size={12} />}
            {isSaved ? "Sauvé" : "Sauver"}
          </button>
          <button className="dem-btn dem-btn-ghost" onClick={(e) => { e.stopPropagation(); onPitch?.(); }} title="Pitch Ready PDF">
            <Icon name="sparkles" size={12} /> Pitch
          </button>
        </div>
      )}

      {compact && (
        <div style={{ display: "flex", gap: 14, alignItems: "center", fontSize: 12, color: "var(--text-secondary)" }}>
          <span className="dem-mono tab-num" style={{ color: "var(--text-primary)", fontWeight: 600 }}>{target.ca_str}</span>
          <span className="dem-mono">{target.naf}</span>
          <span className="dem-mono">{target.dept}</span>
          <button className="dem-btn dem-btn-icon dem-btn-ghost" onClick={(e) => { e.stopPropagation(); onView?.(); }}>
            <Icon name="arrowRight" size={12} />
          </button>
        </div>
      )}
    </div>
  );
}
