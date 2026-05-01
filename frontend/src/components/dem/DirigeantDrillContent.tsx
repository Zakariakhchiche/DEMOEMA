"use client";

import React from "react";

export interface DirigeantFullData {
  identity: Record<string, unknown> | null;
  sci_patrimoine: Record<string, unknown> | null;
  sci_value_total: Record<string, unknown> | null;
  sci_values_per_company: Record<string, unknown>[];
  osint: Record<string, unknown> | null;
  osint_raw: Record<string, unknown> | null;
  sanctions: Record<string, unknown>[];
  dvf_zones: Record<string, unknown> | null;
}

export function DirigeantDrillContent({ data }: { data: Record<string, unknown> | DirigeantFullData }) {
  const id = (data.identity as Record<string, unknown>) || {};
  const sci = (data.sci_patrimoine as Record<string, unknown>) || {};
  const sciVal = (data.sci_value_total as Record<string, unknown>) || {};
  const osint = (data.osint as Record<string, unknown>) || {};
  const osintRaw = (data.osint_raw as Record<string, unknown>) || {};
  const sanctions = (data.sanctions as unknown[]) || [];
  const dvf = (data.dvf_zones as Record<string, unknown>) || null;

  const fmt = (v: unknown) => {
    if (v == null || v === "") return "—";
    const n = Number(v);
    if (!isNaN(n)) {
      if (Math.abs(n) >= 1e9) return `${(n / 1e9).toFixed(1)} Md€`;
      if (Math.abs(n) >= 1e6) return `${(n / 1e6).toFixed(1)} M€`;
      if (Math.abs(n) >= 1e3) return `${(n / 1e3).toFixed(0)} k€`;
      return `${n.toFixed(0)} €`;
    }
    return String(v);
  };
  const arr = (v: unknown): string[] => Array.isArray(v) ? (v as unknown[]).map(String).filter(Boolean) : [];

  const linkedinUrls = arr(osintRaw.linkedin_urls);
  const githubUsers = arr(osintRaw.github_usernames);
  const twitterHandles = arr(osintRaw.twitter_handles);
  const instagramHandles = arr(osintRaw.instagram_handles);
  const mediumProfiles = arr(osintRaw.medium_profiles);
  const facebookUrls = arr(osintRaw.facebook_urls);
  const youtubeChannels = arr(osintRaw.youtube_channels);
  const emailsValid = arr(osintRaw.emails_valid);
  const emailsTested = arr(osintRaw.emails_tested);
  const sourcesScanned = arr(osintRaw.sources_scanned);
  const crunchbase = osintRaw.crunchbase_url ? String(osintRaw.crunchbase_url) : null;

  const Section = ({ title, children }: { title: string; children: React.ReactNode }) => (
    <div style={{ marginBottom: 18 }}>
      <div style={{ fontSize: 11, fontWeight: 700, textTransform: "uppercase", letterSpacing: ".06em", color: "var(--text-tertiary)", marginBottom: 8 }}>{title}</div>
      <div style={{ display: "flex", flexDirection: "column", gap: 6, fontSize: 13 }}>{children}</div>
    </div>
  );
  const Row = ({ label, value }: { label: string; value: React.ReactNode }) => (
    <div style={{ display: "flex", gap: 12, alignItems: "baseline" }}>
      <div style={{ minWidth: 160, color: "var(--text-tertiary)", fontSize: 12 }}>{label}</div>
      <div style={{ flex: 1, color: "var(--text-primary)" }}>{value || "—"}</div>
    </div>
  );

  return (
    <div>
      <Section title="Identité INPI">
        <Row label="Nom & prénom" value={`${id.prenom || ""} ${id.nom || ""}`} />
        <Row label="Date de naissance" value={String(id.date_naissance || "—")} />
        <Row label="Âge (2026)" value={id.age ? `${id.age} ans` : "—"} />
        <Row label="Mandats actifs / total" value={`${id.n_mandats_actifs || 0} / ${id.n_mandats_total || 0}`} />
        <Row label="1er mandat" value={id.first_mandat_date ? String(id.first_mandat_date).slice(0, 10) : "—"} />
        <Row label="Dernier mandat" value={id.last_mandat_date ? String(id.last_mandat_date).slice(0, 10) : "—"} />
        <Row label="Sirens mandats" value={arr(id.sirens_mandats).slice(0, 10).join(", ") + (arr(id.sirens_mandats).length > 10 ? ` (+${arr(id.sirens_mandats).length - 10})` : "")} />
        <Row label="Dénominations" value={arr(id.denominations).slice(0, 10).join(" · ")} />
        <Row label="Formes juridiques" value={arr(id.formes_juridiques).join(" · ")} />
        <Row label="Rôles INPI" value={arr(id.roles).join(", ")} />
      </Section>

      <Section title="Patrimoine SCI (capital + valeur bilan)">
        <Row label="Nombre SCI" value={String(sci.n_sci || 0)} />
        <Row label="Capital cumulé (statutaire)" value={fmt(sci.total_capital_sci)} />
        <Row label="Valeur (total actif bilan)" value={<span style={{ fontWeight: 700, color: "var(--accent-emerald)" }}>{fmt(sciVal.total_actif)}</span>} />
        <Row label="Biens immobiliers" value={fmt(sciVal.immo_corporelles)} />
        <Row label="Capitaux propres" value={fmt(sciVal.capitaux_propres)} />
        <Row label="CA cumulé SCI" value={fmt(sciVal.ca_net_total)} />
        <Row label="Emprunts/dettes" value={fmt(sciVal.emprunts_dettes)} />
        <Row label="SCI ayant déposé comptes" value={`${sciVal.n_sci_with_comptes || 0} / ${sci.n_sci || 0}`} />
        <Row label="1ère SCI" value={sci.first_sci_date ? String(sci.first_sci_date).slice(0, 10) : "—"} />
        <Row label="Dénominations SCI" value={arr(sci.sci_denominations).join(" · ")} />
        <Row label="Codes postaux SCI" value={arr(sci.sci_code_postaux).join(", ")} />
      </Section>

      <Section title="Présence digitale (OSINT)">
        <Row label="LinkedIn URLs" value={linkedinUrls.length === 0 ? "—" : (
          <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
            {linkedinUrls.slice(0, 5).map((u, k) => <a key={k} href={u} target="_blank" rel="noreferrer" style={{ color: "var(--accent-blue)", fontSize: 12, wordBreak: "break-all" }}>{u}</a>)}
          </div>
        )} />
        <Row label="GitHub" value={githubUsers.length === 0 ? "—" : githubUsers.map((u, k) => (
          <a key={k} href={`https://github.com/${u}`} target="_blank" rel="noreferrer" style={{ color: "var(--accent-purple)", marginRight: 8 }}>@{u}</a>
        ))} />
        <Row label="Twitter / X" value={twitterHandles.length === 0 ? "—" : twitterHandles.map((u, k) => (
          <a key={k} href={`https://twitter.com/${u}`} target="_blank" rel="noreferrer" style={{ color: "var(--accent-cyan)", marginRight: 8 }}>@{u}</a>
        ))} />
        <Row label="Instagram" value={instagramHandles.join(", ") || "—"} />
        <Row label="Medium" value={mediumProfiles.join(" · ") || "—"} />
        <Row label="Facebook" value={facebookUrls.join(" · ") || "—"} />
        <Row label="YouTube" value={youtubeChannels.join(" · ") || "—"} />
        <Row label="Crunchbase" value={crunchbase ? <a href={crunchbase} target="_blank" rel="noreferrer" style={{ color: "var(--accent-amber)" }}>{crunchbase}</a> : "—"} />
        <Row label="Sources scannées" value={sourcesScanned.join(", ") || "—"} />
        <Row label="Dernière analyse" value={osint.last_scanned_at ? String(osint.last_scanned_at).slice(0, 10) : "—"} />
      </Section>

      {(emailsValid.length > 0 || emailsTested.length > 0) && (
        <Section title="Emails (outreach M&A)">
          <Row label="Emails validés" value={emailsValid.length === 0 ? "—" : (
            <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
              {emailsValid.map((e, k) => <span key={k} className="dem-mono" style={{ padding: "2px 6px", background: "rgba(52,211,153,0.10)", color: "var(--accent-emerald)", borderRadius: 4, fontSize: 11.5 }}>{e}</span>)}
            </div>
          )} />
          <Row label="Emails testés" value={emailsTested.length === 0 ? "—" : `${emailsTested.length} testés`} />
        </Section>
      )}

      <Section title="Entreprise principale (OSINT)">
        <Row label="Dénomination" value={String(osint.denomination_main_company || "—")} />
        <Row label="Forme juridique" value={String(osint.forme_juridique_main || "—")} />
        <Row label="Capital" value={fmt(osint.capital_main)} />
        <Row label="Date immat." value={osint.date_immat_main ? String(osint.date_immat_main).slice(0, 10) : "—"} />
        <Row label="Mandats INPI" value={String(osint.n_mandats_inpi || 0)} />
        <Row label="Siren principal" value={String(osint.siren_main || "—")} />
      </Section>

      {sanctions.length > 0 && (
        <Section title="Sanctions / red flags personne">
          {sanctions.map((s, k) => {
            const so = s as Record<string, unknown>;
            return (
              <div key={k} style={{ padding: 8, background: "rgba(251,113,133,0.05)", border: "1px solid rgba(251,113,133,0.20)", borderRadius: 6 }}>
                <div style={{ fontWeight: 600 }}>{String(so.caption || "—")}</div>
                <div style={{ fontSize: 11, color: "var(--text-tertiary)" }}>
                  topics: {arr(so.topics).join(", ") || "—"} · pays: {arr(so.countries).join(", ") || "—"} · programmes: {arr(so.sanctions_programs).join(", ") || "—"}
                </div>
              </div>
            );
          })}
        </Section>
      )}

      {dvf && Number(dvf.n_zones) > 0 && Array.isArray(dvf.by_cp) && (
        <Section title="Transactions immobilières DVF (zones SCI)">
          {(dvf.by_cp as unknown[]).map((row, k) => {
            const r = row as Record<string, unknown>;
            return <Row key={k} label={`CP ${String(r.code_postal || "")}`} value={`${r.n} transactions · total ${fmt(r.total)}`} />;
          })}
        </Section>
      )}
    </div>
  );
}
