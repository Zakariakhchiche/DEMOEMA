"use client";

import { useState, useEffect } from "react";
import { Icon } from "./Icon";

export interface ChatConvSummary {
  id: string;
  title: string;
  updated_at: number;
  type?: "sourcing" | "dd" | "compare" | "graph";
}

interface Props {
  active?: string;
  conversations: ChatConvSummary[];
  onSelect: (id: string) => void;
  onNew: () => void;
  collapsed?: boolean;
}

function relativeTime(ts: number): string {
  const diff = Date.now() - ts;
  if (diff < 60_000) return "à l'instant";
  if (diff < 3600_000) return `il y a ${Math.floor(diff / 60_000)} min`;
  if (diff < 86_400_000) return `il y a ${Math.floor(diff / 3600_000)} h`;
  const d = new Date(ts);
  return d.toLocaleDateString("fr-FR", { day: "numeric", month: "short" });
}

function bucket(ts: number): "today" | "7d" | "30d" | "older" {
  const age = Date.now() - ts;
  if (age < 86_400_000) return "today";
  if (age < 7 * 86_400_000) return "7d";
  if (age < 30 * 86_400_000) return "30d";
  return "older";
}

export function ChatSidebar({ active, conversations, onSelect, onNew, collapsed }: Props) {
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [helpOpen, setHelpOpen] = useState(false);
  if (collapsed) return null;

  const groups: { key: "today" | "7d" | "30d" | "older"; label: string }[] = [
    { key: "today", label: "Aujourd'hui" },
    { key: "7d", label: "7 derniers jours" },
    { key: "30d", label: "30 derniers jours" },
    { key: "older", label: "Plus ancien" },
  ];

  return (
    <div style={{
      width: 264, borderRight: "1px solid var(--border-subtle)",
      display: "flex", flexDirection: "column",
      background: "rgba(10,10,13,0.40)", flexShrink: 0,
    }}>
      <div style={{ padding: "12px 12px 8px" }}>
        <button
          onClick={onNew}
          className="dem-btn dem-btn-primary"
          style={{ width: "100%", justifyContent: "center", padding: "9px 12px", fontSize: 13 }}
        >
          <Icon name="plus" size={13} /> Nouvelle conversation
          <span style={{ marginLeft: "auto", display: "flex", gap: 3 }}>
            <span className="kbd">⌘</span>
            <span className="kbd">N</span>
          </span>
        </button>
      </div>

      <div style={{ flex: 1, overflowY: "auto", padding: "4px 6px 12px" }}>
        {conversations.length === 0 && (
          <div style={{ padding: "20px 14px", fontSize: 12, color: "var(--text-tertiary)", textAlign: "center" }}>
            Aucune conversation.<br />
            Démarre la première en posant une question.
          </div>
        )}
        {groups.map((g) => {
          const items = conversations.filter((c) => bucket(c.updated_at) === g.key);
          if (!items.length) return null;
          return (
            <div key={g.key} style={{ marginTop: 10 }}>
              <div className="section-label" style={{ padding: "6px 10px" }}>{g.label}</div>
              {items.map((c) => (
                <button
                  key={c.id}
                  onClick={() => onSelect(c.id)}
                  title={c.title}
                  style={{
                    display: "flex", alignItems: "center", gap: 8, width: "100%",
                    minWidth: 0, // critique pour que ellipsis fonctionne dans flex
                    padding: "8px 10px", borderRadius: 7, border: "none",
                    background: active === c.id ? "rgba(255,255,255,0.05)" : "transparent",
                    color: active === c.id ? "var(--text-primary)" : "var(--text-secondary)",
                    cursor: "pointer", fontSize: 12.5, textAlign: "left",
                    // Bug W rapport QA — hauteur fixe pour éviter que le label
                    // truncated soit dans une bulle de 60px à cause de line-height auto
                    height: 34, lineHeight: 1.2,
                    transition: "background .1s ease",
                  }}
                  onMouseEnter={(e) => {
                    if (active !== c.id) e.currentTarget.style.background = "rgba(255,255,255,0.025)";
                  }}
                  onMouseLeave={(e) => {
                    if (active !== c.id) e.currentTarget.style.background = "transparent";
                  }}
                >
                  <Icon
                    name={c.type === "dd" ? "shield" : c.type === "compare" ? "layers" : c.type === "graph" ? "network" : "search"}
                    size={11}
                    color="var(--text-tertiary)"
                  />
                  <span style={{ flex: 1, minWidth: 0, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{c.title}</span>
                  <span style={{ fontSize: 10.5, color: "var(--text-muted)", flexShrink: 0 }}>{relativeTime(c.updated_at)}</span>
                </button>
              ))}
            </div>
          );
        })}
      </div>

      <div style={{ borderTop: "1px solid var(--border-subtle)", padding: "8px 10px", display: "flex", gap: 4 }}>
        <button
          className="dem-btn dem-btn-ghost"
          onClick={() => setSettingsOpen(true)}
          aria-label="Ouvrir les paramètres"
          style={{ flex: 1, justifyContent: "flex-start" }}
        >
          <Icon name="settings" size={12} /> Settings
        </button>
        <button
          className="dem-btn dem-btn-ghost dem-btn-icon"
          onClick={() => setHelpOpen(true)}
          title="Aide"
          aria-label="Ouvrir l'aide"
        >
          <span style={{ fontWeight: 700, fontSize: 11 }}>?</span>
        </button>
      </div>
      {settingsOpen && <SettingsModal onClose={() => setSettingsOpen(false)} />}
      {helpOpen && <HelpModal onClose={() => setHelpOpen(false)} />}
    </div>
  );
}

function SettingsModal({ onClose }: { onClose: () => void }) {
  const [theme, setTheme] = useState<string>(() => {
    if (typeof window === "undefined") return "dark";
    return localStorage.getItem("dem.theme") || "dark";
  });
  const [density, setDensity] = useState<string>(() => {
    if (typeof window === "undefined") return "comfortable";
    return localStorage.getItem("dem.density") || "comfortable";
  });
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") onClose(); };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);
  const save = (k: string, v: string) => { try { localStorage.setItem(k, v); } catch {} };
  return (
    <>
      <div onClick={onClose} className="sheet-backdrop" />
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="settings-title"
        className="dem-glass-2"
        style={{
          position: "fixed", top: "20%", left: "50%", transform: "translateX(-50%)",
          width: 480, zIndex: 100, borderRadius: 12, padding: 22,
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 14 }}>
          <Icon name="settings" size={16} color="var(--accent-purple)" />
          <h2 id="settings-title" style={{ fontSize: 15, fontWeight: 700, margin: 0 }}>Paramètres</h2>
          <button className="dem-btn dem-btn-ghost dem-btn-icon" onClick={onClose} aria-label="Fermer (Esc)" style={{ marginLeft: "auto" }}>×</button>
        </div>
        <div style={{ display: "flex", flexDirection: "column", gap: 18 }}>
          <div>
            <label style={{ display: "block", fontSize: 11.5, color: "var(--text-tertiary)", textTransform: "uppercase", letterSpacing: "0.06em", fontWeight: 600, marginBottom: 6 }}>Thème</label>
            <div style={{ display: "flex", gap: 6 }}>
              {["dark", "light", "auto"].map((t) => (
                <button
                  key={t}
                  onClick={() => { setTheme(t); save("dem.theme", t); }}
                  className={`dem-btn ${theme === t ? "dem-btn-primary" : "dem-btn-ghost"}`}
                  style={{ fontSize: 12 }}
                >{t}</button>
              ))}
            </div>
          </div>
          <div>
            <label style={{ display: "block", fontSize: 11.5, color: "var(--text-tertiary)", textTransform: "uppercase", letterSpacing: "0.06em", fontWeight: 600, marginBottom: 6 }}>Densité d'affichage</label>
            <div style={{ display: "flex", gap: 6 }}>
              {["compact", "comfortable", "spacious"].map((d) => (
                <button
                  key={d}
                  onClick={() => { setDensity(d); save("dem.density", d); }}
                  className={`dem-btn ${density === d ? "dem-btn-primary" : "dem-btn-ghost"}`}
                  style={{ fontSize: 12 }}
                >{d}</button>
              ))}
            </div>
          </div>
          <div style={{ fontSize: 11, color: "var(--text-tertiary)", paddingTop: 8, borderTop: "1px solid var(--border-subtle)" }}>
            Utilisateur : <span style={{ color: "var(--text-secondary)" }}>Anne Dupont</span><br />
            Modèle IA : DeepSeek<br />
            Version : EdRCF 6.0 BETA
          </div>
        </div>
      </div>
    </>
  );
}

function HelpModal({ onClose }: { onClose: () => void }) {
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") onClose(); };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);
  return (
    <>
      <div onClick={onClose} className="sheet-backdrop" />
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="help-title"
        className="dem-glass-2"
        style={{
          position: "fixed", top: "12%", left: "50%", transform: "translateX(-50%)",
          width: 560, maxHeight: "76vh", overflowY: "auto",
          zIndex: 100, borderRadius: 12, padding: 22,
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 14 }}>
          <span style={{ fontSize: 16, fontWeight: 700, color: "var(--accent-purple)" }}>?</span>
          <h2 id="help-title" style={{ fontSize: 15, fontWeight: 700, margin: 0 }}>Aide & raccourcis</h2>
          <button className="dem-btn dem-btn-ghost dem-btn-icon" onClick={onClose} aria-label="Fermer (Esc)" style={{ marginLeft: "auto" }}>×</button>
        </div>
        <h3 style={{ fontSize: 12, color: "var(--accent-purple)", textTransform: "uppercase", letterSpacing: "0.06em", margin: "6px 0" }}>Raccourcis clavier</h3>
        <ul style={{ margin: 0, paddingLeft: 18, fontSize: 13, color: "var(--text-secondary)", lineHeight: 1.6 }}>
          <li><span className="kbd">⌘</span> <span className="kbd">K</span> — Palette de commandes</li>
          <li><span className="kbd">⌘</span> <span className="kbd">N</span> — Nouvelle conversation</li>
          <li><span className="kbd">Esc</span> — Fermer modale / panneau</li>
          <li><span className="kbd">↵</span> — Envoyer message</li>
        </ul>
        <h3 style={{ fontSize: 12, color: "var(--accent-purple)", textTransform: "uppercase", letterSpacing: "0.06em", margin: "14px 0 6px" }}>Commandes slash</h3>
        <ul style={{ margin: 0, paddingLeft: 18, fontSize: 13, color: "var(--text-secondary)", lineHeight: 1.6 }}>
          <li><code>/siren {`<9 chiffres>`}</code> — Recherche directe par SIREN</li>
          <li><code>/compare {`<A>`} {`<B>`}</code> — Comparer 2 cibles</li>
          <li><code>/dd {`<siren>`}</code> — Due diligence rapide</li>
          <li><code>/graph {`<siren>`}</code> — Ouvrir graphe réseau</li>
          <li><code>/save</code> — Sauver la dernière liste</li>
          <li><code>/export</code> — Export CSV / Parquet</li>
          <li><code>/clear</code> — Vider la conversation</li>
        </ul>
        <h3 style={{ fontSize: 12, color: "var(--accent-purple)", textTransform: "uppercase", letterSpacing: "0.06em", margin: "14px 0 6px" }}>Astuces M&A</h3>
        <ul style={{ margin: 0, paddingLeft: 18, fontSize: 13, color: "var(--text-secondary)", lineHeight: 1.6 }}>
          <li>Tape un SIREN seul (9 chiffres) pour ouvrir la fiche directement</li>
          <li>Précise toujours secteur + dépt + tranche CA pour un sourcing efficace</li>
          <li>Utilise le bouton <strong>Pitch Ready</strong> pour générer une fiche PDF</li>
          <li>Sauvegarde tes cibles favorites pour activer la veille auto</li>
        </ul>
      </div>
    </>
  );
}
