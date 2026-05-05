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
  // Bloc Neo4j (PR #94) — fallback quand silver vide pour SCI/OSINT/Wikidata.
  graph?: Record<string, unknown> | null;
  // Liste détaillée des mandats (1 row par société). Source : bronze.inpi_*.
  mandats_detail?: Record<string, unknown>[];
}

export function DirigeantDrillContent({ data }: { data: Record<string, unknown> | DirigeantFullData }) {
  const id = (data.identity as Record<string, unknown>) || {};
  const sci = (data.sci_patrimoine as Record<string, unknown>) || {};
  const sciVal = (data.sci_value_total as Record<string, unknown>) || {};
  const osint = (data.osint as Record<string, unknown>) || {};
  const osintRaw = (data.osint_raw as Record<string, unknown>) || {};
  const sanctions = (data.sanctions as unknown[]) || [];
  const dvf = (data.dvf_zones as Record<string, unknown>) || null;
  // Graph Neo4j sert de fallback quand silver SCI/OSINT n'a pas de row pour
  // ce dirigeant (cas fréquent : silver.dirigeant_sci_patrimoine n'est pas
  // exhaustif, alors que Neo4j capture les SCI via l'enrichment priority1).
  const g = (data.graph as Record<string, unknown> | null) || {};

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

  // Helpers : préfère silver.osint_persons_enriched, sinon fallback Neo4j (graph)
  // qui capture aussi linkedin_url / github_username / twitter_handle (single string).
  const linkedinUrls = (() => {
    const fromRaw = arr(osintRaw.linkedin_urls);
    if (fromRaw.length > 0) return fromRaw;
    return g.linkedin_url ? [String(g.linkedin_url)] : [];
  })();
  const githubUsers = (() => {
    const fromRaw = arr(osintRaw.github_usernames);
    if (fromRaw.length > 0) return fromRaw;
    return g.github_username ? [String(g.github_username)] : [];
  })();
  const twitterHandles = (() => {
    const fromRaw = arr(osintRaw.twitter_handles);
    if (fromRaw.length > 0) return fromRaw;
    return g.twitter_handle ? [String(g.twitter_handle)] : [];
  })();
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
        {/* Distinction PM/PP via gold.sci_master.ownership_type. Permet de
          repérer les SCI familiales (PP) — typiquement transmission patrimoniale
          M&A — vs structures corporate (PM) — montage holding/investissement. */}
        {Boolean((sci.n_sci_individual as number) || (sci.n_sci_corporate as number) || (sci.n_sci_mixed as number)) && (
          <Row label="Composition associés" value={
            <span style={{ display: "inline-flex", gap: 8, flexWrap: "wrap" }}>
              {Number(sci.n_sci_individual || 0) > 0 && (
                <span style={{
                  fontSize: 11, padding: "2px 8px", borderRadius: 999,
                  background: "rgba(96,165,250,0.10)", color: "var(--accent-blue)",
                  border: "1px solid rgba(96,165,250,0.30)", fontWeight: 600,
                }}>👤 {String(sci.n_sci_individual)} PP (perso. physique)</span>
              )}
              {Number(sci.n_sci_corporate || 0) > 0 && (
                <span style={{
                  fontSize: 11, padding: "2px 8px", borderRadius: 999,
                  background: "rgba(167,139,250,0.10)", color: "var(--accent-purple)",
                  border: "1px solid rgba(167,139,250,0.30)", fontWeight: 600,
                }}>🏢 {String(sci.n_sci_corporate)} PM (perso. morale)</span>
              )}
              {Number(sci.n_sci_mixed || 0) > 0 && (
                <span style={{
                  fontSize: 11, padding: "2px 8px", borderRadius: 999,
                  background: "rgba(251,191,36,0.10)", color: "var(--accent-amber)",
                  border: "1px solid rgba(251,191,36,0.30)", fontWeight: 600,
                }}>⚡ {String(sci.n_sci_mixed)} mixte</span>
              )}
            </span>
          } />
        )}
        <Row label="Capital cumulé (statutaire)" value={fmt(sci.total_capital_sci)} />
        <Row label="Valeur (total actif bilan)" value={<span style={{ fontWeight: 700, color: "var(--accent-emerald)" }}>{fmt(sciVal.total_actif)}</span>} />
        <Row label="Biens immobiliers" value={fmt(sciVal.immo_corporelles)} />
        <Row label="Capitaux propres" value={fmt(sciVal.capitaux_propres)} />
        <Row label="CA cumulé SCI" value={fmt(sciVal.ca_net_total)} />
        <Row label="Emprunts/dettes" value={fmt(sciVal.emprunts_dettes)} />
        <Row label="SCI ayant déposé comptes" value={`${sciVal.n_sci_with_comptes || 0} / ${sci.n_sci || 0}`} />
        <Row label="1ère SCI" value={sci.first_sci_date ? String(sci.first_sci_date).slice(0, 10) : "—"} />
        {/* Détail par SCI : denomination + tag PP/PM/mixte */}
        {Array.isArray(sci.sci_per_siren) && (sci.sci_per_siren as unknown[]).length > 0 ? (
          <Row label="SCI détail" value={
            <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
              {(sci.sci_per_siren as Array<Record<string, unknown>>).map((s, i) => {
                const otype = String(s.ownership_type ?? "");
                const tag = otype === "individual" ? { txt: "PP", c: "var(--accent-blue)", bg: "rgba(96,165,250,0.10)", b: "rgba(96,165,250,0.30)" }
                  : otype === "corporate" ? { txt: "PM", c: "var(--accent-purple)", bg: "rgba(167,139,250,0.10)", b: "rgba(167,139,250,0.30)" }
                  : otype === "mixed" ? { txt: "MIX", c: "var(--accent-amber)", bg: "rgba(251,191,36,0.10)", b: "rgba(251,191,36,0.30)" }
                  : null;
                return (
                  <div key={i} style={{ display: "flex", gap: 8, alignItems: "center", fontSize: 12 }}>
                    {tag && (
                      <span style={{
                        fontSize: 10, padding: "1px 6px", borderRadius: 4,
                        background: tag.bg, color: tag.c, border: `1px solid ${tag.b}`,
                        fontWeight: 700, letterSpacing: "0.04em",
                      }}>{tag.txt}</span>
                    )}
                    <span style={{ fontWeight: 600 }}>{String(s.denomination ?? s.siren ?? "—")}</span>
                    {Boolean(s.patrimoine_net_estime) && (
                      <span style={{ color: "var(--text-tertiary)", fontSize: 11 }}>
                        {fmt(s.patrimoine_net_estime)}
                      </span>
                    )}
                  </div>
                );
              })}
            </div>
          } />
        ) : (
          <Row label="Dénominations SCI" value={arr(sci.sci_denominations).join(" · ")} />
        )}
        <Row label="Codes postaux SCI" value={arr(sci.sci_code_postaux).join(", ")} />
      </Section>

      {/* Bloc Wikidata — apparaît quand silver osint vide mais Neo4j enrichment
        a wikidata_qid/birth_year/occupation. Source-of-truth différente du
        bloc OSINT (Maigret/Holehe) ci-dessous. */}
      {Boolean(g.wikidata_qid || g.wikidata_birth_year || g.wikidata_occupation) && (
        <Section title="Wikidata">
          <Row label="QID" value={g.wikidata_qid ? <a href={`https://www.wikidata.org/wiki/${String(g.wikidata_qid)}`} target="_blank" rel="noreferrer" style={{ color: "var(--accent-blue)" }}>{String(g.wikidata_qid)}</a> : "—"} />
          <Row label="Année de naissance" value={g.wikidata_birth_year ? String(g.wikidata_birth_year) : "—"} />
          <Row label="Occupation" value={g.wikidata_occupation ? String(g.wikidata_occupation) : "—"} />
        </Section>
      )}

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

      {dvf && Number(dvf.n_sci_total ?? dvf.n_sci_with_mutations ?? 0) > 0 && Array.isArray(dvf.per_sci) && (() => {
        // Compte combien de SCI partagent chaque adresse pour annoter le détail.
        const shareCount: Record<string, number> = {};
        (dvf.per_sci as unknown[]).forEach((row) => {
          const r = row as Record<string, unknown>;
          const k = `${r.adresse_code_postal}|${r.adresse_num_voie}|${r.adresse_voie}`;
          shareCount[k] = (shareCount[k] || 0) + 1;
        });
        const nUniq = Number(dvf.n_unique_addresses ?? 0);
        const nTotal = Number(dvf.n_sci_total ?? dvf.n_sci_with_mutations ?? 0);
        const nMatch = Number(dvf.n_sci_with_mutations ?? 0);
        const noMatchList = Array.isArray(dvf.sci_no_match) ? (dvf.sci_no_match as Record<string, unknown>[]) : [];
        return (
          <Section title="🏛️ Patrimoine immobilier DVF (mutations à l'adresse siège SCI)">
            <Row label="SCI avec mutations" value={`${nMatch} / ${nTotal} SCI · ${nUniq} ${nUniq <= 1 ? "adresse unique" : "adresses uniques"}`} />
            {nMatch > 0 ? (
              <>
                <Row label="Total mutations (dédup adresse)" value={`${dvf.total_n_mutations} ventes`} />
                <Row label="Valeur cumulée" value={fmt(dvf.total_value_eur)} />
                <Row label="Surface cumulée bâtie" value={dvf.total_surface_m2 ? `${Number(dvf.total_surface_m2).toLocaleString("fr-FR")} m²` : "—"} />
                <div style={{ marginTop: 8, fontSize: 11, color: "var(--text-muted)" }}>
                  {(dvf.per_sci as unknown[]).map((row, k) => {
                    const r = row as Record<string, unknown>;
                    const key = `${r.adresse_code_postal}|${r.adresse_num_voie}|${r.adresse_voie}`;
                    const shared = (shareCount[key] || 1) - 1;
                    return (
                      <div key={k} style={{ padding: "3px 0", borderBottom: k < (dvf.per_sci as unknown[]).length - 1 ? "1px solid var(--border-subtle)" : "none" }}>
                        <span style={{ color: "var(--text-primary)", fontWeight: 600 }}>{String(r.denomination || r.siren)}</span>
                        <span style={{ marginLeft: 8, color: "var(--text-tertiary)" }}>
                          {String(r.adresse_num_voie || "")} {String(r.adresse_voie || "")} {String(r.adresse_code_postal || "")}
                        </span>
                        <span style={{ marginLeft: 8, color: "var(--accent-purple)" }}>
                          {String(r.n_mutations ?? "")} mut. · {fmt(r.total_value)} · {r.total_surface ? `${String(r.total_surface)} m²` : ""}
                        </span>
                        {shared > 0 && (
                          <span style={{ marginLeft: 8, color: "var(--text-muted)", fontStyle: "italic", fontSize: 10 }}>
                            (partagé avec {shared} autre{shared > 1 ? "s" : ""} SCI)
                          </span>
                        )}
                      </div>
                    );
                  })}
                </div>
              </>
            ) : (
              <div style={{ marginTop: 6, padding: "8px 10px", fontSize: 11.5, color: "var(--text-tertiary)", background: "rgba(255,255,255,0.02)", borderRadius: 6 }}>
                Aucune mutation DVF 2021-2025 à l&apos;adresse siège des {nTotal} SCI — patrimoine stable ou hors période DVF public (acquisitions antérieures à 2021).
              </div>
            )}
            {noMatchList.length > 0 && nMatch > 0 && (
              <div style={{ marginTop: 6, fontSize: 10.5, color: "var(--text-muted)" }}>
                {noMatchList.length} SCI sans mutation DVF :{" "}
                {noMatchList.slice(0, 6).map((s, i) => (
                  <span key={i}>
                    {String(s.denomination || s.siren)}
                    {i < Math.min(noMatchList.length, 6) - 1 ? " · " : ""}
                  </span>
                ))}
                {noMatchList.length > 6 ? ` +${noMatchList.length - 6}` : ""}
              </div>
            )}
            <div style={{ marginTop: 6, fontSize: 10.5, color: "var(--text-muted)", fontStyle: "italic" }}>
              ⚠ DVF anonymise les acquéreurs : ces mutations sont à l&apos;adresse siège SCI, pas certifiées comme étant celles de la SCI.
            </div>
          </Section>
        );
      })()}
    </div>
  );
}
