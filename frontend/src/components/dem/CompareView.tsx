"use client";

import { useState, useEffect, useMemo } from "react";
import { Icon } from "./Icon";
import { ScoreBadge } from "./ScoreBadge";
import { Sparkline } from "./Sparkline";
import { fetchTargets } from "@/lib/dem/adapter";
import type { Target } from "@/lib/dem/types";

const fmtPct = (v: number) => (v >= 0 ? "+" : "") + v.toFixed(1) + "%";
const ebitdaMargin = (t: Target) => (t.ebitda && t.ca ? (t.ebitda / t.ca) * 100 : 0);
const cagr = (arr: number[]) => {
  if (!arr || arr.length < 2) return 0;
  return (Math.pow(arr[arr.length - 1] / arr[0], 1 / (arr.length - 1)) - 1) * 100;
};

interface ColProps {
  t: Target;
  isAnchor: boolean;
  anchor: Target | null;
  onSetAnchor: (siren: string) => void;
  onRemove: (siren: string) => void;
}

function CompareCol({ t, isAnchor, anchor, onSetAnchor, onRemove }: ColProps) {
  const margin = ebitdaMargin(t);
  const growth = cagr(t.ca_history);
  const dMargin = anchor && anchor.siren !== t.siren ? margin - ebitdaMargin(anchor) : null;
  const dGrowth = anchor && anchor.siren !== t.siren ? growth - cagr(anchor.ca_history) : null;
  const dCa = anchor && anchor.siren !== t.siren && anchor.ca ? ((t.ca - anchor.ca) / anchor.ca) * 100 : null;

  const Cell = ({ label, value, sub, delta, accent }: {
    label: string;
    value: React.ReactNode;
    sub?: string;
    delta?: number | null;
    accent?: string;
  }) => (
    <div style={{ padding: "12px 14px", borderBottom: "1px solid var(--border-subtle)" }}>
      <div style={{ fontSize: 10.5, textTransform: "uppercase", letterSpacing: ".06em", color: "var(--text-tertiary)", marginBottom: 4 }}>{label}</div>
      <div style={{
        fontSize: 15, fontWeight: 600, color: accent ?? "var(--text-primary)",
        display: "flex", alignItems: "baseline", gap: 6, flexWrap: "wrap",
      }}>
        {value}
        {delta != null && (
          <span className="dem-mono" style={{
            fontSize: 11,
            color: delta > 0 ? "var(--accent-emerald)" : delta < 0 ? "var(--accent-rose)" : "var(--text-tertiary)",
          }}>
            {fmtPct(delta)}
          </span>
        )}
      </div>
      {sub && <div style={{ fontSize: 11, color: "var(--text-tertiary)", marginTop: 2 }}>{sub}</div>}
    </div>
  );

  return (
    <div style={{
      background: "var(--bg-elevated)",
      border: isAnchor ? "1.5px solid rgba(96,165,250,0.55)" : "1px solid var(--border-subtle)",
      borderRadius: 12, overflow: "hidden",
      display: "flex", flexDirection: "column", minWidth: 0,
    }}>
      <div style={{
        padding: "14px 14px 12px",
        borderBottom: "1px solid var(--border-subtle)",
        background: isAnchor ? "rgba(96,165,250,0.06)" : "rgba(255,255,255,0.02)",
      }}>
        <div style={{ display: "flex", alignItems: "flex-start", gap: 8 }}>
          <div style={{ flex: 1, minWidth: 0 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 4 }}>
              <ScoreBadge value={t.score} />
              {isAnchor && (
                <span className="dem-mono" style={{
                  fontSize: 9, padding: "1px 5px", borderRadius: 4,
                  background: "rgba(96,165,250,0.18)", color: "#cfe1fb",
                  textTransform: "uppercase", letterSpacing: ".06em",
                }}>Ancre</span>
              )}
            </div>
            <div style={{ fontSize: 14, fontWeight: 600, lineHeight: 1.25, marginBottom: 2, wordBreak: "break-word" }}>{t.denomination}</div>
            <div className="dem-mono" style={{ fontSize: 10.5, color: "var(--text-tertiary)" }}>{t.siren} · {t.naf}</div>
          </div>
          <button
            onClick={() => onRemove(t.siren)}
            title="Retirer"
            style={{
              background: "transparent", border: "1px solid var(--border-subtle)",
              borderRadius: 6, color: "var(--text-tertiary)", padding: "3px 6px", cursor: "pointer",
            }}
          >
            <Icon name="close" size={11} />
          </button>
        </div>
        {!isAnchor && (
          <button
            onClick={() => onSetAnchor(t.siren)}
            style={{
              marginTop: 8, width: "100%", padding: "5px 8px", fontSize: 11,
              background: "transparent", border: "1px dashed var(--border-mid)",
              borderRadius: 6, color: "var(--text-secondary)", cursor: "pointer",
            }}
          >
            Définir comme ancre
          </button>
        )}
      </div>

      {t.ca_history.length >= 2 && (
        <div style={{ padding: "12px 14px", borderBottom: "1px solid var(--border-subtle)" }}>
          <div style={{ fontSize: 10.5, textTransform: "uppercase", letterSpacing: ".06em", color: "var(--text-tertiary)", marginBottom: 6 }}>CA 5 ans</div>
          <Sparkline data={t.ca_history} width={180} height={36} color="var(--accent-blue)" />
        </div>
      )}

      <Cell label="Chiffre d'affaires" value={t.ca_str} delta={dCa} sub={`CAGR ${fmtPct(growth)}`} />
      <Cell label="EBITDA" value={t.ebitda_str} sub={`Marge ${margin.toFixed(1)}%`} delta={dMargin} />
      <Cell label="Effectif" value={t.effectif ?? "—"} />
      <Cell label="Localisation" value={`${t.ville}${t.dept ? ` (${t.dept})` : ""}`} sub={`${t.forme || "—"}${t.creation && t.creation !== "—" ? ` · créée ${t.creation}` : ""}`} />
      <Cell
        label="Dirigeant principal"
        value={t.top_dirigeant.nom}
        sub={`${t.top_dirigeant.age ?? "?"} ans · score ${t.top_dirigeant.score} · ${t.top_dirigeant.mandats} mandats`}
      />
      <Cell
        label="Red flags"
        value={t.red_flags.length === 0 ? "Aucun" : `${t.red_flags.length} signal${t.red_flags.length > 1 ? "s" : ""}`}
        accent={t.red_flags.length === 0 ? "var(--accent-emerald)" : "var(--accent-rose)"}
        sub={t.red_flags.length > 0 ? t.red_flags[0].label : "Sanctions, ICIJ, BODACC OK"}
      />
      <Cell label="Sources auditables" value={`${t.sources.length} source${t.sources.length > 1 ? "s" : ""}`} sub={t.sources.join(" · ")} />

      <div style={{ marginTop: "auto", padding: "12px 14px", background: "rgba(255,255,255,0.02)" }}>
        <div style={{ fontSize: 10.5, textTransform: "uppercase", letterSpacing: ".06em", color: "var(--text-tertiary)", marginBottom: 4 }}>Verdict synthétique</div>
        <div style={{ fontSize: 12, color: "var(--text-secondary)", lineHeight: 1.5 }}>
          {t.score >= 85 ? "🟢 Cible prioritaire — score élevé, fundamentals solides." :
           t.score >= 75 ? "🟡 Cible intéressante — à approfondir en DD." :
           "🟠 Score moyen — vigilance dirigeant et marché requise."}
        </div>
      </div>
    </div>
  );
}

export function CompareView() {
  const [pool, setPool] = useState<Target[]>([]);
  const [selected, setSelected] = useState<string[]>([]);
  const [anchorSiren, setAnchorSiren] = useState<string | null>(null);
  const [pickerOpen, setPickerOpen] = useState(false);
  const [pickerQuery, setPickerQuery] = useState("");
  // Cache enrichissement par siren — chaque cible affichée fetche /fiche/<siren>
  // pour avoir effectif/ville/dept/naf/dirigeant qui manquent dans /cibles listing.
  const [enrichments, setEnrichments] = useState<Record<string, Record<string, unknown>>>({});

  useEffect(() => {
    fetchTargets({ limit: 50 }).then((ts) => {
      setPool(ts);
      const initial = ts.slice(0, 3).map((t) => t.siren);
      setSelected(initial);
      setAnchorSiren(initial[1] ?? initial[0]);
    });
  }, []);

  // Enrichit chaque cible sélectionnée via /fiche/<siren> (données complètes :
  // effectif, ville, dept, naf, top dirigeant). Le listing /cibles ne donne
  // qu'un sous-ensemble pour rester rapide ; on complète à la demande.
  useEffect(() => {
    selected.forEach(async (siren) => {
      if (enrichments[siren]) return;
      try {
        const r = await fetch(`/api/datalake/fiche/${siren}`);
        if (!r.ok) return;
        const data = await r.json();
        const f = data.fiche || {};
        const top = (data.dirigeants || [])[0] || {};
        setEnrichments((prev) => ({
          ...prev,
          [siren]: {
            naf: f.naf,
            naf_libelle: f.naf_libelle,
            forme_juridique: f.forme_juridique,
            ville: f.ville,
            dept: f.dept,
            adresse_code_postal: f.adresse_code_postal,
            effectif_exact: f.effectif_exact,
            tranche_effectifs: f.tranche_effectifs,
            annee_creation: f.annee_creation,
            categorie_entreprise: f.categorie_entreprise,
            n_etablissements: f.n_etablissements,
            n_dirigeants: f.n_dirigeants,
            n_bodacc: f.n_bodacc,
            n_sanctions: f.n_sanctions,
            top_dirigeant_full_name: top.nom && top.prenom ? `${top.prenom} ${top.nom}` : null,
            top_dirigeant_age: top.age,
            top_dirigeant_n_mandats: top.n_mandats_actifs,
          },
        }));
      } catch {
        /* noop */
      }
    });
  }, [selected, enrichments]);

  const targets = useMemo(
    () =>
      (selected.map((s) => pool.find((t) => t.siren === s)).filter(Boolean) as Target[]).map((t) => {
        const e = enrichments[t.siren];
        if (!e) return t;
        return {
          ...t,
          naf: (e.naf as string) || t.naf,
          ville: (e.ville as string) || t.ville,
          dept: (e.dept as string) || t.dept,
          forme: (e.forme_juridique as string) || t.forme,
          effectif: (e.effectif_exact as number) ?? t.effectif,
          creation: e.annee_creation ? String(e.annee_creation) : t.creation,
          top_dirigeant: {
            ...t.top_dirigeant,
            nom: (e.top_dirigeant_full_name as string) || t.top_dirigeant.nom,
            age: (e.top_dirigeant_age as number) ?? t.top_dirigeant.age,
            mandats: (e.top_dirigeant_n_mandats as number) ?? t.top_dirigeant.mandats,
          },
        } as Target;
      }),
    [selected, pool, enrichments]
  );
  const anchor = targets.find((t) => t.siren === anchorSiren) ?? targets[0] ?? null;
  const available = pool.filter((t) => !selected.includes(t.siren));

  const remove = (siren: string) => {
    if (selected.length <= 2) return;
    const next = selected.filter((s) => s !== siren);
    setSelected(next);
    if (anchorSiren === siren) setAnchorSiren(next[0]);
  };

  const add = (siren: string) => {
    if (selected.length >= 5) return;
    setSelected([...selected, siren]);
    setPickerOpen(false);
  };

  const winners = useMemo(() => {
    if (targets.length < 2) return {} as Record<string, string>;
    const max = (fn: (t: Target) => number) => targets.reduce((a, b) => (fn(b) > fn(a) ? b : a)).siren;
    return {
      score: max((t) => t.score),
      ca: max((t) => t.ca),
      ebitda: max((t) => t.ebitda ?? -Infinity),
      growth: max((t) => cagr(t.ca_history)),
      cleanest: targets.reduce((a, b) => (b.red_flags.length < a.red_flags.length ? b : a)).siren,
    };
  }, [targets]);

  return (
    <div style={{ flex: 1, display: "flex", flexDirection: "column", overflow: "hidden", background: "var(--bg-base)" }}>
      <div style={{ padding: "16px 22px 12px", borderBottom: "1px solid var(--border-subtle)" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 12, flexWrap: "wrap" }}>
          <div style={{ fontSize: 16, fontWeight: 700, letterSpacing: "-0.01em" }}>Comparateur multi-cibles</div>
          <span className="dem-mono" style={{ fontSize: 11, color: "var(--text-tertiary)" }}>
            · {targets.length}/5 cibles{anchor && ` · ancre ${anchor.denomination}`}
          </span>
          <span style={{ marginLeft: "auto", display: "flex", gap: 6 }}>
            <button
              className="dem-btn"
              onClick={() => {
                if (typeof window !== "undefined") {
                  // Astuce simple : window.print() ouvre le dialog de la page
                  // courante en pdf. Le CSS @media print du shell rend le grid
                  // proprement (cf. globals.css).
                  window.print();
                }
              }}
            >
              <Icon name="download" size={11} /> Export PDF
            </button>
            <button
              className="dem-btn"
              onClick={() => {
                try {
                  const view = { selected, anchorSiren, savedAt: new Date().toISOString() };
                  const all = JSON.parse(localStorage.getItem("dem.compare.views") || "[]");
                  localStorage.setItem("dem.compare.views", JSON.stringify([view, ...all].slice(0, 20)));
                  alert("Vue comparateur sauvegardée localement.");
                } catch {
                  alert("Impossible de sauvegarder (localStorage indisponible).");
                }
              }}
            >
              <Icon name="bookmark" size={11} /> Sauver vue
            </button>
          </span>
        </div>
        {targets.length >= 2 && (
          <div style={{ marginTop: 10, display: "flex", gap: 8, flexWrap: "wrap" }}>
            {[
              { label: "Score max", siren: winners.score, color: "var(--accent-blue)" },
              { label: "CA max", siren: winners.ca, color: "var(--accent-cyan)" },
              { label: "EBITDA max", siren: winners.ebitda, color: "var(--accent-emerald)" },
              { label: "Croissance max", siren: winners.growth, color: "var(--accent-purple)" },
              { label: "Plus propre (compliance)", siren: winners.cleanest, color: "var(--accent-amber)" },
            ].map((w, i) => {
              const t = pool.find((x) => x.siren === w.siren);
              if (!t) return null;
              return (
                <div key={i} style={{
                  display: "flex", alignItems: "center", gap: 6,
                  padding: "4px 10px", borderRadius: 999,
                  background: "rgba(255,255,255,0.03)",
                  border: "1px solid var(--border-subtle)",
                  fontSize: 11.5,
                }}>
                  <span style={{ width: 6, height: 6, borderRadius: "50%", background: w.color }} />
                  <span style={{ color: "var(--text-tertiary)" }}>{w.label}</span>
                  <span style={{ color: "var(--text-primary)", fontWeight: 500 }}>{t.denomination}</span>
                </div>
              );
            })}
          </div>
        )}
      </div>

      <div style={{ flex: 1, overflowX: "auto", overflowY: "auto", padding: 16 }}>
        {targets.length === 0 ? (
          <div style={{ padding: 32, textAlign: "center", color: "var(--text-tertiary)" }}>Chargement…</div>
        ) : (
          <div style={{
            display: "grid",
            gridTemplateColumns: `repeat(${targets.length + (selected.length < 5 ? 1 : 0)}, minmax(260px, 1fr))`,
            gap: 12, alignItems: "stretch", minHeight: "100%",
          }}>
            {targets.map((t) => (
              <CompareCol
                key={t.siren}
                t={t}
                isAnchor={t.siren === anchorSiren}
                anchor={anchor}
                onSetAnchor={setAnchorSiren}
                onRemove={remove}
              />
            ))}

            {selected.length < 5 && (
              <div style={{
                position: "relative",
                border: "1.5px dashed var(--border-mid)",
                borderRadius: 12,
                display: "flex", flexDirection: "column",
                alignItems: "center", justifyContent: "center",
                padding: 24, minHeight: 320,
                background: "rgba(255,255,255,0.01)",
              }}>
                <button
                  onClick={() => setPickerOpen(!pickerOpen)}
                  style={{
                    display: "flex", flexDirection: "column",
                    alignItems: "center", gap: 8,
                    background: "transparent", border: "none",
                    color: "var(--text-secondary)",
                    cursor: "pointer", padding: 12,
                  }}
                >
                  <div style={{
                    width: 36, height: 36, borderRadius: "50%",
                    background: "rgba(96,165,250,0.10)",
                    display: "flex", alignItems: "center", justifyContent: "center",
                    color: "var(--accent-blue)",
                  }}>
                    <Icon name="plus" size={16} />
                  </div>
                  <div style={{ fontSize: 13, fontWeight: 500 }}>Ajouter une cible</div>
                  <div style={{ fontSize: 11, color: "var(--text-tertiary)" }}>{5 - selected.length} slot{5 - selected.length > 1 ? "s" : ""} dispo</div>
                </button>
                {pickerOpen && (
                  <div
                    role="dialog"
                    style={{
                      // position:fixed centré pour ne pas être clippé par le grid
                      // overflow auto qui contient la card placeholder.
                      position: "fixed",
                      inset: 0,
                      background: "rgba(0,0,0,0.5)",
                      zIndex: 100,
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      padding: 20,
                    }}
                    onClick={() => setPickerOpen(false)}
                  >
                    <div
                      style={{
                        width: "min(560px, 92vw)", maxHeight: "70vh",
                        background: "var(--bg-elevated)",
                        border: "1px solid var(--border-mid)", borderRadius: 12,
                        boxShadow: "0 20px 48px rgba(0,0,0,0.6)",
                        display: "flex", flexDirection: "column",
                        overflow: "hidden",
                      }}
                      onClick={(e) => e.stopPropagation()}
                    >
                      <div style={{ padding: "12px 14px", borderBottom: "1px solid var(--border-subtle)" }}>
                        <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 8 }}>
                          Ajouter une cible au comparatif
                        </div>
                        <input
                          autoFocus
                          value={pickerQuery}
                          onChange={(e) => setPickerQuery(e.target.value)}
                          placeholder="Rechercher par nom, SIREN, ville…"
                          className="dem-input"
                          style={{ width: "100%" }}
                        />
                      </div>
                      <div style={{ flex: 1, overflowY: "auto", padding: 6 }}>
                        {available.length === 0 && (
                          <div style={{ padding: 24, fontSize: 12, color: "var(--text-tertiary)", textAlign: "center" }}>
                            Toutes les cibles disponibles sont déjà ajoutées.
                          </div>
                        )}
                        {available
                          .filter((t) => {
                            const q = pickerQuery.trim().toLowerCase();
                            if (!q) return true;
                            return (
                              t.denomination.toLowerCase().includes(q) ||
                              t.siren.includes(q) ||
                              (t.ville || "").toLowerCase().includes(q) ||
                              (t.naf || "").toLowerCase().includes(q)
                            );
                          })
                          .map((t) => (
                            <button
                              key={t.siren}
                              onClick={() => add(t.siren)}
                              style={{
                                width: "100%", display: "flex",
                                alignItems: "center", gap: 10,
                                padding: "8px 10px", background: "transparent",
                                border: "none", borderRadius: 6,
                                color: "var(--text-primary)", cursor: "pointer",
                                textAlign: "left", fontSize: 12.5,
                              }}
                              onMouseEnter={(e) => (e.currentTarget.style.background = "rgba(255,255,255,0.04)")}
                              onMouseLeave={(e) => (e.currentTarget.style.background = "transparent")}
                            >
                              <ScoreBadge value={t.score} />
                              <div style={{ flex: 1, minWidth: 0 }}>
                                <div style={{
                                  fontWeight: 500, whiteSpace: "nowrap",
                                  overflow: "hidden", textOverflow: "ellipsis",
                                }}>{t.denomination}</div>
                                <div className="dem-mono" style={{ fontSize: 10.5, color: "var(--text-tertiary)" }}>
                                  {t.siren} · {t.ca_str} · {t.naf || t.ville || "—"}
                                </div>
                              </div>
                            </button>
                          ))}
                      </div>
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        )}
      </div>

      <div style={{
        padding: "10px 22px",
        borderTop: "1px solid var(--border-subtle)",
        display: "flex", alignItems: "center", gap: 12,
        fontSize: 11, color: "var(--text-tertiary)",
      }}>
        <Icon name="info" size={11} />
        <span>Δ % calculés vs ancre. Cliquez « Définir comme ancre » pour changer le pivot.</span>
        <span style={{ marginLeft: "auto" }} className="dem-mono">live · {targets.length} cibles</span>
      </div>
    </div>
  );
}
