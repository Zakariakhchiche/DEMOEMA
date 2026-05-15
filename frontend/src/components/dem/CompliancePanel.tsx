"use client";

import React from "react";

// Shapes from backend /api/datalake/fiche/{siren}.compliance
//  - procedure_collective: { active: boolean | null, last_date, last_nature }
//  - opensanctions: { count, entries: [{caption, schema, topics, countries, sanctions_programs, last_seen}] }
//  - contentieux: { count, recents: [{decision_id, juridiction_type, juridiction, date_decision, titre}] }
//  - disclaimer: string

export interface CompanyCompliance {
  risk_score?: number;
  risk_level?: "low" | "medium" | "high" | "critical";
  procedure_collective?: {
    active: boolean | null;
    last_date: string | null;
    last_nature: string | null;
  };
  opensanctions?: { count: number; entries: Record<string, unknown>[] };
  contentieux?: { count: number; recents: Record<string, unknown>[] };
  conciliation?: { count: number; entries: Record<string, unknown>[] };
  plan_redressement?: { count: number; entries: Record<string, unknown>[] };
  late_filing?: boolean;
  dirigeant_senior?: boolean;
  trends?: {
    n_exercices: number;
    ca_trend_3y: "growing" | "flat" | "declining" | "unknown";
    resultat_trend_3y: "growing" | "flat" | "declining" | "unknown";
    effectif_trend_3y: "growing" | "flat" | "declining" | "unknown";
    marge_negative_recurrente: boolean;
  };
  cession_signal?: {
    active_24m: boolean;
    count: number;
    entries: Record<string, unknown>[];
  };
  network_red_flags?: { count: number; entries: Record<string, unknown>[] };
  disclaimer?: string;
}

// Shape from /api/datalake/dirigeant/.../compliance
export interface DirigeantCompliance {
  risk_score?: number;
  risk_level?: "low" | "medium" | "high" | "critical";
  interdiction_gerer?: { count: number; entries: Record<string, unknown>[] };
  faillite_personnelle?: { count: number; entries: Record<string, unknown>[] };
  opensanctions?: { count: number; entries: Record<string, unknown>[] };
  hatvp_lobbying?: {
    count: number;
    active: boolean;
    entries: Record<string, unknown>[];
  };
  co_mandataires_toxiques?: {
    count: number;
    entries: Record<string, unknown>[];
  };
  disclaimer?: string;
}

type Severity = "red" | "orange" | "yellow" | "green" | "neutral";

const palette: Record<Severity, { bg: string; fg: string; border: string; dot: string }> = {
  red:    { bg: "rgba(251,113,133,0.10)", fg: "var(--accent-rose)",    border: "rgba(251,113,133,0.30)", dot: "#fb7185" },
  orange: { bg: "rgba(251,146,60,0.10)",  fg: "var(--accent-amber)",   border: "rgba(251,146,60,0.30)",  dot: "#fb923c" },
  yellow: { bg: "rgba(251,191,36,0.10)",  fg: "var(--accent-amber)",   border: "rgba(251,191,36,0.30)", dot: "#fbbf24" },
  green:  { bg: "rgba(52,211,153,0.10)",  fg: "var(--accent-emerald)", border: "rgba(52,211,153,0.30)", dot: "#34d399" },
  neutral:{ bg: "rgba(255,255,255,0.03)", fg: "var(--text-tertiary)",  border: "var(--border-subtle)",   dot: "#888" },
};

function RiskGauge({
  score,
  level,
}: { score: number; level?: "low" | "medium" | "high" | "critical" }) {
  const sev: Severity =
    level === "critical" ? "red" :
    level === "high" ? "orange" :
    level === "medium" ? "yellow" :
    "green";
  const p = palette[sev];
  const label =
    level === "critical" ? "Critique" :
    level === "high" ? "Élevé" :
    level === "medium" ? "Modéré" :
    "Faible";
  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        gap: 14,
        padding: "10px 14px",
        borderRadius: 10,
        background: p.bg,
        border: `1px solid ${p.border}`,
        marginBottom: 10,
      }}
    >
      <div style={{ display: "flex", flexDirection: "column" }}>
        <div style={{ fontSize: 10, color: "var(--text-tertiary)", textTransform: "uppercase", letterSpacing: ".08em", fontWeight: 700 }}>
          Score risque
        </div>
        <div style={{ fontSize: 24, fontWeight: 700, color: p.fg, lineHeight: 1 }}>
          {score}<span style={{ fontSize: 12, color: "var(--text-tertiary)", fontWeight: 400 }}>/100</span>
        </div>
      </div>
      <div style={{ flex: 1, height: 8, background: "rgba(255,255,255,0.05)", borderRadius: 4, overflow: "hidden" }}>
        <div
          style={{
            width: `${score}%`,
            height: "100%",
            background: p.dot,
            transition: "width 0.4s ease",
          }}
        />
      </div>
      <div
        style={{
          padding: "4px 10px",
          borderRadius: 6,
          background: p.dot,
          color: "#fff",
          fontSize: 11,
          fontWeight: 700,
          letterSpacing: ".04em",
        }}
      >
        {label}
      </div>
    </div>
  );
}

function Badge({
  severity,
  label,
  detail,
}: { severity: Severity; label: string; detail?: string }) {
  const p = palette[severity];
  return (
    <div
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: 8,
        padding: "6px 10px",
        borderRadius: 8,
        background: p.bg,
        border: `1px solid ${p.border}`,
        fontSize: 12,
        fontWeight: 600,
        color: p.fg,
      }}
    >
      <span
        style={{
          width: 8,
          height: 8,
          borderRadius: "50%",
          background: p.dot,
          display: "inline-block",
          flexShrink: 0,
        }}
      />
      <span>{label}</span>
      {detail && (
        <span style={{ fontWeight: 500, color: "var(--text-secondary)" }}>· {detail}</span>
      )}
    </div>
  );
}

function Section({
  title,
  children,
}: { title: string; children: React.ReactNode }) {
  return (
    <div style={{ marginBottom: 18 }}>
      <div
        style={{
          fontSize: 11,
          fontWeight: 700,
          textTransform: "uppercase",
          letterSpacing: ".06em",
          color: "var(--text-tertiary)",
          marginBottom: 8,
        }}
      >
        {title}
      </div>
      <div style={{ display: "flex", flexDirection: "column", gap: 8, fontSize: 13 }}>
        {children}
      </div>
    </div>
  );
}

function Disclaimer({ text }: { text: string }) {
  return (
    <div
      style={{
        marginTop: 10,
        padding: "8px 10px",
        background: "rgba(255,255,255,0.03)",
        border: "1px solid var(--border-subtle)",
        borderRadius: 6,
        fontSize: 11,
        color: "var(--text-muted)",
        fontStyle: "italic",
        lineHeight: 1.5,
      }}
    >
      ⚠ {text}
    </div>
  );
}

function arr(v: unknown): string[] {
  return Array.isArray(v) ? (v as unknown[]).map(String).filter(Boolean) : [];
}

function dateOnly(v: unknown): string {
  if (!v) return "—";
  const s = String(v);
  return s.length >= 10 ? s.slice(0, 10) : s;
}

// ───────────────────────────── Company ─────────────────────────────

export function CompanyCompliancePanel({ data }: { data: CompanyCompliance | null | undefined }) {
  if (!data) return null;
  const proc = data.procedure_collective;
  const sanc = data.opensanctions;
  const cont = data.contentieux;
  const conc = data.conciliation;
  const plan = data.plan_redressement;
  const procActive = proc?.active === true;
  const procClosed = proc?.active === false;
  const hasAnySignal =
    procActive ||
    procClosed ||
    Boolean(sanc && sanc.count > 0) ||
    Boolean(cont && cont.count > 0) ||
    Boolean(conc && conc.count > 0) ||
    Boolean(plan && plan.count > 0) ||
    Boolean(data.late_filing) ||
    Boolean(data.dirigeant_senior);

  return (
    <Section title="Compliance & risque">
      {typeof data.risk_score === "number" && (
        <RiskGauge score={data.risk_score} level={data.risk_level} />
      )}

      {!hasAnySignal && (
        <Badge severity="green" label="Aucun signal public détecté" detail="BODACC, OpenSanctions, juridictions" />
      )}

      <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
        {procActive && (
          <Badge
            severity="red"
            label="Procédure collective active"
            detail={`${proc?.last_nature ?? "—"} · ${dateOnly(proc?.last_date)}`}
          />
        )}
        {procClosed && (
          <Badge
            severity="green"
            label="Procédure collective clôturée"
            detail={dateOnly(proc?.last_date)}
          />
        )}
        {plan && plan.count > 0 && (
          <Badge
            severity="orange"
            label={`Plan en exécution : ${plan.count}`}
            detail="redressement / sauvegarde"
          />
        )}
        {conc && conc.count > 0 && (
          <Badge
            severity="orange"
            label={`Conciliation : ${conc.count}`}
            detail="procédure amiable préventive"
          />
        )}
        {sanc && sanc.count > 0 && (
          <Badge severity="red" label={`OpenSanctions : ${sanc.count} match`} />
        )}
        {cont && cont.count > 0 && (
          <Badge severity="orange" label={`Contentieux : ${cont.count} décision${cont.count > 1 ? "s" : ""}`} />
        )}
        {data.late_filing && (
          <Badge severity="orange" label="Retard dépôt comptes" detail="signal stress financier" />
        )}
        {data.dirigeant_senior && (
          <Badge severity="yellow" label="Dirigeant senior 65+" detail="probabilité transmission élevée" />
        )}
        {data.trends && data.trends.ca_trend_3y === "declining" && (
          <Badge severity="orange" label="CA déclinant 3 ans" detail="tendance baissière" />
        )}
        {data.trends && data.trends.effectif_trend_3y === "declining" && (
          <Badge severity="orange" label="Effectif en chute" detail="3 derniers exercices" />
        )}
        {data.trends && data.trends.marge_negative_recurrente && (
          <Badge severity="red" label="Pertes récurrentes" detail="résultat net négatif 3 ans" />
        )}
        {data.trends && data.trends.ca_trend_3y === "growing"
          && data.trends.resultat_trend_3y !== "declining" && (
          <Badge severity="green" label="Trajectoire croissante" detail="CA en hausse 3 ans" />
        )}
        {data.cession_signal && data.cession_signal.active_24m && (
          <Badge
            severity="yellow"
            label={`Cession 24m : ${data.cession_signal.count}`}
            detail="opportunité M&A — vente détectée BODACC"
          />
        )}
        {data.network_red_flags && data.network_red_flags.count > 0 && (
          <Badge
            severity="orange"
            label={`Réseau red flags : ${data.network_red_flags.count}`}
            detail="dirigeants associés en procédure ailleurs"
          />
        )}
      </div>

      {data.network_red_flags && data.network_red_flags.entries.length > 0 && (
        <div style={{ marginTop: 10, display: "flex", flexDirection: "column", gap: 6 }}>
          <div style={{ fontSize: 11, color: "var(--text-tertiary)", fontWeight: 600 }}>
            Dirigeants en procédure ailleurs (1-hop)
          </div>
          {data.network_red_flags.entries.slice(0, 5).map((e, k) => (
            <div
              key={k}
              style={{
                padding: 8,
                background: "rgba(251,146,60,0.05)",
                border: "1px solid rgba(251,146,60,0.20)",
                borderRadius: 6,
              }}
            >
              <div style={{ fontWeight: 600 }}>
                {String(e.prenom ?? "")} {String(e.nom ?? "")}
              </div>
              <div style={{ fontSize: 11, color: "var(--text-tertiary)" }}>
                via SIREN {String(e.toxic_siren ?? "—")} ·{" "}
                {String(e.toxic_denom ?? "—")} · {String(e.reason ?? "—").slice(0, 80)}
              </div>
            </div>
          ))}
        </div>
      )}

      {data.cession_signal && data.cession_signal.entries.length > 0 && (
        <div style={{ marginTop: 10, display: "flex", flexDirection: "column", gap: 4 }}>
          <div style={{ fontSize: 11, color: "var(--text-tertiary)", fontWeight: 600 }}>
            Cessions BODACC (24m)
          </div>
          {data.cession_signal.entries.slice(0, 5).map((e, k) => (
            <div key={k} style={{ fontSize: 12, color: "var(--text-secondary)" }}>
              <span className="dem-mono" style={{ color: "var(--text-tertiary)" }}>
                {dateOnly(e.date_parution)}
              </span>{" "}
              <span style={{ color: "var(--text-tertiary)" }}>· {String(e.type ?? "—")}</span>{" "}
              <span>{String(e.detail ?? e.ville ?? "—").slice(0, 110)}</span>
            </div>
          ))}
        </div>
      )}

      {sanc && sanc.entries.length > 0 && (
        <div style={{ marginTop: 10, display: "flex", flexDirection: "column", gap: 6 }}>
          {sanc.entries.slice(0, 5).map((e, k) => (
            <div
              key={k}
              style={{
                padding: 8,
                background: "rgba(251,113,133,0.05)",
                border: "1px solid rgba(251,113,133,0.20)",
                borderRadius: 6,
              }}
            >
              <div style={{ fontWeight: 600 }}>{String(e.caption ?? "—")}</div>
              <div style={{ fontSize: 11, color: "var(--text-tertiary)" }}>
                topics: {arr(e.topics).join(", ") || "—"} · pays:{" "}
                {arr(e.countries).join(", ") || "—"} · programmes:{" "}
                {arr(e.sanctions_programs).join(", ") || "—"}
                {e.last_seen ? ` · vu : ${dateOnly(e.last_seen)}` : ""}
              </div>
            </div>
          ))}
        </div>
      )}

      {cont && cont.recents.length > 0 && (
        <div style={{ marginTop: 10, display: "flex", flexDirection: "column", gap: 4 }}>
          <div style={{ fontSize: 11, color: "var(--text-tertiary)", fontWeight: 600 }}>
            Décisions récentes
          </div>
          {cont.recents.slice(0, 5).map((r, k) => (
            <div key={k} style={{ fontSize: 12, color: "var(--text-secondary)" }}>
              <span className="dem-mono" style={{ color: "var(--text-tertiary)" }}>
                {dateOnly(r.date_decision)}
              </span>{" "}
              <span style={{ color: "var(--text-tertiary)" }}>
                · {String(r.juridiction ?? r.juridiction_type ?? "—")}
              </span>{" "}
              <span>{String(r.titre ?? "—").slice(0, 110)}</span>
            </div>
          ))}
        </div>
      )}

      {data.disclaimer && <Disclaimer text={data.disclaimer} />}
    </Section>
  );
}

// ───────────────────────────── Dirigeant ─────────────────────────────

export function DirigeantCompliancePanel({
  data,
}: { data: DirigeantCompliance | null | undefined }) {
  if (!data) return null;
  const inter = data.interdiction_gerer;
  const fail = data.faillite_personnelle;
  const sanc = data.opensanctions;
  const hat = data.hatvp_lobbying;
  const tox = data.co_mandataires_toxiques;
  const hasAnySignal =
    Boolean(inter && inter.count > 0) ||
    Boolean(fail && fail.count > 0) ||
    Boolean(sanc && sanc.count > 0) ||
    Boolean(hat && hat.count > 0) ||
    Boolean(tox && tox.count > 0);

  return (
    <Section title="Compliance & risque (dirigeant)">
      {typeof data.risk_score === "number" && (
        <RiskGauge score={data.risk_score} level={data.risk_level} />
      )}

      {!hasAnySignal && (
        <Badge severity="green" label="Aucun signal public détecté" detail="BODACC, OpenSanctions, HATVP, réseau" />
      )}

      <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
        {inter && inter.count > 0 && (
          <Badge
            severity="red"
            label={`Interdiction de gérer : ${inter.count}`}
            detail="dans une société dirigée"
          />
        )}
        {fail && fail.count > 0 && (
          <Badge
            severity="red"
            label={`Faillite personnelle : ${fail.count}`}
            detail="dans une société dirigée"
          />
        )}
        {sanc && sanc.count > 0 && (
          <Badge severity="red" label={`OpenSanctions : ${sanc.count} match`} />
        )}
        {tox && tox.count > 0 && (
          <Badge
            severity="orange"
            label={`Co-mandataires red flag : ${tox.count}`}
            detail="réseau 1-hop en procédure"
          />
        )}
        {hat && hat.count > 0 && (
          <Badge
            severity={hat.active ? "orange" : "yellow"}
            label={`HATVP lobbying : ${hat.count}`}
            detail={hat.active ? "actif" : "inactif"}
          />
        )}
      </div>

      {inter && inter.entries.length > 0 && (
        <div style={{ marginTop: 10, display: "flex", flexDirection: "column", gap: 6 }}>
          <div style={{ fontSize: 11, color: "var(--text-tertiary)", fontWeight: 600 }}>
            Interdictions de gérer (BODACC)
          </div>
          {inter.entries.slice(0, 5).map((e, k) => (
            <div
              key={k}
              style={{
                padding: 8,
                background: "rgba(251,113,133,0.05)",
                border: "1px solid rgba(251,113,133,0.20)",
                borderRadius: 6,
              }}
            >
              <div style={{ fontSize: 11, color: "var(--text-tertiary)" }}>
                <span className="dem-mono">{dateOnly(e.date_parution)}</span> ·
                SIREN {String(e.siren ?? "—")}
              </div>
              <div style={{ fontSize: 12, marginTop: 2 }}>{String(e.detail ?? e.nature ?? "—")}</div>
            </div>
          ))}
        </div>
      )}

      {fail && fail.entries.length > 0 && (
        <div style={{ marginTop: 10, display: "flex", flexDirection: "column", gap: 6 }}>
          <div style={{ fontSize: 11, color: "var(--text-tertiary)", fontWeight: 600 }}>
            Faillites personnelles (BODACC)
          </div>
          {fail.entries.slice(0, 5).map((e, k) => (
            <div
              key={k}
              style={{
                padding: 8,
                background: "rgba(251,113,133,0.05)",
                border: "1px solid rgba(251,113,133,0.20)",
                borderRadius: 6,
              }}
            >
              <div style={{ fontSize: 11, color: "var(--text-tertiary)" }}>
                <span className="dem-mono">{dateOnly(e.date_parution)}</span> ·
                SIREN {String(e.siren ?? "—")}
              </div>
              <div style={{ fontSize: 12, marginTop: 2 }}>{String(e.detail ?? e.nature ?? "—")}</div>
            </div>
          ))}
        </div>
      )}

      {tox && tox.entries.length > 0 && (
        <div style={{ marginTop: 10, display: "flex", flexDirection: "column", gap: 6 }}>
          <div style={{ fontSize: 11, color: "var(--text-tertiary)", fontWeight: 600 }}>
            Co-mandataires en procédure (réseau 1-hop)
          </div>
          {tox.entries.slice(0, 5).map((e, k) => (
            <div
              key={k}
              style={{
                padding: 8,
                background: "rgba(251,146,60,0.05)",
                border: "1px solid rgba(251,146,60,0.20)",
                borderRadius: 6,
              }}
            >
              <div style={{ fontWeight: 600 }}>
                {String(e.prenom ?? "")} {String(e.nom ?? "")}
              </div>
              <div style={{ fontSize: 11, color: "var(--text-tertiary)" }}>
                via SIREN {String(e.toxic_siren ?? "—")} ·{" "}
                {String(e.toxic_denom ?? "—")} · {String(e.reason ?? "—").slice(0, 80)}
              </div>
            </div>
          ))}
        </div>
      )}

      {hat && hat.entries.length > 0 && (
        <div style={{ marginTop: 10, display: "flex", flexDirection: "column", gap: 4 }}>
          <div style={{ fontSize: 11, color: "var(--text-tertiary)", fontWeight: 600 }}>
            HATVP — représentants d&apos;intérêts
          </div>
          {hat.entries.slice(0, 5).map((e, k) => (
            <div key={k} style={{ fontSize: 12, color: "var(--text-secondary)" }}>
              <span style={{ fontWeight: 600 }}>{String(e.denomination ?? "—")}</span>
              {e.dirigeant_fonction ? ` · ${String(e.dirigeant_fonction)}` : ""}
              {e.lobbying_actif ? (
                <span style={{ color: "var(--accent-amber)", marginLeft: 6 }}>· actif</span>
              ) : (
                <span style={{ color: "var(--text-muted)", marginLeft: 6 }}>· inactif</span>
              )}
              {e.date_derniere_activite ? (
                <span style={{ color: "var(--text-tertiary)", marginLeft: 6 }}>
                  · maj {dateOnly(e.date_derniere_activite)}
                </span>
              ) : null}
            </div>
          ))}
        </div>
      )}

      {data.disclaimer && <Disclaimer text={data.disclaimer} />}
    </Section>
  );
}
