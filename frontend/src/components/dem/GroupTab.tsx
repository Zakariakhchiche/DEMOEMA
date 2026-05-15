"use client";

import { useEffect, useState } from "react";
import { Icon } from "./Icon";
import { datalakeApi } from "@/lib/api";
import { formatSiren } from "@/lib/dem/format";

interface Props {
  siren: string;
  onOpenSiren?: (siren: string) => void;
}

type GroupData = Awaited<ReturnType<typeof datalakeApi.groupe>>;

function fmtEur(v: unknown): string {
  if (v == null) return "—";
  const n = typeof v === "number" ? v : Number(v);
  if (isNaN(n) || !n) return "—";
  if (Math.abs(n) >= 1e9) return `${(n / 1e9).toFixed(1)} Md€`;
  if (Math.abs(n) >= 1e6) return `${(n / 1e6).toFixed(1)} M€`;
  if (Math.abs(n) >= 1e3) return `${(n / 1e3).toFixed(0)} k€`;
  return `${n.toFixed(0)} €`;
}

const ROLE_LABELS: Record<string, string> = {
  "73": "Administrateur",
  "71": "Président SA",
  "65": "Gérant",
  "30": "Associé",
  "11": "Représentant PM",
  "29": "Société liée",
  "40": "Représentant permanent",
  "99": "Autre",
  "75": "Membre",
  "72": "Commissaire aux comptes",
  "74": "Directeur général",
  "53": "Liquidateur",
  "28": "Mandataire",
  "64": "Conseil de surveillance",
};

function roleLabel(code: unknown): string {
  if (!code) return "—";
  const c = String(code);
  return ROLE_LABELS[c] ?? `Rôle ${c}`;
}

function countryLabel(c: unknown): string {
  if (!c) return "";
  const code = String(c).toUpperCase();
  if (code === "FRA" || code === "FR" || code === "FRANCE") return "🇫🇷";
  const flags: Record<string, string> = {
    LUX: "🇱🇺", GBR: "🇬🇧", DEU: "🇩🇪", BEL: "🇧🇪", NLD: "🇳🇱",
    CHE: "🇨🇭", USA: "🇺🇸", ESP: "🇪🇸", ITA: "🇮🇹", MCO: "🇲🇨",
    IRL: "🇮🇪", CAN: "🇨🇦", AND: "🇦🇩", HUN: "🇭🇺", ARE: "🇦🇪",
  };
  return `${flags[code] ?? "🌍"} ${code}`;
}

function StatBox({
  label, value, accent,
}: {
  label: string;
  value: number | string;
  accent: "blue" | "purple" | "amber" | "emerald" | "rose" | "neutral";
}) {
  const colors: Record<string, { c: string; bg: string; b: string }> = {
    blue: { c: "var(--accent-blue)", bg: "rgba(96,165,250,0.08)", b: "rgba(96,165,250,0.20)" },
    purple: { c: "var(--accent-purple)", bg: "rgba(167,139,250,0.08)", b: "rgba(167,139,250,0.20)" },
    amber: { c: "var(--accent-amber)", bg: "rgba(251,146,60,0.08)", b: "rgba(251,146,60,0.20)" },
    emerald: { c: "var(--accent-emerald)", bg: "rgba(52,211,153,0.08)", b: "rgba(52,211,153,0.20)" },
    rose: { c: "var(--accent-rose)", bg: "rgba(251,113,133,0.08)", b: "rgba(251,113,133,0.20)" },
    neutral: { c: "var(--text-tertiary)", bg: "rgba(255,255,255,0.03)", b: "var(--border-subtle)" },
  };
  const cc = colors[accent];
  return (
    <div style={{ padding: "8px 10px", borderRadius: 8, background: cc.bg, border: `1px solid ${cc.b}` }}>
      <div style={{ fontSize: 10, color: "var(--text-tertiary)", textTransform: "uppercase", letterSpacing: ".06em", fontWeight: 600 }}>{label}</div>
      <div style={{ fontSize: 18, fontWeight: 700, color: cc.c, marginTop: 2 }}>{value}</div>
    </div>
  );
}

function Section({ title, icon, children }: { title: string; icon?: string; children: React.ReactNode }) {
  return (
    <div style={{ marginBottom: 16 }}>
      <div style={{ fontSize: 11, fontWeight: 700, textTransform: "uppercase", letterSpacing: ".06em", color: "var(--text-tertiary)", marginBottom: 8, display: "flex", alignItems: "center", gap: 6 }}>
        {icon && <Icon name={icon} size={11} />}
        {title}
      </div>
      <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>{children}</div>
    </div>
  );
}

function EntityRow({
  siren, denomination, country, role, source, ca, dept, ape, procActive, effectif, kind, note, onClick,
}: {
  siren: string;
  denomination: string;
  country?: unknown;
  role?: unknown;
  source?: unknown;
  ca?: unknown;
  dept?: unknown;
  ape?: unknown;
  procActive?: boolean;
  effectif?: unknown;
  kind: "parent" | "filiale";
  note?: string;
  onClick?: (siren: string) => void;
}) {
  const isClickable = Boolean(siren && /^\d{9}$/.test(siren) && onClick);
  const accent = kind === "parent" ? "var(--accent-blue)" : "var(--accent-purple)";
  return (
    <div
      onClick={isClickable && onClick ? () => onClick(siren) : undefined}
      style={{
        padding: 10, borderRadius: 8,
        background: procActive ? "rgba(251,113,133,0.08)" : "rgba(255,255,255,0.02)",
        border: `1px solid ${procActive ? "rgba(251,113,133,0.30)" : "var(--border-subtle)"}`,
        cursor: isClickable ? "pointer" : "default",
      }}
    >
      <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
        {procActive && (
          <span style={{ fontSize: 10, padding: "2px 6px", borderRadius: 4, background: "var(--accent-rose)", color: "#fff", fontWeight: 700 }}>RJ</span>
        )}
        <span style={{ fontWeight: 600, color: procActive ? "var(--accent-rose)" : "var(--text-primary)" }}>{denomination}</span>
        {country != null && country !== "" && (
          <span style={{ fontSize: 11, color: "var(--text-tertiary)" }}>{countryLabel(country)}</span>
        )}
        {isClickable && (
          <span style={{ fontSize: 10, color: accent, marginLeft: "auto" }}>ouvrir →</span>
        )}
      </div>
      <div style={{ display: "flex", gap: 12, marginTop: 4, fontSize: 11, color: "var(--text-tertiary)", flexWrap: "wrap" }}>
        {siren && <span className="dem-mono">SIREN {formatSiren(siren)}</span>}
        {role != null && <span>{roleLabel(role)}</span>}
        {ape != null && ape !== "" && <span>NAF {String(ape)}</span>}
        {dept != null && dept !== "" && <span>Dept {String(dept)}</span>}
        {ca != null && Number(ca) > 0 && <span>CA {fmtEur(ca)}</span>}
        {effectif != null && Number(effectif) > 0 && <span>{String(effectif)} salariés</span>}
        {note && <span style={{ fontStyle: "italic" }}>{note}</span>}
        {source != null && source !== "" && <span style={{ color: "var(--text-muted)" }}>· {String(source)}</span>}
      </div>
    </div>
  );
}

export function GroupTab({ siren, onOpenSiren }: Props) {
  const [data, setData] = useState<GroupData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    setError(null);
    datalakeApi
      .groupe(siren)
      .then(setData)
      .catch((e) => setError(e instanceof Error ? e.message : String(e)))
      .finally(() => setLoading(false));
  }, [siren]);

  if (loading) {
    return <div style={{ color: "var(--text-tertiary)", fontSize: 13, padding: 16 }}>Chargement structure groupe…</div>;
  }
  if (error) {
    return (
      <div style={{ color: "var(--accent-rose)", fontSize: 13, padding: 16 }}>
        <Icon name="warning" size={12} /> {error}
      </div>
    );
  }
  if (!data) return null;

  const hasParents = data.parents_directs.length > 0;
  const hasFiliales = data.filiales.length > 0;

  if (!hasParents && !hasFiliales) {
    return (
      <div className="dem-glass" style={{ padding: 24, borderRadius: 12, textAlign: "center", borderColor: "rgba(99,102,241,0.18)" }}>
        <Icon name="building" size={32} color="var(--accent-blue)" />
        <div style={{ fontSize: 16, fontWeight: 600, marginTop: 8 }}>Entité indépendante</div>
        <div style={{ fontSize: 12, color: "var(--text-tertiary)", marginTop: 4 }}>
          Aucun parent ni filiale détecté dans <span className="dem-mono">silver.entreprises_relationships</span>.
        </div>
      </div>
    );
  }

  return (
    <div>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(120px, 1fr))", gap: 8, marginBottom: 18 }}>
        <StatBox label="Parents directs" value={data.n_parents_directs} accent={data.n_parents_directs > 0 ? "blue" : "neutral"} />
        <StatBox label="Parents étranger" value={data.n_parents_etrangers} accent={data.n_parents_etrangers > 0 ? "amber" : "neutral"} />
        <StatBox label="Filiales directes" value={data.n_filiales_directes} accent={data.n_filiales_directes > 0 ? "purple" : "neutral"} />
        {data.n_filiales_en_procedure > 0 && (
          <StatBox label="Filiales en procédure" value={data.n_filiales_en_procedure} accent="rose" />
        )}
        {data.ca_cumule_filiales_eur != null && data.ca_cumule_filiales_eur > 0 && (
          <StatBox label="CA cumulé filiales" value={fmtEur(data.ca_cumule_filiales_eur)} accent="emerald" />
        )}
      </div>

      <div style={{
        padding: "10px 14px", borderRadius: 8, marginBottom: 16,
        background: data.is_holding ? "rgba(167,139,250,0.08)" : data.is_filiale ? "rgba(96,165,250,0.08)" : "rgba(255,255,255,0.03)",
        border: `1px solid ${data.is_holding ? "rgba(167,139,250,0.25)" : data.is_filiale ? "rgba(96,165,250,0.25)" : "var(--border-subtle)"}`,
        fontSize: 12.5,
      }}>
        {data.is_holding && data.is_filiale && (
          <><strong style={{ color: "var(--accent-purple)" }}>🏢 Holding intermédiaire</strong> — société à la fois mère et filiale.</>
        )}
        {data.is_holding && !data.is_filiale && (
          <><strong style={{ color: "var(--accent-purple)" }}>🌳 Tête de groupe / Holding</strong> — pas de parent identifié, possède {data.n_filiales_directes} filiales directes.</>
        )}
        {!data.is_holding && data.is_filiale && (
          <><strong style={{ color: "var(--accent-blue)" }}>🌿 Filiale</strong> — entité contrôlée par {data.n_parents_directs} parent(s).</>
        )}
      </div>

      {hasParents && (
        <Section title={`Parents directs (${data.parents_directs.length})`} icon="arrow-up">
          {data.parents_directs.map((p, i) => (
            <EntityRow
              key={i}
              siren={String(p.parent_siren ?? "")}
              denomination={String(p.parent_denomination ?? "—")}
              country={p.parent_country}
              role={p.role_code}
              source={p.source}
              ca={p.parent_ca}
              dept={p.parent_dept}
              ape={p.parent_ape}
              procActive={Boolean(p.parent_proc_active)}
              kind="parent"
              onClick={onOpenSiren}
            />
          ))}
        </Section>
      )}

      {data.ultimate_parents.length > 0
        && data.ultimate_parents.some(
          (u) => u.parent_siren && u.parent_siren !== data.parents_directs[0]?.parent_siren
        )
        && (
        <Section title="Tête de groupe (récursif)" icon="arrow-up">
          {data.ultimate_parents.map((u, i) => (
            <EntityRow
              key={i}
              siren={String(u.parent_siren ?? "")}
              denomination={String(u.parent_denomination ?? "—")}
              country={u.parent_country}
              kind="parent"
              note={`profondeur ${u.depth}`}
              onClick={onOpenSiren}
            />
          ))}
        </Section>
      )}

      {hasFiliales && (
        <Section title={`Filiales directes (${data.filiales.length})`} icon="arrow-down">
          {data.filiales.map((f, i) => (
            <EntityRow
              key={i}
              siren={String(f.child_siren ?? "")}
              denomination={String(f.child_denomination ?? "—")}
              role={f.role_code}
              source={f.source}
              ca={f.child_ca}
              dept={f.child_dept}
              ape={f.child_ape}
              procActive={Boolean(f.child_proc_active)}
              effectif={f.child_effectif}
              kind="filiale"
              onClick={onOpenSiren}
            />
          ))}
        </Section>
      )}

      {data.disclaimer && (
        <div style={{ marginTop: 14, padding: "8px 10px", background: "rgba(255,255,255,0.03)", border: "1px solid var(--border-subtle)", borderRadius: 6, fontSize: 11, color: "var(--text-muted)", fontStyle: "italic" }}>
          ⚠ {data.disclaimer}
        </div>
      )}
    </div>
  );
}
