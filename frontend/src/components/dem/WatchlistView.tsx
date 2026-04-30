"use client";

import { useEffect, useState } from "react";
import { Icon } from "./Icon";
import { datalakeApi } from "@/lib/api";
import { fetchTargets } from "@/lib/dem/adapter";
import { formatSiren } from "@/lib/dem/format";
import type { Target } from "@/lib/dem/types";

interface Props {
  onOpenTarget: (t: Target) => void;
}

interface Alert {
  id: string;
  siren: string;
  denomination: string;
  title: string;
  family: string;
  source: string;
  ville: string;
  departement: string;
  code_dept: string;
  date_parution: string;
  severity: "high" | "med" | "low";
}

interface Rule {
  id: string;
  name: string;
  ca_min?: number;
  ca_max?: number;
  dept?: string;
  naf_prefix?: string;
  with_red_flags: boolean;
  pro_ma_only: boolean;
  created_at: string;
}

const RULES_KEY = "dem.watchlist.rules";
function loadRules(): Rule[] {
  try { return JSON.parse(localStorage.getItem(RULES_KEY) || "[]"); }
  catch { return []; }
}
function saveRules(r: Rule[]) {
  try { localStorage.setItem(RULES_KEY, JSON.stringify(r)); } catch {}
}

function severityFor(family: unknown): "high" | "med" | "low" {
  const s = String(family || "").toLowerCase();
  if (s.includes("liquidation") || s.includes("redressement") || s.includes("procédure") || s.includes("procedure")) return "high";
  if (s.includes("cession") || s.includes("vente")) return "med";
  return "low";
}

export function WatchlistView({ onOpenTarget }: Props) {
  const [tab, setTab] = useState<"alerts" | "saved" | "rules">("saved");
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [loading, setLoading] = useState(true);
  const [rules, setRules] = useState<Rule[]>(() => loadRules());
  const [showRuleForm, setShowRuleForm] = useState(false);
  const [draft, setDraft] = useState<Partial<Rule>>({ with_red_flags: false, pro_ma_only: false });
  const [savedTargets, setSavedTargets] = useState<Target[]>([]);
  const [savedLoading, setSavedLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    datalakeApi
      .dashboard()
      .then((d) => {
        const mapped: Alert[] = d.alerts.map((a, i) => ({
          id: `a_${i}_${a.siren}`,
          siren: String(a.siren ?? ""),
          denomination: String(a.denomination ?? a.siren ?? "—"),
          title: String(a.title ?? ""),
          family: String(a.family ?? ""),
          source: String(a.source ?? "BODACC"),
          ville: String(a.ville ?? ""),
          departement: String(a.departement ?? ""),
          code_dept: String(a.code_dept ?? ""),
          date_parution: String(a.date_parution ?? "").slice(0, 10),
          severity: severityFor(a.family),
        }));
        setAlerts(mapped);
      })
      .finally(() => setLoading(false));
  }, []);

  const openAlert = async (siren: string) => {
    if (!siren) return;
    const targets = await fetchTargets({ q: siren, limit: 1 });
    if (targets[0]) onOpenTarget(targets[0]);
  };

  // Charger les cibles sauvegardées depuis localStorage (cf. ChatPanel handleSave)
  useEffect(() => {
    setSavedLoading(true);
    let sirens: string[] = [];
    try {
      const raw = localStorage.getItem("dem.savedTargets");
      if (raw) sirens = JSON.parse(raw) as string[];
    } catch { /* noop */ }
    if (sirens.length === 0) {
      setSavedTargets([]);
      setSavedLoading(false);
      return;
    }
    // On fetch les fiches une par une pour avoir les details complets.
    Promise.all(
      sirens.slice(0, 50).map((siren) =>
        fetchTargets({ q: siren, limit: 1 }).then((t) => t[0]).catch(() => null)
      )
    ).then((results) => {
      setSavedTargets(results.filter((t): t is Target => Boolean(t)));
      setSavedLoading(false);
    });
  }, []);

  const removeSaved = (siren: string) => {
    setSavedTargets((prev) => prev.filter((t) => t.siren !== siren));
    try {
      const raw = localStorage.getItem("dem.savedTargets");
      const arr = raw ? (JSON.parse(raw) as string[]) : [];
      const next = arr.filter((s) => s !== siren);
      localStorage.setItem("dem.savedTargets", JSON.stringify(next));
    } catch { /* noop */ }
  };

  return (
    <div style={{ flex: 1, display: "flex", flexDirection: "column", overflow: "hidden", position: "relative", zIndex: 1 }}>
      <div style={{ padding: "16px 22px 0", borderBottom: "1px solid var(--border-subtle)" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <h1 style={{ margin: 0, fontSize: 16, fontWeight: 700, letterSpacing: "-0.01em" }}>Watchlist &amp; Alertes</h1>
          <span className="dem-mono" style={{ fontSize: 11, color: "var(--text-tertiary)" }}>
            · {alerts.length} alertes BODACC 14j · datalake live
          </span>
          <span style={{ marginLeft: "auto" }}>
            <button
              className="dem-btn dem-btn-primary"
              onClick={() => { setTab("rules"); setShowRuleForm(true); }}
            >
              <Icon name="plus" size={11} /> Nouvelle règle
            </button>
          </span>
        </div>
        <div style={{ display: "flex", gap: 4, marginTop: 14 }}>
          {[
            { id: "saved" as const, label: "Mes cibles", count: savedTargets.length },
            { id: "alerts" as const, label: "Alertes BODACC", count: alerts.length },
            { id: "rules" as const, label: "Règles", count: rules.length },
          ].map((t) => (
            <button
              key={t.id}
              onClick={() => setTab(t.id)}
              style={{
                padding: "8px 14px", border: "none", background: "transparent",
                color: tab === t.id ? "var(--text-primary)" : "var(--text-tertiary)",
                borderBottom: `2px solid ${tab === t.id ? "var(--accent-blue)" : "transparent"}`,
                cursor: "pointer", fontSize: 13, fontWeight: tab === t.id ? 600 : 500,
              }}
            >
              {t.label}{" "}
              <span className="dem-mono" style={{ fontSize: 10.5, color: "var(--text-muted)", marginLeft: 4 }}>{t.count}</span>
            </button>
          ))}
        </div>
      </div>

      <div style={{ flex: 1, overflowY: "auto", padding: 22 }}>
        {tab === "saved" && (
          <div style={{ display: "flex", flexDirection: "column", gap: 8, maxWidth: 920, margin: "0 auto" }}>
            {savedLoading && <div style={{ padding: 12, fontSize: 12, color: "var(--text-tertiary)" }}>Chargement…</div>}
            {!savedLoading && savedTargets.length === 0 && (
              <div style={{ padding: 24, textAlign: "center", color: "var(--text-tertiary)" }}>
                Aucune cible sauvegardée. Clique sur le bouton « Sauver » d&apos;une fiche cible pour l&apos;ajouter ici.
              </div>
            )}
            {savedTargets.map((t) => (
              <div
                key={t.siren}
                className="dem-glass card-lift fade-up"
                style={{ borderRadius: 10, padding: 14, display: "flex", gap: 14, alignItems: "center", cursor: "pointer" }}
                onClick={() => onOpenTarget(t)}
              >
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap" }}>
                    <span style={{ fontSize: 13.5, fontWeight: 600 }}>{t.denomination}</span>
                    <span className="dem-mono" style={{ fontSize: 10.5, color: "var(--text-muted)" }}>siren {formatSiren(t.siren)}</span>
                    {t.statut && t.statut !== "actif" && (
                      <span style={{ padding: "1px 6px", borderRadius: 4, background: "rgba(251,113,133,0.10)", border: "1px solid rgba(251,113,133,0.30)", color: "var(--accent-rose)", fontSize: 10, fontWeight: 600 }}>
                        {String(t.statut).toUpperCase()}
                      </span>
                    )}
                  </div>
                  <div style={{ marginTop: 6, fontSize: 11.5, color: "var(--text-tertiary)", display: "flex", gap: 14, flexWrap: "wrap" }}>
                    <span>CA <strong style={{ color: "var(--text-primary)" }}>{t.ca_str || "—"}</strong></span>
                    <span>EBITDA <strong style={{ color: "var(--text-primary)" }}>{t.ebitda_str || "—"}</strong></span>
                    {t.naf && <span>NAF <span className="dem-mono">{t.naf}</span></span>}
                    {t.dept && <span>Dept <span className="dem-mono">{t.dept}</span></span>}
                  </div>
                </div>
                <button
                  className="dem-btn dem-btn-ghost"
                  title="Retirer de la watchlist"
                  onClick={(e) => { e.stopPropagation(); removeSaved(t.siren); }}
                >
                  <Icon name="close" size={11} /> Retirer
                </button>
              </div>
            ))}
          </div>
        )}
        {tab === "alerts" && (
          <div style={{ display: "flex", flexDirection: "column", gap: 8, maxWidth: 920, margin: "0 auto" }}>
            {loading && <div style={{ padding: 12, fontSize: 12, color: "var(--text-tertiary)" }}>Chargement…</div>}
            {!loading && alerts.length === 0 && (
              <div style={{ padding: 24, textAlign: "center", color: "var(--text-tertiary)" }}>
                Aucune alerte BODACC sur 14 jours.
              </div>
            )}
            {alerts.map((a) => (
              <div
                key={a.id}
                className="dem-glass card-lift fade-up"
                style={{ borderRadius: 10, padding: 14, display: "flex", gap: 14, alignItems: "center", cursor: "pointer" }}
                onClick={() => openAlert(a.siren)}
              >
                <span className={`sev-dot ${a.severity}`} />
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                    <span style={{ fontSize: 13.5, fontWeight: 600 }}>{a.denomination}</span>
                    <span className="dem-mono" style={{ fontSize: 10.5, color: "var(--text-muted)" }}>siren {formatSiren(a.siren)}</span>
                  </div>
                  <div style={{ marginTop: 4, fontSize: 12.5, color: a.severity === "high" ? "var(--accent-rose)" : "var(--text-secondary)" }}>
                    {a.title}
                  </div>
                  <div style={{ marginTop: 6, fontSize: 11, color: "var(--text-tertiary)" }}>
                    {a.date_parution} · {a.ville}{a.code_dept ? ` (${a.code_dept})` : ""} · <span className="dem-mono" style={{ color: "var(--accent-cyan)" }}>{a.source}</span>
                  </div>
                </div>
                <button className="dem-btn"><Icon name="eye" size={11} /> Voir fiche</button>
              </div>
            ))}
          </div>
        )}
        {tab === "rules" && (
          <div style={{ maxWidth: 920, margin: "0 auto", padding: 24 }}>
            {showRuleForm && (
              <div className="dem-glass" style={{ padding: 20, borderRadius: 12, marginBottom: 16 }}>
                <div style={{ fontSize: 14, fontWeight: 600, marginBottom: 12 }}>Nouvelle règle de watchlist</div>
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
                  <Field label="Nom de la règle">
                    <input
                      value={draft.name || ""}
                      onChange={(e) => setDraft({ ...draft, name: e.target.value })}
                      placeholder="ex: Cibles Île-de-France 5-15M€"
                      className="dem-input"
                    />
                  </Field>
                  <Field label="Département (code 2 chiffres)">
                    <input
                      value={draft.dept || ""}
                      onChange={(e) => setDraft({ ...draft, dept: e.target.value })}
                      placeholder="ex: 75"
                      className="dem-input"
                    />
                  </Field>
                  <Field label="CA minimum (€)">
                    <input
                      type="number"
                      value={draft.ca_min ?? ""}
                      onChange={(e) => setDraft({ ...draft, ca_min: e.target.value ? Number(e.target.value) : undefined })}
                      placeholder="ex: 5000000"
                      className="dem-input"
                    />
                  </Field>
                  <Field label="CA maximum (€)">
                    <input
                      type="number"
                      value={draft.ca_max ?? ""}
                      onChange={(e) => setDraft({ ...draft, ca_max: e.target.value ? Number(e.target.value) : undefined })}
                      placeholder="ex: 15000000"
                      className="dem-input"
                    />
                  </Field>
                  <Field label="Code NAF (préfixe)">
                    <input
                      value={draft.naf_prefix || ""}
                      onChange={(e) => setDraft({ ...draft, naf_prefix: e.target.value })}
                      placeholder="ex: 62 (informatique)"
                      className="dem-input"
                    />
                  </Field>
                  <Field label="Filtres rapides">
                    <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
                      <label style={{ display: "flex", gap: 6, alignItems: "center", fontSize: 12 }}>
                        <input
                          type="checkbox"
                          checked={!!draft.pro_ma_only}
                          onChange={(e) => setDraft({ ...draft, pro_ma_only: e.target.checked })}
                        /> Pro M&A
                      </label>
                      <label style={{ display: "flex", gap: 6, alignItems: "center", fontSize: 12 }}>
                        <input
                          type="checkbox"
                          checked={!!draft.with_red_flags}
                          onChange={(e) => setDraft({ ...draft, with_red_flags: e.target.checked })}
                        /> Avec red flags
                      </label>
                    </div>
                  </Field>
                </div>
                <div style={{ marginTop: 14, display: "flex", gap: 8, justifyContent: "flex-end" }}>
                  <button className="dem-btn" onClick={() => { setShowRuleForm(false); setDraft({ with_red_flags: false, pro_ma_only: false }); }}>Annuler</button>
                  <button
                    className="dem-btn dem-btn-primary"
                    onClick={() => {
                      if (!draft.name) { alert("Donne un nom à la règle"); return; }
                      const rule: Rule = {
                        id: `r_${Date.now()}`,
                        name: draft.name,
                        ca_min: draft.ca_min,
                        ca_max: draft.ca_max,
                        dept: draft.dept,
                        naf_prefix: draft.naf_prefix,
                        with_red_flags: !!draft.with_red_flags,
                        pro_ma_only: !!draft.pro_ma_only,
                        created_at: new Date().toISOString(),
                      };
                      const next = [rule, ...rules];
                      setRules(next);
                      saveRules(next);
                      setShowRuleForm(false);
                      setDraft({ with_red_flags: false, pro_ma_only: false });
                    }}
                  >
                    Enregistrer la règle
                  </button>
                </div>
              </div>
            )}

            {rules.length === 0 && !showRuleForm && (
              <div className="dem-glass" style={{ padding: 32, borderRadius: 12, textAlign: "center", color: "var(--text-tertiary)", fontSize: 13 }}>
                <Icon name="bookmark" size={24} color="var(--text-muted)" />
                <div style={{ marginTop: 8, fontSize: 14, color: "var(--text-secondary)", fontWeight: 600 }}>
                  Aucune règle sauvegardée
                </div>
                <div style={{ marginTop: 4, fontSize: 12 }}>
                  Crée ta première règle de watchlist pour être alerté automatiquement.
                </div>
                <button
                  className="dem-btn dem-btn-primary"
                  style={{ marginTop: 12 }}
                  onClick={() => setShowRuleForm(true)}
                >
                  <Icon name="plus" size={11} /> Créer une règle
                </button>
              </div>
            )}

            {rules.length > 0 && (
              <div style={{ display: "grid", gap: 8 }}>
                {rules.map((r) => (
                  <div key={r.id} className="dem-glass" style={{ padding: 14, borderRadius: 10, display: "flex", alignItems: "center", gap: 12 }}>
                    <div style={{ flex: 1 }}>
                      <div style={{ fontSize: 14, fontWeight: 600 }}>{r.name}</div>
                      <div style={{ fontSize: 11, color: "var(--text-tertiary)", marginTop: 2 }}>
                        {[
                          r.dept && `dept ${r.dept}`,
                          r.ca_min && `CA ≥ ${(r.ca_min / 1e6).toFixed(1)} M€`,
                          r.ca_max && `CA ≤ ${(r.ca_max / 1e6).toFixed(1)} M€`,
                          r.naf_prefix && `NAF ${r.naf_prefix}`,
                          r.pro_ma_only && "Pro M&A",
                          r.with_red_flags && "Red flags",
                        ].filter(Boolean).join(" · ") || "Aucun filtre"}
                      </div>
                    </div>
                    <button
                      className="dem-btn"
                      onClick={() => {
                        const next = rules.filter((x) => x.id !== r.id);
                        setRules(next);
                        saveRules(next);
                      }}
                    >
                      <Icon name="trash" size={11} /> Supprimer
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <div style={{ fontSize: 11, color: "var(--text-tertiary)", marginBottom: 4, textTransform: "uppercase", letterSpacing: ".06em" }}>
        {label}
      </div>
      {children}
    </div>
  );
}
