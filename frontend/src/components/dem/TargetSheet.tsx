"use client";

import { useState, useEffect } from "react";
import { Icon } from "./Icon";
import { ScoreBadge } from "./ScoreBadge";
import { datalakeApi } from "@/lib/api";
import type { Target } from "@/lib/dem/types";

interface Props {
  target: Target;
  onClose: () => void;
  onPitch: () => void;
}

const TABS = [
  { k: "overview", label: "Overview", icon: "eye" },
  { k: "dirigeants", label: "Dirigeants", icon: "user" },
  { k: "signaux", label: "Signaux BODACC", icon: "sparkles" },
  { k: "compliance", label: "Compliance", icon: "shield" },
  { k: "reseau", label: "Réseau", icon: "network" },
  { k: "presse", label: "Presse", icon: "book" },
] as const;

interface FicheData {
  fiche: Record<string, unknown>;
  dirigeants: Record<string, unknown>[];
  signaux: Record<string, unknown>[];
  red_flags: Record<string, unknown>[];
  network: Record<string, unknown>[];
  presse: Record<string, unknown>[];
}

function fmtEur(v: unknown): string {
  if (v == null) return "—";
  const n = typeof v === "number" ? v : Number(v);
  if (isNaN(n)) return "—";
  if (Math.abs(n) >= 1e9) return `${(n / 1e9).toFixed(1)} Md€`;
  if (Math.abs(n) >= 1e6) return `${(n / 1e6).toFixed(1)} M€`;
  if (Math.abs(n) >= 1e3) return `${(n / 1e3).toFixed(0)} k€`;
  return `${n.toFixed(0)} €`;
}

function fmtDate(v: unknown): string {
  if (!v) return "—";
  const d = new Date(String(v));
  if (isNaN(d.getTime())) return String(v);
  return d.toLocaleDateString("fr-FR");
}

function BarChart({ data, labels }: { data: number[]; labels: string[] }) {
  if (data.length === 0) return null;
  const max = Math.max(...data, 1);
  return (
    <div style={{ display: "flex", alignItems: "flex-end", gap: 12, height: 120, marginTop: 14 }}>
      {data.map((v, i) => (
        <div key={i} style={{ flex: 1, display: "flex", flexDirection: "column", alignItems: "center", gap: 6 }}>
          <div className="dem-mono tab-num" style={{ fontSize: 11, color: "var(--text-secondary)" }}>{fmtEur(v)}</div>
          <div style={{
            width: "100%", height: `${(v / max) * 80}%`,
            background: i === data.length - 1
              ? "linear-gradient(180deg, var(--accent-blue), rgba(96,165,250,0.30))"
              : "rgba(255,255,255,0.10)",
            borderRadius: 4,
            boxShadow: i === data.length - 1 ? "0 0 16px -2px rgba(96,165,250,0.40)" : "none",
          }} />
          <div className="dem-mono" style={{ fontSize: 10.5, color: "var(--text-tertiary)" }}>{labels[i]}</div>
        </div>
      ))}
    </div>
  );
}

export function TargetSheet({ target, onClose, onPitch }: Props) {
  const [tab, setTab] = useState<typeof TABS[number]["k"]>("overview");
  const [data, setData] = useState<FicheData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    setError(null);
    datalakeApi
      .ficheEntreprise(target.siren)
      .then(setData)
      .catch((e) => setError(e instanceof Error ? e.message : String(e)))
      .finally(() => setLoading(false));
  }, [target.siren]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") onClose(); };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  const fiche = data?.fiche ?? {};
  const denomination = String(fiche.denomination || target.denomination);
  const naf = String(fiche.naf || target.naf || "—");
  const nafLib = String(fiche.naf_libelle || target.naf_label || naf);
  const dept = String(fiche.dept || target.dept || "");
  const forme = String(fiche.forme_juridique || target.forme || "");
  const annee = fiche.annee_creation ? String(fiche.annee_creation) : target.creation;
  const ca = fiche.ca_dernier ?? target.ca;
  const ebitda = fiche.ebitda_dernier ?? target.ebitda;
  const margePct = fiche.marge_pct as number | null;
  const effectif = fiche.effectif_exact ?? target.effectif;
  const capital = fiche.capital_social;
  const cp = fiche.adresse_code_postal as string | undefined;
  const ville = fiche.ville as string | undefined;
  const region = fiche.region as string | undefined;
  const adresse = fiche.adresse as string | undefined;
  const caHistory = (fiche.ca_history as number[] | undefined) ?? [];
  const exercices = (fiche.exercices as string[] | undefined) ?? [];
  const tranche = fiche.tranche_effectifs as string | undefined;
  const categorie = fiche.categorie_entreprise as string | undefined;
  const etat = fiche.etat_administratif as string | undefined;
  const dateFermeture = fiche.date_fermeture as string | undefined;
  const nEtab = fiche.n_etablissements as number | undefined;
  const nEtabOuv = fiche.n_etablissements_ouverts as number | undefined;
  const sigle = fiche.sigle as string | undefined;
  const isCesse = fiche.statut === "cesse" || etat === "C";

  return (
    <>
      <div className="sheet-backdrop" onClick={onClose} />
      <div className="sheet-panel">
        <div style={{
          padding: "20px 28px 18px", borderBottom: "1px solid var(--border-subtle)",
          display: "flex", alignItems: "flex-start", gap: 18,
        }}>
          <ScoreBadge value={target.score} size="lg" breakdown={target.score_breakdown} />
          <div style={{ flex: 1, minWidth: 0 }}>
            <div style={{
              fontSize: 11, color: "var(--text-tertiary)",
              textTransform: "uppercase", letterSpacing: "0.08em", fontWeight: 600,
            }}>
              Cible M&A · NAF {naf}{nafLib && nafLib !== naf ? ` — ${nafLib}` : ""}
            </div>
            <div style={{
              fontSize: 26, fontWeight: 700, letterSpacing: "-0.02em",
              color: "var(--text-primary)", marginTop: 4,
              display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap",
            }}>
              {denomination}
              {sigle && <span style={{ fontSize: 16, color: "var(--text-tertiary)", fontWeight: 500 }}>({sigle})</span>}
              {isCesse && (
                <span style={{
                  fontSize: 11, padding: "3px 9px", borderRadius: 999,
                  background: "rgba(251,113,133,0.10)",
                  border: "1px solid rgba(251,113,133,0.30)",
                  color: "var(--accent-rose)", fontWeight: 600,
                  letterSpacing: "0.06em",
                }}>
                  CESSÉE{dateFermeture ? ` ${fmtDate(dateFermeture)}` : ""}
                </span>
              )}
            </div>
            <div style={{
              display: "flex", gap: 14, marginTop: 6, fontSize: 12,
              color: "var(--text-secondary)", flexWrap: "wrap", alignItems: "center",
            }}>
              <span className="dem-mono">siren {target.siren}</span>
              {forme && <span>Forme {forme}</span>}
              {annee && annee !== "—" && <span>Créée en {annee}</span>}
              {ville && <span>{ville}{cp ? ` · ${cp}` : ""}{dept ? ` (${dept})` : ""}</span>}
              {tranche && tranche !== "NN" && <span>Tranche {tranche}</span>}
              {categorie && <span>{categorie}</span>}
              {nEtab != null && <span>{nEtab} étab.{nEtabOuv != null && nEtab !== nEtabOuv ? ` · ${nEtabOuv} ouverts` : ""}</span>}
              {Boolean(fiche.has_linkedin_page) && <span style={{ color: "var(--accent-cyan)" }}>LinkedIn</span>}
              {Boolean(fiche.has_github_org) && <span style={{ color: "var(--accent-purple)" }}>GitHub</span>}
            </div>
            {adresse && (
              <div style={{ marginTop: 4, fontSize: 11.5, color: "var(--text-tertiary)" }}>
                📍 {adresse}{region ? ` · région ${region}` : ""}
              </div>
            )}
          </div>
          <div style={{ display: "flex", gap: 6 }}>
            <button className="dem-btn dem-btn-primary" onClick={onPitch}>
              <Icon name="sparkles" size={12} /> Pitch Ready
            </button>
            <button className="dem-btn">
              <Icon name="bookmark" size={12} /> Sauver
            </button>
            <button className="dem-btn dem-btn-ghost dem-btn-icon" onClick={onClose} title="Fermer (Esc)">
              <span style={{ fontSize: 16, lineHeight: 1 }}>×</span>
            </button>
          </div>
        </div>

        {error && (
          <div style={{
            padding: "8px 28px", fontSize: 12, color: "var(--accent-rose)",
            background: "rgba(251,113,133,0.06)",
            borderBottom: "1px solid rgba(251,113,133,0.20)",
          }}>
            <Icon name="warning" size={11} /> {error}
          </div>
        )}

        <div style={{ flex: 1, display: "flex", overflow: "hidden" }}>
          <div style={{
            width: 200, borderRight: "1px solid var(--border-subtle)",
            padding: "12px 8px", display: "flex", flexDirection: "column", gap: 2,
          }}>
            {TABS.map((t) => {
              const count =
                t.k === "dirigeants" ? data?.dirigeants.length :
                t.k === "signaux" ? data?.signaux.length :
                t.k === "compliance" ? data?.red_flags.length :
                t.k === "reseau" ? data?.network.length :
                t.k === "presse" ? data?.presse.length : null;
              return (
                <button
                  key={t.k}
                  onClick={() => setTab(t.k)}
                  style={{
                    display: "flex", alignItems: "center", gap: 9,
                    padding: "8px 12px", borderRadius: 7, border: "none",
                    background: tab === t.k ? "rgba(96,165,250,0.10)" : "transparent",
                    color: tab === t.k ? "#cfe1fb" : "var(--text-secondary)",
                    cursor: "pointer", fontSize: 12.5, textAlign: "left",
                    fontWeight: tab === t.k ? 600 : 500,
                  }}
                >
                  <Icon name={t.icon} size={12} />
                  <span style={{ flex: 1 }}>{t.label}</span>
                  {count != null && count > 0 && (
                    <span className="dem-mono" style={{ fontSize: 10, color: "var(--text-muted)" }}>{count}</span>
                  )}
                </button>
              );
            })}
          </div>

          <div style={{ flex: 1, overflowY: "auto", padding: "20px 28px 32px" }}>
            {loading && <div style={{ color: "var(--text-tertiary)", fontSize: 13 }}>Chargement live datalake…</div>}

            {tab === "overview" && !loading && (
              <div>
                <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 10 }}>
                  {[
                    { l: "CA dernier", v: fmtEur(ca), sub: exercices.length ? `Exercice ${String(exercices[exercices.length - 1] || "").slice(0, 4)}` : "", color: "var(--accent-emerald)" },
                    { l: "EBITDA / résultat net", v: fmtEur(ebitda), sub: margePct != null ? `Marge ${margePct}%` : "", color: "var(--accent-blue)" },
                    { l: "Effectif moyen", v: effectif != null ? Number(effectif).toLocaleString("fr-FR") : "—", sub: forme || "", color: "var(--text-secondary)" },
                    { l: "Capital social", v: fmtEur(capital), sub: capital ? "" : "non publié", color: "var(--accent-purple)" },
                  ].map((k, i) => (
                    <div key={i} className="dem-glass" style={{ borderRadius: 12, padding: "14px 16px" }}>
                      <div style={{
                        fontSize: 10.5, color: "var(--text-tertiary)",
                        textTransform: "uppercase", letterSpacing: "0.06em", fontWeight: 600,
                      }}>{k.l}</div>
                      <div className="dem-mono tab-num" style={{
                        fontSize: 22, fontWeight: 700, color: "var(--text-primary)", marginTop: 4,
                      }}>{k.v}</div>
                      {k.sub && <div style={{ fontSize: 11, color: k.color, marginTop: 2 }}>{k.sub}</div>}
                    </div>
                  ))}
                </div>

                {caHistory.length >= 2 && (
                  <div className="dem-glass" style={{ borderRadius: 12, padding: 18, marginTop: 14 }}>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline" }}>
                      <div style={{ fontSize: 13, fontWeight: 600 }}>Évolution CA · 5 derniers exercices</div>
                      <div style={{ fontSize: 11, color: "var(--text-tertiary)" }}>silver.inpi_comptes</div>
                    </div>
                    <BarChart
                      data={caHistory}
                      labels={exercices.slice(-caHistory.length).map((e) => String(e || "").slice(0, 4))}
                    />
                  </div>
                )}

                <div className="dem-glass" style={{
                  marginTop: 14, padding: "14px 18px", borderRadius: 12,
                  background: "linear-gradient(135deg, rgba(96,165,250,0.06), rgba(167,139,250,0.06))",
                  border: "1px solid rgba(96,165,250,0.20)",
                  display: "flex", gap: 12,
                }}>
                  <Icon name="sparkles" size={16} color="var(--accent-purple)" />
                  <div>
                    <div style={{ fontSize: 12, fontWeight: 600, color: "var(--accent-purple)", marginBottom: 4 }}>Verdict DEMOEMA</div>
                    <div style={{ fontSize: 13, color: "var(--text-primary)", lineHeight: 1.55 }}>
                      Cible <strong>{target.score >= 80 ? "HIGH" : target.score >= 70 ? "MID-HIGH" : "MID"} potentiel</strong>{naf && naf !== "—" ? ` · NAF ${naf}` : ""}.
                      Score {target.score}/100 — {target.score >= 80 ? "tier-1, prioritaire" : target.score >= 70 ? "tier-1, à qualifier" : "tier-2, surveillance"}.
                      {(data?.red_flags.length ?? 0) > 0 && " Attention : red flags compliance à expliquer en DD."}
                    </div>
                  </div>
                </div>

                <div style={{ marginTop: 14, display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 10 }}>
                  <div className="dem-glass" style={{ borderRadius: 10, padding: 12 }}>
                    <div className="section-label">Dirigeants</div>
                    <div className="dem-mono tab-num" style={{ fontSize: 22, fontWeight: 700, marginTop: 4 }}>
                      {fiche.n_dirigeants?.toString() ?? "0"}
                    </div>
                  </div>
                  <div className="dem-glass" style={{ borderRadius: 10, padding: 12 }}>
                    <div className="section-label">Annonces BODACC</div>
                    <div className="dem-mono tab-num" style={{ fontSize: 22, fontWeight: 700, marginTop: 4 }}>
                      {fiche.n_bodacc?.toString() ?? "0"}
                    </div>
                  </div>
                  <div className="dem-glass" style={{ borderRadius: 10, padding: 12 }}>
                    <div className="section-label">Sanctions / red flags</div>
                    <div className="dem-mono tab-num" style={{
                      fontSize: 22, fontWeight: 700, marginTop: 4,
                      color: Number(fiche.n_sanctions ?? 0) > 0 ? "var(--accent-rose)" : "var(--accent-emerald)",
                    }}>
                      {fiche.n_sanctions?.toString() ?? "0"}
                    </div>
                  </div>
                </div>

                {fiche.primary_domain ? (
                  <div className="dem-glass" style={{ marginTop: 14, padding: "12px 16px", borderRadius: 10, fontSize: 12.5 }}>
                    <span style={{ color: "var(--text-tertiary)" }}>Domaine principal · </span>
                    <a href={`https://${fiche.primary_domain}`} target="_blank" rel="noreferrer" style={{ color: "var(--accent-cyan)" }}>
                      {String(fiche.primary_domain)}
                    </a>
                    {fiche.linkedin_employees ? (
                      <span style={{ marginLeft: 16, color: "var(--text-tertiary)" }}>
                        LinkedIn employees · <span style={{ color: "var(--text-primary)", fontWeight: 600 }} className="dem-mono">{String(fiche.linkedin_employees)}</span>
                      </span>
                    ) : null}
                    {fiche.digital_presence_score ? (
                      <span style={{ marginLeft: 16, color: "var(--text-tertiary)" }}>
                        Digital presence · <span style={{ color: "var(--text-primary)", fontWeight: 600 }} className="dem-mono">{String(fiche.digital_presence_score)}/100</span>
                      </span>
                    ) : null}
                  </div>
                ) : null}
              </div>
            )}

            {tab === "dirigeants" && !loading && (
              <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                {data?.dirigeants.length === 0 && (
                  <div style={{ color: "var(--text-tertiary)", fontSize: 13 }}>Aucun dirigeant trouvé en INPI.</div>
                )}
                {data?.dirigeants.map((d, i) => (
                  <div key={i} className="dem-glass" style={{ borderRadius: 10, padding: 14, display: "flex", gap: 14, alignItems: "center" }}>
                    <div style={{
                      width: 40, height: 40, borderRadius: 999,
                      background: "linear-gradient(135deg, #3b3b44, #1a1a20)",
                      border: "1px solid var(--border-soft)",
                      display: "flex", alignItems: "center", justifyContent: "center",
                      fontWeight: 600, fontSize: 13, color: "var(--text-secondary)",
                    }}>
                      {String(d.prenom ?? "").slice(0, 1)}{String(d.nom ?? "").slice(0, 1)}
                    </div>
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div style={{ display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap" }}>
                        <span style={{ fontSize: 14, fontWeight: 600 }}>
                          {String(d.prenom ?? "")} {String(d.nom ?? "")}
                        </span>
                        {Boolean(d.qualite) && (
                          <span style={{
                            fontSize: 10.5, padding: "2px 7px", borderRadius: 999,
                            background: "rgba(96,165,250,0.10)",
                            color: "#cfe1fb",
                            border: "1px solid rgba(96,165,250,0.30)",
                          }}>
                            {String(d.qualite)}
                          </span>
                        )}
                        {d.type_dirigeant === "personne morale" && (
                          <span style={{
                            fontSize: 10, padding: "2px 6px", borderRadius: 4,
                            background: "rgba(167,139,250,0.10)",
                            color: "var(--accent-purple)",
                            border: "1px solid rgba(167,139,250,0.30)",
                          }}>
                            Personne morale
                          </span>
                        )}
                        {Boolean(d.siren_dirigeant) && (
                          <span className="dem-mono" style={{ fontSize: 10.5, color: "var(--text-tertiary)" }}>
                            siren {String(d.siren_dirigeant)}
                          </span>
                        )}
                        <span className="dem-mono" style={{ fontSize: 11, color: "var(--text-tertiary)" }}>
                          {d.age != null ? `${d.age} ans` : ""}
                        </span>
                        {Boolean(d.is_sanctioned) && (
                          <span className="dem-chip" style={{
                            background: "rgba(251,113,133,0.10)", color: "var(--accent-rose)",
                            borderColor: "rgba(251,113,133,0.30)", fontSize: 10,
                          }}>
                            <Icon name="warning" size={9} /> sanction
                          </span>
                        )}
                        {Boolean(d.has_linkedin) && (
                          <span style={{ color: "var(--accent-cyan)", fontSize: 10 }}>LinkedIn</span>
                        )}
                        {Boolean(d.has_github) && (
                          <span style={{ color: "var(--accent-purple)", fontSize: 10 }}>GitHub</span>
                        )}
                      </div>
                      <div style={{ marginTop: 4, fontSize: 12, color: "var(--text-secondary)", display: "flex", gap: 14, flexWrap: "wrap" }}>
                        <span><span style={{ color: "var(--text-muted)" }}>Mandats actifs</span> <span className="dem-mono">{String(d.n_mandats_actifs ?? 0)}</span></span>
                        {d.n_mandats_total != null && <span><span style={{ color: "var(--text-muted)" }}>Total</span> <span className="dem-mono">{String(d.n_mandats_total)}</span></span>}
                        {d.n_sci != null && Number(d.n_sci) > 0 && (
                          <span><span style={{ color: "var(--text-muted)" }}>SCI</span> <span className="dem-mono">{String(d.n_sci)}</span></span>
                        )}
                        {d.total_capital_sci != null && (
                          <span><span style={{ color: "var(--text-muted)" }}>Capital SCI</span> <span className="dem-mono">{fmtEur(d.total_capital_sci)}</span></span>
                        )}
                      </div>
                      {Array.isArray(d.denominations) && d.denominations.length > 0 && (
                        <div style={{ marginTop: 6, fontSize: 11, color: "var(--text-tertiary)" }}>
                          Mandats : {(d.denominations as string[]).slice(0, 4).join(", ")}{(d.denominations as string[]).length > 4 ? "…" : ""}
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}

            {tab === "signaux" && !loading && (
              <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                {data?.signaux.length === 0 && (
                  <div style={{ color: "var(--text-tertiary)", fontSize: 13 }}>Aucune annonce BODACC.</div>
                )}
                {data?.signaux.map((s, i) => {
                  const sev = String(s.severity || "").toLowerCase();
                  const high = sev.includes("procédure") || sev.includes("liquidation") || sev.includes("redressement");
                  return (
                    <div key={i} className="dem-glass" style={{ borderRadius: 8, padding: "10px 14px" }}>
                      <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                        <span className={`sev-dot ${high ? "high" : "low"}`} />
                        <span style={{ fontSize: 12.5, fontWeight: 600 }}>{String(s.signal_type ?? "—")}</span>
                        <span style={{ fontSize: 11, color: "var(--text-tertiary)" }}>{String(s.severity ?? "")}</span>
                        <span className="dem-mono tab-num" style={{ marginLeft: "auto", fontSize: 11, color: "var(--text-muted)" }}>{fmtDate(s.event_date)}</span>
                      </div>
                      <div style={{ marginTop: 4, fontSize: 11.5, color: "var(--text-secondary)" }}>
                        {String(s.source ?? "")}{s.ville ? ` · ${s.ville}` : ""}{s.code_dept ? ` (${s.code_dept})` : ""}
                      </div>
                    </div>
                  );
                })}
              </div>
            )}

            {tab === "compliance" && !loading && (
              <div>
                {data?.red_flags.length === 0 ? (
                  <div className="dem-glass" style={{
                    padding: 24, borderRadius: 12, textAlign: "center",
                    borderColor: "rgba(52,211,153,0.20)",
                  }}>
                    <Icon name="check" size={32} color="var(--accent-emerald)" />
                    <div style={{ fontSize: 16, fontWeight: 600, marginTop: 8 }}>Aucun red flag identifié</div>
                    <div style={{ fontSize: 12, color: "var(--text-tertiary)", marginTop: 4 }}>
                      Source : silver.opensanctions (UE/US/UK/UN, ICIJ, PEP)
                    </div>
                  </div>
                ) : (
                  <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                    {data?.red_flags.map((f, i) => (
                      <div key={i} className="dem-glass" style={{
                        padding: 16, borderRadius: 12,
                        borderColor: "rgba(251,113,133,0.30)",
                        background: "rgba(251,113,133,0.04)",
                        display: "flex", gap: 12,
                      }}>
                        <Icon name="warning" size={20} color="var(--accent-rose)" />
                        <div style={{ flex: 1 }}>
                          <div style={{ fontSize: 13, fontWeight: 600, color: "var(--accent-rose)" }}>{String(f.caption ?? f.entity_id)}</div>
                          <div style={{ fontSize: 11.5, color: "var(--text-tertiary)", marginTop: 4 }}>
                            Schema : <span className="dem-mono">{String(f.schema)}</span>
                            {Array.isArray(f.topics) && f.topics.length > 0 && (
                              <> · Topics : <span className="dem-mono">{(f.topics as string[]).join(", ")}</span></>
                            )}
                          </div>
                          {Array.isArray(f.sanctions_programs) && f.sanctions_programs.length > 0 && (
                            <div style={{ fontSize: 11, color: "var(--accent-rose)", marginTop: 4 }}>
                              Programmes : {(f.sanctions_programs as string[]).join(" · ")}
                            </div>
                          )}
                          {Array.isArray(f.countries) && (
                            <div style={{ fontSize: 11, color: "var(--text-tertiary)", marginTop: 2 }}>
                              Pays : {(f.countries as string[]).join(", ")}
                            </div>
                          )}
                          <div style={{ fontSize: 10.5, color: "var(--text-muted)", marginTop: 4 }}>
                            Détecté {fmtDate(f.first_seen)} · MAJ {fmtDate(f.last_seen)}
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}

            {tab === "reseau" && !loading && (
              <div>
                {data?.network.length === 0 ? (
                  <div style={{ color: "var(--text-tertiary)", fontSize: 13 }}>
                    Aucun co-mandat trouvé via les dirigeants principaux.
                  </div>
                ) : (
                  <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                    <div style={{ fontSize: 12, color: "var(--text-tertiary)", marginBottom: 8 }}>
                      Entreprises liées via les dirigeants — calculé live sur les arrays de sirens_mandats INPI.
                    </div>
                    {data?.network.map((n, i) => (
                      <div key={i} className="dem-glass" style={{ borderRadius: 8, padding: "10px 14px", display: "flex", alignItems: "center", gap: 10 }}>
                        <Icon name="layers" size={13} color="var(--accent-cyan)" />
                        <div style={{ flex: 1, minWidth: 0 }}>
                          <div style={{ fontSize: 12.5, fontWeight: 600 }}>{String(n.denomination ?? n.siren)}</div>
                          <div style={{ fontSize: 11, color: "var(--text-tertiary)", marginTop: 2 }}>
                            <span className="dem-mono">{String(n.siren ?? "—")}</span>
                            {n.via_dirigeants ? <> · via {String(n.via_dirigeants)}</> : null}
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}

            {tab === "presse" && !loading && (
              <div>
                {data?.presse.length === 0 ? (
                  <div style={{ color: "var(--text-tertiary)", fontSize: 13 }}>
                    Aucun article de presse matché en silver.press_mentions_matched (table en cours de population).
                  </div>
                ) : (
                  <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                    {data?.presse.map((p, i) => (
                      <div key={i} className="dem-glass" style={{ borderRadius: 8, padding: "10px 14px" }}>
                        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                          <span className="dem-mono" style={{ fontSize: 10.5, color: "var(--accent-cyan)" }}>
                            {fmtDate(p.published_at)}
                          </span>
                          <span style={{ fontSize: 11, color: "var(--text-tertiary)" }}>{String(p.source ?? "")}</span>
                          {Boolean(p.ma_signal_type) && (
                            <span className="dem-chip" style={{ fontSize: 10, padding: "1px 7px" }}>{String(p.ma_signal_type)}</span>
                          )}
                        </div>
                        <a
                          href={String(p.url ?? "#")}
                          target="_blank"
                          rel="noreferrer"
                          style={{ display: "block", marginTop: 4, fontSize: 12.5, color: "var(--text-primary)", textDecoration: "none" }}
                        >
                          {String(p.title ?? "")}
                        </a>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      </div>
    </>
  );
}
