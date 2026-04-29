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

// Codes catégories juridiques INSEE — référentiel officiel (top 50 utilisés en France)
const CATEGORIES_JURIDIQUES: Record<string, string> = {
  "1000": "Entrepreneur individuel",
  "1100": "Commerçant",
  "1200": "Artisan-commerçant",
  "1300": "Artisan",
  "1400": "Officier public ou ministériel",
  "1500": "Profession libérale",
  "1600": "Exploitant agricole",
  "1700": "Agent commercial",
  "1800": "Associé gérant de société",
  "1900": "(Autre) personne physique",
  "5202": "SNC",
  "5306": "SCS",
  "5310": "SCA",
  "5410": "SARL nationale",
  "5415": "SARL d'économie mixte",
  "5422": "SARL coopérative agricole",
  "5426": "SARL coopérative artisanale",
  "5430": "SARL coopérative",
  "5460": "SARL d'attribution",
  "5485": "SARL coopérative",
  "5498": "SARL unipersonnelle (EURL)",
  "5499": "SARL",
  "5505": "SA à participation ouvrière à conseil d'administration",
  "5510": "SA nationale à conseil d'administration",
  "5515": "SA d'économie mixte à conseil d'administration",
  "5520": "Fonds à forme sociale",
  "5522": "SA coopérative de banque populaire",
  "5525": "SA coopérative de crédit",
  "5530": "SA d'HLM à conseil d'administration",
  "5531": "SA coopérative de production d'HLM à conseil d'administration",
  "5532": "SA coopérative d'intérêt collectif d'HLM à conseil d'administration",
  "5542": "SA coopérative agricole à conseil d'administration",
  "5546": "SA coopérative artisanale à conseil d'administration",
  "5547": "SA coopérative (Banque populaire) à conseil d'administration",
  "5548": "SA coopérative ouvrière de production",
  "5551": "SA d'union de coopératives à conseil d'administration",
  "5559": "SA coopérative de consommation",
  "5560": "Autre SA à conseil d'administration",
  "5585": "SA d'attribution à conseil d'administration",
  "5599": "SA à conseil d'administration",
  "5605": "SA à participation ouvrière à directoire",
  "5610": "SA nationale à directoire",
  "5615": "SA d'économie mixte à directoire",
  "5625": "SA coopérative de banque populaire à directoire",
  "5630": "SA d'HLM à directoire",
  "5642": "SA coopérative agricole à directoire",
  "5651": "SA d'union de coopératives à directoire",
  "5660": "Autre SA à directoire",
  "5685": "SA d'attribution à directoire",
  "5699": "SA à directoire",
  "5710": "SAS (Société par Actions Simplifiée)",
  "5720": "SAS unipersonnelle (SASU)",
  "5800": "SE (Société européenne)",
  "6100": "Caisse d'épargne et de prévoyance",
  "6210": "GEIE",
  "6220": "GIE",
  "6316": "Coopérative d'utilisation de matériel agricole",
  "6317": "Société coopérative agricole",
  "6318": "Union de sociétés coopératives agricoles",
  "6411": "Société d'assurance à forme mutuelle",
  "6511": "SICAV à conseil d'administration",
  "6532": "SCPI",
  "6533": "Société civile coopérative d'intérêt collectif agricole",
  "6534": "GAEC partiel",
  "6535": "GAEC total",
  "6536": "GAEC",
  "6537": "GAEC",
  "6539": "Autre groupement agricole",
  "6540": "SCM (société civile de moyens)",
  "6541": "SCP (société civile professionnelle)",
  "6542": "SCI (société civile immobilière)",
  "6543": "SCI de construction-vente",
  "6544": "Société civile d'attribution",
  "6551": "Société civile coopérative de consommation",
  "6554": "Société civile coopérative entre médecins",
  "6558": "Société civile coopérative d'intérêt général",
  "6560": "Autre société civile",
  "6561": "SC d'exploitation agricole",
  "6566": "Société d'épargne forestière",
  "6567": "Société de placement à prépondérance immobilière à capital variable",
  "6568": "Société interprofessionnelle de soins ambulatoires",
  "6569": "Société pluri-professionnelle d'exercice",
  "6585": "Société civile de portefeuille",
  "6588": "Société civile laitière",
  "6589": "Société civile fiduciaire",
  "6591": "SCEA",
  "6592": "SCM (société civile de moyens)",
  "6593": "SCI (société civile immobilière)",
  "6594": "Société civile d'attribution",
  "6595": "Société civile coopérative",
  "6596": "Société de financement",
  "6597": "Société civile de Placement Collectif Immobilier",
  "6598": "Société civile",
  "6599": "Autre Société civile",
  "9220": "Association déclarée",
  "9230": "Association non déclarée",
  "9240": "Association non déclarée d'utilité publique",
  "9260": "Association déclarée 'entreprise d'insertion par l'économique'",
  "9300": "Fondation",
};

// Tranches d'effectif INSEE
const TRANCHES_EFFECTIFS: Record<string, string> = {
  "NN": "Non employeur ou inconnu",
  "00": "0 salarié",
  "01": "1 ou 2 salariés",
  "02": "3 à 5 salariés",
  "03": "6 à 9 salariés",
  "11": "10 à 19 salariés",
  "12": "20 à 49 salariés",
  "21": "50 à 99 salariés",
  "22": "100 à 199 salariés",
  "31": "200 à 249 salariés",
  "32": "250 à 499 salariés",
  "41": "500 à 999 salariés",
  "42": "1 000 à 1 999 salariés",
  "51": "2 000 à 4 999 salariés",
  "52": "5 000 à 9 999 salariés",
  "53": "10 000 salariés et plus",
};

function trancheLabel(code: string): string {
  return TRANCHES_EFFECTIFS[code] || `Tranche ${code}`;
}

function formeJuridiqueLabel(code: string): string {
  return CATEGORIES_JURIDIQUES[code] || `Code ${code}`;
}

function BarChart({ data, labels }: { data: number[]; labels: string[] }) {
  if (data.length === 0) return null;
  const max = Math.max(...data, 1);
  const min = Math.min(...data, 0);
  const BAR_AREA = 160; // hauteur du graph en px
  return (
    <div style={{ marginTop: 14 }}>
      <div style={{
        display: "grid",
        gridTemplateColumns: `repeat(${data.length}, 1fr)`,
        gap: 14,
        alignItems: "end",
        height: BAR_AREA,
      }}>
        {data.map((v, i) => {
          const isLatest = i === data.length - 1;
          const prev = i > 0 ? data[i - 1] : null;
          const yoy = prev && prev !== 0 ? ((v - prev) / Math.abs(prev)) * 100 : null;
          const heightPx = Math.max(8, Math.round((v / max) * (BAR_AREA - 36)));
          return (
            <div key={i} style={{
              display: "flex", flexDirection: "column",
              alignItems: "center", justifyContent: "flex-end",
              height: "100%", position: "relative",
            }}>
              {/* YoY badge */}
              {yoy != null && (
                <div className="dem-mono tab-num" style={{
                  fontSize: 10, fontWeight: 600,
                  color: yoy >= 0 ? "var(--accent-emerald)" : "var(--accent-rose)",
                  marginBottom: 2,
                }}>
                  {yoy >= 0 ? "+" : ""}{yoy.toFixed(0)}%
                </div>
              )}
              {/* Value */}
              <div className="dem-mono tab-num" style={{
                fontSize: 11, fontWeight: 600,
                color: isLatest ? "var(--accent-blue)" : "var(--text-secondary)",
                marginBottom: 4,
              }}>
                {fmtEur(v)}
              </div>
              {/* Bar */}
              <div style={{
                width: "70%", maxWidth: 60,
                height: heightPx,
                background: isLatest
                  ? "linear-gradient(180deg, var(--accent-blue), rgba(96,165,250,0.20))"
                  : "linear-gradient(180deg, rgba(255,255,255,0.18), rgba(255,255,255,0.06))",
                borderRadius: "6px 6px 0 0",
                boxShadow: isLatest
                  ? "0 0 18px -2px rgba(96,165,250,0.55), inset 0 1px 0 rgba(255,255,255,0.25)"
                  : "inset 0 1px 0 rgba(255,255,255,0.08)",
                transition: "height 0.4s cubic-bezier(.4,1.2,.3,1)",
              }} />
            </div>
          );
        })}
      </div>
      {/* Year labels */}
      <div style={{
        display: "grid", gridTemplateColumns: `repeat(${data.length}, 1fr)`, gap: 14,
        marginTop: 8, paddingTop: 6,
        borderTop: "1px solid var(--border-subtle)",
      }}>
        {labels.map((l, i) => (
          <div key={i} className="dem-mono" style={{
            fontSize: 11, color: "var(--text-tertiary)",
            textAlign: "center", fontWeight: i === labels.length - 1 ? 600 : 500,
          }}>
            {l}
          </div>
        ))}
      </div>
      {/* Min/max axis hint */}
      {min !== max && (
        <div style={{
          marginTop: 10, fontSize: 10.5, color: "var(--text-muted)",
          display: "flex", justifyContent: "space-between",
        }}>
          <span>min {fmtEur(min)}</span>
          <span>max {fmtEur(max)}</span>
          <span>CAGR {data.length >= 2 ? ((Math.pow(data[data.length - 1] / data[0], 1 / (data.length - 1)) - 1) * 100).toFixed(1) : "0"}%</span>
        </div>
      )}
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
  const formeRaw = String(fiche.forme_juridique || target.forme || "");
  const forme = formeRaw ? formeJuridiqueLabel(formeRaw) : "";
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
              {forme && <span title={`code ${formeRaw}`}>{forme}</span>}
              {annee && annee !== "—" && <span>Créée en {annee}</span>}
              {ville && <span>{ville}{cp ? ` · ${cp}` : ""}{dept ? ` (${dept})` : ""}</span>}
              {tranche && tranche !== "NN" && <span title={`code INSEE ${tranche}`}>{trancheLabel(tranche)}</span>}
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
                    {
                      l: "Effectif",
                      v: effectif != null && Number(effectif) > 0
                        ? Number(effectif).toLocaleString("fr-FR")
                        : (tranche && tranche !== "NN" ? trancheLabel(tranche) : "—"),
                      sub: effectif != null && Number(effectif) > 0
                        ? "moyen INPI"
                        : (tranche && tranche !== "NN" ? `tranche ${tranche} INSEE` : ""),
                      color: "var(--text-secondary)",
                    },
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
